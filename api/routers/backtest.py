import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_backtest_service
from api.models.backtest import BacktestDefinitionResponse, DayDetailResponse
from api.services.backtest_service import (
    BacktestService,
    is_future_paris_date,
)
from model import BacktestDefinition

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


@router.get("/day", response_model=DayDetailResponse)
async def get_backtest_day(
    definition: str = Query(..., description="Backtest definition code"),
    date: str = Query(..., description="Trading day (YYYY-MM-DD)"),
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> DayDetailResponse:
    """Run the backtest for a single day and return full trade detail."""
    backtest_definition = _resolve_definition(backtest_service, definition)
    trading_date = _parse_date(date)
    day_result = backtest_service.evaluate_day(
        backtest_definition, trading_date
    )
    return DayDetailResponse.from_day_result(day_result)


def _resolve_definition(
    backtest_service: BacktestService, code: str
) -> BacktestDefinition:
    definition = backtest_service.get_definition(code)
    if definition is None:
        raise HTTPException(
            status_code=400, detail=f"Unknown backtest definition: {code}"
        )
    return definition


def _parse_date(value: str) -> datetime.date:
    try:
        trading_date = datetime.date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date, expected YYYY-MM-DD",
        )
    if is_future_paris_date(trading_date):
        raise HTTPException(
            status_code=400, detail="date must not be in the future"
        )
    return trading_date
