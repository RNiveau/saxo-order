"""Turning a BacktestDefinition into the exit-policy chain it runs on.

This is the one place that reads a definition's variant flags. Everything
downstream sees a chain of policies and never asks which backtest it is
running, so adding a variant means composing existing policies here (or
adding one policy) rather than threading another boolean through the
engine.
"""

from typing import List

from api.services.backtest.lots import SINGLE_LOT, LotModel, TwoLot
from api.services.backtest.policies import (
    ArmBreakEven,
    DoubleTarget,
    ExitPolicy,
    Stop,
    StructuralStop,
    Target,
    TimeCut,
)
from model import BacktestDefinition, BacktestParameters


def build_exit_chain(
    definition: BacktestDefinition, params: BacktestParameters
) -> List[ExitPolicy]:
    """The definition's exit rules, in the order they are evaluated on
    each candle.

    The stop leads (FR-009: a stop and a target reached on the same candle
    resolve conservatively as the stop) - except under a structural stop,
    which is measured on the close and so is evaluated after the target,
    which is reached intrabar. Break-even arming always trails, since it
    closes nothing and must only apply to later candles.
    """
    chain: List[ExitPolicy] = []

    if definition.structural_stop:
        # No fixed stop distance applies until break-even arms; until then
        # the stop is the close-beyond-level rule below.
        chain.append(Stop(only_when_armed=True))
    else:
        chain.append(Stop())

    two_lot = isinstance(build_lot_model(definition), TwoLot)
    chain.append(DoubleTarget() if two_lot else Target())

    if definition.structural_stop:
        chain.append(StructuralStop())

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

    chain.append(ArmBreakEven(params.break_even_trigger_points))
    return chain


def build_lot_model(definition: BacktestDefinition) -> LotModel:
    """The definition's position sizing.

    BacktestDefinition already rejects a double take-profit with no
    first-target fraction, so this raises rather than degrading to a
    single lot: two answers to one question is how a flag ends up
    silently not applying, which is the thing this refactor removed."""
    if not definition.double_take_profit:
        return SINGLE_LOT
    if definition.first_target_fraction is None:
        raise ValueError(
            "double_take_profit requires first_target_fraction - the "
            f"first lot would have nowhere to exit (definition "
            f"{definition.code!r})"
        )
    return TwoLot(definition.first_target_fraction)
