import datetime

import pytest

from engines.workflows import InclinedWorkflow
from model import Candle, UnitTime
from model.workflow import IndicatorInclined, Point
from utils.exception import SaxoException


class TestInclinedWorkflow:

    def _make_indicator(self, x1_date, y1, x2_date, y2):
        return IndicatorInclined(
            name="inclined",
            ut="h1",
            x1=Point(x=x1_date, y=y1),
            x2=Point(x=x2_date, y=y2),
        )

    def test_init_workflow_computes_line_value(self, mocker):
        saxo_client = mocker.Mock()
        saxo_client.get_asset.return_value = {
            "Identifier": "123",
            "AssetType": "Stock",
        }
        saxo_client.is_day_open.return_value = True

        workflow = InclinedWorkflow(saxo_client, "aca:xpar")

        x1_date = datetime.datetime(2024, 9, 19)
        x2_date = datetime.datetime(2024, 9, 25)
        indicator = self._make_indicator(x1_date, 100.0, x2_date, 106.0)

        now = datetime.datetime(2024, 10, 1)
        mocker.patch("engines.workflows.get_date_utc0", return_value=now)

        candles = [
            Candle(lower=100, higher=110, open=105, close=107, ut=UnitTime.H1)
        ]

        workflow.init_workflow(indicator, candles)

        assert workflow.indicator_value is not None
        assert isinstance(workflow.indicator_value, float)

    def test_init_workflow_rejects_non_inclined_indicator(self, mocker):
        from model import Indicator

        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "aca:xpar")
        indicator = Indicator(name="ma50", ut="h1")
        candles = [
            Candle(lower=100, higher=110, open=105, close=107, ut=UnitTime.H1)
        ]

        with pytest.raises(SaxoException):
            workflow.init_workflow(indicator, candles)

    def test_init_workflow_rejects_missing_points(self, mocker):
        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "aca:xpar")
        indicator = IndicatorInclined(
            name="inclined", ut="h1", x1=None, x2=None
        )
        candles = [
            Candle(lower=100, higher=110, open=105, close=107, ut=UnitTime.H1)
        ]

        with pytest.raises(SaxoException):
            workflow.init_workflow(indicator, candles)

    def test_below_condition_with_element(self, mocker):
        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "test")
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=100, higher=110, open=103, close=104, ut=UnitTime.H1
        )

        assert workflow.below_condition(candle, spread=1.0, element=105.5)
        assert workflow.below_condition(candle, spread=1.0, element=105.0)
        assert not workflow.below_condition(candle, spread=1.0, element=106.5)
        assert not workflow.below_condition(candle, spread=1.0, element=104.0)

    def test_below_condition_with_candle(self, mocker):
        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "test")
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=105.5, higher=110, open=106, close=105.3, ut=UnitTime.H1
        )
        assert workflow.below_condition(candle, spread=1.0)

        candle_far = Candle(
            lower=108, higher=110, open=109, close=109, ut=UnitTime.H1
        )
        assert not workflow.below_condition(candle_far, spread=1.0)

    def test_above_condition_with_element(self, mocker):
        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "test")
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=100, higher=110, open=103, close=104, ut=UnitTime.H1
        )

        assert workflow.above_condition(candle, spread=1.0, element=104.5)
        assert workflow.above_condition(candle, spread=1.0, element=105.0)
        assert not workflow.above_condition(candle, spread=1.0, element=103.5)
        assert not workflow.above_condition(candle, spread=1.0, element=106.0)

    def test_above_condition_with_candle(self, mocker):
        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "test")
        workflow.indicator_value = 105.0

        candle = Candle(
            lower=100, higher=104.5, open=103, close=104.2, ut=UnitTime.H1
        )
        assert workflow.above_condition(candle, spread=1.0)

        candle_far = Candle(
            lower=100, higher=102, open=101, close=101.5, ut=UnitTime.H1
        )
        assert not workflow.above_condition(candle_far, spread=1.0)

    def test_conditions_return_false_when_no_indicator_value(self, mocker):
        saxo_client = mocker.Mock()
        workflow = InclinedWorkflow(saxo_client, "test")
        workflow.indicator_value = None

        candle = Candle(
            lower=100, higher=110, open=105, close=107, ut=UnitTime.H1
        )
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

    def test_real_data_inclined_line(self, mocker):
        saxo_client = mocker.Mock()
        saxo_client.get_asset.return_value = {
            "Identifier": "123",
            "AssetType": "Stock",
        }
        saxo_client.is_day_open.return_value = True

        workflow = InclinedWorkflow(saxo_client, "test")

        x1_date = datetime.datetime(2026, 1, 29)
        x2_date = datetime.datetime(2026, 2, 12)
        indicator = self._make_indicator(x1_date, 131.8, x2_date, 129.7)

        now = datetime.datetime(2026, 2, 27)
        mocker.patch("engines.workflows.get_date_utc0", return_value=now)

        candles = [
            Candle(lower=125, higher=130, open=127, close=128, ut=UnitTime.H1)
        ]

        workflow.init_workflow(indicator, candles)

        assert workflow.indicator_value == pytest.approx(127.39, abs=0.01)

    def test_real_data_ascending_line(self, mocker):
        saxo_client = mocker.Mock()
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

        x1_date = datetime.datetime(2026, 3, 9)
        x2_date = datetime.datetime(2026, 4, 7)
        indicator = self._make_indicator(x1_date, 39.21, x2_date, 48.55)

        now = datetime.datetime(2026, 5, 21)
        mocker.patch("engines.workflows.get_date_utc0", return_value=now)

        candles = [
            Candle(lower=60, higher=65, open=62, close=63, ut=UnitTime.H1)
        ]

        workflow.init_workflow(indicator, candles)

        assert workflow.indicator_value == pytest.approx(63.79, abs=0.01)

    def test_descending_line(self, mocker):
        saxo_client = mocker.Mock()
        saxo_client.get_asset.return_value = {
            "Identifier": "123",
            "AssetType": "Stock",
        }
        saxo_client.is_day_open.return_value = True

        workflow = InclinedWorkflow(saxo_client, "test")
        x1_date = datetime.datetime(2024, 9, 19)
        x2_date = datetime.datetime(2024, 9, 25)
        indicator = self._make_indicator(x1_date, 110.0, x2_date, 104.0)

        now = datetime.datetime(2024, 9, 25)
        mocker.patch("engines.workflows.get_date_utc0", return_value=now)

        candles = [
            Candle(lower=100, higher=110, open=105, close=107, ut=UnitTime.H1)
        ]
        workflow.init_workflow(indicator, candles)

        assert workflow.indicator_value < 110.0
