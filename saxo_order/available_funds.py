import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order import (
    catch_exception,
    select_account,
    config_option,
    get_account_open_orders,
)


@config_option
@click.command()
@catch_exception(handle=SaxoException)
def available_funds(config: str):
    client = SaxoClient(Configuration(config))
    account = select_account(client)
    open_orders = client.get_open_orders()
    sum_open_order = get_account_open_orders(account=account, open_orders=open_orders)
    print(account.available_fund - sum_open_order)
