import click

from functools import wraps, partial
from typing import List

from client.saxo_client import SaxoClient
from utils.exception import SaxoException
from model import Account, Order, Taxes


def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            print(e)
            raise click.Abort()

    return wrapper


def select_account(client: SaxoClient) -> Account:
    accounts = client.get_accounts()
    if len(accounts["Data"]) > 1:
        prompt = "Select the account (select with ID):\n"
        for account in accounts["Data"]:
            if "DisplayName" in account:
                prompt += f"- {account['DisplayName']} | {account['AccountId']}\n"
            else:
                prompt += f"- NoName | {account['AccountId']}\n"
        id = input(prompt)
    else:
        id = accounts["Data"][0]["AccountId"]
        print(f"Auto select account {id} as only one account is available")
    account = list(filter(lambda x: x["AccountId"] == id, accounts["Data"]))
    if len(account) != 1:
        raise SaxoException("Wrong account selection")
    return client.get_account(account[0]["AccountKey"], account[0]["ClientKey"])


def get_stop_objective() -> tuple:
    try:
        stop = float(input("What is the stop price ?"))
        objective = float(input("What is the objective price ?"))
    except:
        stop = 0
        objective = 0
    if stop == 0:
        print("Stop price is mandatory to set an order")
        raise click.Abort()
    if objective == 0:
        print("Objective price is mandatory to set an order")
        raise click.Abort()
    return (stop, objective)


def validate_ratio(order: Order) -> bool:
    return ((order.objective - order.price) / (order.price - order.stop)) >= 1.5


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
    if validate_ratio(order) is False:
        return "Ratio earn / lost must be greater than 1.5"
    if validate_fund(account, order, open_orders) is False:
        return "Not enough money for this order"
    if validate_max_order(order, total_amount) is False:
        return f"A position can't be greater than 10% of the fund ({total_amount})"
    return None


def update_order(order: Order):
    stop, objective = get_stop_objective()
    order.stop = stop
    order.objective = objective
    order.comment = input("Comment about this position: ")
    order.taxes = calculate_taxes(order)


def validate_buy_order(account: Account, client: SaxoClient, order: Order) -> None:
    open_orders = client.get_open_orders()
    total_amount = client.get_total_amount()
    error = apply_rules(account, order, total_amount, open_orders)
    if error is not None:
        print(error)
        raise click.Abort(error)


def config_option(func):
    return click.option(
        "--config",
        type=str,
        required=True,
        default="config.yml",
        help="The path to config file",
    )(func)


def command_common_options(func):
    func = click.option(
        "--code",
        type=str,
        required=True,
        help="The code of the stock",
        prompt="What is the code of the product ?",
    )(func)
    func = click.option(
        "--country-code",
        type=str,
        required=True,
        default="xpar",
        help="The country code of the stock",
    )(func)
    func = click.option(
        "--quantity",
        type=int,
        required=True,
        help="The wanted quantity of stocks",
        prompt="What is the quantity of product ?",
    )(func)
    return func


def calculate_taxes(order: Order) -> Taxes:
    total = order.price * order.quantity
    cost = 2.5
    if total >= 1000:
        cost = 5
    taxes = 0.003 * total
    return Taxes(cost, taxes)
