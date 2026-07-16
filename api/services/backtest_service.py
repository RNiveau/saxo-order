import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from model import (
    BacktestDefinition,
    Candle,
    DayResult,
    Strategy,
    Trade,
    UnitTime,
)
from model.enum import DayStatus, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException
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
FIVE_MINUTE_HORIZON = 5
H1_HORIZON = 60


def paris_reference_window_utc(
    trading_date: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """9:00-10:00 Paris local time for trading_date, as naive UTC bounds."""
    start_local = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        9,
        0,
        tzinfo=PARIS_TZ,
    )
    end_local = start_local + datetime.timedelta(hours=1)
    return (_to_naive_utc(start_local), _to_naive_utc(end_local))


def paris_session_end_utc(trading_date: datetime.date) -> datetime.datetime:
    """End of FRA40.I's regular trading session (Euronext Paris close,
    17:30 local), as a naive UTC datetime."""
    end_local = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        17,
        30,
        tzinfo=PARIS_TZ,
    )
    return _to_naive_utc(end_local)


def is_future_paris_date(d: datetime.date) -> bool:
    today_paris = datetime.datetime.now(PARIS_TZ).date()
    return d > today_paris


def _to_naive_utc(value: datetime.datetime) -> datetime.datetime:
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _candle_date(candle: Candle) -> datetime.datetime:
    """Candles from get_candles_in_window always carry a date (it is
    part of that method's window filter), so this narrows the type."""
    assert candle.date is not None
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
            candles=five_min_candles,
            trades=trades,
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

    def _evaluate_trades(
        self,
        candles: List[Candle],
        h1_high: float,
        h1_low: float,
    ) -> List[Trade]:
        trades: List[Trade] = []
        position: Optional[_OpenPosition] = None
        breached = False
        take_profit_level = h1_high - TAKE_PROFIT_OFFSET_POINTS

        for candle in candles:
            candle_date = _candle_date(candle)
            if position is None:
                if not breached:
                    if candle.lower < h1_low:
                        breached = True
                    continue
                if candle.close >= h1_low:
                    position = _OpenPosition(
                        entry_time=candle_date,
                        entry_price=candle.close,
                    )
                    breached = False
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
