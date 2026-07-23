import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from model import (
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    BacktestSummary,
    Candle,
    DayResult,
    DayResultSummary,
    EUMarket,
    Market,
    Strategy,
    Trade,
    UnitTime,
)
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from services.indicator_service import mobile_average, slope_percentage
from utils.exception import SaxoException
from utils.helper import market_in_utc
from utils.logger import Logger

PARIS_TZ = ZoneInfo("Europe/Paris")

# Daily MA50 slope regime measure: MA50 needs 50 daily closes and the
# slope is taken over a 10-candle lookback, so at least 60 prior daily
# candles are required before a day can be scored.
MM50_MIN_DAILY_CANDLES = 60
MM50_SLOPE_LOOKBACK = 10

BACKTEST_DEFINITIONS: List[BacktestDefinition] = [
    BacktestDefinition(
        code="B9H",
        name=Strategy.B9H.value,
        display_name="CAC40 Bougie de 9h",
        instrument="FRA40.I",
    ),
    BacktestDefinition(
        code="B9HTC",
        name=Strategy.B9HTC.value,
        display_name="CAC40 Bougie de 9h (time cut)",
        instrument="FRA40.I",
        time_cut_minutes=30,
        time_cut_min_favorable_points=5.0,
    ),
]

# Candle horizons for the two Saxo fetches. Unlike the strategy
# thresholds (now tunable via BacktestParameters), these describe the
# fixed shape of the "CAC40 Bougie de 9h" setup - a 1-hour reference
# window scanned with 5-minute candles - and are not exposed as
# parameters.
FIVE_MINUTE_HORIZON = 5
H1_HORIZON = 60

# Default thresholds, kept in one place so the free-function unit tests
# and the dataclass agree on what "unparametrized" means.
_DEFAULTS = BacktestParameters()


def _is_valid_long_entry(
    entry_price: float,
    h1_low: float,
    take_profit_level: float,
    max_entry_distance: float = _DEFAULTS.max_entry_distance_points,
) -> bool:
    """A long breakout entry only produces a trade when it still leaves
    room to work: within max_entry_distance points of the H1 low, and
    below the take-profit level (H1 high minus the take-profit offset).
    An entry too far above the low, or already at/above take-profit, is
    not valid - it would exit on the very next candle for little or no
    favorable move despite being labeled a take-profit."""
    return (
        entry_price - h1_low <= max_entry_distance
        and entry_price < take_profit_level
    )


def _is_valid_short_entry(
    entry_price: float,
    h1_high: float,
    take_profit_level: float,
    max_entry_distance: float = _DEFAULTS.max_entry_distance_points,
) -> bool:
    """Mirror of _is_valid_long_entry for the short side: a short
    breakdown entry is only valid when it is within max_entry_distance
    points below the H1 high, and above the take-profit level (H1 low
    plus the take-profit offset)."""
    return (
        h1_high - entry_price <= max_entry_distance
        and entry_price > take_profit_level
    )


def _eu_market_in_utc(trading_date: datetime.date) -> Market:
    reference = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        tzinfo=PARIS_TZ,
    )
    return market_in_utc(EUMarket(), reference)


def paris_reference_window_utc(
    trading_date: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """9:00-10:00 Paris local time for trading_date, as naive UTC bounds."""
    utc_market = _eu_market_in_utc(trading_date)
    start = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.open_hour,
        utc_market.open_minutes,
    )
    end = start + datetime.timedelta(hours=1)
    return (start, end)


def paris_session_end_utc(trading_date: datetime.date) -> datetime.datetime:
    """End of FRA40.I's regular trading session (Euronext Paris close,
    17:30 local, from EUMarket.close_hour/end_minute), as a naive UTC
    datetime."""
    utc_market = _eu_market_in_utc(trading_date)
    return datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.close_hour,
        utc_market.end_minute,
    )


