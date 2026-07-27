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
    # Control run for G9H: the same GER40 setup and the same 150-point
    # stop measured from the H1 reference level, but a single lot and a
    # single take-profit. Isolates what the double take-profit overlay
    # itself contributes. Note it also drops the TP1 entry filter (a
    # midpoint that only exists under double_take_profit), so it takes
    # entries G9H rejects rather than the same entries at half size.
    BacktestDefinition(
        code="G9HSL",
        name=Strategy.G9HSL.value,
        display_name="GER40 Bougie de 9h (lot unique)",
        instrument="GER40.I",
        default_parameters=BacktestParameters(
            stop_loss_points=150,
            take_profit_offset_points=10,
            break_even_trigger_points=50,
            max_entry_distance_points=40,
        ),
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


def is_below_min_range(
    definition: BacktestDefinition, h1_high: float, h1_low: float
) -> bool:
    """Wide-range variant (FR-033): whether the day's H1 range fails to
    clear the definition's threshold. Always False for definitions
    without one (min_h1_range_points is None)."""
    return (
        definition.min_h1_range_points is not None
        and h1_high - h1_low <= definition.min_h1_range_points
    )
