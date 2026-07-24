import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from api.date_utils import parse_iso_date
from api.dependencies import get_backtest_service
from api.models.backtest import (
    BacktestDefinitionResponse,
    BacktestRunResponse,
    DayDetailResponse,
    backtest_definition_to_response,
    backtest_run_result_to_csv,
    backtest_run_result_to_response,
    day_result_to_csv,
    day_result_to_response,
)
from api.services.backtest_service import (
    BacktestService,
    is_future_paris_date,
    is_today_not_yet_closed,
)
from model import BacktestDefinition, BacktestParameters

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def _params(
    stop_loss_points: Optional[float] = Query(
        None, gt=0, description="Stop-loss distance in points (default 50)"
    ),
    take_profit_offset_points: Optional[float] = Query(
        None,
        gt=0,
        description="Take-profit offset from the H1 level (default 10)",
    ),
    break_even_trigger_points: Optional[float] = Query(
        None,
        gt=0,
        description="Favorable move that arms break-even (default 20)",
    ),
    max_entry_distance_points: Optional[float] = Query(
        None,
        gt=0,
        description="Max distance from the H1 level for a valid entry "
        "(default 20)",
    ),
) -> BacktestParameters:
    """Build BacktestParameters from optional query params, falling back
    to the strategy defaults for any value the caller omits."""
    defaults = BacktestParameters()
    return BacktestParameters(
        stop_loss_points=(
            stop_loss_points
            if stop_loss_points is not None
            else defaults.stop_loss_points
        ),
        take_profit_offset_points=(
            take_profit_offset_points
            if take_profit_offset_points is not None
            else defaults.take_profit_offset_points
        ),
        break_even_trigger_points=(
            break_even_trigger_points
            if break_even_trigger_points is not None
            else defaults.break_even_trigger_points
        ),
        max_entry_distance_points=(
            max_entry_distance_points
            if max_entry_distance_points is not None
            else defaults.max_entry_distance_points
        ),
    )


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
    params: BacktestParameters = Depends(_params),
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> DayDetailResponse:
    """Run the backtest for a single day and return full trade detail."""
    backtest_definition = _resolve_definition(backtest_service, definition)
    trading_date = _parse_date(date)
    day_result = await backtest_service.evaluate_day(
        backtest_definition, trading_date, params
    )
    return day_result_to_response(day_result)


@router.get("/run", response_model=BacktestRunResponse)
async def get_backtest_run(
    definition: str = Query(..., description="Backtest definition code"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    params: BacktestParameters = Depends(_params),
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> BacktestRunResponse:
    """Run the backtest across a date range and return the aggregate
    summary plus a compact per-day list."""
    backtest_definition = _resolve_definition(backtest_service, definition)
    start, end = _parse_range(start_date, end_date)
    run_result = await backtest_service.run_range(
        backtest_definition, start, end, params
    )
    return backtest_run_result_to_response(run_result)


@router.get("/day/csv")
async def get_backtest_day_csv(
    definition: str = Query(..., description="Backtest definition code"),
    date: str = Query(..., description="Trading day (YYYY-MM-DD)"),
    params: BacktestParameters = Depends(_params),
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> Response:
    """CSV export of a single day's detail (FR-018)."""
    backtest_definition = _resolve_definition(backtest_service, definition)
    trading_date = _parse_date(date)
    day_result = await backtest_service.evaluate_day(
        backtest_definition, trading_date, params
    )
    return Response(
        content=day_result_to_csv(day_result, params),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="backtest-{definition}-{date}.csv"'
            )
        },
    )


@router.get("/run/csv")
async def get_backtest_run_csv(
    definition: str = Query(..., description="Backtest definition code"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    params: BacktestParameters = Depends(_params),
    backtest_service: BacktestService = Depends(get_backtest_service),
) -> Response:
    """CSV export of a range run's day-by-day summary (FR-017)."""
    backtest_definition = _resolve_definition(backtest_service, definition)
    start, end = _parse_range(start_date, end_date)
    run_result = await backtest_service.run_range(
        backtest_definition, start, end, params
    )
    return Response(
        content=backtest_run_result_to_csv(run_result, params),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="backtest-{definition}-{start_date}-{end_date}.csv"'
            )
        },
    )


def _parse_range(
    start_date: str, end_date: str
) -> tuple[datetime.date, datetime.date]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise HTTPException(
            status_code=400, detail="end_date must not be before start_date"
        )
    return start, end


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
