from typing import Optional

import click

from client.saxo_client import SaxoClient
from model import (
    Account,
    AssetType,
    ConditionalOrder,
    Order,
    Signal,
    Strategy,
    TriggerOrder,
    Underlying,
)
from saxo_order.service import apply_rules, calculate_taxes, get_earn, get_lost
from utils.exception import SaxoException


def select_account(client: SaxoClient) -> Account:
    accounts = client.get_accounts()
    if len(accounts["Data"]) > 1:
        prompt = "Select the account (select with ID):\n"
        for index, account in enumerate(accounts["Data"]):
            if "DisplayName" in account:
                prompt += f"[{index + 1}] {account['DisplayName']}"
                prompt += "| {account['AccountId']}\n"
            else:
                prompt += f"[{index + 1}] NoName | {account['AccountId']}\n"
        id = input(prompt)
    else:
        id = "1"
        print(
            f"Auto select account {accounts['Data'][0]['AccountId']} as only"
            " one account is available"
        )
    if "/" in id:
        account = list(
            filter(lambda x: x["AccountId"] == id, accounts["Data"])
        )
        if len(account) != 1:
            raise SaxoException("Wrong account selection")
        return client.get_account(account[0]["AccountKey"])
    if int(id) < 1 or int(id) > len(accounts["Data"]):
        raise SaxoException("Wrong account selection")
    account = accounts["Data"][int(id) - 1]
    return client.get_account(account["AccountKey"])


def get_stop_objective(validate_input: bool) -> tuple:
    try:
        stop = click.prompt(
            "What is the stop price ?",
            type=float,
            show_default=False,
            default=0,
        )
        objective = click.prompt(
            "What is the objective price ?",
            type=float,
            show_default=False,
            default=0,
        )
        if stop == 0:
            stop = None
        if objective == 0:
            objective = None
    except Exception:
        stop = None
        objective = None
    if stop is None and validate_input:
        print("Stop price is mandatory to set an order")
        raise click.Abort()
    if objective is None and validate_input:
        print("Objective price is mandatory to set an order")
        raise click.Abort()
    return (stop, objective)


def update_order(
    order: Order,
    conditional_order: Optional[ConditionalOrder] = None,
    validate_input: bool = True,
) -> None:
    with_underlying = (
        order.asset_type
        not in [
            AssetType.STOCK,
            AssetType.CFDFUTURE,
            AssetType.CFDINDEX,
            AssetType.CRYPTO,
        ]
        or conditional_order is not None
    )
    if with_underlying:
        if conditional_order is None:
            price = click.prompt(
                "What is the price of the underlying ?", type=float
            )
        else:
            price = conditional_order.price
        underlying = Underlying(price)
    stop, objective = get_stop_objective(validate_input)
    order.stop = stop
    order.objective = objective
    if with_underlying:
        underlying.stop = stop
        underlying.objective = objective
        order.underlying = underlying
    order.strategy = get_strategy()
    order.signal = get_signal()
    order.comment = click.prompt("Comment about this position: ", type=str)
    if order.taxes is None:
        order.taxes = calculate_taxes(order)


def get_strategy() -> Optional[Strategy]:
    _list = [e.value for e in Strategy]
    for index, strategy in enumerate(_list):
        print(f"{index + 1} - {strategy}")
    index = click.prompt(
        "What is the strategy ? ",
        type=click.IntRange(0, index + 1),
        show_default=False,
        default=0,
    )
    if index == 0:
        return None
    return Strategy.get_value(_list[index - 1])


def get_signal() -> Optional[Signal]:
    _list = [e.value for e in Signal]
    for index, signal in enumerate(_list):
        print(f"{index + 1} - {signal}")
    index = click.prompt(
        "What is the signal ? ",
        type=click.IntRange(0, index + 1),
        show_default=False,
        default=0,
    )
    if index == 0:
        return None
    return Signal.get_value(_list[index - 1])


def validate_buy_order(
    account: Account, client: SaxoClient, order: Order
) -> None:
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
    code_conditional = click.prompt(
        "What is the code of the condition ?", type=str
    )
    price_conditional = click.prompt(
        "What is the price of the condition ?", type=float
    )
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
