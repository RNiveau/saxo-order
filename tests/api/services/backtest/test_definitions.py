import pytest

from api.services.backtest import (
    get_definition,
    list_definitions,
    resolve_parameters,
)
from model import (
    BacktestDefinition,
    BacktestParameters,
    EuCfdMarket,
    EUMarket,
)


class TestRegistry:
    def test_the_default_menu_selection_does_not_move(self):
        """BACKTEST_DEFINITIONS order is the Backtest menu's dropdown
        order, and Backtest.tsx selects defs[0] on load - so the first
        entry is user-visible state, not an implementation detail.
        Only the first is pinned: appending a definition is free, moving
        the default is not."""
        assert list_definitions()[0].code == "B9H"

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

    def test_g9hic_is_the_impulsive_candle_variant(self):
        definition = get_definition("G9HIC")
        assert definition is not None
        assert (
            definition.display_name == "GER40 Bougie de 9h (bougie impulsive)"
        )
        assert definition.instrument == "GER40.I"
        assert definition.min_h1_range_points == 70.0
        assert definition.impulsive_candle_points == 70.0
        assert definition.impulsive_close_fraction == 0.25
        # Single lot, and no close-measured stop other than the impulse.
        assert definition.double_take_profit is False
        assert definition.structural_stop is False
        assert definition.stop_from_reference_level is False
        assert definition.default_parameters == BacktestParameters(
            stop_loss_points=150,
            take_profit_offset_points=10,
            break_even_trigger_points=50,
            max_entry_distance_points=40,
        )

    def test_g9hic_trades_the_cfd_session(self):
        definition = get_definition("G9HIC")
        assert definition is not None
        assert isinstance(definition.market, EuCfdMarket)
        assert (
            definition.market.open_hour,
            definition.market.open_minutes,
        ) == (
            9,
            0,
        )
        # 21:00 + 60 minutes = a 22:00 Paris close.
        assert (
            definition.market.close_hour,
            definition.market.end_minute,
        ) == (
            21,
            60,
        )

    def test_only_the_impulsive_variant_left_the_cash_session(self):
        """Derived from the registry rather than a second copy of it: any
        definition that silently changed session would fail here."""
        for definition in list_definitions():
            expected = EuCfdMarket if definition.code == "G9HIC" else EUMarket
            assert isinstance(definition.market, expected)

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

    def test_half_configured_impulse_is_rejected(self):
        with pytest.raises(ValueError, match="impulsive-candle stop needs"):
            self._build(impulsive_candle_points=70.0)
        with pytest.raises(ValueError, match="impulsive-candle stop needs"):
            self._build(impulsive_close_fraction=0.25)

    @pytest.mark.parametrize("points", [0, -70.0])
    def test_a_non_positive_impulse_threshold_is_rejected(self, points):
        with pytest.raises(ValueError, match="must be positive"):
            self._build(
                impulsive_candle_points=points, impulsive_close_fraction=0.25
            )

    @pytest.mark.parametrize("fraction", [0, 1, 1.5, -0.2])
    def test_an_impulse_fraction_outside_the_candle_is_rejected(
        self, fraction
    ):
        with pytest.raises(ValueError, match="impulsive_close_fraction"):
            self._build(
                impulsive_candle_points=70.0,
                impulsive_close_fraction=fraction,
            )

    def test_an_impulse_with_a_structural_stop_is_rejected(self):
        with pytest.raises(ValueError, match="structural stop"):
            self._build(
                impulsive_candle_points=70.0,
                impulsive_close_fraction=0.25,
                structural_stop=True,
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
        assert list_definitions()
