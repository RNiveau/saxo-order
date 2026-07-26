import datetime
from typing import List, Optional

from api.services.backtest.analytics import (
    DAILY_CANDLES_LEAD_IN,
    adx_before,
    mm50_slope_before,
    overnight_gap,
)
from api.services.backtest.calendar import PARIS_TZ
from api.services.backtest.candle_source import CandleSource
from api.services.backtest.candles import candle_date
from api.services.backtest.definitions import (
    get_definition,
    is_below_min_range,
    list_definitions,
)
from api.services.backtest.statistics import build_summary
from client.aws_client import DynamoDBClient
from model import (
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    Candle,
    DayResult,
    DayResultSummary,
    EUMarket,
    Trade,
    UnitTime,
)
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException
from utils.logger import Logger

# Default thresholds, kept in one place so the free-function unit tests
# and the dataclass agree on what "unparametrized" means.
_DEFAULTS = BacktestParameters()


def _is_valid_long_entry(
    entry_price: float,
    h1_low: float,
    take_profit_level: float,
    max_entry_distance: float = _DEFAULTS.max_entry_distance_points,
    first_target: Optional[float] = None,
) -> bool:
    """A long breakout entry only produces a trade when it still leaves
    room to work: within max_entry_distance points of the H1 low, and
    below the take-profit level (H1 high minus the take-profit offset).
    An entry too far above the low, or already at/above take-profit, is
    not valid - it would exit on the very next candle for little or no
    favorable move despite being labeled a take-profit.

    For a double take-profit setup, first_target (the H1 midpoint, TP1)
    is also required to sit strictly above the entry: on a narrow H1
    range an otherwise-valid entry (within max_entry_distance of the low)
    can open past the midpoint, which would fire TP1 immediately, bank a
    loss as a take-profit, and discard the structural stop - so such an
    entry is rejected, mirroring the take_profit_level guard."""
    valid = (
        entry_price - h1_low <= max_entry_distance
        and entry_price < take_profit_level
    )
    if first_target is not None:
        valid = valid and entry_price < first_target
    return valid


def _is_valid_short_entry(
    entry_price: float,
    h1_high: float,
    take_profit_level: float,
    max_entry_distance: float = _DEFAULTS.max_entry_distance_points,
    first_target: Optional[float] = None,
) -> bool:
    """Mirror of _is_valid_long_entry for the short side: a short
    breakdown entry is only valid when it is within max_entry_distance
    points below the H1 high, and above the take-profit level (H1 low
    plus the take-profit offset). For a double take-profit setup,
    first_target (TP1) must also sit strictly below the entry."""
    valid = (
        h1_high - entry_price <= max_entry_distance
        and entry_price > take_profit_level
    )
    if first_target is not None:
        valid = valid and entry_price > first_target
    return valid


class _OpenPosition:
    def __init__(
        self,
        entry_time: datetime.datetime,
        entry_price: float,
        direction: Direction,
        take_profit_level: float,
        stop_loss_points: float,
        time_cut_minutes: Optional[int] = None,
        time_cut_min_favorable_points: Optional[float] = None,
        double: bool = False,
        first_target_level: Optional[float] = None,
        initial_stop_price: Optional[float] = None,
        h1_high: Optional[float] = None,
        h1_low: Optional[float] = None,
        structural_stop: bool = False,
    ):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction
        self.take_profit_level = take_profit_level
        self.stop_loss_points = stop_loss_points
        self.be_armed = False
        self.time_cut_minutes = time_cut_minutes
        self.time_cut_min_favorable_points = time_cut_min_favorable_points
        self.max_favorable_points = 0.0
        # Double take-profit / two-lot state (GER40). double gates the
        # split-exit path; first_target_level is TP1 (H1 midpoint); once
        # the first lot fills, first_target_taken flips and banked_points
        # holds lot A's realised P&L, added to the runner's leg at close.
        self.double = double
        self.first_target_level = first_target_level
        self.first_target_taken = False
        self.banked_points = 0.0
        # Absolute initial stop level. When set (GER40, stop measured from
        # the H1 reference level) it overrides the entry-relative stop; both
        # lots share it until break-even moves the stop to entry.
        self.initial_stop_price = initial_stop_price
        # Wide-range structural-stop variant (spec 021, US1d): the H1
        # reference levels and the flag enabling the close-beyond-level stop.
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.structural_stop = structural_stop

    @property
    def time_cut_enabled(self) -> bool:
        return (
            self.time_cut_minutes is not None
            and self.time_cut_min_favorable_points is not None
        )

    @property
    def is_long(self) -> bool:
        return self.direction == Direction.BUY

    @property
    def stop_level(self) -> float:
        if self.be_armed:
            return self.entry_price
        if self.initial_stop_price is not None:
            return self.initial_stop_price
        if self.is_long:
            return self.entry_price - self.stop_loss_points
        return self.entry_price + self.stop_loss_points


