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


def shortcut_common_options(func):
    func = click.option(
        "--price",
        type=float,
        required=True,
        help="The price of the order",
        prompt="What is the price of the order ?",
    )(func)
    func = click.option(
        "--order-type",
        type=click.Choice(["limit", "stop", "open_stop", "market"]),
        help="The order type",
        default="limit",
        prompt="What is the order type ?",
    )(func)
    func = click.option(
        "--direction",
        type=click.Choice(["buy", "sell"]),
        required=True,
        default="buy",
        help="The direction of the order",
        prompt="What is the direction of the order ?",
    )(func)
    return func


@click.command()
@shortcut_common_options
@catch_exception(handle=SaxoException)
@click.pass_context
def dax(ctx: Context, price: float, order_type: str, direction: str):
    code = "GER40.I"
    shortcut(ctx, price, order_type, direction, code)


@click.command()
@shortcut_common_options
@catch_exception(handle=SaxoException)
@click.pass_context
def nasdaq(ctx: Context, price: float, order_type: str, direction: str):
    code = "USNAS100.I"
    shortcut(ctx, price, order_type, direction, code)


@click.command()
@shortcut_common_options
@catch_exception(handle=SaxoException)
@click.pass_context
def nikkei(ctx: Context, price: float, order_type: str, direction: str):
    code = "JP225.I"
    shortcut(ctx, price, order_type, direction, code)


@click.command()
@shortcut_common_options
@catch_exception(handle=SaxoException)
@click.pass_context
def cac(ctx: Context, price: float, order_type: str, direction: str):
    code = "FRA40.I"
    shortcut(ctx, price, order_type, direction, code)


@click.command()
@shortcut_common_options
@catch_exception(handle=SaxoException)
@click.pass_context
def sp500(ctx: Context, price: float, order_type: str, direction: str):
    code = "US500.I"
    shortcut(ctx, price, order_type, direction, code)


@click.command()
@shortcut_common_options
@catch_exception(handle=SaxoException)
@click.pass_context
def russell(ctx: Context, price: float, order_type: str, direction: str):
    print("You need to think about the cotation diff: future is + 20")
    code = "US2000MAR24"
    shortcut(ctx, price, order_type, direction, code)


def shortcut(ctx: Context, price: float, order_type: str, direction: str, code: str):
    configuration = Configuration(ctx.obj["config"])
    saxo_client = SaxoClient(configuration)
    asset = saxo_client.get_asset(code=code)
    saxo_uic = asset["Identifier"]
    asset = saxo_client.get_asset_detail(
        saxo_uic=saxo_uic, asset_type=asset["AssetType"]
    )
    if len(asset["TradableOn"]) != 1:
        click.Abort("Can't select a tradable account")
        exit(1)
    if OrderType.MARKET == OrderType.get_value(order_type):
        price = saxo_client.get_price(saxo_uic, asset["AssetType"])
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
    accounts = saxo_client.get_accounts()
    account_key = list(
        filter(lambda x: x["AccountId"] == asset["TradableOn"][0], accounts["Data"])
    )[0]["AccountKey"]
    account = saxo_client.get_account(account_key)
    update_order(order)
    confirm_order(saxo_client, order)
    saxo_client.set_order(
        account=account,
        order=order,
        saxo_uic=saxo_uic,
    )
    gsheet_client = GSheetClient(
        key_path=configuration.gsheet_creds_path,
        spreadsheet_id=configuration.spreadsheet_id,
    )
    calculate_currency(order, configuration.currencies_rate)
    result = gsheet_client.create_order(account, order)
    print(f"Row {result['updates']['updatedRange']} appended.")
