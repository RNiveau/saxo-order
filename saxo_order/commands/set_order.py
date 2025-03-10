import click
from click.core import Context

from client.saxo_client import SaxoClient
from model import Currency, Direction, Order, OrderType
from saxo_order.commands import catch_exception
from saxo_order.commands.common import logs_order
from saxo_order.commands.input_helper import (
    confirm_order,
    get_conditional_order,
    select_account,
    update_order,
    validate_buy_order,
)
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("set_order")


@click.command(name="order")
@click.option(
    "--price",
    type=float,
    required=True,
    help="The price of the order",
    prompt="What is the price of the order ?",
)
@click.option(
    "--order-type",
    type=click.Choice(["limit", "stop", "open_stop", "market"]),
    help="The order type",
    default="limit",
    prompt="What is the order type ?",
)
@click.option(
    "--direction",
    type=click.Choice(["buy", "sell"]),
    required=True,
    default="buy",
    help="The direction of the order",
    prompt="What is the direction of the order ?",
)
@click.option(
    "--conditional",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Set a conditional order",
    prompt="Is it a conditional order ?",
)
@click.pass_context
@catch_exception(handle=SaxoException)
def set_order(
    ctx: Context,
    price: float,
    order_type: str,
    direction: str,
    conditional: bool,
):
    code = ctx.obj["code"]
    configuration = Configuration(ctx.obj["config"])
    saxo_client = SaxoClient(configuration)
    asset = saxo_client.get_asset(code=code, market=ctx.obj["country_code"])
    if OrderType.MARKET == OrderType.get_value(order_type):
        price = saxo_client.get_price(asset["Identifier"], asset["AssetType"])
    order = Order(
        code=code,
        name=asset["Description"],
        price=price,
        quantity=ctx.obj["quantity"],
        asset_type=asset["AssetType"],
        type=OrderType.get_value(order_type),
        direction=Direction.get_value(direction),
        currency=Currency.get_value(asset["CurrencyCode"]),
    )
    conditional_order = None
    if conditional == "y":
        conditional_order = get_conditional_order(saxo_client)
    account = select_account(saxo_client)
    if Direction.BUY == order.direction:
        update_order(order, conditional_order)
        validate_buy_order(account, saxo_client, order)
        confirm_order(saxo_client, order)
    saxo_client.set_order(
        account=account,
        order=order,
        saxo_uic=asset["Identifier"],
        conditional_order=conditional_order,
    )
    if Direction.BUY == order.direction:
        logs_order(configuration, order, account)
