"""Which engine a definition runs on.

The seam's whole job is answering that question, and answering it wrongly
is silent: a combo definition routed to the session-range engine would
return a plausible result computed from rules it never applied.
"""

from unittest.mock import MagicMock

import pytest

from api.services.backtest import get_definition, list_definitions
from api.services.backtest.session_range import SessionRangeStrategy
from api.services.backtest.strategy import StrategySelector
from client.aws_client import DynamoDBClient
from model import BacktestDefinition, UnitTime
from services.candles_service import CandlesService
from utils.exception import SaxoException


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

    def test_it_is_built_once_and_reused_across_calls(self):
        """The engine holds a candle source; handing out a fresh one per
        request would throw away everything it had already fetched."""
        selector = make_selector()
        first = selector.for_definition(get_definition("B9H"))
        second = selector.for_definition(get_definition("G9H"))
        assert first is second

    def test_a_combo_definition_raises_instead_of_running(self):
        """Until the combo engine lands, selecting one must fail loudly.
        Returning the session-range engine would report a result for
        rules that were never applied - the failure this seam exists to
        prevent."""
        with pytest.raises(SaxoException, match="not implemented yet"):
            make_selector().for_definition(combo_definition())

    def test_a_combo_definition_never_falls_back_to_session_range(self):
        selector = make_selector()
        try:
            returned = selector.for_definition(combo_definition())
        except SaxoException:
            return
        assert returned is not selector.session_range, (
            "a combo definition must not be silently routed to the "
            "session-range engine"
        )

    def test_the_error_names_the_definition(self):
        with pytest.raises(SaxoException, match="CTEST"):
            make_selector().for_definition(combo_definition())
