"""The exit chain each definition composes.

The chain's *order* encodes the conservative same-candle conventions, and
its membership is the only place a definition's variant flags are read -
so both are asserted here rather than inferred from engine behavior.
"""

import datetime

from api.services.backtest.entry_gate import ALWAYS_OPEN, FilteredEntry
from api.services.backtest.lots import SINGLE_LOT, ExtendedTwoLot, TwoLot
from api.services.backtest.policies import (
    ArmBreakEven,
    DoubleTarget,
    ImpulsiveStop,
    Stop,
    StructuralStop,
    Target,
    TimeCut,
    TrailToFirstTarget,
)
from api.services.backtest.rules import (
    build_entry_gate,
    build_exit_chain,
    build_lot_model,
)
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

    def test_a_two_lot_impulse_definition_composes_both(self):
        """G9HICD is the first shipped definition to combine the double
        take-profit with the impulse stop; they compose without either
        being special-cased."""
        definition = _definition(
            impulsive_candle_points=70.0,
            impulsive_close_fraction=0.25,
            double_take_profit=True,
            runner_extension_points=100.0,
        )
        assert _shape(definition) == [
            Stop,
            DoubleTarget,
            ImpulsiveStop,
            ArmBreakEven,
        ]

    def test_impulsive_stop_is_evaluated_after_the_target(self):
        """Like the structural stop, the impulse is measured on the close,
        so an intrabar target touch beats it."""
        definition = _definition(
            impulsive_candle_points=70.0, impulsive_close_fraction=0.25
        )
        assert _shape(definition) == [
            Stop,
            Target,
            ImpulsiveStop,
            ArmBreakEven,
        ]

    def test_impulsive_variant_has_no_fixed_stop_until_break_even_arms(self):
        definition = _definition(
            impulsive_candle_points=70.0, impulsive_close_fraction=0.25
        )
        chain = build_exit_chain(definition, PARAMS)
        stop = chain[0]
        assert isinstance(stop, Stop)
        assert stop.only_when_armed is True

    def test_the_impulse_policy_carries_the_definition_thresholds(self):
        definition = _definition(
            impulsive_candle_points=70.0, impulsive_close_fraction=0.25
        )
        impulse = build_exit_chain(definition, PARAMS)[2]
        assert isinstance(impulse, ImpulsiveStop)
        assert (impulse.points, impulse.fraction) == (70.0, 0.25)

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
            _definition(
                impulsive_candle_points=70.0, impulsive_close_fraction=0.25
            ),
        ):
            chain = build_exit_chain(definition, PARAMS)
            assert isinstance(chain[-1], ArmBreakEven)


class TestTrailPolicy:
    def test_the_trail_is_appended_after_break_even_arming(self):
        """Both are arming policies that close nothing and take effect on
        later candles, so both trail the chain."""
        definition = _definition(
            double_take_profit=True,
            runner_extension_points=100.0,
            trail_to_first_target_points=50.0,
        )
        assert _shape(definition) == [
            Stop,
            DoubleTarget,
            ArmBreakEven,
            TrailToFirstTarget,
        ]

    def test_the_trigger_is_carried_onto_the_policy(self):
        definition = _definition(
            double_take_profit=True,
            runner_extension_points=100.0,
            trail_to_first_target_points=50.0,
        )
        trail = build_exit_chain(definition, PARAMS)[-1]
        assert isinstance(trail, TrailToFirstTarget)
        assert trail.trigger_points == 50.0

    def test_definitions_without_a_trigger_get_no_trail(self):
        for definition in (
            _definition(),
            _definition(double_take_profit=True, first_target_fraction=0.5),
        ):
            chain = build_exit_chain(definition, PARAMS)
            assert not any(
                isinstance(policy, TrailToFirstTarget) for policy in chain
            )


