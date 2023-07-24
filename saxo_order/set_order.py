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
from model import Order, OrderType, Direction


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
    "--direction",
    type=click.Choice(["buy", "sell"]),
    required=True,
    default="buy",
    help="The direction of the order",
    prompt="What is the direction of the order ?",
)
@catch_exception(handle=SaxoException)
def set_order(config, price, code, country_code, quantity, order_type, direction):
    client = SaxoClient(Configuration(config))
    asset = client.get_asset(code=code, market=country_code)
    order = Order(
        code=code,
        name=asset["Description"],
        price=price,
        quantity=quantity,
        asset_type=asset["AssetType"],
        type=OrderType.get_value(order_type),
        direction=Direction.get_value(direction),
    )
    account = select_account(client)
    if Direction.BUY == order.direction:
        update_order(order)
        validate_buy_order(account, client, order)
    client.set_order(
        account=account,
        order=order,
        saxo_uic=asset["Identifier"],
    )
    if Direction.BUY == order.direction:
        print(order.csv())
