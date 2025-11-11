import click
from click.core import Context

from client.saxo_client import SaxoClient
from model import Direction
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

logger = Logger.get_logger("set_oco_order")


@click.command(name="oco-order")
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
    default="buy",
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
@click.pass_context
@catch_exception(handle=SaxoException)
def set_oco_order(
    ctx: Context,
    limit_price: float,
    limit_direction: str,
    stop_price: float,
    stop_direction: str,
):
    code = ctx.obj["code"]
    quantity = ctx.obj["quantity"]
    configuration = Configuration(ctx.obj["config"])
    client = SaxoClient(configuration)
    order_service = OrderService(client, configuration)

    account = select_account(client)

    stop = None
    objective = None
    strategy = None
    signal = None
    comment = None

    if Direction.get_value(stop_direction) == Direction.BUY:
        temp_asset = client.get_asset(
            code=code, market=ctx.obj["country_code"]
        )
        from model import Currency, Order, OrderType

        temp_stop_order = Order(
            code=code,
            name=temp_asset["Description"],
            price=stop_price,
            quantity=quantity,
            direction=Direction.get_value(stop_direction),
            asset_type=temp_asset["AssetType"],
            type=OrderType.OCO,
            currency=Currency.get_value(temp_asset["CurrencyCode"]),
        )
        update_order(temp_stop_order)
        confirm_order(client, temp_stop_order)
        stop = temp_stop_order.stop
        objective = temp_stop_order.objective
        strategy = (
            temp_stop_order.strategy.value
            if temp_stop_order.strategy
            else None
        )
        signal = (
            temp_stop_order.signal.value if temp_stop_order.signal else None
        )
        comment = temp_stop_order.comment

    result = order_service.create_oco_order(
        code=code,
        quantity=quantity,
        limit_price=limit_price,
        limit_direction=limit_direction,
        stop_price=stop_price,
        stop_direction=stop_direction,
        country_code=ctx.obj["country_code"],
        stop=stop,
        objective=objective,
        strategy=strategy,
        signal=signal,
        comment=comment,
        account_key=account.key,
    )

    if Direction.get_value(stop_direction) == Direction.BUY:
        logs_order(configuration, result["stop_order"], account)
