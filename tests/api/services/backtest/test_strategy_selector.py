"""Which engine a definition runs on.

The seam's whole job is answering that question, and answering it wrongly
is silent: a combo definition routed to the session-range engine would
return a plausible result computed from rules it never applied.
"""

from unittest.mock import MagicMock

from api.services.backtest import get_definition, list_definitions
from api.services.backtest.combo_strategy import ComboStrategy
from api.services.backtest.session_range import SessionRangeStrategy
from api.services.backtest.strategy import StrategySelector
from client.aws_client import DynamoDBClient
from model import BacktestDefinition, UnitTime
from services.candles_service import CandlesService


def make_selector() -> StrategySelector:
    return StrategySelector(
        MagicMock(spec=CandlesService), MagicMock(spec=DynamoDBClient)
    )


def combo_definition() -> BacktestDefinition:
    return BacktestDefinition(
        code="CTEST",
        name="combo test",
        display_name="combo test",
        instrument="GER40.I",
        unit_time=UnitTime.M15,
        combo_entry=True,
        double_take_profit=True,
    )


class TestStrategySelector:
    def test_every_shipped_definition_runs_on_the_session_range_engine(self):
        """Walks the registry rather than a list of codes, and keys on
        the rule rather than on names: every definition without
        combo_entry belongs to the day engine, so one added later is
        covered by this test the day it lands."""
        selector = make_selector()
        for definition in list_definitions():
            if definition.combo_entry:
                continue
            assert (
                selector.for_definition(definition) is selector.session_range
            )

    def test_the_session_range_engine_is_the_moved_day_loop(self):
        assert isinstance(make_selector().session_range, SessionRangeStrategy)

    def test_the_combo_engine_is_the_indicator_driven_one(self):
        assert isinstance(make_selector().combo, ComboStrategy)

    def test_it_is_built_once_and_reused_across_calls(self):
        """An engine holds a candle source; handing out a fresh one per
        request would throw away everything it had already fetched."""
        selector = make_selector()
        assert selector.for_definition(
            get_definition("B9H")
        ) is selector.for_definition(get_definition("G9H"))
        assert selector.for_definition(
            get_definition("C5M")
        ) is selector.for_definition(get_definition("C1H"))

    def test_a_combo_definition_runs_on_the_combo_engine(self):
        selector = make_selector()
        assert selector.for_definition(combo_definition()) is selector.combo

    def test_a_combo_definition_never_falls_back_to_session_range(self):
        """The failure this seam exists to prevent: the session-range
        engine would return a plausible result computed from rules the
        definition does not have."""
        selector = make_selector()
        assert (
            selector.for_definition(combo_definition())
            is not selector.session_range
        )

    def test_every_shipped_combo_definition_routes_to_the_combo_engine(self):
        selector = make_selector()
        combo_codes = [d.code for d in list_definitions() if d.combo_entry]
        assert combo_codes == ["C5M", "C15M", "C1H"]
        for code in combo_codes:
            assert (
                selector.for_definition(get_definition(code)) is selector.combo
            )

    def test_the_two_engines_are_distinct(self):
        selector = make_selector()
        assert selector.combo is not selector.session_range
