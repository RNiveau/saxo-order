import datetime
import logging
from typing import List

import click
import yaml
from click.core import Context

from client.saxo_client import SaxoClient
from model import Condition, Indicator, Trigger, Workflow
from saxo_order.commands import catch_exception
from services.workflow_service import WorkflowService
from utils.configuration import Configuration
from utils.exception import SaxoException


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def workflow(ctx: Context):
    logging.basicConfig(level=logging.INFO)
    workflow_service = WorkflowService(SaxoClient(Configuration(ctx.obj["config"])))
    workflows = _yaml_loader()
    for workflow in workflows:
        if workflow.enable:
            # workflow.conditions[0].
            ###            print(saxo_client.calculate_ma(workflow.index, workflow.conditions[0].indicator.ut, workflow.conditions[0].indicator.name))
            print(
                workflow_service.calculate_ma(
                    workflow.index,
                    workflow.conditions[0].indicator.ut,
                    workflow.conditions[0].indicator.name,
                    _get_date_utc0(),
                )
            )


def _get_date_utc0() -> datetime.datetime:
    date = datetime.datetime.now(tz=datetime.UTC)
    return date
    one_hour = datetime.timedelta(hours=1)
    return date + one_hour


def _yaml_loader() -> List[Workflow]:
    # Load YAML data
    yaml_data = """
- name: sell ma50 h4 dax
  index: CAC40.I #DAX.I
  cfd: FRA40.I #GER40.I
  end_date: 2024/04/01
  enable: true
  conditions:
    - indicator:
          name: ma50
          ut: h4
      close:
         direction: below
         ut: h1
         spread: 10
  trigger:
      ut: h1
      signal: breakout
      location: lower
    """

    workflows_data = yaml.safe_load(yaml_data)

    workflows = []
    for workflow_data in workflows_data:
        name = workflow_data["name"]
        index = workflow_data["index"]
        cfd = workflow_data["cfd"]
        end_date = workflow_data["end_date"]
        enable = workflow_data["enable"]

        conditions_data = workflow_data["conditions"]
        conditions = []
        for condition_data in conditions_data:
            indicator_data = condition_data["indicator"]
            indicator = Indicator(indicator_data["name"], indicator_data["ut"])
            close_data = condition_data["close"]
            close = Condition(indicator, close_data)
            conditions.append(close)

        trigger_data = workflow_data["trigger"]
        trigger = Trigger(
            trigger_data["ut"], trigger_data["signal"], trigger_data["location"]
        )

        workflows.append(
            Workflow(name, index, cfd, end_date, enable, conditions, trigger)
        )
    return workflows
