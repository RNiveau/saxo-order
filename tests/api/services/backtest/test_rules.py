"""The exit chain each definition composes.

The chain's *order* encodes the conservative same-candle conventions, and
its membership is the only place a definition's variant flags are read -
so both are asserted here rather than inferred from engine behavior.
"""

from api.services.backtest.policies import (
    ArmBreakEven,
    DoubleTarget,
    Stop,
    StructuralStop,
    Target,
    TimeCut,
)
from api.services.backtest.rules import build_exit_chain
from model import BacktestDefinition, BacktestParameters

PARAMS = BacktestParameters()


def _definition(**kwargs) -> BacktestDefinition:
    return BacktestDefinition(
        code="X",
        name="x",
        display_name="x",
        instrument="FRA40.I",
        **kwargs,
    )


def _shape(definition):
    return [type(policy) for policy in build_exit_chain(definition, PARAMS)]


class TestChainShape:
    def test_plain_definition_is_stop_target_arm(self):
        assert _shape(_definition()) == [Stop, Target, ArmBreakEven]

    def test_time_cut_sits_after_the_target(self):
        definition = _definition(
            time_cut_minutes=30, time_cut_min_favorable_points=5.0
        )
        assert _shape(definition) == [Stop, Target, TimeCut, ArmBreakEven]

    def test_double_take_profit_swaps_the_target_policy(self):
        definition = _definition(
            double_take_profit=True, first_target_fraction=0.5
        )
        assert _shape(definition) == [Stop, DoubleTarget, ArmBreakEven]

    def test_structural_stop_is_evaluated_after_the_target(self):
        """The structural stop is measured on the candle's close, which
        happens after an intrabar target touch."""
        definition = _definition(structural_stop=True)
        assert _shape(definition) == [
            Stop,
            Target,
            StructuralStop,
            ArmBreakEven,
        ]

    def test_structural_variant_has_no_fixed_stop_until_break_even_arms(self):
        chain = build_exit_chain(_definition(structural_stop=True), PARAMS)
        stop = chain[0]
        assert isinstance(stop, Stop)
        assert stop.only_when_armed is True

    def test_non_structural_stop_applies_from_the_first_candle(self):
        chain = build_exit_chain(_definition(), PARAMS)
        assert chain[0].only_when_armed is False

    def test_break_even_arming_always_trails(self):
        for definition in (
            _definition(),
            _definition(structural_stop=True),
            _definition(double_take_profit=True, first_target_fraction=0.5),
            _definition(
                time_cut_minutes=30, time_cut_min_favorable_points=5.0
            ),
        ):
            chain = build_exit_chain(definition, PARAMS)
            assert isinstance(chain[-1], ArmBreakEven)


class TestChainComposition:
    """Combinations that used to be dropped on the floor: the old code
    routed to one of three hand-written resolvers, so a second variant
    flag on the same definition was silently ignored. Composing the chain
    means every flag that is set is now evaluated."""

    def test_structural_stop_and_time_cut_both_apply(self):
        definition = _definition(
            structural_stop=True,
            time_cut_minutes=30,
            time_cut_min_favorable_points=5.0,
        )
        assert _shape(definition) == [
            Stop,
            Target,
            StructuralStop,
            TimeCut,
            ArmBreakEven,
        ]

    def test_structural_stop_and_double_take_profit_both_apply(self):
        definition = _definition(
            structural_stop=True,
            double_take_profit=True,
            first_target_fraction=0.5,
        )
        assert _shape(definition) == [
            Stop,
            DoubleTarget,
            StructuralStop,
            ArmBreakEven,
        ]


class TestRegisteredDefinitionChains:
    """The four shipped backtests, so a chain-building change that alters
    one of them has to be deliberate."""

    def test_shipped_chains(self):
        from api.services.backtest import list_definitions

        expected = {
            "B9H": [Stop, Target, ArmBreakEven],
            "B9HTC": [Stop, Target, TimeCut, ArmBreakEven],
            "G9H": [Stop, DoubleTarget, ArmBreakEven],
            "B9HWS": [Stop, Target, StructuralStop, ArmBreakEven],
        }
        actual = {
            definition.code: _shape(definition)
            for definition in list_definitions()
        }
        assert actual == expected