class _DirectionSearch:
    """Tracks the breakout/reversal candidate search for a single
    direction while no position is open.

    LONG watches for a candle closing below the H1 low, then a reversal
    candle closing back at/above it, confirmed by a later candle trading
    above that reversal candle's high. SHORT is the mirror image around
    the H1 high: a candle closing above the high, a reversal candle
    closing back at/below it, confirmed by a later candle trading below
    that candle's low. The breach is measured on the close (a confirmed
    candle outside the H1 range), not an intrabar wick. The two
    directions are searched independently and concurrently; the engine
    (see _evaluate_trades) enforces that only one may open a position at
    a time.
    """

    def __init__(
        self,
        direction: Direction,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
        max_entry_distance: float,
        first_target_level: Optional[float] = None,
    ):
        self.direction = direction
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.take_profit_level = take_profit_level
        self.max_entry_distance = max_entry_distance
        # TP1 (H1 midpoint) for double take-profit definitions; None for
        # single-lot ones. When set, a valid entry must sit on the
        # favorable side of it (see _is_valid_long_entry / _short).
        self.first_target_level = first_target_level
        self.breached = False
        self.candidate: Optional[Candle] = None

    @property
    def is_long(self) -> bool:
        return self.direction == Direction.BUY

    def reset(self) -> None:
        self.breached = False
        self.candidate = None

    def feed(self, candle: Candle) -> Optional[float]:
        """Advance the search by one candle. Returns a valid entry price
        when this candle confirms a tradeable breakout, otherwise None
        (updating the internal breach/candidate state)."""
        if self.is_long:
            return self._feed_long(candle)
        return self._feed_short(candle)

    def _feed_long(self, candle: Candle) -> Optional[float]:
        if self.candidate is None:
            if not self.breached:
                if candle.close < self.h1_low:
                    self.breached = True
                return None
            if candle.close >= self.h1_low:
                self.candidate = candle
                self.breached = False
            return None

        # candidate is the reversal candle awaiting breakout
        # confirmation: only a later candle trading above its high
        # confirms the reversal has momentum.
        if candle.higher > self.candidate.higher:
            entry_price = max(self.candidate.higher, candle.open)
            self.candidate = None
            if _is_valid_long_entry(
                entry_price,
                self.h1_low,
                self.take_profit_level,
                self.max_entry_distance,
                self.first_target_level,
            ):
                return entry_price
            return None
        if candle.close < self.h1_low:
            self.candidate = None
            self.breached = True
            return None
        self.candidate = candle
        return None

    def _feed_short(self, candle: Candle) -> Optional[float]:
        if self.candidate is None:
            if not self.breached:
                if candle.close > self.h1_high:
                    self.breached = True
                return None
            if candle.close <= self.h1_high:
                self.candidate = candle
                self.breached = False
            return None

        # mirror of _feed_long: a later candle trading below the
        # reversal candle's low confirms the downside breakout.
        if candle.lower < self.candidate.lower:
            entry_price = min(self.candidate.lower, candle.open)
            self.candidate = None
            if _is_valid_short_entry(
                entry_price,
                self.h1_high,
                self.take_profit_level,
                self.max_entry_distance,
                self.first_target_level,
            ):
                return entry_price
            return None
        if candle.close > self.h1_high:
            self.candidate = None
            self.breached = True
            return None
        self.candidate = candle
        return None


