import copy
from typing import Dict, List, Optional, Union

from model import Account, AssetType, Currency, Order, ReportOrder, Taxes


def validate_ratio(order: Order) -> tuple:
    if order.underlying is not None:
        ratio = (order.underlying.objective - order.underlying.price) / (
            order.underlying.price - order.underlying.stop
        )
        return ratio >= 1.1, ratio
    if order.objective is not None and order.stop is not None:
        ratio = (order.objective - order.price) / (order.price - order.stop)
        return ratio >= 1.1, ratio
    return False, 0


def validate_max_order(order: Order, total_amount: float) -> bool:
    return order.price * order.quantity < total_amount * 0.1


def get_account_open_orders(account: Account, open_orders: List) -> float:
    buy_orders = list(
        filter(
            lambda x: x["AccountKey"] == account.key and x["BuySell"] == "Buy",
            open_orders,
        )
    )
    return sum(map(lambda x: x["Amount"] * x["Price"], buy_orders))


def validate_fund(account: Account, order: Order, open_orders: List) -> bool:
    sum_buy_orders = get_account_open_orders(account=account, open_orders=open_orders)
    return order.quantity * order.price < account.fund - sum_buy_orders


def apply_rules(
    account: Account,
    order: Order,
    total_amount: float,
    open_orders: List,
) -> Optional[str]:
    ratio = validate_ratio(order)
    if ratio[0] is False:
        return f"Ratio earn / lost must be greater than 1.5 ({ratio[1]})"
    if validate_fund(account, order, open_orders) is False:
        return "Not enough money for this order"
    if validate_max_order(order, total_amount) is False:
        return f"A position can't be greater than 10% of the fund ({total_amount})"
    return None


def calculate_taxes(order: Order) -> Taxes:
    total = order.price * order.quantity
    cost = 2.5
    if total >= 1000:
        cost = 5
    taxes = 0.003 * total if order.asset_type == AssetType.STOCK else 0
    if order.asset_type in [AssetType.CFDINDEX, AssetType.CFDFUTURE]:
        cost = 0
    return Taxes(cost, taxes)


def calculate_currency(order: Order, currencies_rate: Dict) -> Order | ReportOrder:
    rate = 1
    new_order = copy.deepcopy(order)
    if order.currency == Currency.USD:
        rate = currencies_rate["usdeur"]
    elif order.currency == Currency.JPY:
        rate = currencies_rate["jpyeur"]
    new_order.price *= rate
    if new_order.stop is not None:
        new_order.stop *= rate
    if new_order.objective is not None:
        new_order.objective *= rate
    if new_order.underlying is not None:
        new_order.underlying.price *= rate
        if new_order.underlying.stop is not None:
            new_order.underlying.stop *= rate
        if new_order.underlying.objective is not None:
            new_order.underlying.objective *= rate
    return new_order


def get_lost(total_funds: float, order: Order) -> str:
    if order.stop is not None:
        lost = order.quantity * (order.price - order.stop)
        return f"Lost: {lost} ({((order.price - order.stop) / order.price) * 100:.2f} %) ({(lost / total_funds) * 100:.2f} % of funds)"
    return "Stop is not set"


def get_earn(total_funds: float, order: Order) -> str:
    if order.objective is not None:
        earn = order.quantity * (order.objective - order.price)
        return f"Earn: {earn} ({((order.objective - order.price) / order.price) * 100:.2f} %) ({(earn / total_funds) * 100:.2f} % of funds)"
    return "Objective is not set"
