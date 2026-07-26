"""The registry of hardcoded backtests exposed by the Backtest menu."""

from typing import List, Optional

from model import BacktestDefinition, BacktestParameters, Strategy

BACKTEST_DEFINITIONS: List[BacktestDefinition] = [
    BacktestDefinition(
        code="B9H",
        name=Strategy.B9H.value,
        display_name="CAC40 Bougie de 9h",
        instrument="FRA40.I",
    ),
    BacktestDefinition(
        code="B9HTC",
        name=Strategy.B9HTC.value,
        display_name="CAC40 Bougie de 9h (time cut)",
        instrument="FRA40.I",
        time_cut_minutes=30,
        time_cut_min_favorable_points=5.0,
    ),
    BacktestDefinition(
        code="G9H",
        name=Strategy.G9H.value,
        display_name="GER40 Bougie de 9h",
        instrument="GER40.I",
        default_parameters=BacktestParameters(
            stop_loss_points=150,
            take_profit_offset_points=10,
            break_even_trigger_points=50,
            max_entry_distance_points=40,
        ),
        double_take_profit=True,
        first_target_fraction=0.5,
        stop_from_reference_level=True,
    ),
    BacktestDefinition(
        code="B9HWS",
        name=Strategy.B9HWS.value,
        display_name="CAC40 Bougie de 9h (wide-range structural stop)",
        instrument="FRA40.I",
        min_h1_range_points=40.0,
        structural_stop=True,
    ),
]


def list_definitions() -> List[BacktestDefinition]:
    return BACKTEST_DEFINITIONS


def get_definition(code: str) -> Optional[BacktestDefinition]:
    for definition in BACKTEST_DEFINITIONS:
        if definition.code == code:
            return definition
    return None


def resolve_parameters(
    definition: BacktestDefinition,
    stop_loss_points: Optional[float] = None,
    take_profit_offset_points: Optional[float] = None,
    break_even_trigger_points: Optional[float] = None,
    max_entry_distance_points: Optional[float] = None,
) -> BacktestParameters:
    """Merge per-run overrides onto the definition's default thresholds.
    An omitted (None) override falls back to definition.default_parameters,
    so each definition keeps its own defaults - CAC40 50/10/20/20, GER40
    150/10/50/40."""
    defaults = definition.default_parameters
    return BacktestParameters(
        stop_loss_points=(
            stop_loss_points
            if stop_loss_points is not None
            else defaults.stop_loss_points
        ),
        take_profit_offset_points=(
            take_profit_offset_points
            if take_profit_offset_points is not None
            else defaults.take_profit_offset_points
        ),
        break_even_trigger_points=(
            break_even_trigger_points
            if break_even_trigger_points is not None
            else defaults.break_even_trigger_points
        ),
        max_entry_distance_points=(
            max_entry_distance_points
            if max_entry_distance_points is not None
            else defaults.max_entry_distance_points
        ),
    )
