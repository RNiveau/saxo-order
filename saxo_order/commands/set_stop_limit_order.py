import click
from click.core import Context

from client.saxo_client import SaxoClient
from model import Currency, Direction, Order, OrderType
from saxo_order.commands import catch_exception
from saxo_order.commands.common import logs_order
from saxo_order.commands.input_helper import (
    confirm_order,
    select_account,
    update_order,
    validate_buy_order,
)
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("set_stop_limit_order")


@click.command(name="stop-limit-order")
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
@click.pass_context
@catch_exception(handle=SaxoException)
def set_stop_limit_order(
    ctx: Context,
    limit_price: float,
    stop_price: float,
):
    code = ctx.obj["code"]
    quantity = ctx.obj["quantity"]
    configuration = Configuration(ctx.obj["config"])
    client = SaxoClient(configuration)
    asset = client.get_asset(code=code, market=ctx.obj["country_code"])
    account = select_account(client)
    order = Order(
        code=code,
        name=asset["Description"],
        price=limit_price,
        quantity=quantity,
        asset_type=asset["AssetType"],
        type=OrderType.STOP_LIMIT,
        direction=Direction.BUY,
        currency=Currency.get_value(asset["CurrencyCode"]),
    )
    update_order(order)
    validate_buy_order(account, client, order)
    confirm_order(client, order)
    client.set_order(
        account=account,
        stop_price=stop_price,
        order=order,
        saxo_uic=asset["Identifier"],
    )
    logs_order(configuration, order, account)
