import pytest

from api.services.backtest import (
    get_definition,
    list_definitions,
    resolve_parameters,
)
from model import BacktestDefinition, BacktestParameters


class TestRegistry:
    def test_lists_the_hardcoded_backtests_in_order(self):
        definitions = list_definitions()
        codes = [definition.code for definition in definitions]
        assert codes == ["B9H", "B9HTC", "G9H", "B9HWS"]

    def test_b9h_is_the_plain_single_lot_variant(self):
        definition = get_definition("B9H")
        assert definition is not None
        assert definition.display_name == "CAC40 Bougie de 9h"
        assert definition.instrument == "FRA40.I"
        assert definition.time_cut_minutes is None
        assert definition.double_take_profit is False
        assert definition.structural_stop is False

    def test_b9htc_carries_the_time_cut(self):
        definition = get_definition("B9HTC")
        assert definition is not None
        assert definition.time_cut_minutes == 30
        assert definition.time_cut_min_favorable_points == 5.0

    def test_g9h_is_the_ger40_double_take_profit_variant(self):
        definition = get_definition("G9H")
        assert definition is not None
        assert definition.instrument == "GER40.I"
        assert definition.double_take_profit is True
        assert definition.first_target_fraction == 0.5
        assert definition.stop_from_reference_level is True
        assert definition.default_parameters == BacktestParameters(
            stop_loss_points=150,
            take_profit_offset_points=10,
            break_even_trigger_points=50,
            max_entry_distance_points=40,
        )

    def test_b9hws_is_the_wide_range_structural_variant(self):
        definition = get_definition("B9HWS")
        assert definition is not None
        assert (
            definition.display_name
            == "CAC40 Bougie de 9h (wide-range structural stop)"
        )
        assert definition.min_h1_range_points == 40.0
        assert definition.structural_stop is True

    def test_unknown_code_returns_none(self):
        assert get_definition("NOPE") is None


class TestResolveParameters:
    def test_omitted_overrides_fall_back_to_definition_defaults(self):
        """GER40 must get 150/10/50/40, not the BacktestParameters
        class defaults of 50/10/20/20."""
        definition = get_definition("G9H")
        assert definition is not None
        assert resolve_parameters(definition) == definition.default_parameters

    def test_cac40_falls_back_to_the_class_defaults(self):
        definition = get_definition("B9H")
        assert definition is not None
        assert resolve_parameters(definition) == BacktestParameters()

    def test_overrides_win_over_definition_defaults(self):
        definition = get_definition("G9H")
        assert definition is not None
        resolved = resolve_parameters(
            definition, stop_loss_points=99, max_entry_distance_points=11
        )
        assert resolved.stop_loss_points == 99
        assert resolved.max_entry_distance_points == 11
        # untouched thresholds keep the definition's defaults
        assert resolved.take_profit_offset_points == 10
        assert resolved.break_even_trigger_points == 50


class TestBacktestDefinitionValidation:
    def test_double_take_profit_with_time_cut_is_rejected(self):
        """PR #659 review #3: the double-TP exit path does not evaluate the
        time cut, so combining them would silently ignore the cut."""
        with pytest.raises(ValueError):
            BacktestDefinition(
                code="BAD",
                name="bad",
                display_name="bad",
                instrument="GER40.I",
                double_take_profit=True,
                time_cut_minutes=30,
                time_cut_min_favorable_points=5.0,
            )
