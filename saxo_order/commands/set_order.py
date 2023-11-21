import click

from client.saxo_client import SaxoClient
from client.gsheet_client import GSheetClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order.commands.input_helper import (
    select_account,
    validate_buy_order,
    update_order,
    confirm_order,
    get_conditional_order,
)
from saxo_order.commands import catch_exception, config_option, command_common_options
from model import Order, OrderType, Direction, Currency
from saxo_order.service import calculate_currency


@click.command()
@config_option
@command_common_options
@click.option(
    "--price",
    type=float,
    required=True,
    help="The price of the order",
    prompt="What is the price of the order ?",
)
@click.option(
    "--order-type",
    type=click.Choice(["limit", "stop", "market"]),
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
@catch_exception(handle=SaxoException)
def set_order(
    config, price, code, country_code, quantity, order_type, direction, conditional
):
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)
    asset = saxo_client.get_asset(code=code, market=country_code)
    if OrderType.MARKET == OrderType.get_value(order_type):
        price = saxo_client.get_price(asset["Identifier"], asset["AssetType"])
    order = Order(
        code=code,
        name=asset["Description"],
        price=price,
        quantity=quantity,
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
        gsheet_client = GSheetClient(
            key_path=configuration.gsheet_creds_path,
            spreadsheet_id=configuration.spreadsheet_id,
        )
        calculate_currency(order, configuration.usdeur_rate)
        result = gsheet_client.create_order(account, order)
        print(f"Row {result['updates']['updatedRange']} appended.")
