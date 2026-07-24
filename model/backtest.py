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
    # Wide-range structural-stop variant (spec 021, US1d): when
    # min_h1_range_points is set, days whose H1 range (high - low) is not
    # strictly greater than it are not traded; when structural_stop is True,
    # the fixed stop-loss distance is replaced by a stop that fires when a
    # 5-minute candle closes beyond the H1 level while break-even is unarmed.
    # Left None/False on the other backtests so their behavior is unchanged.
    min_h1_range_points: Optional[float] = None
    structural_stop: bool = False

    def __post_init__(self) -> None:
        # The double take-profit exit path does not evaluate the time cut,
        # so combining the two would silently ignore the cut. Reject it at
        # construction (registration) time rather than shipping a no-op.
        if self.double_take_profit and self.time_cut_minutes is not None:
            raise ValueError(
                "double_take_profit is not supported together with a time "
                f"cut (definition {self.code!r})"
            )


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
    h1_open: Optional[float] = None
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
    # Daily MA50 slope (%) as of the close strictly before this day - a
    # trend/chop regime measure, lookahead-safe and config-independent.
    # None when fewer than 60 prior daily candles are available.
    mm50_slope: Optional[float] = None
    # Daily ADX(14) as of the close strictly before this day - a
    # direction-agnostic trend/chop strength measure, lookahead-safe and
    # config-independent. None when fewer than 42 prior daily candles exist.
    adx14: Optional[float] = None
    # 9h reference candle open, and the overnight gap (9h open - the prior
    # daily close). A same-day, pre-trade shock/impulse signal, lookahead-
    # safe and config-independent. overnight_gap is None when there is no
    # prior daily candle to measure against.
    h1_open: Optional[float] = None
    overnight_gap: Optional[float] = None


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


@dataclass
class CachedDayCandles:
    """Raw Saxo candle data cached for one (backtest definition, trading
    date) pair (FR-036-FR-040). Never holds a computed Trade/DayResult -
    only the H1 reference candle and 5-minute session candles a day's
    strategy evaluation is run against."""

    has_data: bool
    h1_candle: Optional[Candle] = None
    m5_candles: List[Candle] = field(default_factory=list)