class TestLotModelSelection:
    def test_a_plain_definition_is_a_single_lot(self):
        assert build_lot_model(_definition()) is SINGLE_LOT

    def test_a_fraction_selects_the_range_split_model(self):
        model = build_lot_model(
            _definition(double_take_profit=True, first_target_fraction=0.5)
        )
        assert isinstance(model, TwoLot)
        assert model.first_target_fraction == 0.5

    def test_a_runner_extension_selects_the_extended_model(self):
        model = build_lot_model(
            _definition(double_take_profit=True, runner_extension_points=100.0)
        )
        assert isinstance(model, ExtendedTwoLot)
        assert model.extension_points == 100.0


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


class TestEntryGate:
    """Entry filters are read here, the same place the exit chain is
    built, so a definition's flags stay read in exactly one module."""

    TRADING_DATE = datetime.date(2026, 6, 2)

    def test_a_definition_without_filters_gets_the_always_open_gate(self):
        gate = build_entry_gate(_definition(), self.TRADING_DATE)

        assert gate is ALWAYS_OPEN

    def test_the_filters_are_carried_onto_the_gate(self):
        definition = _definition(
            last_entry_time=datetime.time(16, 0), max_daily_losses=2
        )

        gate = build_entry_gate(definition, self.TRADING_DATE)

        assert isinstance(gate, FilteredEntry)
        assert gate.cutoff_utc == datetime.datetime(2026, 6, 2, 14, 0)
        assert gate.max_losses == 2

    def test_either_filter_alone_still_builds_a_gate(self):
        cut_off_only = build_entry_gate(
            _definition(last_entry_time=datetime.time(16, 0)),
            self.TRADING_DATE,
        )
        cap_only = build_entry_gate(
            _definition(max_daily_losses=2), self.TRADING_DATE
        )

        assert cut_off_only.max_losses is None
        assert cap_only.cutoff_utc is None

    def test_exactly_the_impulsive_variants_ship_with_entry_filters(self):
        """Keyed on the rule rather than on codes: the entry filters bound
        a strategy whose worst case is unbounded, which is what the
        impulse stop creates - so the two travel together."""
        from api.services.backtest import list_definitions

        filtered = {
            definition.code
            for definition in list_definitions()
            if build_entry_gate(definition, self.TRADING_DATE)
            is not ALWAYS_OPEN
        }
        impulsive = {
            definition.code
            for definition in list_definitions()
            if definition.impulsive_candle_points is not None
        }
        assert filtered == impulsive


class TestRegisteredDefinitionChains:
    """Every shipped backtest, so a chain-building change that alters one
    of them has to be deliberate."""

    def test_shipped_chains(self):
        from api.services.backtest import list_definitions

        expected = {
            "B9H": [Stop, Target, ArmBreakEven],
            "B9HTC": [Stop, Target, TimeCut, ArmBreakEven],
            "G9H": [Stop, DoubleTarget, ArmBreakEven],
            "G9HSL": [Stop, Target, ArmBreakEven],
            "B9HWS": [Stop, Target, StructuralStop, ArmBreakEven],
            "G9HIC": [Stop, Target, ImpulsiveStop, ArmBreakEven],
            "G9HICD": [
                Stop,
                DoubleTarget,
                ImpulsiveStop,
                ArmBreakEven,
                TrailToFirstTarget,
            ],
            # The MM50 variants filter *entries*; their exit chain is
            # G9HIC's, unchanged.
            "G9HICMH": [Stop, Target, ImpulsiveStop, ArmBreakEven],
            "G9HICMD": [Stop, Target, ImpulsiveStop, ArmBreakEven],
            # No ArmBreakEven: TP1 filling is the combo strategy's only
            # path to break-even (FR-C08), and DoubleTarget arms it.
            "C5M": [Stop, DoubleTarget],
            "C15M": [Stop, DoubleTarget],
            "C1H": [Stop, DoubleTarget],
        }
        actual = {
            definition.code: _shape(definition)
            for definition in list_definitions()
        }
        assert actual == expected
