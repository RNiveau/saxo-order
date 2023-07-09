import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order import catch_exception, select_account, validate_buy_order, update_order
from model import Order, Direction


@click.command()
@click.option(
    "--config",
    type=str,
    required=True,
    default="config.yml",
    help="The path to config file",
)
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
    prompt="What is the keyword (Stock, ETF, Turbo, ...)?",
)
@catch_exception(handle=SaxoException)
def search(config: str, search: str, asset_type: str):
    client = SaxoClient(Configuration(config))
    for data in client.search(keyword=search, asset_type=asset_type):
        print(
            f"{data['Description']}: code: {data['Symbol']}, type: {data['AssetType']}"
        )
