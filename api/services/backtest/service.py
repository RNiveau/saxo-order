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
from api.services.backtest.entry import DirectionSearch
from api.services.backtest.position import Position
from api.services.backtest.side import LONG, SHORT, Side
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
from model.enum import DayStatus, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException
from utils.logger import Logger


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
        position: Optional[Position] = None

        # TP1 (the H1 midpoint) for double take-profit definitions; None
        # on the single-lot ones, where it is not consulted.
        first_target: Optional[float] = None
        if (
            definition.double_take_profit
            and definition.first_target_fraction is not None
        ):
            first_target = h1_low + definition.first_target_fraction * (
                h1_high - h1_low
            )

        searches = {
            side: DirectionSearch(
                side,
                h1_high,
                h1_low,
                self._take_profit_level(side, h1_high, h1_low, params),
                params.max_entry_distance_points,
                first_target,
            )
            for side in (LONG, SHORT)
        }

        for candle in candles:
            candle_time = candle_date(candle)
            if position is None:
                # One position at a time, either side: whichever direction
                # confirms first opens. On the rare candle that would
                # confirm both (opposing candidates pending, an engulfing
                # candle), the long entry takes precedence as a
                # deterministic tiebreak - hence the fixed LONG, SHORT
                # iteration order.
                entries = {
                    side: search.feed(candle)
                    for side, search in searches.items()
                }
                for side in (LONG, SHORT):
                    entry_price = entries[side]
                    if entry_price is not None:
                        position = self._open_position(
                            side,
                            candle_time,
                            entry_price,
                            h1_high,
                            h1_low,
                            first_target,
                            params,
                            definition,
                        )
                        break
                if position is not None:
                    self._reset(searches)
                continue

            closed = self._resolve_exit(position, candle, candle_time, params)
            if closed is not None:
                trades.append(closed)
                position = None
                self._reset(searches)

        if position is not None and candles:
            last_candle = candles[-1]
            trades.append(
                position.close(
                    candle_date(last_candle),
                    last_candle.close,
                    ExitReason.END_OF_DAY,
                )
            )

        return trades

    @staticmethod
    def _reset(searches) -> None:
        for search in searches.values():
            search.reset()

    @staticmethod
    def _take_profit_level(
        side: Side,
        h1_high: float,
        h1_low: float,
        params: BacktestParameters,
    ) -> float:
        """The take-profit sits inside the far end of the H1 range: the
        H1 high minus the offset for a long, the H1 low plus it for a
        short."""
        far_level = side.reference_level(h1_low, h1_high)
        return far_level - side.sign * params.take_profit_offset_points

    @staticmethod
    def _open_position(
        side: Side,
        candle_time: datetime.datetime,
        entry_price: float,
        h1_high: float,
        h1_low: float,
        first_target: Optional[float],
        params: BacktestParameters,
        definition: BacktestDefinition,
    ) -> Position:
        # A stop measured from the reference level (GER40) sits
        # stop_loss_points beyond the H1 level the side trades off, and is
        # shared by both lots; otherwise the stop is entry-relative and
        # Position derives it itself.
        initial_stop_price: Optional[float] = None
        if definition.stop_from_reference_level:
            initial_stop_price = (
                side.reference_level(h1_high, h1_low)
                - side.sign * params.stop_loss_points
            )
        return Position(
            entry_time=candle_time,
            entry_price=entry_price,
            side=side,
            take_profit_level=BacktestService._take_profit_level(
                side, h1_high, h1_low, params
            ),
            stop_loss_points=params.stop_loss_points,
            time_cut_minutes=definition.time_cut_minutes,
            time_cut_min_favorable_points=(
                definition.time_cut_min_favorable_points
            ),
            double=definition.double_take_profit,
            first_target_level=first_target,
            initial_stop_price=initial_stop_price,
            h1_high=h1_high,
            h1_low=h1_low,
            structural_stop=definition.structural_stop,
        )

    def _resolve_exit(
        self,
        position: Position,
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
        side = position.side

        if side.receded(position.stop_level, candle):
            return self._stop_exit(position, candle, candle_time)

        if side.reached(position.take_profit_level, candle):
            return self._take_profit_exit(position, candle, candle_time)

        if position.time_cut_enabled:
            time_cut = self._resolve_time_cut(position, candle, candle_time)
            if time_cut is not None:
                return time_cut

        self._arm_break_even(position, candle, params)
        return None

    def _resolve_exit_double(
        self,
        position: Position,
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
        side = position.side
        first_target = position.first_target_level

        if side.receded(position.stop_level, candle):
            return self._stop_exit(position, candle, candle_time)

        tp2_hit = side.reached(position.take_profit_level, candle)

        if (
            not position.first_target_taken
            and first_target is not None
            and side.reached(first_target, candle)
        ):
            tp1_fill = side.target_fill(first_target, candle)
            position.banked_points += side.favorable(
                tp1_fill, position.entry_price
            )
            position.first_target_taken = True
            position.be_armed = True
            if tp2_hit:
                return self._take_profit_exit(position, candle, candle_time)
            return None

        if position.first_target_taken and tp2_hit:
            return self._take_profit_exit(position, candle, candle_time)

        self._arm_break_even(position, candle, params)
        return None

    def _resolve_structural_exit(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Exit resolution for the wide-range structural-stop variant while
        break-even is unarmed (FR-034/FR-035). Take-profit is reached
        intrabar (before the candle's close), so it is resolved first; the
        structural stop then fires when the candle *closes* beyond the H1
        level on the losing side, filling at that close with a stop-loss
        reason (no gap-fill - it is a market/close exit). Break-even arms as
        usual; once armed, _resolve_exit routes to the base logic instead."""
        side = position.side
        if side.reached(position.take_profit_level, candle):
            return self._take_profit_exit(position, candle, candle_time)

        level = position.structural_level
        if level is not None and side.closed_beyond(level, candle):
            return position.close(
                candle_time, candle.close, ExitReason.STOP_LOSS
            )

        self._arm_break_even(position, candle, params)
        return None

    @staticmethod
    def _stop_exit(
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Trade:
        """Close a position at its stop, applying the FR-010 gap-fill
        convention. An armed break-even stop is reported as such."""
        exit_price = position.side.stop_fill(position.stop_level, candle)
        reason = (
            ExitReason.BREAK_EVEN
            if position.be_armed
            else ExitReason.STOP_LOSS
        )
        return position.close(candle_time, exit_price, reason)

    @staticmethod
    def _take_profit_exit(
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Trade:
        """Close a position at take-profit, applying the FR-010 gap-fill
        convention (fill at the candle open when it gapped past the
        level)."""
        exit_price = position.side.target_fill(
            position.take_profit_level, candle
        )
        return position.close(candle_time, exit_price, ExitReason.TAKE_PROFIT)

    @staticmethod
    def _arm_break_even(
        position: Position,
        candle: Candle,
        params: BacktestParameters,
    ) -> None:
        """Arm the break-even stop the first time a candle reaches entry
        plus the break-even trigger in the position's favor (FR-008a);
        takes effect on later candles."""
        if position.be_armed:
            return
        arm_level = position.break_even_arm_level(
            params.break_even_trigger_points
        )
        if position.side.reached(arm_level, candle):
            position.be_armed = True

    @staticmethod
    def _resolve_time_cut(
        position: Position,
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

        favorable = position.side.favorable(
            position.side.extreme(candle), position.entry_price
        )
        if favorable > position.max_favorable_points:
            position.max_favorable_points = favorable

        deadline = position.entry_time + datetime.timedelta(minutes=minutes)
        if (
            candle_time >= deadline
            and position.max_favorable_points <= threshold
        ):
            return position.close(
                candle_time, candle.close, ExitReason.TIME_CUT
            )
        return None
