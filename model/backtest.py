"""Domain models for hardcoded backtests (Model Layer, no external deps)."""

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from model.enum import DayStatus, Direction, ExitReason
from model.workflow import Candle


@dataclass
class BacktestParameters:
    """Tunable thresholds for the "CAC40 Bougie de 9h" strategy. Defaults
    reproduce the values originally hardcoded for spec 021, so an
    unparametrized run behaves exactly as before. A definition may carry
    its own defaults (BacktestDefinition.default_parameters) - e.g. GER40
    uses 150/10/50/40 - which the router merges with per-run overrides."""

    stop_loss_points: float = 50
    take_profit_offset_points: float = 10
    break_even_trigger_points: float = 20
    max_entry_distance_points: float = 20


@dataclass
class BacktestDefinition:
    code: str
    name: str
    display_name: str
    instrument: str
    # Optional time-based cut: when both are set, a position that has
    # never moved more than time_cut_min_favorable_points in its favor by
    # time_cut_minutes after entry is closed at market. Left None on the
    # plain "Bougie de 9h" so its behavior is unchanged.
    time_cut_minutes: Optional[int] = None
    time_cut_min_favorable_points: Optional[float] = None
    # Per-definition default thresholds. An omitted per-run override falls
    # back to these (not to a single global default), so a definition can
    # ship its own defaults - GER40 uses 150/10/50/40, CAC40 keeps the
    # BacktestParameters defaults 50/10/20/20.
    default_parameters: BacktestParameters = field(
        default_factory=BacktestParameters
    )
    # Double take-profit / two-lot overlay (GER40 "Bougie de 9h"). When
    # True, every entry opens two lots: the first exits at first_target
    # (the H1 midpoint), the runner at the full take-profit, and the
    # runner's stop moves to break-even the moment the first lot fills.
    # Left False on the CAC40 backtests so their single-lot behavior is
    # unchanged.
    double_take_profit: bool = False
    # Fraction of the H1 high-low range at which the first lot takes
    # profit (0.5 = midpoint). Only used when double_take_profit is True.
    first_target_fraction: Optional[float] = None
    # When True, the initial stop is stop_loss_points beyond the H1
    # reference level (below the H1 low for a long, above the H1 high for
    # a short) rather than that distance from the entry price. GER40 sets
    # this True; CAC40 measures its stop from entry (False).
    stop_from_reference_level: bool = False


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
    # 9h reference candle levels for the day, carried through so a range
    # export can expose the setup's H1 range (a regime/volatility proxy
    # that is independent of the SL/TP parameters). None only on NO_DATA
    # days, which run_range excludes from the summary anyway.
    h1_high: Optional[float] = None
    h1_low: Optional[float] = None


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
