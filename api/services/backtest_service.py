import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from model import BacktestDefinition, Strategy
from services.candles_service import CandlesService
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
