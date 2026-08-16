import datetime

import pytest

from engines.workflows import InclinedWorkflow
from model import Candle, UnitTime
from model.workflow import IndicatorInclined, Point
from utils.exception import SaxoException


@pytest.fixture
def saxo_client(mocker):
    """A Saxo client whose market is open every day."""
    client = mocker.Mock()
    client.get_asset.return_value = {
        "Identifier": "123",
        "AssetType": "Stock",
    }
    client.is_day_open.return_value = True
    return client


@pytest.fixture
def workflow(saxo_client):
    return InclinedWorkflow(saxo_client, "test")


@pytest.fixture
def make_indicator():
    def _make(x1_date, y1, x2_date, y2):
        return IndicatorInclined(
            name="inclined",
            ut="h1",
            x1=Point(x=x1_date, y=y1),
            x2=Point(x=x2_date, y=y2),
        )

    return _make


@pytest.fixture
def freeze_now(mocker):
    """Pin the workflow's notion of "now", which drives how far along the
    line the indicator value is projected."""

    def _freeze(now):
        mocker.patch("engines.workflows.get_date_utc0", return_value=now)

    return _freeze


@pytest.fixture
def candle():
    return Candle(lower=100, higher=110, open=105, close=107, ut=UnitTime.H1)


class TestInclinedWorkflow:

    def test_init_workflow_computes_line_value(
        self, workflow, make_indicator, freeze_now, candle
    ):
        indicator = make_indicator(
            datetime.datetime(2024, 9, 19),
            100.0,
            datetime.datetime(2024, 9, 25),
            106.0,
        )
        freeze_now(datetime.datetime(2024, 10, 1))

        workflow.init_workflow(indicator, [candle])

        assert workflow.indicator_value is not None
        assert isinstance(workflow.indicator_value, float)

    def test_init_workflow_rejects_non_inclined_indicator(
        self, workflow, candle
    ):
        from model import Indicator

        indicator = Indicator(name="ma50", ut="h1")

        with pytest.raises(SaxoException):
            workflow.init_workflow(indicator, [candle])

    def test_init_workflow_rejects_missing_points(self, workflow, candle):
        indicator = IndicatorInclined(
            name="inclined", ut="h1", x1=None, x2=None
        )

        with pytest.raises(SaxoException):
            workflow.init_workflow(indicator, [candle])

    def test_below_condition_with_element(self, workflow):
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=100, higher=110, open=103, close=104, ut=UnitTime.H1
        )

        assert workflow.below_condition(candle, spread=1.0, element=105.5)
        assert workflow.below_condition(candle, spread=1.0, element=105.0)
        assert not workflow.below_condition(candle, spread=1.0, element=106.5)
        assert not workflow.below_condition(candle, spread=1.0, element=104.0)

    def test_below_condition_with_candle(self, workflow):
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=105.5, higher=110, open=106, close=105.3, ut=UnitTime.H1
        )
        assert workflow.below_condition(candle, spread=1.0)

        candle_far = Candle(
            lower=108, higher=110, open=109, close=109, ut=UnitTime.H1
        )
        assert not workflow.below_condition(candle_far, spread=1.0)

    def test_above_condition_with_element(self, workflow):
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=100, higher=110, open=103, close=104, ut=UnitTime.H1
        )

        assert workflow.above_condition(candle, spread=1.0, element=104.5)
        assert workflow.above_condition(candle, spread=1.0, element=105.0)
        assert not workflow.above_condition(candle, spread=1.0, element=103.5)
        assert not workflow.above_condition(candle, spread=1.0, element=106.0)

    def test_above_condition_with_candle(self, workflow):
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=100, higher=104.5, open=103, close=104.2, ut=UnitTime.H1
        )
        assert workflow.above_condition(candle, spread=1.0)

        candle_far = Candle(
            lower=100, higher=102, open=101, close=101.5, ut=UnitTime.H1
        )
        assert not workflow.above_condition(candle_far, spread=1.0)

    def test_conditions_return_false_when_no_indicator_value(
        self, workflow, candle
    ):
        workflow.indicator_value = None

        assert not workflow.below_condition(candle, spread=1.0)
        assert not workflow.above_condition(candle, spread=1.0)

    def test_same_date_raises_error(self):
        same_date = datetime.datetime(2024, 9, 19)
        with pytest.raises(ValueError):
            IndicatorInclined(
                name="inclined",
                ut="h1",
                x1=Point(x=same_date, y=100),
                x2=Point(x=same_date, y=200),
            )

    def test_real_data_inclined_line(
        self, workflow, make_indicator, freeze_now
    ):
        indicator = make_indicator(
            datetime.datetime(2026, 1, 29),
            131.8,
            datetime.datetime(2026, 2, 12),
            129.7,
        )
        freeze_now(datetime.datetime(2026, 2, 27))

        candles = [
            Candle(lower=125, higher=130, open=127, close=128, ut=UnitTime.H1)
        ]

        workflow.init_workflow(indicator, candles)

        assert workflow.indicator_value == pytest.approx(127.39, abs=0.01)

    def test_real_data_ascending_line(
        self, saxo_client, make_indicator, freeze_now
    ):
        """Closed market days are skipped when projecting the line."""
        saxo_client.get_asset.return_value = {
            "Identifier": "456",
            "AssetType": "Stock",
        }
        closed_dates = {
            datetime.datetime(2026, 4, 3),
            datetime.datetime(2026, 4, 6),
            datetime.datetime(2026, 5, 1),
        }
        saxo_client.is_day_open.side_effect = (
            lambda saxo_uic, asset_type, date: date not in closed_dates
        )

        workflow = InclinedWorkflow(saxo_client, "test")

        indicator = make_indicator(
            datetime.datetime(2026, 3, 9),
            39.21,
            datetime.datetime(2026, 4, 7),
            48.55,
        )
        freeze_now(datetime.datetime(2026, 5, 21))

        candles = [
            Candle(lower=60, higher=65, open=62, close=63, ut=UnitTime.H1)
        ]

        workflow.init_workflow(indicator, candles)

        assert workflow.indicator_value == pytest.approx(63.79, abs=0.01)

    def test_descending_line(
        self, workflow, make_indicator, freeze_now, candle
    ):
        indicator = make_indicator(
            datetime.datetime(2024, 9, 19),
            110.0,
            datetime.datetime(2024, 9, 25),
            104.0,
        )
        freeze_now(datetime.datetime(2024, 9, 25))

        workflow.init_workflow(indicator, [candle])

        assert workflow.indicator_value < 110.0
