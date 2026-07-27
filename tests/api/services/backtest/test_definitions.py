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
        assert codes == ["B9H", "B9HTC", "G9H", "G9HSL", "B9HWS"]

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

    def test_g9hsl_is_the_ger40_single_lot_control(self):
        definition = get_definition("G9HSL")
        assert definition is not None
        assert definition.display_name == "GER40 Bougie de 9h (lot unique)"
        assert definition.instrument == "GER40.I"
        assert definition.double_take_profit is False
        assert definition.first_target_fraction is None
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
    """A definition is read once, when the exit chain and lot model are
    built. A flag that could not take effect there has to be rejected at
    construction, or the backtest reports results for a rule it never
    applied."""

    def _build(self, **kwargs):
        return BacktestDefinition(
            code="BAD",
            name="bad",
            display_name="bad",
            instrument="GER40.I",
            **kwargs,
        )

    def test_double_take_profit_with_time_cut_is_rejected(self):
        with pytest.raises(ValueError, match="time cut"):
            self._build(
                double_take_profit=True,
                first_target_fraction=0.5,
                time_cut_minutes=30,
                time_cut_min_favorable_points=5.0,
            )

    def test_double_take_profit_without_a_first_target_is_rejected(self):
        with pytest.raises(ValueError, match="first_target_fraction"):
            self._build(double_take_profit=True)

    def test_first_target_without_double_take_profit_is_rejected(self):
        with pytest.raises(ValueError, match="only used with"):
            self._build(first_target_fraction=0.5)

    @pytest.mark.parametrize("fraction", [0, 1, 1.5, -0.2])
    def test_first_target_outside_the_range_is_rejected(self, fraction):
        with pytest.raises(ValueError):
            self._build(
                double_take_profit=True, first_target_fraction=fraction
            )

    def test_half_configured_time_cut_is_rejected(self):
        with pytest.raises(ValueError, match="time cut needs both"):
            self._build(time_cut_minutes=30)
        with pytest.raises(ValueError, match="time cut needs both"):
            self._build(time_cut_min_favorable_points=5.0)

    def test_the_shipped_definitions_are_all_valid(self):
        """The registry is built at import time, so this passes trivially
        - it is here so a future definition that trips a rule fails in
        this file rather than at application startup."""
        assert len(list_definitions()) == 5
