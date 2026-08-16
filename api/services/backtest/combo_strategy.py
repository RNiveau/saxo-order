"""The combo backtests' engine (spec 026).

One walk over one continuous candle series. While flat it asks the
indicator for an entry; while in a position it re-reads the two targets
from the current candle and runs the exit chain. There is no day
boundary in here at all - a position opened on Tuesday is still the same
object on Friday (FR-C11), and only the run's end forces it closed
(FR-C12).

What it does *not* do is as much the point: no reference range, no entry
gate, no end-of-day close, and no exit rule of its own. Stop, TP1, TP2,
break-even on TP1 and the two-lot accounting all come from the policies
and lot models the session backtests already use.
"""

import datetime
from typing import Dict, List, Optional

from api.services.backtest.analytics import (
    DAILY_CANDLES_LEAD_IN,
    adx_before,
    mm50_slope_before,
)
from api.services.backtest.bands import (
    BandLevels,
    levels,
    levels_or_raise,
)
from api.services.backtest.calendar import PARIS_TZ
from api.services.backtest.candles import candle_date
from api.services.backtest.combo_candle_source import (
    WARM_UP_CANDLES,
    ComboCandleSource,
)
from api.services.backtest.lots import ComboTwoLot
from api.services.backtest.policies import resolve_exit
from api.services.backtest.position import Position
from api.services.backtest.rules import build_exit_chain
from api.services.backtest.signals import ComboEntrySearch, Entry
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

# How many candles of history each combo evaluation sees. Bounded so the
# cost per candle stays flat over a long run, and equal to the warm-up so
# every evaluated candle is scored against the same amount of history -
# including the first one of the run.
EVALUATION_WINDOW = WARM_UP_CANDLES