class BacktestService:
    """Runs the hardcoded backtests exposed by the Backtest menu."""

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
    ):
        self.logger = Logger.get_logger("backtest_service")
        self.candles_service = candles_service
        self.dynamodb_client = dynamodb_client
        self.candle_source = CandleSource(
            candles_service, dynamodb_client, self.logger
        )

    def list_definitions(self) -> List[BacktestDefinition]:
        return list_definitions()

    def get_definition(self, code: str) -> Optional[BacktestDefinition]:
        return get_definition(code)

    async def evaluate_day(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> DayResult:
        """Run the day's strategy rules against its candles.

        The candles come from the raw-candle cache when available and from
        Saxo otherwise (see CandleSource); the strategy evaluation always
        runs fresh against them, cached or not (FR-039)."""
        params = params or BacktestParameters()
        day = await self.candle_source.day_candles(definition, trading_date)
        if day is None or day.h1_candle is None:
            return DayResult(date=trading_date, status=DayStatus.NO_DATA)
        return self._evaluate_from_candles(
            definition,
            trading_date,
            params,
            day.h1_candle,
            day.m5_candles,
        )

    def _evaluate_from_candles(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: BacktestParameters,
        h1_candle: Candle,
        five_min_candles: List[Candle],
    ) -> DayResult:
        """Shared tail of evaluate_day once the day's H1/5-minute candles
        are known, whether from the cache or a fresh Saxo fetch: applies
        the wide-range filter (FR-033) then runs the strategy. Pure/no
        I/O, so it's reused unchanged by both the cache-hit and
        cache-miss paths."""
        h1_high = h1_candle.higher
        h1_low = h1_candle.lower
        if is_below_min_range(definition, h1_high, h1_low):
            return DayResult(
                date=trading_date,
                status=DayStatus.NO_TRADE,
                h1_high=h1_high,
                h1_low=h1_low,
                h1_open=h1_candle.open,
            )

        chronological = sorted(five_min_candles, key=candle_date)
        trades = self._evaluate_trades(
            chronological, h1_high, h1_low, params, definition
        )

        status = DayStatus.TRADED if trades else DayStatus.NO_TRADE
        return DayResult(
            date=trading_date,
            status=status,
            h1_high=h1_high,
            h1_low=h1_low,
            h1_open=h1_candle.open,
            candles=chronological,
            trades=trades,
        )

    async def run_range(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> BacktestRunResult:
        """Run the backtest across every day in [start_date, end_date]."""
        params = params or BacktestParameters()
        day_summaries: List[DayResultSummary] = []
        all_trades: List[Trade] = []

        daily_candles = self._fetch_daily_candles(
            definition.instrument, start_date, end_date
        )

        current = start_date
        while current <= end_date:
            if current.weekday() >= 5:
                # Saturday/Sunday: FRA40.I never trades, so skip the
                # H1/5-minute fetches that would only resolve to
                # NO_DATA - avoids two wasted Saxo calls per weekend day.
                current += datetime.timedelta(days=1)
                continue
            day_result = await self.evaluate_day(definition, current, params)
            if day_result.status != DayStatus.NO_DATA:
                day_points = round(
                    sum(trade.points for trade in day_result.trades), 4
                )
                day_summaries.append(
                    DayResultSummary(
                        date=day_result.date,
                        status=day_result.status,
                        trade_count=len(day_result.trades),
                        points=day_points,
                        h1_high=day_result.h1_high,
                        h1_low=day_result.h1_low,
                        mm50_slope=mm50_slope_before(
                            daily_candles, day_result.date
                        ),
                        adx14=adx_before(daily_candles, day_result.date),
                        h1_open=day_result.h1_open,
                        overnight_gap=overnight_gap(
                            daily_candles,
                            day_result.date,
                            day_result.h1_open,
                        ),
                    )
                )
                all_trades.extend(day_result.trades)
            current += datetime.timedelta(days=1)

        summary = build_summary(
            definition, start_date, end_date, all_trades, len(day_summaries)
        )
        return BacktestRunResult(summary=summary, days=day_summaries)

    def _fetch_daily_candles(
        self,
        instrument: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Candle]:
        """Daily (newest-first) candle series covering the run range plus
        enough lead-in to compute a 50-day MA slope on the first day.
        Fetched once per run_range. A failure degrades to an empty series
        (blank mm50_slope column) rather than aborting the whole export."""
        # Daily candles are fetched counting backward from end_date, so
        # count must reach ~60 trading days before start_date for the
        # first day's MA50 slope. Calendar days is a safe upper bound on
        # the range's trading days (build_candles caps at available data),
        # so no need to exclude weekends/holidays precisely.
        count = (end_date - start_date).days + DAILY_CANDLES_LEAD_IN
        reference = datetime.datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=PARIS_TZ
        )
        try:
            return self.candles_service.build_candles(
                instrument, UnitTime.D, EUMarket(), count, reference
            )
        except SaxoException as e:
            self.logger.warning(
                f"No daily candles for {instrument} regime measure: {e}"
            )
            return []

    def _evaluate_trades(
        self,
        candles: List[Candle],
        h1_high: float,
        h1_low: float,
        params: BacktestParameters,
        definition: BacktestDefinition,
    ) -> List[Trade]:
        """Evaluate both directions concurrently, with at most one
        position open at any time. The H1 high/low reference levels are
        shared: a long trades the reversal off the H1 low, a short the
        reversal off the H1 high. Whichever direction confirms a valid
        breakout first opens the position and holds it until it closes;
        the search for both directions only resumes once flat again."""
        trades: List[Trade] = []
        position: Optional[_OpenPosition] = None
        long_take_profit = h1_high - params.take_profit_offset_points
        short_take_profit = h1_low + params.take_profit_offset_points

        # Double take-profit / two-lot setup (GER40). first_target is the
        # H1 midpoint (TP1); the stop, when measured from the reference
        # level, sits stop_loss_points beyond the H1 low/high (shared by
        # both lots). Both stay None on the single-lot CAC40 backtests.
        double = definition.double_take_profit
        first_target: Optional[float] = None
        if double and definition.first_target_fraction is not None:
            first_target = h1_low + definition.first_target_fraction * (
                h1_high - h1_low
            )
        long_stop_price: Optional[float] = None
        short_stop_price: Optional[float] = None
        if definition.stop_from_reference_level:
            long_stop_price = h1_low - params.stop_loss_points
            short_stop_price = h1_high + params.stop_loss_points

        long_search = _DirectionSearch(
            Direction.BUY,
            h1_high,
            h1_low,
            long_take_profit,
            params.max_entry_distance_points,
            first_target,
        )
        short_search = _DirectionSearch(
            Direction.SELL,
            h1_high,
            h1_low,
            short_take_profit,
            params.max_entry_distance_points,
            first_target,
        )

        for candle in candles:
            candle_time = candle_date(candle)
            if position is None:
                long_entry = long_search.feed(candle)
                short_entry = short_search.feed(candle)
                # One position at a time, either side: whichever
                # direction confirms first opens. On the rare candle
                # that would confirm both (opposing candidates pending,
                # an engulfing candle), the long entry takes precedence
                # as a deterministic tiebreak.
                if long_entry is not None:
                    position = _OpenPosition(
                        entry_time=candle_time,
                        entry_price=long_entry,
                        direction=Direction.BUY,
                        take_profit_level=long_take_profit,
                        stop_loss_points=params.stop_loss_points,
                        time_cut_minutes=definition.time_cut_minutes,
                        time_cut_min_favorable_points=(
                            definition.time_cut_min_favorable_points
                        ),
                        double=double,
                        first_target_level=first_target,
                        initial_stop_price=long_stop_price,
                        h1_high=h1_high,
                        h1_low=h1_low,
                        structural_stop=definition.structural_stop,
                    )
                elif short_entry is not None:
                    position = _OpenPosition(
                        entry_time=candle_time,
                        entry_price=short_entry,
                        direction=Direction.SELL,
                        take_profit_level=short_take_profit,
                        stop_loss_points=params.stop_loss_points,
                        time_cut_minutes=definition.time_cut_minutes,
                        time_cut_min_favorable_points=(
                            definition.time_cut_min_favorable_points
                        ),
                        double=double,
                        first_target_level=first_target,
                        initial_stop_price=short_stop_price,
                        h1_high=h1_high,
                        h1_low=h1_low,
                        structural_stop=definition.structural_stop,
                    )
                if position is not None:
                    long_search.reset()
                    short_search.reset()
                continue

            closed = self._resolve_exit(position, candle, candle_time, params)
            if closed is not None:
                trades.append(closed)
                position = None
                long_search.reset()
                short_search.reset()

        if position is not None and candles:
            last_candle = candles[-1]
            close = (
                self._close_double_trade
                if position.double
                else self._close_trade
            )
            trades.append(
                close(
                    position,
                    candle_date(last_candle),
                    last_candle.close,
                    ExitReason.END_OF_DAY,
                )
            )

        return trades

    def _resolve_exit(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_time: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Resolve the exit conditions for an open position on a single
        candle. Checks stop-loss (or break-even) before take-profit
        (FR-009), and only arms the break-even stop when neither exit
        triggered. Returns the closed Trade, or None if the position
        stays open."""
        if position.double:
            return self._resolve_exit_double(
                position, candle, candle_time, params
            )
        if position.structural_stop and not position.be_armed:
            return self._resolve_structural_exit(
                position, candle, candle_time, params
            )
        stop_level = position.stop_level
        take_profit_level = position.take_profit_level

        if position.is_long:
            stop_hit = candle.lower <= stop_level
            take_profit_hit = candle.higher >= take_profit_level
        else:
            stop_hit = candle.higher >= stop_level
            take_profit_hit = candle.lower <= take_profit_level

        if stop_hit:
            exit_price = self._stop_fill(position, candle, stop_level)
            reason = (
                ExitReason.BREAK_EVEN
                if position.be_armed
                else ExitReason.STOP_LOSS
            )
            return self._close_trade(position, candle_time, exit_price, reason)

        if take_profit_hit:
            return self._take_profit_exit(position, candle, candle_time)

        if position.time_cut_enabled:
            time_cut = self._resolve_time_cut(position, candle, candle_time)
            if time_cut is not None:
                return time_cut

        self._arm_break_even(position, candle, params)
        return None

    def _resolve_exit_double(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_time: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Exit resolution for a two-lot / double-take-profit position
        (GER40). While both lots are open they share one stop; a stop hit
        closes both (the "SL is x2" loss). The first lot takes profit at
        the H1 midpoint (TP1); when it fills, the runner's stop moves to
        break-even and the runner then targets the full take-profit (TP2)
        or that break-even stop. Stop is checked before take-profit on the
        same candle (conservative, FR-009/FR-G05)."""
        stop_level = position.stop_level
        first_target = position.first_target_level

        if position.is_long:
            stop_hit = candle.lower <= stop_level
            tp1_hit = (
                first_target is not None and candle.higher >= first_target
            )
            tp2_hit = candle.higher >= position.take_profit_level
        else:
            stop_hit = candle.higher >= stop_level
            tp1_hit = first_target is not None and candle.lower <= first_target
            tp2_hit = candle.lower <= position.take_profit_level

        if stop_hit:
            exit_price = self._stop_fill(position, candle, stop_level)
            reason = (
                ExitReason.BREAK_EVEN
                if position.be_armed
                else ExitReason.STOP_LOSS
            )
            return self._close_double_trade(
                position, candle_time, exit_price, reason
            )

        if (
            not position.first_target_taken
            and tp1_hit
            and first_target is not None
        ):
            tp1_fill = self._target_fill(position, candle, first_target)
            leg = (
                tp1_fill - position.entry_price
                if position.is_long
                else position.entry_price - tp1_fill
            )
            position.banked_points += leg
            position.first_target_taken = True
            position.be_armed = True
            if tp2_hit:
                tp2_fill = self._target_fill(
                    position, candle, position.take_profit_level
                )
                return self._close_double_trade(
                    position, candle_time, tp2_fill, ExitReason.TAKE_PROFIT
                )
            return None

        if position.first_target_taken and tp2_hit:
            tp2_fill = self._target_fill(
                position, candle, position.take_profit_level
            )
            return self._close_double_trade(
                position, candle_time, tp2_fill, ExitReason.TAKE_PROFIT
            )

        self._arm_break_even(position, candle, params)
        return None

    def _resolve_structural_exit(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_time: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Exit resolution for the wide-range structural-stop variant while
        break-even is unarmed (FR-034/FR-035). Take-profit is reached
        intrabar (before the candle's close), so it is resolved first; the
        structural stop then fires when the candle *closes* beyond the H1
        level on the losing side (below the H1 low for a long, above the H1
        high for a short), filling at that close with a stop-loss reason (no
        gap-fill - it is a market/close exit). Break-even arms as usual;
        once armed, _resolve_exit routes to the base logic instead."""
        if position.is_long:
            take_profit_hit = candle.higher >= position.take_profit_level
        else:
            take_profit_hit = candle.lower <= position.take_profit_level
        if take_profit_hit:
            return self._take_profit_exit(position, candle, candle_time)

        if position.is_long:
            structural_hit = (
                position.h1_low is not None and candle.close < position.h1_low
            )
        else:
            structural_hit = (
                position.h1_high is not None
                and candle.close > position.h1_high
            )
        if structural_hit:
            return self._close_trade(
                position, candle_time, candle.close, ExitReason.STOP_LOSS
            )

        self._arm_break_even(position, candle, params)
        return None

    @staticmethod
    def _take_profit_exit(
        position: _OpenPosition,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Trade:
        """Close a position at take-profit, applying the FR-010 gap-fill
        convention (fill at the candle open when it gapped past the level)."""
        exit_price = BacktestService._target_fill(
            position, candle, position.take_profit_level
        )
        return BacktestService._close_trade(
            position, candle_time, exit_price, ExitReason.TAKE_PROFIT
        )

    @staticmethod
    def _arm_break_even(
        position: _OpenPosition,
        candle: Candle,
        params: BacktestParameters,
    ) -> None:
        """Arm the break-even stop the first time a candle reaches entry ±
        the break-even trigger (FR-008a); takes effect on later candles."""
        if position.be_armed:
            return
        arm_threshold = params.break_even_trigger_points
        if position.is_long:
            if candle.higher >= position.entry_price + arm_threshold:
                position.be_armed = True
        elif candle.lower <= position.entry_price - arm_threshold:
            position.be_armed = True

    @staticmethod
    def _stop_fill(
        position: _OpenPosition, candle: Candle, level: float
    ) -> float:
        """Gap-fill for a stop-type exit: the candle open when it gapped
        through the level, else the level itself (FR-010)."""
        if position.is_long:
            return candle.open if candle.open <= level else level
        return candle.open if candle.open >= level else level

    @staticmethod
    def _target_fill(
        position: _OpenPosition, candle: Candle, level: float
    ) -> float:
        """Gap-fill for a take-profit-type exit (mirror of _stop_fill),
        for an arbitrary target level (TP1 midpoint or the full TP)."""
        if position.is_long:
            return candle.open if candle.open >= level else level
        return candle.open if candle.open <= level else level

    @staticmethod
    def _resolve_time_cut(
        position: _OpenPosition,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        """Time-based cut for the "Bougie de 9h (time cut)" variant.

        Tracks the position's max favorable excursion candle by candle.
        Once time_cut_minutes have elapsed since entry, if the trade has
        never moved more than time_cut_min_favorable_points in its favor,
        it is closed at market (this candle's close). "Never been higher
        than N points" means the cut also fires when the best move was
        exactly N points, so the comparison is <=.
        """
        threshold = position.time_cut_min_favorable_points
        minutes = position.time_cut_minutes
        if threshold is None or minutes is None:
            return None

        favorable = (
            candle.higher - position.entry_price
            if position.is_long
            else position.entry_price - candle.lower
        )
        if favorable > position.max_favorable_points:
            position.max_favorable_points = favorable

        deadline = position.entry_time + datetime.timedelta(minutes=minutes)
        if (
            candle_time >= deadline
            and position.max_favorable_points <= threshold
        ):
            return BacktestService._close_trade(
                position, candle_time, candle.close, ExitReason.TIME_CUT
            )
        return None

    @staticmethod
    def _close_trade(
        position: _OpenPosition,
        exit_time: datetime.datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        if position.is_long:
            points = exit_price - position.entry_price
        else:
            points = position.entry_price - exit_price
        return Trade(
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            direction=position.direction,
            points=round(points, 4),
        )

    @staticmethod
    def _close_double_trade(
        position: _OpenPosition,
        exit_time: datetime.datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        """Aggregate a two-lot position into one Trade whose points is the
        sum of both lots (FR-G07). Before the first lot takes profit both
        lots exit at exit_price (2x the leg - the "SL is x2" loss);
        afterwards only the runner remains, added to the first lot's
        banked points. exit_price/exit_reason reflect the runner's final
        exit, so points need not equal exit_price - entry_price here."""
        leg = (
            exit_price - position.entry_price
            if position.is_long
            else position.entry_price - exit_price
        )
        if position.first_target_taken:
            points = position.banked_points + leg
        else:
            points = 2 * leg
        return Trade(
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            direction=position.direction,
            points=round(points, 4),
        )
