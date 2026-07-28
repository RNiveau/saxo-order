import datetime
from typing import Dict, List, Optional

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
from api.services.backtest.lots import LotModel, Targets
from api.services.backtest.policies import resolve_exit
from api.services.backtest.position import Position
from api.services.backtest.rules import (
    build_entry_gate,
    build_exit_chain,
    build_lot_model,
)
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
        params = params or definition.default_parameters
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
            chronological,
            h1_high,
            h1_low,
            params,
            definition,
            trading_date,
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
        params = params or definition.default_parameters
        day_summaries: List[DayResultSummary] = []
        all_trades: List[Trade] = []

        daily_candles = self._fetch_daily_candles(
            definition, start_date, end_date
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
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Candle]:
        """Daily (newest-first) candle series covering the run range plus
        enough lead-in to compute a 50-day MA slope on the first day.
        Fetched once per run_range. A failure degrades to an empty series
        (blank mm50_slope column) rather than aborting the whole export.

        Deliberately built on EUMarket rather than definition.market: the
        regime columns (mm50_slope, adx14, overnight_gap) are a
        *measurement* of the instrument, not part of any strategy, and
        they only earn their keep if the same day scores the same on every
        definition. Following the definition's market would build the CFD
        variant's daily bars over a 13-hour window instead of the cash
        session's 9 (build_daily_candles_from_h1 sizes the day from
        close_hour - open_hour), so its MA50 slope and ADX would not be
        comparable with the variants it exists to be compared against, and
        overnight_gap would silently start measuring from the 22:00 close
        instead of the 17:30 one."""
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
                definition.instrument,
                UnitTime.D,
                EUMarket(),
                count,
                reference,
            )
        except SaxoException as e:
            self.logger.warning(
                f"No daily candles for {definition.instrument} "
                f"regime measure: {e}"
            )
            return []

    def _evaluate_trades(
        self,
        candles: List[Candle],
        h1_high: float,
        h1_low: float,
        params: BacktestParameters,
        definition: BacktestDefinition,
        trading_date: datetime.date,
    ) -> List[Trade]:
        """Evaluate both directions concurrently, with at most one
        position open at any time. The H1 high/low reference levels are
        shared: a long trades the reversal off the H1 low, a short the
        reversal off the H1 high. Whichever direction confirms a valid
        breakout first opens the position and holds it until it closes;
        the search for both directions only resumes once flat again."""
        trades: List[Trade] = []
        position: Optional[Position] = None
        chain = build_exit_chain(definition, params)
        lots = build_lot_model(definition)
        gate = build_entry_gate(definition, trading_date)
        # Where each side's take-profits sit. Per side, not once: the
        # extended two-lot model's first target is the ordinary
        # take-profit and so is mirrored between long and short, unlike
        # the H1 midpoint, which is the same level for both.
        targets = {
            side: lots.targets(
                side,
                h1_high,
                h1_low,
                self._take_profit_level(side, h1_high, h1_low, params),
            )
            for side in (LONG, SHORT)
        }

        searches = {
            side: DirectionSearch(
                side,
                h1_high,
                h1_low,
                targets[side].runner,
                params.max_entry_distance_points,
                targets[side].first,
            )
            for side in (LONG, SHORT)
        }

        for candle in candles:
            candle_time = candle_date(candle)
            if position is None:
                # Both sides are fed before either is allowed to open,
                # and the two loops must stay separate: feed() advances a
                # side's breach/candidate state machine, so collapsing
                # this into one loop with an early break would leave the
                # short side unfed on any candle the long side opens on,
                # silently changing what it sees next.
                #
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
                # Checked after feeding, not before: the searches advance
                # on every candle either way, so a gate-blocked entry
                # leaves their state exactly where a confirmed-but-invalid
                # entry does, and there is no second walk that behaves
                # differently late in the day.
                if not gate.allows(candle_time):
                    continue
                for side in (LONG, SHORT):
                    entry_price = entries[side]
                    if entry_price is not None:
                        position = self._open_position(
                            side,
                            candle_time,
                            entry_price,
                            h1_high,
                            h1_low,
                            targets[side],
                            lots,
                            params,
                            definition,
                        )
                        break
                if position is not None:
                    self._reset(searches)
                continue

            closed = resolve_exit(chain, position, candle, candle_time)
            if closed is not None:
                trades.append(closed)
                gate.record(closed)
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
    def _reset(searches: Dict[Side, DirectionSearch]) -> None:
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
        far_level = side.far_level(h1_high, h1_low)
        return far_level - side.sign * params.take_profit_offset_points

    @staticmethod
    def _open_position(
        side: Side,
        candle_time: datetime.datetime,
        entry_price: float,
        h1_high: float,
        h1_low: float,
        targets: Targets,
        lots: LotModel,
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
            take_profit_level=targets.runner,
            stop_loss_points=params.stop_loss_points,
            lots=lots,
            first_target_level=targets.first,
            initial_stop_price=initial_stop_price,
            h1_high=h1_high,
            h1_low=h1_low,
        )