class ComboStrategy:
    """Runs the indicator-driven backtests over a continuous series."""

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
    ):
        self.logger = Logger.get_logger("backtest_combo")
        self.candles_service = candles_service
        self.candle_source = ComboCandleSource(
            candles_service, dynamodb_client, self.logger
        )

    async def evaluate_day(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> DayResult:
        """A single day, which for this strategy is a one-day range run.

        A position still open when the day ends is force-closed as
        END_OF_RUN, exactly as it would be at the end of any range - so
        this view can differ from a longer run's, which is the caveat
        FR-C12 already carries.
        """
        params = params or definition.default_parameters
        series = await self.candle_source.series(
            definition, trading_date, trading_date
        )
        if not series:
            return DayResult(date=trading_date, status=DayStatus.NO_DATA)

        trades = self._run(definition, params, series, trading_date)
        day_candles = [
            candle
            for candle in series
            if candle_date(candle).date() == trading_date
        ]
        day_trades = [
            trade
            for trade in trades
            if trade.entry_time.date() == trading_date
        ]
        return DayResult(
            date=trading_date,
            status=DayStatus.TRADED if day_trades else DayStatus.NO_TRADE,
            candles=day_candles,
            trades=day_trades,
        )

    async def run_range(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> BacktestRunResult:
        params = params or definition.default_parameters
        series = await self.candle_source.series(
            definition, start_date, end_date
        )
        trades = self._run(definition, params, series, start_date)

        daily_candles = self._fetch_daily_candles(
            definition, start_date, end_date
        )
        day_summaries = self._day_summaries(
            series, trades, start_date, end_date, daily_candles
        )
        summary = build_summary(
            definition, start_date, end_date, trades, len(day_summaries)
        )
        return BacktestRunResult(summary=summary, days=day_summaries)

    def _run(
        self,
        definition: BacktestDefinition,
        params: BacktestParameters,
        series: List[Candle],
        start_date: datetime.date,
    ) -> List[Trade]:
        """One pass over the series, oldest candle first.

        The series opens with the warm-up lead-in, which exists to give
        the indicator its history and nothing else: those candles feed
        the entry search but may not open a position. Without that gate
        the run reports P&L from trades entered before the range the
        caller asked for - and the total would shift whenever
        WARM_UP_CANDLES was retuned, since where the boundary lands
        decides how many such trades there are.

        The two halves never interleave: a candle either manages the open
        position or feeds the entry search, because a signal arriving
        while a position is open is ignored outright (FR-C09). That is
        also why `combo` is not evaluated at all while in a trade - the
        single biggest saving on the 5-minute timeframe, and
        behavior-preserving rather than an approximation.
        """
        chain = build_exit_chain(definition, params)
        search = ComboEntrySearch()
        position: Optional[Position] = None
        trades: List[Trade] = []

        for index, candle in enumerate(series):
            window = self._window(series, index)
            candle_time = candle_date(candle)

            if position is not None:
                band_levels = levels_or_raise(window)
                position.retarget(
                    band_levels.mm20, band_levels.opposite(position.side)
                )
                closed = resolve_exit(chain, position, candle, candle_time)
                if closed is not None:
                    trades.append(closed)
                    position = None
                    search.reset()
                continue

            entry = search.feed(candle, window)
            if entry is None or candle_time.date() < start_date:
                continue
            entry_levels = levels(window)
            if entry_levels is None:
                # Still inside the warm-up: the targets this entry would
                # be managed against do not exist yet (FR-C13).
                continue
            position = self._open(entry, candle_time, entry_levels, params)

        if position is not None and series:
            last = series[-1]
            trades.append(
                position.close(
                    candle_date(last), last.close, ExitReason.END_OF_RUN
                )
            )
        return trades

    @staticmethod
    def _window(series: List[Candle], index: int) -> List[Candle]:
        """The newest-first window ending at series[index], as `combo`
        and `bollinger_bands` expect it (CLAUDE.md: index 0 is the
        newest). Bounded to EVALUATION_WINDOW so the slice cost does not
        grow with the run."""
        start = max(0, index + 1 - EVALUATION_WINDOW)
        return series[start : index + 1][::-1]

    @staticmethod
    def _open(
        entry: Entry,
        candle_time: datetime.datetime,
        band_levels: BandLevels,
        params: BacktestParameters,
    ) -> Optional[Position]:
        """Open a two-lot position, or decline the entry (FR-C10).

        The stop sits stop_loss_points beyond the *signal* candle's
        adverse extreme (FR-C06) - the candle the indicator fired on,
        which on a pending entry is not the candle that filled it.

        The entry is declined when TP1 is not strictly on the favorable
        side of the fill: TP1 would otherwise fire on the very next
        candle, bank a loss as a take-profit and arm break-even before
        the stop could do anything.
        """
        side = entry.side
        if side.favorable(band_levels.mm20, entry.price) <= 0:
            return None
        stop_price = (
            side.adverse_extreme(entry.signal_candle)
            - side.sign * params.stop_loss_points
        )
        return Position(
            entry_time=candle_time,
            entry_price=entry.price,
            side=side,
            take_profit_level=band_levels.opposite(side),
            stop_loss_points=params.stop_loss_points,
            lots=ComboTwoLot(),
            first_target_level=band_levels.mm20,
            initial_stop_price=stop_price,
        )

    def _day_summaries(
        self,
        series: List[Candle],
        trades: List[Trade],
        start_date: datetime.date,
        end_date: datetime.date,
        daily_candles: List[Candle],
    ) -> List[DayResultSummary]:
        """One row per trading day that had candles, with each trade
        attributed to the day it *entered* (FR-C15).

        A day a position merely ran through is a NO_TRADE day with 0
        points - it opened nothing. The regime columns are still filled:
        they measure the instrument, not the strategy.
        """
        by_day: Dict[datetime.date, List[Trade]] = {}
        for trade in trades:
            by_day.setdefault(trade.entry_time.date(), []).append(trade)

        days_with_candles = sorted(
            {
                candle_date(candle).date()
                for candle in series
                if start_date <= candle_date(candle).date() <= end_date
            }
        )

        summaries: List[DayResultSummary] = []
        for day in days_with_candles:
            day_trades = by_day.get(day, [])
            summaries.append(
                DayResultSummary(
                    date=day,
                    status=(
                        DayStatus.TRADED if day_trades else DayStatus.NO_TRADE
                    ),
                    trade_count=len(day_trades),
                    points=round(sum(trade.points for trade in day_trades), 4),
                    mm50_slope=mm50_slope_before(daily_candles, day),
                    adx14=adx_before(daily_candles, day),
                )
            )
        return summaries

    def _fetch_daily_candles(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Candle]:
        """Daily series for the regime columns, on EUMarket for the same
        reason the session strategy uses it: those columns measure the
        instrument, so a day must score the same on every definition or
        the numbers cannot be compared across them. A failure degrades to
        blank columns rather than aborting the run."""
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
