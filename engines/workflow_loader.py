import datetime
import logging
import os
from typing import Any, Dict, List

import yaml

from client.aws_client import DynamoDBClient, S3Client
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


def _load_from_dynamodb(logger) -> List[Dict[str, Any]]:
    """
    Load workflows from DynamoDB.

    Returns:
        List of workflow dictionaries from DynamoDB

    Raises:
        Exception: If DynamoDB query fails
    """
    dynamodb_client = DynamoDBClient()
    workflows_data = dynamodb_client.get_all_workflows()

    enabled_workflows = [w for w in workflows_data if w.get("enable", False)]
    logger.info(
        f"Loaded {len(enabled_workflows)} enabled workflows from DynamoDB"
    )
    return enabled_workflows


def _load_from_yaml(logger, force_from_disk: bool) -> List[Dict[str, Any]]:
    """
    Load workflows from S3 or local YAML file.

    Args:
        logger: Logger instance
        force_from_disk: If True, load from local file even in AWS context

    Returns:
        List of workflow dictionaries from YAML

    Raises:
        SaxoException: If no YAML file found
    """
    if S3Client.is_aws_context() and force_from_disk is False:
        logger.info("Loading workflows from S3/YAML")
        workflows_data = yaml.safe_load(S3Client().get_workflows())
    elif os.path.isfile("workflows.yml"):
        logger.info(
            "Loading workflows from local YAML"
            f" (force_from_disk={force_from_disk})"
        )
        with open("workflows.yml", "r") as file:
            workflows_data = yaml.safe_load(file)
    else:
        raise SaxoException("No yaml to load")
    return workflows_data


def load_workflows(force_from_disk: bool = False) -> List[Workflow]:
    logger = Logger.get_logger("workflow_loader", logging.DEBUG)

    if S3Client.is_aws_context() and force_from_disk is False:
        try:
            logger.info("Attempting to load workflows from DynamoDB")
            workflows_data = _load_from_dynamodb(logger)
            if workflows_data:
                logger.info(
                    "Using DynamoDB as workflow source"
                    f" ({len(workflows_data)} workflows)"
                )
            else:
                logger.warning(
                    "DynamoDB returned empty workflow list,"
                    " falling back to YAML"
                )
                workflows_data = _load_from_yaml(logger, force_from_disk)
        except Exception as e:
            logger.warning(f"Failed to load workflows from DynamoDB: {e}")
            logger.info("Falling back to S3/YAML workflow loading")
            workflows_data = _load_from_yaml(logger, force_from_disk)
    else:
        workflows_data = _load_from_yaml(logger, force_from_disk)

    workflows = []
    for workflow_data in workflows_data:
        name = workflow_data["name"]
        index = workflow_data["index"]
        cfd = workflow_data["cfd"]

        end_date_str = workflow_data.get("end_date")
        end_date = None
        if end_date_str:
            if "/" in end_date_str:
                end_date = datetime.datetime.strptime(
                    end_date_str, "%Y/%m/%d"
                ).date()
            else:
                end_date = datetime.datetime.strptime(
                    end_date_str, "%Y-%m-%d"
                ).date()
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
