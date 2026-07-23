"""Pydantic request/response models and CSV export for the Backtest API."""

import csv
import datetime
import io
from typing import Any, List, Optional

from pydantic import BaseModel

from model import (
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    BacktestSummary,
    Candle,
    DayResult,
    DayResultSummary,
    Trade,
)


class BacktestParametersResponse(BaseModel):
    stop_loss_points: float
    take_profit_offset_points: float
    break_even_trigger_points: float
    max_entry_distance_points: float


class BacktestDefinitionResponse(BaseModel):
    code: str
    display_name: str
    instrument: str
    double_take_profit: bool = False
    default_parameters: BacktestParametersResponse


class TradeResponse(BaseModel):
    entry_time: datetime.datetime
    entry_price: float
    exit_time: datetime.datetime
    exit_price: float
    exit_reason: str
    direction: str
    points: float


class CandleResponse(BaseModel):
    date: Optional[datetime.datetime] = None
    open: float
    close: float
    lower: float
    higher: float


class DayDetailResponse(BaseModel):
    date: datetime.date
    status: str
    h1_high: Optional[float] = None
    h1_low: Optional[float] = None
    candles: List[CandleResponse] = []
    trades: List[TradeResponse] = []


class DayResultSummaryResponse(BaseModel):
    date: datetime.date
    status: str
    trade_count: int
    points: float
    h1_high: Optional[float] = None
    h1_low: Optional[float] = None


class BacktestSummaryResponse(BaseModel):
    definition_code: str
    start_date: datetime.date
    end_date: datetime.date
    number_of_days: int
    number_of_trades: int
    number_of_winning_positions: int
    number_of_losing_positions: int
    number_of_be: int
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    final_result: float


class BacktestRunResponse(BaseModel):
    summary: BacktestSummaryResponse
    days: List[DayResultSummaryResponse] = []


def backtest_definition_to_response(
    definition: BacktestDefinition,
) -> BacktestDefinitionResponse:
    defaults = definition.default_parameters
    return BacktestDefinitionResponse(
        code=definition.code,
        display_name=definition.display_name,
        instrument=definition.instrument,
        double_take_profit=definition.double_take_profit,
        default_parameters=BacktestParametersResponse(
            stop_loss_points=defaults.stop_loss_points,
            take_profit_offset_points=defaults.take_profit_offset_points,
            break_even_trigger_points=defaults.break_even_trigger_points,
            max_entry_distance_points=defaults.max_entry_distance_points,
        ),
    )


def _trade_to_response(trade: Trade) -> TradeResponse:
    return TradeResponse(
        entry_time=trade.entry_time,
        entry_price=trade.entry_price,
        exit_time=trade.exit_time,
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason.value,
        direction=trade.direction.value,
        points=trade.points,
    )


def _candle_to_response(candle: Candle) -> CandleResponse:
    return CandleResponse(
        date=candle.date,
        open=candle.open,
        close=candle.close,
        lower=candle.lower,
        higher=candle.higher,
    )


def day_result_to_response(day_result: DayResult) -> DayDetailResponse:
    return DayDetailResponse(
        date=day_result.date,
        status=day_result.status.value,
        h1_high=day_result.h1_high,
        h1_low=day_result.h1_low,
        candles=[_candle_to_response(candle) for candle in day_result.candles],
        trades=[_trade_to_response(trade) for trade in day_result.trades],
    )


def _day_result_summary_to_response(
    summary: DayResultSummary,
) -> DayResultSummaryResponse:
    return DayResultSummaryResponse(
        date=summary.date,
        status=summary.status.value,
        trade_count=summary.trade_count,
        points=summary.points,
        h1_high=summary.h1_high,
        h1_low=summary.h1_low,
    )


def _backtest_summary_to_response(
    summary: BacktestSummary,
) -> BacktestSummaryResponse:
    return BacktestSummaryResponse(
        definition_code=summary.definition_code,
        start_date=summary.start_date,
        end_date=summary.end_date,
        number_of_days=summary.number_of_days,
        number_of_trades=summary.number_of_trades,
        number_of_winning_positions=summary.number_of_winning_positions,
        number_of_losing_positions=summary.number_of_losing_positions,
        number_of_be=summary.number_of_be,
        average_win=summary.average_win,
        average_loss=summary.average_loss,
        final_result=summary.final_result,
    )


def backtest_run_result_to_response(
    run_result: BacktestRunResult,
) -> BacktestRunResponse:
    return BacktestRunResponse(
        summary=_backtest_summary_to_response(run_result.summary),
        days=[_day_result_summary_to_response(day) for day in run_result.days],
    )


def _write_parameters_block(writer: Any, params: BacktestParameters) -> None:
    """Leading block echoing the run parameters so an exported CSV is
    self-describing about the thresholds it was produced with."""
    writer.writerow(["parameter", "value"])
    writer.writerow(["stop_loss_points", params.stop_loss_points])
    writer.writerow(
        ["take_profit_offset_points", params.take_profit_offset_points]
    )
    writer.writerow(
        ["break_even_trigger_points", params.break_even_trigger_points]
    )
    writer.writerow(
        ["max_entry_distance_points", params.max_entry_distance_points]
    )
    writer.writerow([])


def backtest_run_result_to_csv(
    run_result: BacktestRunResult, params: BacktestParameters
) -> str:
    """FR-017: one row per day in run_result.days (no-data days already
    excluded by BacktestService.run_range)."""
    output = io.StringIO()
    writer = csv.writer(output)
    _write_parameters_block(writer, params)
    writer.writerow(
        [
            "date",
            "status",
            "trade_count",
            "points",
            "h1_high",
            "h1_low",
            "h1_range",
        ]
    )
    for day in run_result.days:
        h1_range = (
            round(day.h1_high - day.h1_low, 4)
            if day.h1_high is not None and day.h1_low is not None
            else None
        )
        writer.writerow(
            [
                day.date.isoformat(),
                day.status.value,
                day.trade_count,
                day.points,
                day.h1_high,
                day.h1_low,
                h1_range,
            ]
        )
    return output.getvalue()


def day_result_to_csv(
    day_result: DayResult, params: BacktestParameters
) -> str:
    """FR-018: H1 levels, 5-minute candles, and trades as three blocks
    separated by a blank line."""
    output = io.StringIO()
    writer = csv.writer(output)

    _write_parameters_block(writer, params)

    writer.writerow(["h1_high", "h1_low"])
    writer.writerow([day_result.h1_high, day_result.h1_low])
    writer.writerow([])

    writer.writerow(["date", "open", "higher", "lower", "close"])
    for candle in day_result.candles:
        writer.writerow(
            [
                candle.date.isoformat() if candle.date else "",
                candle.open,
                candle.higher,
                candle.lower,
                candle.close,
            ]
        )
    writer.writerow([])

    writer.writerow(
        [
            "entry_time",
            "entry_price",
            "exit_time",
            "exit_price",
            "exit_reason",
            "direction",
            "points",
        ]
    )
    for trade in day_result.trades:
        writer.writerow(
            [
                trade.entry_time.isoformat(),
                trade.entry_price,
                trade.exit_time.isoformat(),
                trade.exit_price,
                trade.exit_reason.value,
                trade.direction.value,
                trade.points,
            ]
        )

    return output.getvalue()
