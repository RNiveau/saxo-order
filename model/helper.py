from typing import Optional

from model import Order, Taxes


def get_stop(order: Order) -> Optional[float]:
    if order.underlying is not None:
        return order.underlying.stop
    return order.stop


def get_objective(order: Order) -> Optional[float]:
    if order.underlying is not None:
        return order.underlying.objective
    return order.objective


def get_taxes(order: Order) -> Taxes:
    return Taxes(0, 0) if order.taxes is None else order.taxes
