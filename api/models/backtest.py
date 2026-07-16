"""Pydantic request/response models for the Backtest API."""

import datetime
from typing import List, Optional

from pydantic import BaseModel

from model import (
    BacktestDefinition,
    BacktestRunResult,
    BacktestSummary,
    Candle,
    DayResult,
    DayResultSummary,
    Trade,
)


class BacktestDefinitionResponse(BaseModel):
    code: str
    display_name: str
    instrument: str

    @classmethod
    def from_definition(
        cls, definition: BacktestDefinition
    ) -> "BacktestDefinitionResponse":
        return cls(
            code=definition.code,
            display_name=definition.display_name,
            instrument=definition.instrument,
        )


class TradeResponse(BaseModel):
    entry_time: datetime.datetime
    entry_price: float
    exit_time: datetime.datetime
    exit_price: float
    exit_reason: str
    points: float

    @classmethod
    def from_trade(cls, trade: Trade) -> "TradeResponse":
        return cls(
            entry_time=trade.entry_time,
            entry_price=trade.entry_price,
            exit_time=trade.exit_time,
            exit_price=trade.exit_price,
            exit_reason=trade.exit_reason.value,
            points=trade.points,
        )


class CandleResponse(BaseModel):
    date: Optional[datetime.datetime] = None
    open: float
    close: float
    lower: float
    higher: float

    @classmethod
    def from_candle(cls, candle: Candle) -> "CandleResponse":
        return cls(
            date=candle.date,
            open=candle.open,
            close=candle.close,
            lower=candle.lower,
            higher=candle.higher,
        )


class DayDetailResponse(BaseModel):
    date: datetime.date
    status: str
    h1_high: Optional[float] = None
    h1_low: Optional[float] = None
    candles: List[CandleResponse] = []
    trades: List[TradeResponse] = []

    @classmethod
    def from_day_result(cls, day_result: DayResult) -> "DayDetailResponse":
        return cls(
            date=day_result.date,
            status=day_result.status.value,
            h1_high=day_result.h1_high,
            h1_low=day_result.h1_low,
            candles=[
                CandleResponse.from_candle(candle)
                for candle in day_result.candles
            ],
            trades=[
                TradeResponse.from_trade(trade) for trade in day_result.trades
            ],
        )


class DayResultSummaryResponse(BaseModel):
    date: datetime.date
    status: str
    trade_count: int
    points: float

    @classmethod
    def from_day_result_summary(
        cls, summary: DayResultSummary
    ) -> "DayResultSummaryResponse":
        return cls(
            date=summary.date,
            status=summary.status.value,
            trade_count=summary.trade_count,
            points=summary.points,
        )


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

    @classmethod
    def from_summary(
        cls, summary: BacktestSummary
    ) -> "BacktestSummaryResponse":
        return cls(
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


class BacktestRunResponse(BaseModel):
    summary: BacktestSummaryResponse
    days: List[DayResultSummaryResponse] = []

    @classmethod
    def from_run_result(
        cls, run_result: BacktestRunResult
    ) -> "BacktestRunResponse":
        return cls(
            summary=BacktestSummaryResponse.from_summary(run_result.summary),
            days=[
                DayResultSummaryResponse.from_day_result_summary(day)
                for day in run_result.days
            ],
        )
