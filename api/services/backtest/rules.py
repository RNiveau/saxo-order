"""Turning a BacktestDefinition into the exit-policy chain it runs on.

This is the one place that reads a definition's variant flags. Everything
downstream sees a chain of policies and never asks which backtest it is
running, so adding a variant means composing existing policies here (or
adding one policy) rather than threading another boolean through the
engine.
"""

import datetime
from typing import List

from api.services.backtest.entry_gate import (
    ALWAYS_OPEN,
    EntryGate,
    FilteredEntry,
    cutoff_utc,
)
from api.services.backtest.lots import (
    SINGLE_LOT,
    ComboTwoLot,
    ExtendedTwoLot,
    LotModel,
    TwoLot,
    TwoLotAccounting,
)
from api.services.backtest.policies import (
    ArmBreakEven,
    DoubleTarget,
    ExitPolicy,
    ImpulsiveStop,
    Stop,
    StructuralStop,
    Target,
    TimeCut,
    TrailToFirstTarget,
)
from model import BacktestDefinition, BacktestParameters


def build_exit_chain(
    definition: BacktestDefinition, params: BacktestParameters
) -> List[ExitPolicy]:
    """The definition's exit rules, in the order they are evaluated on
    each candle.

    The stop leads (FR-009: a stop and a target reached on the same candle
    resolve conservatively as the stop) - except for the close-measured
    stops (structural, impulsive), which are evaluated after the target,
    since a target is reached intrabar. Break-even arming always trails,
    since it closes nothing and must only apply to later candles.
    """
    chain: List[ExitPolicy] = []
    close_measured_stop = (
        definition.structural_stop
        or definition.impulsive_candle_points is not None
    )

    if close_measured_stop:
        # No fixed stop distance applies until break-even arms; until then
        # the stop is the close-measured rule appended below.
        chain.append(Stop(only_when_armed=True))
    else:
        chain.append(Stop())

    two_lot = isinstance(build_lot_model(definition), TwoLotAccounting)
    chain.append(DoubleTarget() if two_lot else Target())

    if definition.structural_stop:
        chain.append(StructuralStop())

    if (
        definition.impulsive_candle_points is not None
        and definition.impulsive_close_fraction is not None
    ):
        chain.append(
            ImpulsiveStop(
                definition.impulsive_candle_points,
                definition.impulsive_close_fraction,
            )
        )

    if (
        definition.time_cut_minutes is not None
        and definition.time_cut_min_favorable_points is not None
    ):
        chain.append(
            TimeCut(
                definition.time_cut_minutes,
                definition.time_cut_min_favorable_points,
            )
        )

    if not definition.combo_entry:
        # The combo strategy has exactly one path to break-even: TP1
        # filling, which DoubleTarget arms itself (FR-C08). It has no
        # favorable-move trigger, and break_even_trigger_points is one
        # of the three thresholds that mean nothing to it (FR-C16), so
        # arming off that value would invent a rule the spec does not
        # have.
        chain.append(ArmBreakEven(params.break_even_trigger_points))

    if definition.trail_to_first_target_points is not None:
        chain.append(
            TrailToFirstTarget(definition.trail_to_first_target_points)
        )
    return chain


def build_entry_gate(
    definition: BacktestDefinition, trading_date: datetime.date
) -> EntryGate:
    """The definition's entry filters (FR-G19/FR-G20), or a gate that
    allows everything when it carries none - so the engine never asks
    which backtest it is running.

    Built per day, because the cut-off resolves to a different UTC instant
    either side of a DST boundary and the loss counter is per trading
    day."""
    if (
        definition.last_entry_time is None
        and definition.max_daily_losses is None
    ):
        return ALWAYS_OPEN
    cutoff = (
        cutoff_utc(definition.last_entry_time, definition.market, trading_date)
        if definition.last_entry_time is not None
        else None
    )
    return FilteredEntry(cutoff, definition.max_daily_losses)


def build_lot_model(definition: BacktestDefinition) -> LotModel:
    """The definition's position sizing.

    A combo definition is the one two-lot setup that places no target at
    entry - its mm20 and opposite band are read from each candle - so it
    is answered before the placement fields are consulted.

    For every other definition BacktestDefinition rejects a double
    take-profit with no first-target fraction, so the tail raises rather
    than degrading to a single lot: two answers to one question is how a
    flag ends up silently not applying, which is the thing this refactor
    removed."""
    if not definition.double_take_profit:
        return SINGLE_LOT
    if definition.combo_entry:
        return ComboTwoLot()
    if definition.runner_extension_points is not None:
        return ExtendedTwoLot(definition.runner_extension_points)
    if definition.first_target_fraction is None:
        raise ValueError(
            "double_take_profit requires first_target_fraction or "
            "runner_extension_points - the first lot would have nowhere "
            f"to exit (definition {definition.code!r})"
        )
    return TwoLot(definition.first_target_fraction)
