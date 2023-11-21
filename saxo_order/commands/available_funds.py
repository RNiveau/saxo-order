import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order.service import get_account_open_orders
from saxo_order.commands import catch_exception, config_option
from saxo_order.commands.input_helper import select_account


@click.command()
@config_option
@catch_exception(handle=SaxoException)
def available_funds(config: str):
    client = SaxoClient(Configuration(config))
    account = select_account(client)
    open_orders = client.get_open_orders()
    sum_open_order = get_account_open_orders(account=account, open_orders=open_orders)
    print(account.available_fund - sum_open_order)
