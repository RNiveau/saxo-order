import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order import (
    catch_exception,
    select_account,
    validate_buy_order,
    update_order,
    config_option,
)
from model import Order, Direction


@config_option
@click.command()
@click.option(
    "--search",
    type=str,
    required=True,
    help="The keyword for search",
    prompt="What is the keyword ?",
)
@click.option(
    "--asset-type",
    type=str,
    help="The asset type of the search",
    default="",
    prompt="What is the asset type (Stock, ETF, Turbo, ...)?",
)
@catch_exception(handle=SaxoException)
def search(config: str, search: str, asset_type: str):
    client = SaxoClient(Configuration(config))
    for data in client.search(keyword=search, asset_type=asset_type):
        print(
            f"{data['Description']}: code: {data['Symbol']}, type: {data['AssetType']}"
        )
