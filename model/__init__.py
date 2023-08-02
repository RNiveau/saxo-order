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


class OrderType(StrEnum):
    LIMIT = "limit"
    STOP = "stop"
    OCO = "oco"
    STOP_LIMIT = "stoplimit"

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
        fund: Optional[float] = None,
        available_fund: Optional[float] = None,
    ) -> None:
        self.key = key
        self.name = name
        self.fund = fund
        self.available_fund = available_fund


class Underlying:
    def __init__(
        self,
        price: float,
        stop: Optional[float] = None,
        objective: Optional[float] = None,
    ) -> None:
        self.price = price
        self.stop = stop
        self.objective = objective


class Order:
    def __init__(
        self,
        code: str,
        price: float,
        name: Optional[str] = None,
        quantity: Optional[int] = None,
        objective: Optional[float] = None,
        stop: Optional[float] = None,
        comment: Optional[str] = None,
        strategy: Optional[str] = None,
        direction: Optional[Direction] = None,
        asset_type: Optional[str] = "Stock",
        type: Optional[OrderType] = OrderType.LIMIT,
        taxes: Optional[Taxes] = None,
        underlying: Optional[Underlying] = None,
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

    def csv(self):
        locale.setlocale(locale.LC_ALL, "fr_FR")
        now = datetime.now().strftime("%d/%m/%Y")
        return f"{self.name};{self.code.upper()};{self.price:n};{self.quantity};;;0;{self.stop:n};;{self.objective:n};;;;{self.taxes.cost};{self.taxes.taxes};;{now};;;;;;;Achat;;{self.strategy};;;;;;;;;;{self.comment}"
