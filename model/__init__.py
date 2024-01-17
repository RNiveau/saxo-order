from datetime import datetime
from enum import StrEnum
from typing import Optional


class Strategy(StrEnum):
    IMP = "Bougie impulsive"
    BH = "Breakout haussier"
    C200 = "Cassure mm200"
    COMBO = "Combo"
    CONG = "Congestion"
    DIV = "Dividende"
    EH = "Engloblante haussière"
    INTRA = "Intraday"
    IVT = "IVT"
    FLUX = "Journée flux"
    R7 = "Rebond mm7"
    R20 = "Rebond mm20"
    R50 = "Rebond mm50"
    R200 = "Rebond mm200"
    RES = "Résultat d'entreprise"
    REVERSE = "Revere"
    SI = "Stratagème de l'impulsion"
    SCT = "Support court terme"
    SMT = "Support moyen terme"
    SLT = "Support long terme"
    TF = "Trendfollowing"
    VS = "Vente cassure de support"
    VR = "Vente de résistance"
    VB = "Vente plus bas"
    YOLO = "Yolo"

    @staticmethod
    def get_value(value):
        for member in Strategy:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class Signal(StrEnum):
    BHH1 = "Breakout h1"
    BHH4 = "Breakout h4"
    BHD = "Breakout daily"
    BHW = "Breakout weekly"
    ENGLO = "Englobante"
    DOUBLE_TOP = "Double top"
    FIBO = "Fibo 50%"
    POL = "Polarité"
    RP = "Reprise de l'open"
    TMM7 = "Touchette mm7"
    TMM20 = "Touchette mm20"
    TMM50 = "Touchette mm50"
    TMM200 = "Touchette mm200"
    NONE = "No signal"

    @staticmethod
    def get_value(value):
        for member in Signal:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")


class Currency(StrEnum):
    EURO = "EUR"
    USD = "USD"
    JPY = "JPY"

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
    CRYPTO = "Crypto"

    @staticmethod
    def get_value(value):
        for member in AssetType:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid string: {value}")

    @staticmethod
    def all_saxo_values():
        values = filter(lambda x: x != AssetType.CRYPTO, AssetType)
        return ",".join(values)


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
    OPEN_STOP = "open_stop"
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
        date: datetime,
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
