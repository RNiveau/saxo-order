import click

from client.saxo_client import SaxoClient
from model import Account, Order, Underlying
from saxo_order.service import apply_rules, calculate_taxes
from utils.exception import SaxoException


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


def update_order(order: Order):
    if order.asset_type != "Stock":
        price = float(input("What is the price of the underlying ?"))
        underlying = Underlying(price)
    stop, objective = get_stop_objective()
    order.stop = stop
    order.objective = objective
    if order.asset_type != "Stock":
        underlying.stop = stop
        underlying.objective = objective
        order.underlying = underlying
    order.comment = input("Comment about this position: ")
    order.taxes = calculate_taxes(order)


def validate_buy_order(account: Account, client: SaxoClient, order: Order) -> None:
    open_orders = client.get_open_orders()
    total_amount = client.get_total_amount()
    error = apply_rules(account, order, total_amount, open_orders)
    if error is not None:
        print(error)
        raise click.Abort(error)
