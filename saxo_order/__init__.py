import click

from functools import wraps, partial
from typing import List

from client.saxo_client import SaxoClient
from utils.exception import SaxoException
from model import Account


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
    prompt = "Select the account (select with ID):\n"
    for account in accounts["Data"]:
        if "DisplayName" in account:
            prompt += f"- {account['DisplayName']} | {account['AccountId']}\n"
        else:
            prompt += f"- NoName | {account['AccountId']}\n"
    id = input(prompt)
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


def validate_ratio(price: float, stop: float, objective: float) -> bool:
    return ((objective - price) / (price - stop)) >= 1.5


def validate_max_order(price: float, quantity: int, total_amount: float) -> bool:
    return price * quantity < total_amount * 0.1


def validate_fund(
    account: Account, price: float, quantity: int, open_orders: List
) -> bool:
    buy_orders = list(
        filter(
            lambda x: x["AccountKey"] == account.key and x["BuySell"] == "Buy",
            open_orders,
        )
    )
    sum_buy_orders = sum(map(lambda x: x["Amount"] * x["Price"], buy_orders))
    return quantity * price < account.fund - sum_buy_orders


def apply_rules(
    account: Account,
    price: float,
    stop: float,
    objective: float,
    quantity: int,
    total_amount: float,
    open_orders: List,
) -> None:
    if validate_ratio(price, stop, objective) is False:
        return "Ratio earn / lost must be greater than 1.5"
    if validate_fund(account, price, quantity, open_orders) is False:
        return "Not enough money for this order"
    if validate_max_order(price, quantity, total_amount) is False:
        return f"A position can't be greater than 10% of the fund ({total_amount})"
    return None


def validate_buy_order(
    account: Account, client: SaxoClient, price: float, quantity: int
) -> None:
    stop, objective = get_stop_objective()
    open_orders = client.get_open_orders()
    total_amount = client.get_total_amount()
    error = apply_rules(
        account, price, stop, objective, quantity, total_amount, open_orders
    )
    if error is not None:
        print(error)
        raise click.Abort(error)
