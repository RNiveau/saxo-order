from typing import List

from fastapi import APIRouter, Depends

from api.dependencies import get_backtest_service
from api.models.backtest import BacktestDefinitionResponse
from api.services.backtest_service import BacktestService

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/definitions", response_model=List[BacktestDefinitionResponse])
async def get_backtest_definitions(
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> List[BacktestDefinitionResponse]:
    """List the hardcoded backtests available in the Backtest menu."""
    return [
        BacktestDefinitionResponse.from_definition(definition)
        for definition in backtest_service.list_definitions()
    ]
