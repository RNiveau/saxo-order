from typing import List, Union

from model.enum_with_get_value import EnumWithGetValue


class UnitTime(EnumWithGetValue):

    D = "daily"
    H1 = "h1"
    H4 = "h4"
    W = "weekly"


class WorkflowDirection(EnumWithGetValue):

    BELOW = "below"
    ABOVE = "above"


class WorkflowLocation(EnumWithGetValue):

    LOWER = "lower"


class WorkflowSignal(EnumWithGetValue):

    BREAK = "breakout"


class IndicatorType(EnumWithGetValue):
    MA50 = "ma50"


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
