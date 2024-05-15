import datetime
from typing import Optional

from model.enum import *
from model.workflow import *
from model.zone_bourse import ZoneBourseScore, ZoneBourseScrap


class Taxes:
    def __init__(self, cost: float, taxes: float) -> None:
        self.cost = cost
        self.taxes = taxes


class Account:
    def __init__(
        self,
        key: str,
        name: str,
        fund: float = 0,
        available_fund: float = 0,
        client_key: str = "",
    ) -> None:
        self.key = key
        self.name = name
        self.fund = fund
        self.available_fund = available_fund
        self.client_key = client_key


class Underlying:
    def __init__(
        self,
        price: float,
        stop: float = 0,
        objective: float = 0,
    ) -> None:
        self.price = price
        self.stop = stop
        self.objective = objective


class Order:
    def __init__(
        self,
        code: str,
        price: float,
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
        signal: Optional[Signal] = None,
    ) -> None:
        self.code = code
        self.price = price
        self.name = name
        self.quantity = quantity
        self.stop = stop
        self.objective = objective
        self.comment = comment
        self.strategy = strategy
        self.direction = direction
        self.asset_type = asset_type
        self.type = type
        self.taxes = taxes
        self.underlying = underlying
        self.conditional = conditional
        self.currency = currency
        self.signal = signal

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


class ConditionalOrder:
    def __init__(
        self, saxo_uic: int, trigger: TriggerOrder, price: float, asset_type: str
    ) -> None:
        self.saxo_uic = saxo_uic
        self.trigger = trigger
        self.price = price
        self.asset_type = asset_type


class StackingReport:
    def __init__(self, date: str, asset: str, quantity: float) -> None:
        self.date = date
        self.asset = asset
        self.quantity = quantity

    @property
    def id(self) -> str:
        return f"{self.date}{self.asset}"
