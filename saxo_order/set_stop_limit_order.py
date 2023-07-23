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
    "--limit-price",
    type=float,
    required=True,
    help="The limit price of the order",
    prompt="What is the price of the limit order ?",
)
@click.option(
    "--stop-price",
    type=float,
    required=True,
    help="The stop price of the order",
    prompt="What is the price of the stop order ?",
)
@catch_exception(handle=SaxoException)
def set_stop_limit_order(config, limit_price, stop_price, code, country_code, quantity):
    client = SaxoClient(Configuration(config))
    stock = client.get_stock(code=code, market=country_code)
    account = select_account(client)
    order = Order(
        code=code, name=stock["Description"], price=limit_price, quantity=quantity
    )
    update_order(order)
    validate_buy_order(account, client, order)
    client.set_order(
        account_key=account.key,
        price=limit_price,
        stop_price=stop_price,
        quantiy=quantity,
        order="stoplimit",
        direction="buy",
        stock_code=stock["Identifier"],
    )
    print(order.csv())
