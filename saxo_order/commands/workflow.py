import datetime
import logging
import os
from typing import List

import click
import yaml
from click.core import Context
from slack_sdk import WebClient

from client.aws_client import AwsClient
from client.saxo_client import SaxoClient
from engines.workflow_engine import WorkflowEngine
from model import (
    Close,
    Condition,
    Indicator,
    Trigger,
    Workflow,
    WorkflowElement,
)
from saxo_order.commands import catch_exception
from services.candles_service import CandlesService
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("workflow", logging.DEBUG)


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
@click.option(
    "--force-from-disk",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Load the workflows file from disk",
)
@click.option(
    "--select-workflow",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Select the workflow to run",
)
def workflow(ctx: Context, force_from_disk: str, select_workflow: str):
    config = ctx.obj["config"]
    execute_workflow(
        config,
        True if force_from_disk == "y" else False,
        True if select_workflow == "y" else False,
    )


def execute_workflow(
    config: str, force_from_disk: bool = False, select_workflow: bool = False
) -> None:
    configuration = Configuration(config)
    candles_service = CandlesService(SaxoClient(configuration))
    workflows = _yaml_loader(force_from_disk)

    if select_workflow is True:
        if len(workflows) > 1:
            prompt = "Select the workflow to run:\n"
            for index, workflow in enumerate(workflows):
                prompt += f"[{index + 1}] {workflow.name}\n"
            id = input(prompt)
        else:
            id = "1"
        if int(id) < 1 or int(id) > len(workflows):
            raise SaxoException("Wrong account selection")
        workflows = [workflows[int(id) - 1]]

    engine = WorkflowEngine(
        workflows=workflows,
        slack_client=WebClient(token=configuration.slack_token),
        candles_service=candles_service,
    )
    engine.run()


def _yaml_loader(force_from_disk: bool) -> List[Workflow]:
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
        end_date = datetime.datetime.strptime(
            workflow_data["end_date"], "%Y/%m/%d"
        ).date()
        enable = workflow_data["enable"]
        dry_run = workflow_data["dry_run"]
        is_us = workflow_data.get("is_us", False)

        conditions_data = workflow_data["conditions"]
        conditions = []
        for condition_data in conditions_data:
            indicator_data = condition_data["indicator"]
            indicator = Indicator(
                indicator_data["name"],
                indicator_data["ut"],
                indicator_data.get("value"),
            )
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
                is_us=is_us,
            )
        )
    return workflows
