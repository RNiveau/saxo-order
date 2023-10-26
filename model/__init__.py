from typing import Optional
from datetime import datetime
from enum import StrEnum
import locale


class Direction(StrEnum):
    BUY = "Buy"
    SELL = "Sell"

    @staticmethod
    def get_value(value):
        for member in Direction:
            if member.value.lower() == value.lower():
                return member
        raise ValueError("Invalid string")


class TriggerOrder(StrEnum):
    ABOVE = "above"
    BELLOW = "below"

    @staticmethod
    def get_value(value):
        for member in TriggerOrder:
            if member.value.lower() == value.lower():
                return member
        raise ValueError("Invalid string")


class OrderType(StrEnum):
    LIMIT = "limit"
    STOP = "stop"
    OCO = "oco"
    STOP_LIMIT = "stoplimit"
    MARKET = "market"

    @staticmethod
    def get_value(value):
        for member in OrderType:
            if member.value.lower() == value.lower():
                return member
        raise ValueError("Invalid string")


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
        quantity: int = 0,
        objective: Optional[float] = None,
        stop: Optional[float] = None,
        comment: Optional[str] = None,
        strategy: Optional[str] = None,
        direction: Optional[Direction] = None,
        asset_type: str = "Stock",
        type: OrderType = OrderType.LIMIT,
        taxes: Optional[Taxes] = None,
        underlying: Optional[Underlying] = None,
        conditional: bool = False,
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

    def csv(self):
        locale.setlocale(locale.LC_ALL, "fr_FR")
        now = datetime.now().strftime("%d/%m/%Y")
        objective = self.objective if self.objective is not None else 0
        stop = self.stop if self.stop is not None else 0
        taxes = self.taxes if self.taxes is not None else Taxes(0, 0)
        return f"{self.name};{self.code.upper()};{self.price:n};{self.quantity};;;0;{stop:n};;;{objective:n};;;;{taxes.cost};{taxes.taxes};;{now};;;;;;;Achat;;{self.strategy};;;;;;;;;;{self.comment}"


class ReportOrder(Order):
    def __init__(
        self,
        code: str,
        price: float,
        name: str = "",
        quantity: int = 0,
        objective: Optional[float] = None,
        stop: Optional[float] = None,
        comment: Optional[str] = None,
        strategy: Optional[str] = None,
        direction: Optional[Direction] = None,
        asset_type: str = "Stock",
        type: OrderType = OrderType.LIMIT,
        taxes: Optional[Taxes] = None,
        underlying: Optional[Underlying] = None,
        conditional: bool = False,
        date: str = "",
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
        )
        self.date = date


class ConditionalOrder:
    def __init__(
        self, saxo_uic: int, trigger: TriggerOrder, price: float, asset_type: str
    ) -> None:
        self.saxo_uic = saxo_uic
        self.trigger = trigger
        self.price = price
        self.asset_type = asset_type
