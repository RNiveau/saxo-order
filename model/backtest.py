"""Domain models for hardcoded backtests (Model Layer, no external deps)."""

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from model.enum import DayStatus, Direction, ExitReason
from model.workflow import Candle


@dataclass
class BacktestDefinition:
    code: str
    name: str
    display_name: str
    instrument: str


@dataclass
class BacktestParameters:
    """Tunable thresholds for the "CAC40 Bougie de 9h" strategy. Defaults
    reproduce the values originally hardcoded for spec 021, so an
    unparametrized run behaves exactly as before."""

    stop_loss_points: float = 50
    take_profit_offset_points: float = 10
    break_even_trigger_points: float = 20
    max_entry_distance_points: float = 20


@dataclass
class Trade:
    entry_time: datetime.datetime
    entry_price: float
    exit_time: datetime.datetime
    exit_price: float
    exit_reason: ExitReason
    points: float
    direction: Direction = Direction.BUY


@dataclass
class DayResult:
    date: datetime.date
    status: DayStatus
    h1_high: Optional[float] = None
    h1_low: Optional[float] = None
    candles: List[Candle] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)


@dataclass
class DayResultSummary:
    date: datetime.date
    status: DayStatus
    trade_count: int
    points: float


@dataclass
class BacktestSummary:
    definition_code: str
    start_date: datetime.date
    end_date: datetime.date
    number_of_days: int
    number_of_trades: int
    number_of_winning_positions: int
    number_of_losing_positions: int
    number_of_be: int
    average_win: Optional[float]
    average_loss: Optional[float]
    final_result: float


@dataclass
class BacktestRunResult:
    summary: BacktestSummary
    days: List[DayResultSummary] = field(default_factory=list)
