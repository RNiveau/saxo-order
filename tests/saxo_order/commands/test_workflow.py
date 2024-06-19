import datetime
import logging

import pytest

from client.saxo_client import SaxoClient
from model import *
from saxo_order.commands.workflow import run_workflows
from services.workflow_service import WorkflowService


class MockWorkflowService(WorkflowService):

    def __init__(self):
        self.candle = None
        self.ma = 0
        pass

    def calculate_ma(
        self,
        code: str,
        cfd: str,
        ut: UnitTime,
        indicator: IndicatorType,
        date: datetime.datetime,
    ):
        return self.ma

    def get_candle_per_hour(
        self, code: str, ut: UnitTime, date: datetime.datetime
    ) -> Candle:
        return self.candle


class TestWorkflow:

    def test_run_not_running_workflow(self, caplog, mocker):
        with caplog.at_level(logging.INFO):
            workflows = [
                Workflow(
                    name="Test",
                    index="CAC40.I",
                    cfd="FRA40.I",
                    end_date=datetime.datetime.strptime(
                        "2022/01/01", "%Y/%m/%d"
                    ).date(),
                    enable=True,
                    conditions=list(),
                    trigger=None,
                )
            ]
            triggers = run_workflows(workflows, MockWorkflowService(), mocker.Mock())
            assert "Workflow Test will not run" == caplog.records[0].getMessage()
            assert 0 == len(triggers)
            caplog.clear()
            workflows[0].name = "Test 2"
            workflows[0].enable = False
            workflows[0].end_date = datetime.datetime.now().date()
            triggers = run_workflows(workflows, MockWorkflowService(), mocker.Mock())
            assert "Workflow Test 2 will not run" == caplog.records[0].getMessage()
            assert 0 == len(triggers)

    def test_run_workflow_and_trigger_order(self, caplog, mocker):
        with caplog.at_level(logging.DEBUG):
            condition = Condition(
                indicator=Indicator(IndicatorType.MA50, UnitTime.H4),
                close=Close(
                    direction=WorkflowDirection.BELOW, ut=UnitTime.H1, spread=1.5
                ),
                element=WorkflowElement.CLOSE,
            )
            workflows = [
                Workflow(
                    name="Test",
                    index="CAC40.I",
                    cfd="FRA40.I",
                    end_date=datetime.datetime.now().date(),
                    enable=True,
                    dry_run=False,
                    conditions=[condition],
                    trigger=Trigger(
                        ut=UnitTime.H1,
                        signal=WorkflowSignal.BREAKOUT,
                        location=WorkflowLocation.LOWER,
                        order_direction=Direction.SELL,
                        quantity=9,
                    ),
                )
            ]
            workflow_service = MockWorkflowService()
            workflow_service.ma = 12
            workflow_service.candle = Candle(
                close=10.6, lower=9, higher=10.5, open=8.5, ut=UnitTime.H1
            )
            triggers = run_workflows(workflows, workflow_service, mocker.Mock())
            assert "Run workflow Test" == caplog.records[0].getMessage()
            assert 1 == len(triggers)
            assert triggers[0].code == "FRA40.I"
            assert triggers[0].price == 8
            assert triggers[0].quantity == 9
            assert triggers[0].direction == Direction.SELL
            assert triggers[0].type == OrderType.OPEN_STOP
