import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order.commands import catch_exception, config_option


@config_option
@click.command()
@click.option(
    "--search",
    type=str,
    required=True,
    help="The keyword for search",
    prompt="What is the keyword ?",
)
@catch_exception(handle=SaxoException)
def search(config: str, search: str):
    client = SaxoClient(Configuration(config))
    for data in client.search(keyword=search):
        print(
            f"{data['Description']}: code: {data['Symbol']}, type: {data['AssetType']}"
        )
