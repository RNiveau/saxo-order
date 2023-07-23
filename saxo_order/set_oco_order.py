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
)
from model import Order, Direction


@command_common_options
@click.command()
@click.option(
    "--limit-price",
    type=float,
    required=True,
    help="The price of the limit order",
    prompt="What is the price of the limit order ?",
)
@click.option(
    "--limit-direction",
    type=click.Choice(["buy", "sell"]),
    default="sell",
    required=True,
    help="The direction of the limit order",
    prompt="What is the direction of the limit order ?",
)
@click.option(
    "--stop-price",
    type=float,
    required=True,
    help="The price of the stop order",
    prompt="What is the price of the stop order ?",
)
@click.option(
    "--stop-direction",
    type=click.Choice(["buy", "sell"]),
    default="buy",
    required=True,
    help="The direction of the stop order",
    prompt="What is the direction of the stop order ?",
)
@catch_exception(handle=SaxoException)
def set_oco_order(
    config: str,
    limit_price: float,
    limit_direction: str,
    stop_price: float,
    stop_direction: str,
    code: str,
    country_code: str,
    quantity: int,
):
    client = SaxoClient(Configuration(config))
    stock = client.get_stock(code=code, market=country_code)
    limit_order = Order(
        code=code,
        name=stock["Description"],
        price=limit_price,
        quantity=quantity,
        direction=Direction.get_value(limit_direction),
    )
    stop_order = Order(
        code=code,
        name=stock["Description"],
        price=stop_price,
        quantity=quantity,
        direction=Direction.get_value(stop_direction),
    )
    account = select_account(client)
    if stop_direction == "buy":
        update_order(stop_order)
        validate_buy_order(account, client, stop_order)
    client.set_oco_order(
        account=account,
        limit_order=limit_order,
        stop_order=stop_order,
        saxo_uic=stock["Identifier"],
    )
    if stop_direction == "buy":
        print(stop_order.csv())
