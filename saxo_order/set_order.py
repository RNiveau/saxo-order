import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order import (
    catch_exception,
    select_account,
    validate_buy_order,
    update_order,
    command_common_options,
    config_option,
)
from model import Order


@config_option
@command_common_options
@click.command()
@click.option(
    "--price",
    type=float,
    required=True,
    help="The price of the order",
    prompt="What is the price of the order ?",
)
@click.option(
    "--order-type",
    type=click.Choice(["limit", "stop"]),
    help="The order type",
    default="limit",
)
@click.option(
    "--buy-or-sell",
    type=click.Choice(["buy", "sell"]),
    required=True,
    default="buy",
    help="The direction of the order",
    prompt="What is the direction of the order ?",
)
@catch_exception(handle=SaxoException)
def set_order(config, price, code, country_code, quantity, order_type, buy_or_sell):
    client = SaxoClient(Configuration(config))
    stock = client.get_stock(code=code, market=country_code)
    order = Order(code=code, name=stock["Description"], price=price, quantity=quantity)
    account = select_account(client)
    if buy_or_sell == "buy":
        update_order(order)
        validate_buy_order(account, client, order)
    client.set_order(
        account_key=account.key,
        price=price,
        quantity=quantity,
        order=order_type,
        direction=buy_or_sell,
        stock_code=stock["Identifier"],
    )
    if buy_or_sell == "buy":
        print(order.csv())
