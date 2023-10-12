import click

from client.saxo_client import SaxoClient
from model import Account, Order, Underlying, ConditionalOrder, TriggerOrder
from saxo_order.service import apply_rules, calculate_taxes, get_lost, get_earn
from utils.exception import SaxoException
from typing import Optional


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
        stop = click.prompt("What is the stop price ?", type=float)
        objective = click.prompt("What is the objective price ?", type=float)
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


def update_order(order: Order, conditional_order: Optional[ConditionalOrder] = None):
    if order.asset_type != "Stock" or conditional_order is not None:
        if conditional_order is None:
            price = click.prompt("What is the price of the underlying ?", type=float)
        else:
            price = conditional_order.price
        underlying = Underlying(price)
    stop, objective = get_stop_objective()
    order.stop = stop
    order.objective = objective
    if order.asset_type != "Stock" or conditional_order is not None:
        underlying.stop = stop
        underlying.objective = objective
        order.underlying = underlying
    order.comment = click.prompt("Comment about this position: ", type=str)
    order.taxes = calculate_taxes(order)


def validate_buy_order(account: Account, client: SaxoClient, order: Order) -> None:
    open_orders = client.get_open_orders()
    total_amount = client.get_total_amount()
    error = apply_rules(account, order, total_amount, open_orders)
    if error is not None:
        print(error)
        raise click.Abort(error)


def confirm_order(client: SaxoClient, order: Order) -> None:
    total = client.get_total_amount()
    print(get_lost(total, order))
    print(get_earn(total, order))
    click.confirm("Do you want to continue?", abort=True)


def get_conditional_order(client: SaxoClient) -> ConditionalOrder:
    code_conditional = click.prompt("What is the code of the condition ?", type=str)
    price_conditional = click.prompt("What is the price of the condition ?", type=float)
    trigger = TriggerOrder.get_value(
        click.prompt(
            "Trigger the order if we are above or below the price ?",
            type=click.Choice(["above", "below"]),
        )
    )
    asset_conditional = client.get_asset(code=code_conditional)
    return ConditionalOrder(
        saxo_uic=asset_conditional["Identifier"],
        price=price_conditional,
        asset_type=asset_conditional["AssetType"],
        trigger=trigger,
    )
