import click
from click.core import Context

from client.saxo_client import SaxoClient
from saxo_order.commands import catch_exception
from saxo_order.commands.input_helper import select_account
from saxo_order.service import get_account_open_orders
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("available_funds")


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def available_funds(ctx: Context):

    client = SaxoClient(Configuration(ctx.obj["config"]))
    account = select_account(client)
    open_orders = client.get_open_orders()
    sum_open_order = get_account_open_orders(account=account, open_orders=open_orders)
    print(account.available_fund - sum_open_order)
