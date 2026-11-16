import pytest

from engines.workflows import (
    MA7Workflow,
    MA50Workflow,
    MA200Workflow,
    MovingAverageWorkflow,
)
from model import Candle, Indicator, IndicatorType, UnitTime


def _candle(close: float) -> Candle:
    return Candle(
        close=close, lower=close, higher=close, open=close, ut=UnitTime.D
    )


@pytest.mark.parametrize(
    "workflow_class, indicator_type",
    [
        (MA7Workflow, IndicatorType.MA7),
        (MA50Workflow, IndicatorType.MA50),
        (MA200Workflow, IndicatorType.MA200),
    ],
)
class TestMovingAverageWorkflowConditions:

    async def _init(self, workflow_class, indicator_type):
        workflow = workflow_class()
        candles = [_candle(100.0)] * workflow_class.period
        await workflow.init_workflow(
            Indicator(indicator_type, UnitTime.D), candles
        )
        return workflow

    async def test_below_condition_within_spread_under_average(
        self, workflow_class, indicator_type
    ):
        workflow = await self._init(workflow_class, indicator_type)
        assert workflow.below_condition(_candle(99.0), 2.0) is True
        assert workflow.below_condition(_candle(101.0), 2.0) is False

    async def test_above_condition_within_spread_over_average(
        self, workflow_class, indicator_type
    ):
        workflow = await self._init(workflow_class, indicator_type)
        assert workflow.above_condition(_candle(101.0), 2.0) is True
        assert workflow.above_condition(_candle(99.0), 2.0) is False


def test_moving_average_subclass_without_period_is_rejected():
    with pytest.raises(TypeError):

        class NoPeriodWorkflow(MovingAverageWorkflow):
            pass
