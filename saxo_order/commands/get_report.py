import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order.commands import catch_exception, config_option
from saxo_order.commands.input_helper import select_account


@config_option
@click.command()
@catch_exception(handle=SaxoException)
def get_report(config: str):
    client = SaxoClient(Configuration(config))
    account = select_account(client)
    client.get_report(account)
