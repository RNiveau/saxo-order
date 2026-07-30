"""Domain models for hardcoded backtests (Model Layer, no external deps)."""

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from model.enum import DayStatus, Direction, ExitReason
from model.market import EUMarket, Market
from model.workflow import Candle, UnitTime


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
    # The trading session this backtest runs on: it fixes the 9h reference
    # window, the session end an end-of-day exit lands on, and the "has
    # today closed yet" check. Defaults to EUMarket (9:00-17:30 Paris, the
    # Euronext/Xetra cash session) so every existing definition keeps the
    # window it runs today; the impulsive variant uses EuCfdMarket to trade
    # the 9:00-22:00 CFD session.
    market: Market = field(default_factory=EUMarket)
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
    # Impulsive-candle variant (spec 025 addendum, FR-G14/FR-G15): when
    # impulsive_candle_points is set, the fixed stop-loss distance is
    # dropped entirely and the only stop while break-even is unarmed is an
    # impulsive candle moving against the position - one at least this many
    # points wide (full range, wicks included) that also closes within
    # impulsive_close_fraction of its range from the extreme adverse to the
    # position, beyond the H1 reference level. Left None on the other
    # backtests so their behavior is unchanged.
    impulsive_candle_points: Optional[float] = None
    impulsive_close_fraction: Optional[float] = None
    # Entry filters (spec 025 addendum 2, FR-G19/FR-G20). Both are about
    # *opening* a position and never affect one already open: no new
    # position on a candle starting at or after last_entry_time (market
    # local, DST-aware), and none once max_daily_losses positions have
    # closed with negative points that day. Left None on the other
    # backtests, which take entries at any hour and under any loss run.
    last_entry_time: Optional[datetime.time] = None
    max_daily_losses: Optional[int] = None
    # The other way to place a double take-profit's two targets (spec 025
    # addendum 3, FR-G26): instead of first_target_fraction's split inside
    # the H1 range, the first lot takes the ordinary take-profit and the
    # runner targets this many points beyond it - outside the H1 range.
    # Exactly one of the two is set on a double-take-profit definition.
    runner_extension_points: Optional[float] = None
    # One-step trail for the runner (spec 025 addendum 4, FR-G32): once
    # the first lot has filled and the runner has gained this many points
    # beyond TP1, its stop moves up from break-even to TP1 itself, so the
    # runner is locked in to at least match what the first lot banked.
    trail_to_first_target_points: Optional[float] = None
    # The candle timeframe the strategy is evaluated on (spec 026,
    # FR-C01). None on the session-range backtests, whose shape is fixed
    # at "an H1 reference candle scanned with 5-minute candles" and is
    # not a parameter.
    unit_time: Optional[UnitTime] = None
    # Selects the combo strategy (spec 026): entries come from the combo
    # indicator on unit_time candles instead of a breakout of the 9h
    # reference range, and a position is held until an exit rule fires
    # rather than closed at the session end. Left False on every
    # session-range backtest.
    combo_entry: bool = False

    def __post_init__(self) -> None:
        """Reject at construction (registration) time any combination of
        flags that could not be honored in full.

        A definition is read once, when the exit chain and lot model are
        built; a flag that cannot take effect there would otherwise ship
        as a silent no-op, and the backtest would report results for
        rules it never applied."""
        placements = [
            self.first_target_fraction is not None,
            self.runner_extension_points is not None,
        ]
        # A combo definition is the one two-lot setup whose targets are
        # not placed from the H1 range at entry: the mm20 and the
        # opposite bollinger band are re-read on every candle, so it
        # carries neither placement field.
        if (
            self.double_take_profit
            and not self.combo_entry
            and not any(placements)
        ):
            raise ValueError(
                "double_take_profit requires first_target_fraction or "
                "runner_extension_points - the first lot would have "
                f"nowhere to take profit (definition {self.code!r})"
            )
        if all(placements):
            raise ValueError(
                "first_target_fraction and runner_extension_points are two "
                "ways to place the same pair of targets; set exactly one "
                f"(definition {self.code!r})"
            )
        if (
            self.runner_extension_points is not None
            and not self.double_take_profit
        ):
            raise ValueError(
                "runner_extension_points is only used with "
                f"double_take_profit (definition {self.code!r})"
            )
        if (
            self.runner_extension_points is not None
            and self.runner_extension_points <= 0
        ):
            raise ValueError(
                "runner_extension_points must be positive - the runner "
                "would otherwise target the first lot's level or worse "
                f"(definition {self.code!r})"
            )
        if (
            not self.double_take_profit
            and self.first_target_fraction is not None
        ):
            raise ValueError(
                "first_target_fraction is only used with "
                f"double_take_profit (definition {self.code!r})"
            )
        if self.first_target_fraction is not None and not (
            0 < self.first_target_fraction < 1
        ):
            raise ValueError(
                "first_target_fraction must sit strictly inside the H1 "
                f"range (definition {self.code!r})"
            )
        if (self.time_cut_minutes is None) != (
            self.time_cut_min_favorable_points is None
        ):
            raise ValueError(
                "a time cut needs both time_cut_minutes and "
                f"time_cut_min_favorable_points (definition {self.code!r})"
            )
        # The two now compose (the time cut is an ordinary policy in the
        # exit chain and the lot model handles the two-lot points), but
        # no backtest ships the combination and none has been validated
        # against it, so it stays rejected until one needs it.
        if self.double_take_profit and self.time_cut_minutes is not None:
            raise ValueError(
                "double_take_profit is not supported together with a time "
                f"cut (definition {self.code!r})"
            )
        if (self.impulsive_candle_points is None) != (
            self.impulsive_close_fraction is None
        ):
            raise ValueError(
                "an impulsive-candle stop needs both "
                "impulsive_candle_points and impulsive_close_fraction "
                f"(definition {self.code!r})"
            )
        if (
            self.impulsive_candle_points is not None
            and self.impulsive_candle_points <= 0
        ):
            raise ValueError(
                "impulsive_candle_points must be positive - every candle "
                f"would otherwise be impulsive (definition {self.code!r})"
            )
        if self.impulsive_close_fraction is not None and not (
            0 < self.impulsive_close_fraction < 1
        ):
            raise ValueError(
                "impulsive_close_fraction must sit strictly inside the "
                f"candle's range (definition {self.code!r})"
            )
        # Both replace the fixed stop with a close-measured one, and the
        # chain has room for only one such stop. They compose in principle
        # (the impulse rule is strictly the stricter of the two), but no
        # backtest ships the combination and none has been validated
        # against it, so it stays rejected until one needs it.
        if self.impulsive_candle_points is not None and self.structural_stop:
            raise ValueError(
                "an impulsive-candle stop is not supported together with a "
                f"structural stop (definition {self.code!r})"
            )
        if (
            self.trail_to_first_target_points is not None
            and not self.double_take_profit
        ):
            raise ValueError(
                "trail_to_first_target_points needs a first target to "
                "trail to, which only a double take-profit has "
                f"(definition {self.code!r})"
            )
        if (
            self.trail_to_first_target_points is not None
            and self.trail_to_first_target_points <= 0
        ):
            raise ValueError(
                "trail_to_first_target_points must be positive - the trail "
                "would otherwise arm the instant the first lot filled "
                f"(definition {self.code!r})"
            )
        if (
            self.trail_to_first_target_points is not None
            and self.runner_extension_points is not None
            and self.trail_to_first_target_points
            >= self.runner_extension_points
        ):
            raise ValueError(
                "trail_to_first_target_points must be short of the "
                "runner's target - DoubleTarget precedes the trail in the "
                "chain, so the runner would take profit before the trail "
                f"could ever arm (definition {self.code!r})"
            )
        if self.max_daily_losses is not None and self.max_daily_losses <= 0:
            raise ValueError(
                "max_daily_losses must be positive - a cap of zero would "
                f"forbid every entry (definition {self.code!r})"
            )
        if self.combo_entry and self.unit_time is None:
            raise ValueError(
                "combo_entry requires unit_time - the indicator has no "
                f"timeframe to be evaluated on (definition {self.code!r})"
            )
        if self.combo_entry and not self.double_take_profit:
            raise ValueError(
                "combo_entry requires double_take_profit - the combo "
                "strategy takes TP1 at the mm20 and runs the rest to the "
                f"opposite band (definition {self.code!r})"
            )
        # Everything below describes the 9h reference range - where the
        # entry is searched, where the stop sits, when the day stops
        # trading. A combo definition has no reference range, so nothing
        # would read these; rejecting them here keeps a flag from
        # shipping as a silent no-op, which is what the rest of this
        # method exists for.
        session_range_only = {
            "min_h1_range_points": self.min_h1_range_points,
            "structural_stop": self.structural_stop or None,
            "impulsive_candle_points": self.impulsive_candle_points,
            "last_entry_time": self.last_entry_time,
            "max_daily_losses": self.max_daily_losses,
            "time_cut_minutes": self.time_cut_minutes,
            "stop_from_reference_level": self.stop_from_reference_level
            or None,
            "first_target_fraction": self.first_target_fraction,
            "runner_extension_points": self.runner_extension_points,
            "trail_to_first_target_points": self.trail_to_first_target_points,
        }
        if self.combo_entry:
            for name, value in session_range_only.items():
                if value is not None:
                    raise ValueError(
                        f"{name} describes the 9h reference range, which a "
                        "combo_entry definition does not have "
                        f"(definition {self.code!r})"
                    )
        if self.last_entry_time is not None and not (
            datetime.time(self.market.open_hour, self.market.open_minutes)
            < self.last_entry_time
            <= self._market_close_time()
        ):
            raise ValueError(
                "last_entry_time must fall inside the session - a cut-off "
                "outside it either forbids every entry or can never fire "
                f"(definition {self.code!r})"
            )

    def _market_close_time(self) -> datetime.time:
        """The market's local closing time. end_minute is added as an
        offset because it is documented to exceed 59 when close_hour
        labels the last full H1 candle rather than the literal close."""
        close = datetime.datetime(
            2000, 1, 1, self.market.close_hour
        ) + datetime.timedelta(minutes=self.market.end_minute)
        return close.time()


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
    # Whether the 5-minute fetch actually happened. False marks a partial
    # entry: a definition with a minimum H1 range skipped the 5-minute
    # fetch on a day that fails the filter (FR-033), so m5_candles is
    # empty because nothing was asked for, not because Saxo had nothing.
    # Since the cache is shared by every definition on the instrument, a
    # definition the filter doesn't apply to must complete such an entry
    # rather than read its empty m5_candles as the day's real data.
    m5_fetched: bool = True
