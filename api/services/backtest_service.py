import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from model import (
    BacktestDefinition,
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
from model.enum import DayStatus, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException
from utils.helper import market_in_utc
from utils.logger import Logger

PARIS_TZ = ZoneInfo("Europe/Paris")

BACKTEST_DEFINITIONS: List[BacktestDefinition] = [
    BacktestDefinition(
        code="B9H",
        name=Strategy.B9H.value,
        display_name="CAC40 Bougie de 9h",
        instrument="FRA40.I",
    ),
]

# "CAC40 Bougie de 9h" strategy thresholds — intentionally hardcoded in
# code, not configuration: FR-002 requires each backtest to be a fixed,
# hardcoded implementation, not a generic configurable engine.
STOP_LOSS_POINTS = 50
TAKE_PROFIT_OFFSET_POINTS = 10
BREAK_EVEN_TRIGGER_POINTS = 20
MAX_ENTRY_DISTANCE_FROM_LOW = 20
FIVE_MINUTE_HORIZON = 5
H1_HORIZON = 60


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
    def __init__(self, entry_time: datetime.datetime, entry_price: float):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.be_armed = False

    @property
    def stop_level(self) -> float:
        if self.be_armed:
            return self.entry_price
        return self.entry_price - STOP_LOSS_POINTS


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
        self, definition: BacktestDefinition, trading_date: datetime.date
    ) -> DayResult:
        """Run the "CAC40 Bougie de 9h" rules for a single trading day."""
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

        trades = self._evaluate_trades(chronological, h1_high, h1_low)

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
    ) -> BacktestRunResult:
        """Run the backtest across every day in [start_date, end_date]."""
        day_summaries: List[DayResultSummary] = []
        all_trades: List[Trade] = []

        current = start_date
        while current <= end_date:
            if current.weekday() >= 5:
                # Saturday/Sunday: FRA40.I never trades, so skip the
                # H1/5-minute fetches that would only resolve to
                # NO_DATA - avoids two wasted Saxo calls per weekend day.
                current += datetime.timedelta(days=1)
                continue
            day_result = self.evaluate_day(definition, current)
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

    @staticmethod
    def _is_valid_entry(
        entry_price: float, h1_low: float, take_profit_level: float
    ) -> bool:
        """A breakout entry only produces a trade when it still leaves
        room to work: within MAX_ENTRY_DISTANCE_FROM_LOW points of the
        H1 low, and below the take-profit level. An entry too far
        above the low, or already at/above H1-high-10, is not valid -
        it would exit on the very next candle for little or no
        favorable move despite being labeled a take-profit (added
        after PR review)."""
        return (
            entry_price - h1_low <= MAX_ENTRY_DISTANCE_FROM_LOW
            and entry_price < take_profit_level
        )

    def _evaluate_trades(
        self,
        candles: List[Candle],
        h1_high: float,
        h1_low: float,
    ) -> List[Trade]:
        trades: List[Trade] = []
        position: Optional[_OpenPosition] = None
        breached = False
        candidate: Optional[Candle] = None
        take_profit_level = h1_high - TAKE_PROFIT_OFFSET_POINTS

        for candle in candles:
            candle_date = _candle_date(candle)
            if position is None:
                if candidate is None:
                    if not breached:
                        if candle.lower < h1_low:
                            breached = True
                        continue
                    if candle.close >= h1_low:
                        candidate = candle
                        breached = False
                    continue

                # candidate is the reversal candle awaiting breakout
                # confirmation: only a later candle trading above its
                # high confirms the reversal has momentum - closing
                # back above the H1 low is not itself an entry.
                if candle.higher > candidate.higher:
                    entry_price = max(candidate.higher, candle.open)
                    if self._is_valid_entry(
                        entry_price, h1_low, take_profit_level
                    ):
                        position = _OpenPosition(
                            entry_time=candle_date,
                            entry_price=entry_price,
                        )
                    candidate = None
                    continue
                if candle.close < h1_low:
                    # New full context: this candle both invalidates
                    # the pending candidate and is itself a fresh
                    # breach (its low is necessarily below h1_low
                    # whenever its close is).
                    candidate = None
                    breached = True
                    continue
                candidate = candle
                continue

            stop_level = position.stop_level
            if candle.lower <= stop_level:
                exit_price = (
                    candle.open if candle.open <= stop_level else stop_level
                )
                reason = (
                    ExitReason.BREAK_EVEN
                    if position.be_armed
                    else ExitReason.STOP_LOSS
                )
                trades.append(
                    self._close_trade(
                        position, candle_date, exit_price, reason
                    )
                )
                position = None
            elif candle.higher >= take_profit_level:
                exit_price = (
                    candle.open
                    if candle.open >= take_profit_level
                    else take_profit_level
                )
                trades.append(
                    self._close_trade(
                        position,
                        candle_date,
                        exit_price,
                        ExitReason.TAKE_PROFIT,
                    )
                )
                position = None
            elif (
                not position.be_armed
                and candle.higher
                >= position.entry_price + BREAK_EVEN_TRIGGER_POINTS
            ):
                position.be_armed = True

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

    @staticmethod
    def _close_trade(
        position: _OpenPosition,
        exit_time: datetime.datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        return Trade(
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            points=round(exit_price - position.entry_price, 4),
        )
