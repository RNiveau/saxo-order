from typing import Optional


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
        quantity: Optional[int] = None,
        objective: Optional[float] = None,
        stop: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> None:
        self.code = code
        self.price = price
        self.quantity = quantity
        self.stop = stop
        self.objective = objective
        self.comment = comment
