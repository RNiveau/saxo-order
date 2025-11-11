import click
from click.core import Context

from client.saxo_client import SaxoClient
from model import Direction
from saxo_order.commands import catch_exception
from saxo_order.commands.common import logs_order
from saxo_order.commands.input_helper import (
    confirm_order,
    get_conditional_order,
    select_account,
    update_order,
)
from saxo_order.services.order_service import OrderService
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
    quantity = ctx.obj["quantity"]
    configuration = Configuration(ctx.obj["config"])
    saxo_client = SaxoClient(configuration)
    order_service = OrderService(saxo_client, configuration)

    conditional_order = None
    if conditional == "y":
        conditional_order = get_conditional_order(saxo_client)

    account = select_account(saxo_client)

    stop = None
    objective = None
    strategy = None
    signal = None
    comment = None

    if Direction.get_value(direction) == Direction.BUY:
        temp_order = order_service.client.get_asset(
            code=code, market=ctx.obj["country_code"]
        )
        from model import Currency, Order, OrderType

        temp_order_obj = Order(
            code=code,
            name=temp_order["Description"],
            price=price,
            quantity=quantity,
            asset_type=temp_order["AssetType"],
            type=OrderType.get_value(order_type),
            direction=Direction.get_value(direction),
            currency=Currency.get_value(temp_order["CurrencyCode"]),
        )
        update_order(temp_order_obj, conditional_order)
        confirm_order(saxo_client, temp_order_obj)
        stop = temp_order_obj.stop
        objective = temp_order_obj.objective
        strategy = (
            temp_order_obj.strategy.value if temp_order_obj.strategy else None
        )
        signal = temp_order_obj.signal.value if temp_order_obj.signal else None
        comment = temp_order_obj.comment

    result = order_service.create_order(
        code=code,
        price=price,
        quantity=quantity,
        order_type=order_type,
        direction=direction,
        country_code=ctx.obj["country_code"],
        conditional_order=conditional_order,
        stop=stop,
        objective=objective,
        strategy=strategy,
        signal=signal,
        comment=comment,
        account_key=account.key,
    )

    if Direction.get_value(direction) == Direction.BUY:
        logs_order(configuration, result["order"], account)
