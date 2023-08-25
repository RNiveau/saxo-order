from typing import List

from model import Account, Order, Taxes


def validate_ratio(order: Order) -> tuple:
    if order.asset_type != "Stock":
        ratio = (order.underlying.objective - order.underlying.price) / (
            order.underlying.price - order.underlying.stop
        )
        return ratio >= 1.5, ratio
    ratio = (order.objective - order.price) / (order.price - order.stop)
    return ratio >= 1.5, ratio


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
) -> None:
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
    taxes = 0.003 * total
    return Taxes(cost, taxes)