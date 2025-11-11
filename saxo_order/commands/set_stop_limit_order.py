import click
from click.core import Context

from client.saxo_client import SaxoClient
from saxo_order.commands import catch_exception
from saxo_order.commands.common import logs_order
from saxo_order.commands.input_helper import (
    confirm_order,
    select_account,
    update_order,
)
from saxo_order.services.order_service import OrderService
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
    order_service = OrderService(client, configuration)

    account = select_account(client)

    temp_asset = client.get_asset(code=code, market=ctx.obj["country_code"])
    from model import Currency, Direction, Order, OrderType

    temp_order = Order(
        code=code,
        name=temp_asset["Description"],
        price=limit_price,
        quantity=quantity,
        asset_type=temp_asset["AssetType"],
        type=OrderType.STOP_LIMIT,
        direction=Direction.BUY,
        currency=Currency.get_value(temp_asset["CurrencyCode"]),
    )
    update_order(temp_order)
    confirm_order(client, temp_order)

    result = order_service.create_stop_limit_order(
        code=code,
        quantity=quantity,
        limit_price=limit_price,
        stop_price=stop_price,
        country_code=ctx.obj["country_code"],
        stop=temp_order.stop,
        objective=temp_order.objective,
        strategy=temp_order.strategy.value if temp_order.strategy else None,
        signal=temp_order.signal.value if temp_order.signal else None,
        comment=temp_order.comment,
        account_key=account.key,
    )

    logs_order(configuration, result["order"], account)
