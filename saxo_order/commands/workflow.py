import datetime
import logging
import os
from typing import List

import click
import yaml
from click.core import Context
from slack_sdk import WebClient

from client.aws_client import AwsClient
from client.client_helper import *
from client.saxo_client import SaxoClient
from model import (
    Candle,
    Close,
    Condition,
    Direction,
    Indicator,
    IndicatorType,
    Order,
    OrderType,
    Trigger,
    UnitTime,
    Workflow,
    WorkflowDirection,
    WorkflowElement,
    WorkflowLocation,
    WorkflowSignal,
)
from saxo_order.commands import catch_exception
from services.workflow_service import WorkflowService
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.helper import get_date_utc0

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def workflow(ctx: Context):
    config = ctx.obj["config"]
    execute_workflow(config)


def execute_workflow(config: str) -> None:
    logging.basicConfig(level=logging.WARN)
    logger.setLevel(logging.DEBUG)
    configuration = Configuration(config)
    workflow_service = WorkflowService(SaxoClient(configuration))
    workflows = _yaml_loader()
    orders = run_workflows(
        workflows, workflow_service, WebClient(token=configuration.slack_token)
    )


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def technical(ctx: Context):
    logging.basicConfig(level=logging.WARN)
    logger.setLevel(logging.DEBUG)

    configuration = Configuration(ctx.obj["config"])
    workflow_service = WorkflowService(SaxoClient(configuration))
    data = workflow_service.get_candle_per_minutes(
        code="DAX.I", duration=450, ut=UnitTime.M15
    )


def run_workflows(
    workflows: List[Workflow],
    workflow_service: WorkflowService,
    slack_client: WebClient,
) -> List[Order]:
    orders = []
    for workflow in workflows:
        if workflow.enable and workflow.end_date >= datetime.datetime.now().date():
            logger.info(f"Run workflow {workflow.name}")
            if workflow.conditions[0].indicator.name in [IndicatorType.MA50]:
                ma = workflow_service.calculate_ma(
                    workflow.index,
                    workflow.cfd,
                    workflow.conditions[0].indicator.ut,
                    workflow.conditions[0].indicator.name,
                    get_date_utc0(),
                )
                logger.debug(
                    f"Get indicator {ma}, ut {workflow.conditions[0].indicator.ut}"
                )
                # we use the cdf here to run the workflow even in index off hours
                # TODO manage the cfd spread for some index
                candle = workflow_service.get_candle_per_hour(
                    workflow.cfd, workflow.conditions[0].close.ut, get_date_utc0()
                )
                if candle is None:
                    raise SaxoException("Can't retrive candle")
                if workflow.conditions[0].close.direction == WorkflowDirection.BELOW:
                    element = _get_price_from_element(
                        candle, workflow.conditions[0].element
                    )
                    if (
                        element <= ma
                        and element >= ma - workflow.conditions[0].close.spread
                    ):
                        trigger = workflow.trigger
                        trigger_candle = workflow_service.get_candle_per_hour(
                            workflow.cfd, workflow.trigger.ut, get_date_utc0()
                        )
                        if trigger_candle is None:
                            raise SaxoException("Can't retrive candle")
                        price = 0.0
                        if (
                            trigger.location == WorkflowLocation.LOWER
                            and trigger.signal == WorkflowSignal.BREAKOUT
                        ):
                            price = trigger_candle.lower - 1
                            order_type = (
                                OrderType.OPEN_STOP
                                if trigger.order_direction == Direction.SELL
                                else OrderType.LIMIT
                            )
                        elif (
                            trigger.location == WorkflowLocation.HIGHER
                            and trigger.signal == WorkflowSignal.BREAKOUT
                        ):
                            price = trigger_candle.higher + 1
                            order_type = (
                                OrderType.STOP
                                if trigger.order_direction == Direction.SELL
                                else OrderType.OPEN_STOP
                            )

                        order = Order(
                            code=workflow.cfd,
                            price=price,
                            quantity=trigger.quantity,
                            direction=trigger.order_direction,
                            type=order_type,
                        )
                        log = f"Workflow will trigger an order {order.direction} for {order.quantity} {order.code} at {order.price}"
                        logger.debug(log)
                        slack_client.chat_postMessage(channel="#stock", text=log)
                        if workflow.dry_run is False:
                            orders.append(order)
        else:
            logger.info(f"Workflow {workflow.name} will not run")
    return orders


def _yaml_loader() -> List[Workflow]:
    if AwsClient.is_aws_context():
        logger.info("Load workflows.yml from AWS")
        workflows_data = yaml.safe_load(AwsClient().get_workflows())
    elif os.path.isfile("workflows.yml"):
        with open("workflows.yml", "r") as file:
            logger.info("Load workflows.yml from disk")
            workflows_data = yaml.safe_load(file)
    else:
        raise SaxoException("No yaml to load")

    workflows = []
    for workflow_data in workflows_data:
        name = workflow_data["name"]
        index = workflow_data["index"]
        cfd = workflow_data["cfd"]
        end_date = datetime.datetime.strptime(
            workflow_data["end_date"], "%Y/%m/%d"
        ).date()
        enable = workflow_data["enable"]
        dry_run = workflow_data["dry_run"]

        conditions_data = workflow_data["conditions"]
        conditions = []
        for condition_data in conditions_data:
            indicator_data = condition_data["indicator"]
            indicator = Indicator(indicator_data["name"], indicator_data["ut"])
            close_data = condition_data["close"]
            close = Close(
                close_data["direction"], close_data["ut"], close_data["spread"]
            )
            condition = Condition(
                indicator,
                close,
                WorkflowElement.get_value(
                    condition_data.get("element", WorkflowElement.CLOSE)
                ),
            )
            conditions.append(condition)

        trigger_data = workflow_data["trigger"]
        trigger = Trigger(
            ut=trigger_data["ut"],
            signal=trigger_data["signal"],
            location=trigger_data["location"],
            order_direction=trigger_data["order_direction"],
            quantity=float(trigger_data["quantity"]),
        )

        workflows.append(
            Workflow(
                name=name,
                index=index,
                cfd=cfd,
                end_date=end_date,
                enable=enable,
                conditions=conditions,
                trigger=trigger,
                dry_run=dry_run,
            )
        )
    return workflows


def _get_price_from_element(candle: Candle, element: WorkflowElement) -> float:
    match element:
        case WorkflowElement.CLOSE:
            return candle.close
        case WorkflowElement.HIGH:
            return candle.higher
        case WorkflowElement.LOW:
            return candle.lower
        case _:
            raise SaxoException(f"We don't handle {element} price")
