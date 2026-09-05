"""The Backtest menu's entry point.

Holds the registry and dispatches each request to the engine the chosen
definition runs on (see `strategy`). Every rule about *how* a backtest is
evaluated lives in an engine, not here, so adding a strategy does not
touch this class.
"""

import datetime
from typing import List, Optional

from api.services.backtest.definitions import get_definition, list_definitions
from api.services.backtest.strategy import StrategySelector
from client.aws_client import DynamoDBClient
from model import (
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    DayResult,
)
from services.candles_service import CandlesService


class BacktestService:
    """Runs the hardcoded backtests exposed by the Backtest menu."""

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
    ):
        # Kept as an attribute only because the backtest tests reach
        # through it to the shared CandlesService mock; nothing here
        # calls it. The engines hold their own reference.
        self.candles_service = candles_service
        self.strategies = StrategySelector(candles_service, dynamodb_client)

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
        return await self.strategies.for_definition(definition).evaluate_day(
            definition, trading_date, params
        )

    async def run_range(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> BacktestRunResult:
        return await self.strategies.for_definition(definition).run_range(
            definition, start_date, end_date, params
        )
