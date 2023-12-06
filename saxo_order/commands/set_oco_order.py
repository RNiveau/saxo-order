import click
from click.core import Context

from client.gsheet_client import GSheetClient
from client.saxo_client import SaxoClient
from model import Currency, Direction, Order, OrderType
from saxo_order.commands import catch_exception
from saxo_order.commands.input_helper import (
    confirm_order,
    select_account,
    update_order,
    validate_buy_order,
)
from saxo_order.service import calculate_currency
from utils.configuration import Configuration
from utils.exception import SaxoException


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
    asset = client.get_asset(code=code, market=ctx.obj["country_code"])
    limit_order = Order(
        code=code,
        name=asset["Description"],
        price=limit_price,
        quantity=quantity,
        direction=Direction.get_value(limit_direction),
        asset_type=asset["AssetType"],
        type=OrderType.OCO,
        currency=Currency.get_value(asset["CurrencyCode"]),
    )
    stop_order = Order(
        code=code,
        name=asset["Description"],
        price=stop_price,
        quantity=quantity,
        direction=Direction.get_value(stop_direction),
        asset_type=asset["AssetType"],
        type=OrderType.OCO,
        currency=Currency.get_value(asset["CurrencyCode"]),
    )
    account = select_account(client)
    if stop_order.direction == Direction.BUY:
        update_order(stop_order)
        validate_buy_order(account, client, stop_order)
        confirm_order(client, stop_order)
    client.set_oco_order(
        account=account,
        limit_order=limit_order,
        stop_order=stop_order,
        saxo_uic=asset["Identifier"],
    )
    if stop_order.direction == Direction.BUY:
        gsheet_client = GSheetClient(
            key_path=configuration.gsheet_creds_path,
            spreadsheet_id=configuration.spreadsheet_id,
        )
        stop_order = calculate_currency(stop_order, configuration.currencies_rate)
        result = gsheet_client.create_order(account, stop_order)
        print(f"Row {result['updates']['updatedRange']} appended.")
