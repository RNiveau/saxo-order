import pytest

from engines.workflows import (
    MA7Workflow,
    MA50Workflow,
    MA200Workflow,
    MovingAverageWorkflow,
)


@pytest.mark.parametrize(
    "workflow, period",
    [(MA7Workflow, 7), (MA50Workflow, 50), (MA200Workflow, 200)],
)
def test_moving_average_workflow_period(workflow, period):
    assert workflow.period == period


def test_moving_average_subclass_without_period_is_rejected():
    with pytest.raises(TypeError):

        class NoPeriodWorkflow(MovingAverageWorkflow):
            pass
