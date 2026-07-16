"""Pydantic request/response models for the Backtest API."""

import datetime
from typing import List, Optional

from pydantic import BaseModel

from model import BacktestDefinition, Candle, DayResult, Trade


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
