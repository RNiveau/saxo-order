import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from api.date_utils import parse_iso_date
from api.dependencies import get_backtest_service
from api.models.backtest import (
    BacktestDefinitionResponse,
    BacktestRunResponse,
    DayDetailResponse,
    backtest_definition_to_response,
    backtest_run_result_to_response,
    day_result_to_response,
)
from api.services.backtest_service import (
    BacktestService,
    is_future_paris_date,
    is_today_not_yet_closed,
)
from model import BacktestDefinition

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/definitions", response_model=List[BacktestDefinitionResponse])
async def get_backtest_definitions(
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> List[BacktestDefinitionResponse]:
    """List the hardcoded backtests available in the Backtest menu."""
    return [
        backtest_definition_to_response(definition)
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
    return day_result_to_response(day_result)


@router.get("/run", response_model=BacktestRunResponse)
async def get_backtest_run(
    definition: str = Query(..., description="Backtest definition code"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> BacktestRunResponse:
    """Run the backtest across a date range and return the aggregate
    summary plus a compact per-day list."""
    backtest_definition = _resolve_definition(backtest_service, definition)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise HTTPException(
            status_code=400, detail="end_date must not be before start_date"
        )
    run_result = backtest_service.run_range(backtest_definition, start, end)
    return backtest_run_result_to_response(run_result)


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
    trading_date = parse_iso_date(value)
    if is_future_paris_date(trading_date):
        raise HTTPException(
            status_code=400, detail="date must not be in the future"
        )
    if is_today_not_yet_closed(trading_date):
        raise HTTPException(
            status_code=400,
            detail="today's session has not closed yet",
        )
    return trading_date
