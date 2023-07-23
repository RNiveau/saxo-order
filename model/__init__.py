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


class Account:
    def __init__(self, key: str, fund: float, available_fund: float) -> None:
        self.key = key
        self.fund = fund
        self.available_fund = available_fund


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
        type: Optional[str] = "Stock",
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
        self.type = type

    def csv(self):
        locale.setlocale(locale.LC_ALL, "fr_FR")
        now = datetime.now().strftime("%d/%m/%Y")
        return f"{self.name};{self.code.upper()};{self.price:n};{self.quantity};;;0;{self.stop:n};;{self.objective:n};;;;2,50;;;{now};;;;;;;Achat;;{self.strategy};;;;;;;;;;{self.comment}"
