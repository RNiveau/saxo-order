import datetime
import logging
from unittest.mock import call

import pytest

from engines.workflow_engine import WorkflowEngine
from model import (
    Candle,
    Close,
    Condition,
    Direction,
    Indicator,
    IndicatorType,
    Trigger,
    UnitTime,
    Workflow,
    WorkflowDirection,
    WorkflowElement,
    WorkflowLocation,
    WorkflowSignal,
)
from model.enum import AssetType


class TestWorkflowEngine:

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
            slack_client = mocker.Mock()
            dynamodb_client = mocker.Mock()
            mocker.patch.object(slack_client, "chat_postMessage")
            workflow_engine = WorkflowEngine(
                workflows,
                slack_client,
                mocker.Mock(),
                mocker.Mock(),
                dynamodb_client,
            )
            workflow_engine.run()
            assert slack_client.chat_postMessage.call_count == 0
            assert (
                "Workflow Test will not run" == caplog.records[0].getMessage()
            )
            caplog.clear()
            workflows[0].name = "Test 2"
            workflows[0].enable = False
            workflows[0].end_date = datetime.datetime.now().date()
            workflow_engine.run()
            assert (
                "Workflow Test 2 will not run"
                == caplog.records[0].getMessage()
            )
            assert slack_client.chat_postMessage.call_count == 0

    @pytest.mark.parametrize(
        "workflow, ma, slack_call, slack_message",
        [
            (
                Workflow(
                    name="Test",
                    index="CAC40.I",
                    cfd="FRA40.I",
                    end_date=datetime.datetime.now().date(),
                    enable=True,
                    dry_run=False,
                    conditions=[
                        Condition(
                            indicator=Indicator(
                                IndicatorType.MA50, UnitTime.H4
                            ),
                            close=Close(
                                direction=WorkflowDirection.BELOW,
                                ut=UnitTime.H1,
                                spread=1.5,
                            ),
                            element=WorkflowElement.CLOSE,
                        )
                    ],
                    trigger=Trigger(
                        ut=UnitTime.H1,
                        signal=WorkflowSignal.BREAKOUT,
                        location=WorkflowLocation.LOWER,
                        order_direction=Direction.SELL,
                        quantity=9,
                    ),
                ),
                12,
                1,
                "Workflow `Test` will trigger an order Sell"
                " for 9 FRA40.I at 8: last price 10.6",
            ),
            (
                Workflow(
                    name="Test",
                    index="CAC40.I",
                    cfd="FRA40.I",
                    end_date=datetime.datetime.now().date(),
                    enable=True,
                    dry_run=False,
                    conditions=[
                        Condition(
                            indicator=Indicator(
                                IndicatorType.MA50, UnitTime.H4
                            ),
                            close=Close(
                                direction=WorkflowDirection.ABOVE,
                                ut=UnitTime.H1,
                                spread=2,
                            ),
                            element=WorkflowElement.CLOSE,
                        )
                    ],
                    trigger=Trigger(
                        ut=UnitTime.H1,
                        signal=WorkflowSignal.BREAKOUT,
                        location=WorkflowLocation.HIGHER,
                        order_direction=Direction.BUY,
                        quantity=1,
                    ),
                ),
                10.5,
                1,
                "Workflow `Test` will trigger an order Buy for"
                " 1 FRA40.I at 11.5: last price 10.6",
            ),
        ],
    )
    def test_run_ma_50_workflow(
        self,
        workflow: Workflow,
        ma: float,
        slack_call: int,
        slack_message: str,
        mocker,
    ):
        workflows = [workflow]
        slack_client = mocker.Mock()
        candles_service = mocker.Mock()
        saxo_client = mocker.Mock()
        dynamodb_client = mocker.Mock()
        mocker.patch.object(slack_client, "chat_postMessage")
        mocker.patch.object(
            candles_service, "build_hour_candles", return_value=[]
        )
        mocker.patch.object(
            candles_service,
            "get_candle_per_hour",
            return_value=Candle(
                close=10.6, lower=9, higher=10.5, open=8.5, ut=UnitTime.H1
            ),
        )
        mocker.patch.object(
            saxo_client,
            "get_asset",
            return_value={"AssetType": AssetType.STOCK},
        )
        mocker.patch("engines.workflows.mobile_average", return_value=ma)

        workflow_engine = WorkflowEngine(
            workflows,
            slack_client,
            candles_service,
            saxo_client,
            dynamodb_client,
        )
        workflow_engine.run()
        assert candles_service.build_hour_candles.call_count == 1
        assert candles_service.get_candle_per_hour.call_count == 2
        assert slack_client.chat_postMessage.call_count == slack_call
        if slack_call > 0:
            assert slack_client.chat_postMessage.call_args_list[0] == call(
                channel="#workflows-stock", text=slack_message
            )
