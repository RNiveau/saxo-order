"""Turning a BacktestDefinition into the exit-policy chain it runs on.

This is the one place that reads a definition's variant flags. Everything
downstream sees a chain of policies and never asks which backtest it is
running, so adding a variant means composing existing policies here (or
adding one policy) rather than threading another boolean through the
engine.
"""

from typing import List

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

    chain.append(DoubleTarget() if definition.double_take_profit else Target())

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
