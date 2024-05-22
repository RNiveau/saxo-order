import datetime
from dataclasses import dataclass
from typing import List, Optional, Union

from model.enum import Direction
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
    HIGHER = "higher"


class WorkflowSignal(EnumWithGetValue):

    BREAKOUT = "breakout"


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
        self,
        ut: Union[str | UnitTime],
        signal: Union[str | WorkflowSignal],
        location: Union[str | WorkflowLocation],
        order_direction: Union[str | Direction],
        quantity: float,
    ):
        self.ut = UnitTime.get_value(ut) if type(ut) == str else ut
        self.signal = (
            WorkflowSignal.get_value(signal) if type(signal) == str else signal
        )
        self.location = (
            WorkflowLocation.get_value(location) if type(location) == str else location
        )
        self.order_direction = (
            Direction.get_value(order_direction)
            if type(order_direction) == str
            else order_direction
        )
        self.quantity = quantity


@dataclass
class Workflow:
    name: str
    index: str
    cfd: str
    end_date: datetime.date
    conditions: List[Condition]
    trigger: Trigger
    enable: bool = False
    dry_run: bool = True


@dataclass
class Candle:
    lower: float
    higher: float
    open: float
    close: float
    ut: UnitTime
    date: Optional[datetime.datetime] = None


@dataclass
class BollingerBands:

    bottom: float
    up: float
    middle: float
    ut: Optional[UnitTime] = None
    date: Optional[datetime.datetime] = None
