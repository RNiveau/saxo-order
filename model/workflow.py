from enum import StrEnum
from typing import List, Union

import yaml


class UnitTime(StrEnum):

    D = "daily"
    H1 = "h1"
    H4 = "h4"
    W = "weekly"

    @staticmethod
    def get_value(value):
        for member in UnitTime:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class WorkflowDirection(StrEnum):

    BELOW = "below"
    ABOVE = "above"

    @staticmethod
    def get_value(value):
        for member in WorkflowDirection:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class WorkflowLocation(StrEnum):

    LOWER = "lower"

    @staticmethod
    def get_value(value):
        for member in WorkflowLocation:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class WorkflowSignal(StrEnum):

    BREAK = "breakout"

    @staticmethod
    def get_value(value):
        for member in WorkflowSignal:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class IndicatorType(StrEnum):
    MA50 = "ma50"

    @staticmethod
    def get_value(value):
        for member in IndicatorType:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class Indicator:
    def __init__(self, name: Union[str | IndicatorType], ut: Union[str | UnitTime]):
        self.name = IndicatorType.get_value(name) if type(name) == str else name
        self.ut = UnitTime.get_value(ut) if type(ut) == str else ut


class Close:
    def __init__(
        self,
        direction: Union[str | WorkflowDirection],
        ut: Union[str | UnitTime],
        spread: float,
    ):
        self.direction = (
            WorkflowDirection.get_value(direction)
            if type(direction) == str
            else direction
        )
        self.ut = UnitTime.get_value(ut) if type(ut) == str else ut
        self.spread = spread


class Condition:
    def __init__(self, indicator: Indicator, close: Close):
        self.indicator = indicator
        self.close = close


class Trigger:
    def __init__(
        self, ut: Union[str | UnitTime], signal: Union[str | UnitTime], location
    ):
        self.ut = UnitTime.get_value(ut) if type(ut) == str else ut
        self.signal = (
            WorkflowSignal.get_value(signal) if type(signal) == str else signal
        )
        self.location = (
            WorkflowLocation.get_value(location) if type(location) == str else location
        )


class Workflow:
    def __init__(
        self,
        name: str,
        index: str,
        cfd: str,
        end_date: str,
        enable: bool,
        conditions: List[Condition],
        trigger: Trigger,
    ):
        self.name = name
        self.index = index
        self.cfd = cfd
        self.end_date = end_date
        self.enable = enable
        self.conditions = conditions
        self.trigger = trigger


# Load YAML data
yaml_data = """
- name: sell ma50 h4 dax
  index: DAX.I
  cfd: GER40.I
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
    type: breakout
    where: lower
"""

# Parse YAML
workflows_data = yaml.safe_load(yaml_data)

# Create Workflow objects
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
    trigger = Trigger(trigger_data["ut"], trigger_data["type"], trigger_data["where"])

    workflows.append(Workflow(name, index, cfd, end_date, enable, conditions, trigger))
