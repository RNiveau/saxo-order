import datetime

import pytest

from api.services.backtest import (
    get_definition,
    list_definitions,
    resolve_parameters,
)
from model import (
    BacktestDefinition,
    BacktestParameters,
    DaxCfdMarket,
    EuCfdMarket,
    EUMarket,
    UnitTime,
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
        assert definition.last_entry_time == datetime.time(16, 0)
        assert definition.max_daily_losses == 2
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

    def test_each_definition_trades_the_session_its_rules_need(self):
        """Derived from the registry rather than a second copy of it, and
        keyed on the rules rather than on codes. Three sessions now: the
        combo backtests read the instrument continuously and take the
        full 02:00-22:00 DAX CFD day; the impulse stop makes holding into
        the evening meaningful, so those variants take 09:00-22:00;
        everything else is flat at the 17:30 cash close."""
        for definition in list_definitions():
            if definition.combo_entry:
                expected: type = DaxCfdMarket
            elif definition.impulsive_candle_points is not None:
                expected = EuCfdMarket
            else:
                expected = EUMarket
            assert isinstance(definition.market, expected)

    def test_g9hicd_is_the_two_lot_impulsive_variant(self):
        definition = get_definition("G9HICD")
        assert definition is not None
        assert (
            definition.display_name
            == "GER40 Bougie de 9h (bougie impulsive, 2 lots)"
        )
        assert definition.double_take_profit is True
        assert definition.runner_extension_points == 100.0
        assert definition.trail_to_first_target_points == 50.0
        # TP1 is the ordinary take-profit, not a fraction of the range.
        assert definition.first_target_fraction is None

    def test_g9hicd_inherits_every_g9hic_rule(self):
        """The pair is a comparison of position management alone, so the
        two definitions must differ *only* in the two-lot fields."""
        single = get_definition("G9HIC")
        double = get_definition("G9HICD")
        assert single is not None and double is not None
        shared = (
            "instrument",
            "default_parameters",
            "min_h1_range_points",
            "impulsive_candle_points",
            "impulsive_close_fraction",
            "last_entry_time",
            "max_daily_losses",
        )
        for field_name in shared:
            assert getattr(single, field_name) == getattr(double, field_name)
        assert type(single.market) is type(double.market)

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

    @pytest.mark.parametrize("cap", [0, -1])
    def test_a_non_positive_loss_cap_is_rejected(self, cap):
        with pytest.raises(ValueError, match="max_daily_losses"):
            self._build(max_daily_losses=cap)

    @pytest.mark.parametrize(
        "cut_off",
        [
            datetime.time(8, 0),  # before the 9:00 open
            datetime.time(9, 0),  # at it, so nothing could ever open
            datetime.time(18, 0),  # after the 17:30 close
        ],
    )
    def test_a_cut_off_outside_the_session_is_rejected(self, cut_off):
        with pytest.raises(ValueError, match="last_entry_time"):
            self._build(last_entry_time=cut_off)

    def test_a_cut_off_inside_the_session_is_accepted(self):
        assert self._build(
            last_entry_time=datetime.time(16, 0)
        ).last_entry_time == datetime.time(16, 0)

    def test_the_cut_off_bound_follows_the_definition_market(self):
        """18:00 is outside EUMarket's session but inside the CFD one."""
        assert self._build(
            market=EuCfdMarket(), last_entry_time=datetime.time(18, 0)
        ).last_entry_time == datetime.time(18, 0)

    def test_a_trail_without_a_first_target_is_rejected(self):
        with pytest.raises(ValueError, match="first target to trail to"):
            self._build(trail_to_first_target_points=50.0)

    @pytest.mark.parametrize("trigger", [0, -50.0])
    def test_a_non_positive_trail_trigger_is_rejected(self, trigger):
        with pytest.raises(ValueError, match="must be positive"):
            self._build(
                double_take_profit=True,
                runner_extension_points=100.0,
                trail_to_first_target_points=trigger,
            )

    @pytest.mark.parametrize("trigger", [100.0, 150.0])
    def test_a_trail_at_or_past_the_runner_target_is_rejected(self, trigger):
        """The trail would never arm: DoubleTarget precedes it in the
        chain, so the runner takes profit on any candle that reaches
        TP1 + extension."""
        with pytest.raises(ValueError, match="short of the runner"):
            self._build(
                double_take_profit=True,
                runner_extension_points=100.0,
                trail_to_first_target_points=trigger,
            )

    def test_two_target_placements_at_once_are_rejected(self):
        with pytest.raises(ValueError, match="exactly one"):
            self._build(
                double_take_profit=True,
                first_target_fraction=0.5,
                runner_extension_points=100.0,
            )

    def test_double_take_profit_with_no_placement_is_rejected(self):
        with pytest.raises(ValueError, match="nowhere to take profit"):
            self._build(double_take_profit=True)

    def test_runner_extension_without_double_take_profit_is_rejected(self):
        with pytest.raises(ValueError, match="only used with"):
            self._build(runner_extension_points=100.0)

    @pytest.mark.parametrize("extension", [0, -100.0])
    def test_a_non_positive_runner_extension_is_rejected(self, extension):
        with pytest.raises(ValueError, match="must be positive"):
            self._build(
                double_take_profit=True, runner_extension_points=extension
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


class TestComboDefinitionValidation:
    """A combo definition is driven by the indicator and has no 9h
    reference range, so every flag describing that range must be
    rejected at construction rather than shipped as a no-op."""

    def _build(self, **kwargs):
        return BacktestDefinition(
            code="BADCOMBO",
            name="bad",
            display_name="bad",
            instrument="GER40.I",
            **kwargs,
        )

    def _combo(self, **kwargs):
        return self._build(
            combo_entry=True,
            unit_time=UnitTime.M15,
            double_take_profit=True,
            **kwargs,
        )

    def test_a_valid_combo_definition_is_accepted(self):
        definition = self._combo()
        assert definition.combo_entry is True
        assert definition.unit_time == UnitTime.M15
        assert definition.first_target_fraction is None
        assert definition.runner_extension_points is None

    def test_combo_without_a_timeframe_is_rejected(self):
        with pytest.raises(ValueError, match="unit_time"):
            self._build(combo_entry=True, double_take_profit=True)

    def test_combo_without_double_take_profit_is_rejected(self):
        with pytest.raises(ValueError, match="double_take_profit"):
            self._build(combo_entry=True, unit_time=UnitTime.M15)

    @pytest.mark.parametrize(
        "flag,value",
        [
            ("min_h1_range_points", 40.0),
            ("structural_stop", True),
            ("stop_from_reference_level", True),
            ("last_entry_time", datetime.time(16, 0)),
            ("max_daily_losses", 2),
            ("first_target_fraction", 0.5),
            ("runner_extension_points", 100.0),
            ("trail_to_first_target_points", 50.0),
            ("ma50_direction_filter", UnitTime.H1),
        ],
    )
    def test_session_range_flags_are_rejected_on_a_combo(self, flag, value):
        with pytest.raises(ValueError, match="reference range"):
            self._combo(**{flag: value})

    def test_a_combo_impulse_stop_is_rejected(self):
        with pytest.raises(ValueError, match="reference range"):
            self._combo(
                impulsive_candle_points=70.0, impulsive_close_fraction=0.25
            )

    def test_a_combo_time_cut_is_rejected(self):
        """Caught by the older double-take-profit/time-cut rule before
        the combo one, hence the different message - what matters is
        that the combination cannot be registered."""
        with pytest.raises(ValueError, match="time cut"):
            self._combo(time_cut_minutes=30, time_cut_min_favorable_points=5.0)

    def test_a_session_range_definition_still_needs_a_target_placement(self):
        """The combo exemption must not weaken the rule for everyone
        else: a non-combo double take-profit still has to say where its
        first lot exits."""
        with pytest.raises(ValueError, match="first_target_fraction"):
            self._build(double_take_profit=True)


class TestComboRegistry:
    @pytest.mark.parametrize(
        "code,ut,label",
        [
            ("C5M", UnitTime.M5, "5m"),
            ("C15M", UnitTime.M15, "15m"),
            ("C1H", UnitTime.H1, "H1"),
        ],
    )
    def test_the_three_timeframes_are_registered(self, code, ut, label):
        definition = get_definition(code)
        assert definition is not None
        assert definition.display_name == f"GER40 Combo {label}"
        assert definition.instrument == "GER40.I"
        assert definition.unit_time == ut
        assert definition.combo_entry is True
        assert definition.double_take_profit is True

    def test_they_trade_the_full_dax_cfd_session(self):
        """02:00-22:00, not the 09:00-22:00 the impulsive variants use:
        the combo strategy reads the instrument continuously and should
        see the pre-open hours too."""
        for code in ("C5M", "C15M", "C1H"):
            definition = get_definition(code)
            assert isinstance(definition.market, DaxCfdMarket)
            assert definition.market.open_hour == 2

    def test_they_default_to_a_50_point_stop(self):
        for code in ("C5M", "C15M", "C1H"):
            assert (
                get_definition(code).default_parameters.stop_loss_points == 50
            )

    def test_they_differ_only_in_timeframe(self):
        """The comparison the feature exists for is only meaningful if
        nothing else varies between the three."""
        definitions = [get_definition(c) for c in ("C5M", "C15M", "C1H")]
        shared = (
            "instrument",
            "default_parameters",
            "combo_entry",
            "double_take_profit",
        )
        first = definitions[0]
        for field_name in shared:
            for other in definitions[1:]:
                assert getattr(other, field_name) == getattr(first, field_name)
        assert len({d.unit_time for d in definitions}) == 3

    def test_no_session_range_definition_gained_a_timeframe(self):
        for definition in list_definitions():
            if not definition.combo_entry:
                assert definition.unit_time is None


class TestComboParameters:
    def test_only_the_stop_is_tunable(self):
        """FR-C16: the other three describe a reference range this
        strategy does not have, so an override for them must not be
        silently carried into the run."""
        definition = get_definition("C15M")
        resolved = resolve_parameters(
            definition,
            stop_loss_points=80,
            take_profit_offset_points=999,
            break_even_trigger_points=999,
            max_entry_distance_points=999,
        )
        assert resolved.stop_loss_points == 80
        assert resolved == BacktestParameters(stop_loss_points=80)

    def test_an_omitted_stop_falls_back_to_the_definition_default(self):
        assert resolve_parameters(get_definition("C5M")).stop_loss_points == 50

    def test_a_session_range_definition_still_takes_all_four(self):
        resolved = resolve_parameters(
            get_definition("G9H"),
            take_profit_offset_points=7,
            max_entry_distance_points=11,
        )
        assert resolved.take_profit_offset_points == 7
        assert resolved.max_entry_distance_points == 11
