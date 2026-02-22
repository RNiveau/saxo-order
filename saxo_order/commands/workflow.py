import logging

import click
from click.core import Context
from slack_sdk import WebClient

from client.aws_client import DynamoDBClient
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
def run(ctx: Context, force_from_disk: str, select_workflow: str):
    """Run workflows."""
    config = ctx.obj["config"]
    execute_workflow(
        config,
        True if force_from_disk == "y" else False,
        True if select_workflow == "y" else False,
    )


@click.command()
@click.pass_context
@click.option(
    "--code",
    type=str,
    required=True,
    help="The asset code (e.g., itp, DAX.I)",
)
@click.option(
    "--country-code",
    type=str,
    required=False,
    default="xpar",
    help="The country code of the asset (e.g., xpar)",
)
@click.option(
    "--force-from-disk",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Load the workflows file from disk",
)
@catch_exception(handle=SaxoException)
def asset(ctx: Context, code: str, country_code: str, force_from_disk: str):
    """List all workflows for a specific asset."""
    symbol = f"{code}:{country_code}" if country_code else code
    workflows = load_workflows(True if force_from_disk == "y" else False)

    matching_workflows = [
        w
        for w in workflows
        if w.index.lower() == code.lower() or w.index.lower() == symbol.lower()
    ]

    if not matching_workflows:
        print(f"No workflows found for asset: {symbol}")
        return

    print(f"\nWorkflows for {symbol}:")
    print("=" * 80)
    for workflow in matching_workflows:
        status = "✓ ENABLED" if workflow.enable else "✗ DISABLED"
        dry_run = " [DRY RUN]" if workflow.dry_run else ""
        print(f"\n{workflow.name} - {status}{dry_run}")
        print(f"  Index: {workflow.index}")
        print(f"  CFD: {workflow.cfd}")
        if workflow.end_date:
            print(f"  End Date: {workflow.end_date}")
        print("  Conditions:")
        for cond in workflow.conditions:
            element_str = f" ({cond.element.value})" if cond.element else ""
            print(
                f"    - {cond.indicator.name.value} {cond.indicator.ut.value}"
                f" {cond.close.direction.value} close"
                f" {cond.close.ut.value}{element_str}"
            )
        print("  Trigger:")
        print(
            f"    - {workflow.trigger.signal.value} "
            f"{workflow.trigger.location.value}"
            f" -> {workflow.trigger.order_direction.value}"
            f" (qty: {workflow.trigger.quantity})"
        )
    print("\n" + "=" * 80)
    print(f"Total: {len(matching_workflows)} workflow(s)")


def execute_workflow(
    config: str, force_from_disk: bool = False, select_workflow: bool = False
) -> None:
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)
    candles_service = CandlesService(saxo_client)
    dynamodb_client = DynamoDBClient()
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
        saxo_client=saxo_client,
        dynamodb_client=dynamodb_client,
    )
    engine.run()
