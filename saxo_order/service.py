from typing import List, Optional

from model import Account, Order, Taxes, AssetType


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


def get_lost(total_funds: float, order: Order) -> str:
    lost = order.quantity * (order.price - order.stop)
    return f"Lost: {lost} ({((order.price - order.stop) / order.price) * 100:.2f} %) ({(lost / total_funds) * 100:.2f} % of funds)"


def get_earn(total_funds: float, order: Order) -> str:
    earn = order.quantity * (order.objective - order.price)
    return f"Earn: {earn} ({((order.objective - order.price) / order.price) * 100:.2f} %) ({(earn / total_funds) * 100:.2f} % of funds)"
