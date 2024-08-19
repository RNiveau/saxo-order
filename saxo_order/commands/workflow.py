import logging

import click
from click.core import Context
from slack_sdk import WebClient

from client.saxo_client import SaxoClient
from engines.workflow_engine import WorkflowEngine
from engines.workflow_loader import load_workflows
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
    workflows = load_workflows(force_from_disk)

    if select_workflow is True:
        workflows_select = list(filter(lambda x: x.enable, workflows))
        if len(workflows_select) > 1:
            prompt = "Select the workflow to run:\n"
            for index, workflow in enumerate(workflows_select):
                prompt += f"[{index + 1}] {workflow.name}\n"
            id = input(prompt)
        else:
            id = "1"
        if int(id) < 1 or int(id) > len(workflows):
            raise SaxoException("Wrong account selection")
        workflows = [workflows_select[int(id) - 1]]

    engine = WorkflowEngine(
        workflows=workflows,
        slack_client=WebClient(token=configuration.slack_token),
        candles_service=candles_service,
    )
    engine.run()
