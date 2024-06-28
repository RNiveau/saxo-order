import click
from click.core import Context

from client.saxo_client import SaxoClient
from saxo_order.commands import catch_exception
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("search")


@click.command()
@click.option(
    "--search",
    type=str,
    required=True,
    help="The keyword for search",
    prompt="What is the keyword ?",
)
@click.pass_context
@catch_exception(handle=SaxoException)
def search(ctx: Context, search: str):
    client = SaxoClient(Configuration(ctx.obj["config"]))
    for data in client.search(keyword=search):
        print(
            f"{data['Description']}: code: {data['Symbol']},"
            f" type: {data['AssetType']}"
        )
