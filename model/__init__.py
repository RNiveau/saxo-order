from typing import Optional
from datetime import datetime
from enum import StrEnum


class Currency(StrEnum):
    EURO = "EUR"
    USD = "USD"

    @staticmethod
    def get_value(value):
        for member in Currency:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class AssetType(StrEnum):
    WARRANT = "WarrantOpenEndKnockOut"
    WARRANT_KNOCK_OUT = "WarrantKnockOut"
    ETF = "Etf"
    TURBO = "MiniFuture"
    STOCK = "Stock"
    INDEX = "StockIndex"
    CFDINDEX = "CfdOnIndex"
    CFDFUTURE = "CfdOnFutures"

    @staticmethod
    def get_value(value):
        for member in AssetType:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")

    @staticmethod
    def all_values():
        return ",".join(AssetType)


class Direction(StrEnum):
    BUY = "Buy"
    SELL = "Sell"

    @staticmethod
    def get_value(value):
        for member in Direction:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class TriggerOrder(StrEnum):
    ABOVE = "above"
    BELLOW = "below"

    @staticmethod
    def get_value(value):
        for member in TriggerOrder:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


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
        raise ValueError(f"Invalid string: {value}")


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
        strategy: Optional[str] = None,
        direction: Optional[Direction] = None,
        asset_type: str = "Stock",
        type: OrderType = OrderType.LIMIT,
        taxes: Optional[Taxes] = None,
        underlying: Optional[Underlying] = None,
        conditional: bool = False,
        currency: Currency = Currency.EURO,
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


class ReportOrder(Order):
    def __init__(
        self,
        code: str,
        price: float,
        date: datetime,
        name: str = "",
        quantity: float = 0,
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
