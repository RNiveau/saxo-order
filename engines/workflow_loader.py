import datetime
import logging
import os
from typing import List

import yaml

from client.aws_client import AwsClient
from model.workflow import (
    Close,
    Condition,
    Indicator,
    Trigger,
    UnitTime,
    Workflow,
    WorkflowDirection,
    WorkflowElement,
    WorkflowSignal,
)
from utils.exception import SaxoException
from utils.logger import Logger


def load_workflows(force_from_disk: bool = False) -> List[Workflow]:
    logger = Logger.get_logger("workflow_loader", logging.DEBUG)
    if AwsClient.is_aws_context() and force_from_disk is False:
        logger.info("Load workflows.yml from AWS")
        workflows_data = yaml.safe_load(AwsClient().get_workflows())
    elif os.path.isfile("workflows.yml"):
        with open("workflows.yml", "r") as file:
            logger.info(
                f"Load workflows.yml from disk"
                f" force_from_disk={force_from_disk}"
            )
            workflows_data = yaml.safe_load(file)
    else:
        raise SaxoException("No yaml to load")

    workflows = []
    for workflow_data in workflows_data:
        name = workflow_data["name"]
        index = workflow_data["index"]
        cfd = workflow_data["cfd"]
        end_date = (
            datetime.datetime.strptime(
                workflow_data["end_date"], "%Y/%m/%d"
            ).date()
            if workflow_data.get("end_date") is not None
            else None
        )
        enable = workflow_data["enable"]
        dry_run = workflow_data.get("dry_run", False)
        is_us = workflow_data.get("is_us", False)

        conditions_data = workflow_data["conditions"]
        conditions = []
        for condition_data in conditions_data:
            indicator_data = condition_data["indicator"]
            indicator = Indicator(
                indicator_data["name"],
                indicator_data["ut"],
                indicator_data.get("value"),
                indicator_data.get("zone_value"),
            )
            close_data = condition_data["close"]
            close = Close(
                close_data["direction"],
                close_data["ut"],
                close_data.get("spread", 0),
            )
            element = condition_data.get("element")
            if element is not None:
                element = WorkflowElement.get_value(element)
            condition = Condition(
                indicator,
                close,
                element,
            )
            conditions.append(condition)

        trigger_data = workflow_data.get("trigger", None)
        if trigger_data is None:
            trigger = Trigger(
                ut=UnitTime.H1,
                # indicator.ut, due to the bug on close candle, we use H1 here
                signal=WorkflowSignal.BREAKOUT,
                location=(
                    "lower"
                    if close.direction == WorkflowDirection.BELOW
                    else "higher"
                ),
                order_direction=(
                    "sell"
                    if close.direction == WorkflowDirection.BELOW
                    else "buy"
                ),
                quantity=float(0.1),
            )
        else:
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
                is_us=is_us,
            )
        )
    return workflows
