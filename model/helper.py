from typing import Optional

from model import Order


def get_stop(order: Order) -> Optional[float]:
    if order.underlying is not None:
        return order.underlying.stop
    return order.stop


def get_objective(order: Order) -> Optional[float]:
    if order.underlying is not None:
        return order.underlying.objective
    return order.objective
