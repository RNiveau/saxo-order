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
from model import Order, Direction, OrderType


@config_option
@command_common_options
@click.command()
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
    default="sell",
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
@catch_exception(handle=SaxoException)
def set_oco_order(
    config: str,
    limit_price: float,
    limit_direction: str,
    stop_price: float,
    stop_direction: str,
    code: str,
    country_code: str,
    quantity: int,
):
    configuration = Configuration(config)
    client = SaxoClient(configuration)
    asset = client.get_asset(code=code, market=country_code)
    limit_order = Order(
        code=code,
        name=asset["Description"],
        price=limit_price,
        quantity=quantity,
        direction=Direction.get_value(limit_direction),
        asset_type=asset["AssetType"],
        type=OrderType.OCO,
    )
    stop_order = Order(
        code=code,
        name=asset["Description"],
        price=stop_price,
        quantity=quantity,
        direction=Direction.get_value(stop_direction),
        asset_type=asset["AssetType"],
        type=OrderType.OCO,
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
        result = gsheet_client.create_order(account, stop_order)
        print(f"Row {result['updates']['updatedRange']} appended.")
