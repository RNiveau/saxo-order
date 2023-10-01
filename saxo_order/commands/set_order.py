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
)
from saxo_order.commands import catch_exception, config_option, command_common_options
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
@catch_exception(handle=SaxoException)
def set_order(config, price, code, country_code, quantity, order_type, direction):
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
    )
    account = select_account(saxo_client)
    if Direction.BUY == order.direction:
        update_order(order)
        validate_buy_order(account, saxo_client, order)
        confirm_order(saxo_client, order)
    saxo_client.set_order(
        account=account,
        order=order,
        saxo_uic=asset["Identifier"],
    )
    if Direction.BUY == order.direction:
        gsheet_client = GSheetClient(
            key_path=configuration.gsheet_creds_path,
            spreadsheet_id=configuration.spreadsheet_id,
        )
        result = gsheet_client.save_order(account, order)
        print(f"Row {result['updates']['updatedRange']} appended.")
        print(order.csv())
