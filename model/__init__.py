import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional

from model.enum import (  # noqa: F401
    AlertType,
    AssetType,
    Currency,
    Direction,
    OrderType,
    Signal,
    Strategy,
    TriggerOrder,
)
from model.workflow import (  # noqa: F401
    BollingerBands,
    Candle,
    Close,
    ComboSignal,
    Condition,
    Indicator,
    IndicatorType,
    SignalStrength,
    Trigger,
    UnitTime,
    Workflow,
    WorkflowDirection,
    WorkflowElement,
    WorkflowLocation,
    WorkflowSignal,
)
from model.zone_bourse import ZoneBourseScore, ZoneBourseScrap  # noqa: F401


@dataclass
class Alert:
    alert_type: AlertType
    date: datetime.datetime
    data: Dict[str, Any]
    asset_code: str
    asset_description: str
    exchange: str = "saxo"
    country_code: Optional[str] = None

    @property
    def id(self) -> str:
        """Composite ID from asset code and country code"""
        if self.country_code:
            return f"{self.asset_code}_{self.country_code}"
        else:
            return self.asset_code


@dataclass
class Taxes:
    cost: float
    taxes: float


@dataclass
class Account:

    key: str
    name: str
    fund: float = 0
    available_fund: float = 0
    client_key: str = ""


@dataclass
class Underlying:
    price: float
    stop: float = 0
    objective: float = 0


@dataclass
class Order:

    code: str
    price: float
    name: str = ""
    quantity: float = 0
    objective: Optional[float] = None
    stop: Optional[float] = None
    comment: Optional[str] = None
    strategy: Optional[Strategy] = None
    direction: Optional[Direction] = None
    asset_type: str = "Stock"
    type: OrderType = OrderType.LIMIT
    taxes: Optional[Taxes] = None
    underlying: Optional[Underlying] = None
    conditional: bool = False
    currency: Currency = Currency.EURO
    signal: Optional[Signal] = None

    def __repr__(self) -> str:
        return f"{self.code}: {self.quantity} * {self.price} {self.currency}"


class ReportOrder(Order):
    def __init__(
        self,
        code: str,
        price: float,
        date: datetime.datetime,
        name: str = "",
        quantity: float = 0,
        objective: Optional[float] = None,
        stop: Optional[float] = None,
        comment: Optional[str] = None,
        strategy: Optional[Strategy] = None,
        direction: Optional[Direction] = None,
        asset_type: str = "Stock",
        type: OrderType = OrderType.LIMIT,
        taxes: Optional[Taxes] = None,
        underlying: Optional[Underlying] = None,
        conditional: bool = False,
        currency: Currency = Currency.EURO,
        stopped: bool = False,
        be_stopped: bool = False,
        open_position: bool = True,
    ) -> None:
        super().__init__(
            code,
            price,
            name,
            quantity,
            objective,
            stop,
            comment,
            strategy,
            direction,
            asset_type,
            type,
            taxes,
            underlying,
            conditional,
            currency,
        )
        self.date = date
        self.stopped = stopped
        self.be_stopped = be_stopped
        self.open_position = open_position


@dataclass
class ConditionalOrder:
    saxo_uic: int
    trigger: TriggerOrder
    price: float
    asset_type: str


@dataclass
class StackingReport:
    date: str
    asset: str
    quantity: float

    @property
    def id(self) -> str:
        return f"{self.date}{self.asset}"


@dataclass
class Market:
    open_hour: int
    open_minutes: int
    close_hour: int


class USMarket(Market):
    def __init__(self) -> None:
        super().__init__(open_hour=13, close_hour=21, open_minutes=30)


class EUMarket(Market):
    def __init__(self) -> None:
        super().__init__(open_hour=7, close_hour=17, open_minutes=0)
