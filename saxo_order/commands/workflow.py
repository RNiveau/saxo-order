import datetime
import logging
from typing import List

import click
import yaml
from click.core import Context
from slack_sdk import WebClient

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
    WorkflowLocation,
    WorkflowSignal,
)
from saxo_order.commands import catch_exception
from services.workflow_service import WorkflowService
from utils.configuration import Configuration
from utils.exception import SaxoException

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def workflow(ctx: Context):
    logging.basicConfig(level=logging.WARN)
    logger.setLevel(logging.DEBUG)

    configuration = Configuration(ctx.obj["config"])
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
    saxo_client = SaxoClient(configuration)
    data = saxo_client.get_historical_data(
        saxo_uic="1907568",
        asset_type="StockIndex",
        horizon=1440,
        count=3,
        date=datetime.datetime.now(),
    )
    candles = list(
        map(
            lambda x: Candle(
                get_low_from_saxo_data(x),
                get_high_from_saxo_data(x),
                get_open_from_saxo_data(x),
                get_price_from_saxo_data(x),
                UnitTime.D,
                x["Time"],
            ),
            data,
        )
    )
    detail = saxo_client.get_asset_detail(
        saxo_client.get_asset("itp", "xpar")["Identifier"], "Stock"
    )
    tick = get_tick_size(detail["TickSizeScheme"], 48.4)
    print(candles)


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
                    workflow.conditions[0].indicator.ut,
                    workflow.conditions[0].indicator.name,
                    _get_date_utc0(),
                )
                logger.debug(
                    f"Get indicator {ma}, ut {workflow.conditions[0].indicator.ut}"
                )
                candle = workflow_service.get_candle(
                    workflow.index, workflow.conditions[0].close.ut, _get_date_utc0()
                )
                if candle is None:
                    raise SaxoException("Can't retrive candle")
                if workflow.conditions[0].close.direction == WorkflowDirection.BELOW:
                    if (
                        candle.close <= ma
                        and candle.close >= ma - workflow.conditions[0].close.spread
                    ):
                        trigger = workflow.trigger
                        trigger_candle = workflow_service.get_candle(
                            workflow.index, workflow.trigger.ut, _get_date_utc0()
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


def _get_date_utc0() -> datetime.datetime:
    date = datetime.datetime.now(tz=datetime.UTC)
    return date


def _yaml_loader() -> List[Workflow]:
    # Load YAML data
    yaml_data = """
- name: sell ma50 h4 dax
  index: CAC40.I #DAX.I
  cfd: FRA40.I #GER40.I
  end_date: 2024/06/01
  enable: true
  dry_run: false
  conditions:
    - indicator:
          name: ma50
          ut: h1
      close:
         direction: below
         ut: h1
         spread: 10
  trigger:
      ut: h1
      signal: breakout
      location: lower
      order_direction: sell
      quantity: 0.1
    """

    workflows_data = yaml.safe_load(yaml_data)

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
            condition = Condition(indicator, close)
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
