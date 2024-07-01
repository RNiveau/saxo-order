import datetime
from dataclasses import dataclass
from typing import List, Optional, Union

from model.enum import Direction
from model.enum_with_get_value import EnumWithGetValue


class UnitTime(EnumWithGetValue):

    D = "daily"
    M15 = "15m"
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
    BBB = "bbb"
    BBH = "bbh"
    POL = "polarite"


class WorkflowElement(EnumWithGetValue):
    CLOSE = "close"
    HIGH = "high"
    LOW = "low"


class Indicator:
    def __init__(
        self,
        name: Union[str | IndicatorType],
        ut: Union[str | UnitTime],
        value: Optional[float] = None,
    ):
        self.name = (
            IndicatorType.get_value(name) if isinstance(name, str) else name
        )
        self.ut = UnitTime.get_value(ut) if isinstance(ut, str) else ut
        self.value = value


class Close:
    def __init__(
        self,
        direction: Union[str | WorkflowDirection],
        ut: Union[str | UnitTime],
        spread: float,
    ):
        self.direction = (
            WorkflowDirection.get_value(direction)
            if isinstance(direction, str)
            else direction
        )
        self.ut = UnitTime.get_value(ut) if isinstance(ut, str) else ut
        self.spread = spread


@dataclass
class Condition:

    indicator: Indicator
    close: Close
    element: WorkflowElement


class Trigger:
    def __init__(
        self,
        ut: Union[str | UnitTime],
        signal: Union[str | WorkflowSignal],
        location: Union[str | WorkflowLocation],
        order_direction: Union[str | Direction],
        quantity: float,
    ):
        self.ut = UnitTime.get_value(ut) if isinstance(ut, str) else ut
        self.signal = (
            WorkflowSignal.get_value(signal)
            if isinstance(signal, str)
            else signal
        )
        self.location = (
            WorkflowLocation.get_value(location)
            if isinstance(location, str)
            else location
        )
        self.order_direction = (
            Direction.get_value(order_direction)
            if isinstance(order_direction, str)
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
    is_us: bool = False


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
