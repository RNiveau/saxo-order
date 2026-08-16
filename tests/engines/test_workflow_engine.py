import datetime
import logging
from unittest.mock import AsyncMock, call

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


@pytest.fixture
def slack_client(mocker):
    return mocker.Mock()


@pytest.fixture
def dynamodb_client():
    return AsyncMock()


@pytest.fixture
def saxo_client(mocker):
    client = mocker.Mock()
    client.get_asset.return_value = {"AssetType": AssetType.STOCK}
    return client


@pytest.fixture
def candles_service(mocker):
    """The engine asks for candles three times per run; the first call
    returns nothing so only the later two carry a candle."""
    service = mocker.Mock()
    candle = Candle(close=10.6, lower=9, higher=10.5, open=8.5, ut=UnitTime.H1)
    service.build_candles.side_effect = [[], [candle], [candle]]
    return service


@pytest.fixture
def make_engine(slack_client, candles_service, saxo_client, dynamodb_client):
    def _make(workflows):
        return WorkflowEngine(
            workflows,
            slack_client,
            candles_service,
            saxo_client,
            dynamodb_client,
        )

    return _make


class TestWorkflowEngine:

    async def test_run_not_running_workflow(
        self, caplog, slack_client, make_engine
    ):
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
            workflow_engine = make_engine(workflows)
            await workflow_engine.run()
            assert slack_client.chat_postMessage.call_count == 0
            assert (
                "Workflow Test will not run" == caplog.records[0].getMessage()
            )
            caplog.clear()
            workflows[0].name = "Test 2"
            workflows[0].enable = False
            workflows[0].end_date = datetime.datetime.now().date()
            await workflow_engine.run()
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
    async def test_run_ma_50_workflow(
        self,
        workflow: Workflow,
        ma: float,
        slack_call: int,
        slack_message: str,
        slack_client,
        candles_service,
        make_engine,
        mocker,
    ):
        workflows = [workflow]
        mocker.patch("engines.workflows.mobile_average", return_value=ma)

        workflow_engine = make_engine(workflows)
        await workflow_engine.run()
        assert candles_service.build_candles.call_count == 3
        assert slack_client.chat_postMessage.call_count == slack_call
        if slack_call > 0:
            assert slack_client.chat_postMessage.call_args_list[0] == call(
                channel="#workflows-stock", text=slack_message
            )

    async def test_run_ma_7_workflow_below(
        self, slack_client, candles_service, make_engine, mocker
    ):
        workflow = Workflow(
            name="Test",
            index="CAC40.I",
            cfd="FRA40.I",
            end_date=datetime.datetime.now().date(),
            enable=True,
            dry_run=False,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.MA7, UnitTime.H4),
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
        )
        mocker.patch("engines.workflows.mobile_average", return_value=12)

        workflow_engine = make_engine([workflow])
        await workflow_engine.run()
        assert candles_service.build_candles.call_count == 3
        assert slack_client.chat_postMessage.call_count == 1
        assert slack_client.chat_postMessage.call_args_list[0] == call(
            channel="#workflows-stock",
            text="Workflow `Test` will trigger an order Sell"
            " for 9 FRA40.I at 8: last price 10.6",
        )

    async def test_run_ma_7_workflow_above(
        self, slack_client, candles_service, make_engine, mocker
    ):
        workflow = Workflow(
            name="Test",
            index="CAC40.I",
            cfd="FRA40.I",
            end_date=datetime.datetime.now().date(),
            enable=True,
            dry_run=False,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.MA7, UnitTime.H4),
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
        )
        mocker.patch("engines.workflows.mobile_average", return_value=10.5)

        workflow_engine = make_engine([workflow])
        await workflow_engine.run()
        assert candles_service.build_candles.call_count == 3
        assert slack_client.chat_postMessage.call_count == 1
        assert slack_client.chat_postMessage.call_args_list[0] == call(
            channel="#workflows-stock",
            text="Workflow `Test` will trigger an order Buy for"
            " 1 FRA40.I at 11.5: last price 10.6",
        )