def is_future_paris_date(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    return d > current.date()


def is_today_not_yet_closed(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    """True if d is today (Paris) and the regular session hasn't ended
    yet - the backtest only operates on already-closed historical days,
    and Saxo won't return a complete H1/5-minute series for a session
    still in progress."""
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    if d != current.date():
        return False
    market = EUMarket()
    session_end_local = datetime.datetime(
        d.year,
        d.month,
        d.day,
        market.close_hour,
        market.end_minute,
        tzinfo=PARIS_TZ,
    )
    return current < session_end_local


def _candle_date(candle: Candle) -> datetime.datetime:
    """Candles from get_candles_in_window always carry a date (it is
    part of that method's window filter); raise rather than assert so
    a violation surfaces as a normal exception instead of silently
    passing through under `-O` or crashing with a bare AssertionError."""
    if candle.date is None:
        raise SaxoException(
            "Candle from get_candles_in_window is missing a date"
        )
    return candle.date


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
    ):
        self.direction = direction
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.take_profit_level = take_profit_level
        self.max_entry_distance = max_entry_distance
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

    def __init__(self, candles_service: CandlesService):
        self.logger = Logger.get_logger("backtest_service")
        self.candles_service = candles_service

    def list_definitions(self) -> List[BacktestDefinition]:
        return BACKTEST_DEFINITIONS

    def get_definition(self, code: str) -> Optional[BacktestDefinition]:
        for definition in BACKTEST_DEFINITIONS:
            if definition.code == code:
                return definition
        return None

    def evaluate_day(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> DayResult:
        """Run the "CAC40 Bougie de 9h" rules for a single trading day."""
        params = params or BacktestParameters()
        h1_start_utc, h1_end_utc = paris_reference_window_utc(trading_date)
        h1_candle = self._fetch_h1_reference_candle(
            definition.instrument, h1_start_utc, h1_end_utc
        )
        if h1_candle is None:
            return DayResult(date=trading_date, status=DayStatus.NO_DATA)

        h1_high = h1_candle.higher
        h1_low = h1_candle.lower
        session_end_utc = paris_session_end_utc(trading_date)
        five_min_candles = self._fetch_five_minute_candles(
            definition.instrument, h1_end_utc, session_end_utc
        )
        chronological = sorted(five_min_candles, key=_candle_date)

        trades = self._evaluate_trades(
            chronological, h1_high, h1_low, params, definition
        )

        status = DayStatus.TRADED if trades else DayStatus.NO_TRADE
        return DayResult(
            date=trading_date,
            status=status,
            h1_high=h1_high,
            h1_low=h1_low,
            candles=chronological,
            trades=trades,
        )

    def run_range(
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
            day_result = self.evaluate_day(definition, current, params)
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
                        mm50_slope=self._mm50_slope_before(
                            daily_candles, day_result.date
                        ),
                    )
                )
                all_trades.extend(day_result.trades)
            current += datetime.timedelta(days=1)

        summary = self._build_summary(
            definition, start_date, end_date, all_trades, len(day_summaries)
        )
        return BacktestRunResult(summary=summary, days=day_summaries)

    @staticmethod
    def _build_summary(
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        trades: List[Trade],
        number_of_days: int,
    ) -> BacktestSummary:
        winning: List[Trade] = []
        losing: List[Trade] = []
        be_trades: List[Trade] = []
        for trade in trades:
            if trade.exit_reason == ExitReason.BREAK_EVEN:
                be_trades.append(trade)
            elif trade.points > 0:
                winning.append(trade)
            else:
                losing.append(trade)

        average_win = (
            round(sum(t.points for t in winning) / len(winning), 4)
            if winning
            else None
        )
        average_loss = (
            round(-sum(t.points for t in losing) / len(losing), 4)
            if losing
            else None
        )
        final_result = round(sum(t.points for t in trades), 4)

        return BacktestSummary(
            definition_code=definition.code,
            start_date=start_date,
            end_date=end_date,
            number_of_days=number_of_days,
            number_of_trades=len(trades),
            number_of_winning_positions=len(winning),
            number_of_losing_positions=len(losing),
            number_of_be=len(be_trades),
            average_win=average_win,
            average_loss=average_loss,
            final_result=final_result,
        )

    def _fetch_h1_reference_candle(
        self,
        instrument: str,
        h1_start_utc: datetime.datetime,
        h1_end_utc: datetime.datetime,
    ) -> Optional[Candle]:
        try:
            candles = self.candles_service.get_candles_in_window(
                instrument,
                UnitTime.H1,
                H1_HORIZON,
                h1_start_utc,
                h1_end_utc,
            )
        except SaxoException as e:
            self.logger.warning(
                f"No H1 reference candle for {instrument} on "
                f"{h1_start_utc.date()}: {e}"
            )
            return None
        if not candles:
            return None
        return sorted(candles, key=_candle_date)[0]

    def _fetch_five_minute_candles(
        self,
        instrument: str,
        start_utc: datetime.datetime,
        end_utc: datetime.datetime,
    ) -> List[Candle]:
        try:
            return self.candles_service.get_candles_in_window(
                instrument,
                UnitTime.M5,
                FIVE_MINUTE_HORIZON,
                start_utc,
                end_utc,
            )
        except SaxoException as e:
            self.logger.warning(
                f"No 5-minute candles for {instrument} between "
                f"{start_utc} and {end_utc}: {e}"
            )
            return []

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
        count = (
            (end_date - start_date).days
            + MM50_MIN_DAILY_CANDLES
            + MM50_SLOPE_LOOKBACK
            + 5
        )
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

    @staticmethod
    def _mm50_slope_before(
        daily_candles: List[Candle], trading_date: datetime.date
    ) -> Optional[float]:
        """Daily MA50 slope (%) as of the last close strictly before
        trading_date (lookahead-safe: today's daily candle is never in the
        window). Mirrors the MA50 slope used by the MM50 alert (spec 019).
        Returns None when fewer than MM50_MIN_DAILY_CANDLES prior daily
        candles are available."""
        prior = [
            candle
            for candle in daily_candles
            if candle.date is not None and candle.date.date() < trading_date
        ]
        if len(prior) < MM50_MIN_DAILY_CANDLES:
            return None
        prior.sort(key=_candle_date, reverse=True)
        ma50_last = mobile_average(prior, 50)
        ma50_first = mobile_average(prior[MM50_SLOPE_LOOKBACK:], 50)
        return slope_percentage(0, ma50_first, MM50_SLOPE_LOOKBACK, ma50_last)

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
        long_search = _DirectionSearch(
            Direction.BUY,
            h1_high,
            h1_low,
            long_take_profit,
            params.max_entry_distance_points,
        )
        short_search = _DirectionSearch(
            Direction.SELL,
            h1_high,
            h1_low,
            short_take_profit,
            params.max_entry_distance_points,
        )

        for candle in candles:
            candle_date = _candle_date(candle)
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
                        entry_time=candle_date,
                        entry_price=long_entry,
                        direction=Direction.BUY,
                        take_profit_level=long_take_profit,
                        stop_loss_points=params.stop_loss_points,
                        time_cut_minutes=definition.time_cut_minutes,
                        time_cut_min_favorable_points=(
                            definition.time_cut_min_favorable_points
                        ),
                    )
                elif short_entry is not None:
                    position = _OpenPosition(
                        entry_time=candle_date,
                        entry_price=short_entry,
                        direction=Direction.SELL,
                        take_profit_level=short_take_profit,
                        stop_loss_points=params.stop_loss_points,
                        time_cut_minutes=definition.time_cut_minutes,
                        time_cut_min_favorable_points=(
                            definition.time_cut_min_favorable_points
                        ),
                    )
                if position is not None:
                    long_search.reset()
                    short_search.reset()
                continue

            closed = self._resolve_exit(position, candle, candle_date, params)
            if closed is not None:
                trades.append(closed)
                position = None
                long_search.reset()
                short_search.reset()

        if position is not None and candles:
            last_candle = candles[-1]
            trades.append(
                self._close_trade(
                    position,
                    _candle_date(last_candle),
                    last_candle.close,
                    ExitReason.END_OF_DAY,
                )
            )

        return trades

    def _resolve_exit(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Resolve the exit conditions for an open position on a single
        candle. Checks stop-loss (or break-even) before take-profit
        (FR-009), and only arms the break-even stop when neither exit
        triggered. Returns the closed Trade, or None if the position
        stays open."""
        stop_level = position.stop_level
        take_profit_level = position.take_profit_level

        if position.is_long:
            stop_hit = candle.lower <= stop_level
            take_profit_hit = candle.higher >= take_profit_level
        else:
            stop_hit = candle.higher >= stop_level
            take_profit_hit = candle.lower <= take_profit_level

        if stop_hit:
            if position.is_long:
                exit_price = (
                    candle.open if candle.open <= stop_level else stop_level
                )
            else:
                exit_price = (
                    candle.open if candle.open >= stop_level else stop_level
                )
            reason = (
                ExitReason.BREAK_EVEN
                if position.be_armed
                else ExitReason.STOP_LOSS
            )
            return self._close_trade(position, candle_date, exit_price, reason)

        if take_profit_hit:
            if position.is_long:
                exit_price = (
                    candle.open
                    if candle.open >= take_profit_level
                    else take_profit_level
                )
            else:
                exit_price = (
                    candle.open
                    if candle.open <= take_profit_level
                    else take_profit_level
                )
            return self._close_trade(
                position, candle_date, exit_price, ExitReason.TAKE_PROFIT
            )

        if position.time_cut_enabled:
            time_cut = self._resolve_time_cut(position, candle, candle_date)
            if time_cut is not None:
                return time_cut

        if not position.be_armed:
            arm_threshold = params.break_even_trigger_points
            if position.is_long:
                if candle.higher >= position.entry_price + arm_threshold:
                    position.be_armed = True
            elif candle.lower <= position.entry_price - arm_threshold:
                position.be_armed = True

        return None

    @staticmethod
    def _resolve_time_cut(
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
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
            candle_date >= deadline
            and position.max_favorable_points <= threshold
        ):
            return BacktestService._close_trade(
                position, candle_date, candle.close, ExitReason.TIME_CUT
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
