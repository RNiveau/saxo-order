import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order.commands import catch_exception, config_option
from saxo_order.commands.input_helper import select_account


@config_option
@click.command()
@click.option(
    "--from-date",
    type=str,
    required=True,
    help="What is the start date",
    prompt="What is the start date ? (YYYY/MM/DD)",
)
@catch_exception(handle=SaxoException)
def get_report(config: str, from_date: str):
    client = SaxoClient(Configuration(config))
    account = select_account(client)
    print(client.get_report(account, from_date))
