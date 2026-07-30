"""Which engine a backtest definition runs on.

Every backtest shipped before spec 026 is a *session* strategy: a 9h
reference range fixes the levels, the day is scanned once and ends flat,
so it can be evaluated one day at a time. The combo backtests are not -
their entries come from an indicator and their positions carry across
days - which removes both inputs the day loop is built on.

Rather than thread that difference through the day loop as another
variant flag, a definition names the engine it runs on and the engine
answers the same two questions. `BacktestService` picks one here and
never asks again; everything downstream (the router, the response
models, the CSV exports, the summary) is shared.
"""

import datetime
from typing import Optional, Protocol

from api.services.backtest.session_range import SessionRangeStrategy
from client.aws_client import DynamoDBClient
from model import (
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    DayResult,
)
from services.candles_service import CandlesService
from utils.exception import SaxoException


class BacktestStrategy(Protocol):
    async def evaluate_day(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> DayResult:
        """The day's result under this definition's rules."""
        ...

    async def run_range(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> BacktestRunResult:
        """Every day in [start_date, end_date], plus the aggregate."""
        ...


class StrategySelector:
    """Builds the engines once and hands out the one a definition names.

    Construction happens here rather than per call because an engine
    holds a candle source, and rebuilding it per request would drop
    whatever that source had already fetched.

    `dynamodb_client` is taken but not yet used: the combo engine reads
    its own candle cache through it, and it is threaded now so adding
    that engine does not also change this constructor's signature and
    every call site with it.
    """

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
    ):
        self.session_range = SessionRangeStrategy(
            candles_service, dynamodb_client
        )

    def for_definition(
        self, definition: BacktestDefinition
    ) -> BacktestStrategy:
        if definition.combo_entry:
            raise SaxoException(
                "the combo strategy is not implemented yet; definition "
                f"{definition.code!r} cannot be run. Falling back to the "
                "session-range engine would report results for rules it "
                "never applied"
            )
        return self.session_range
