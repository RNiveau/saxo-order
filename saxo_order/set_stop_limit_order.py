import click

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order import catch_exception, select_account, validate_buy_order


@click.command()
@click.option(
    "--config",
    type=str,
    required=True,
    default="config.yml",
    help="The path to config file",
)
@click.option(
    "--limit-price", type=float, required=True, help="The limit price of the order"
)
@click.option(
    "--stop-price", type=float, required=True, help="The stop price of the order"
)
@click.option("--code", type=str, required=True, help="The code of the stock")
@click.option(
    "--country-code",
    type=str,
    required=True,
    default="xpar",
    help="The country code of the stock",
)
@click.option(
    "--quantity", type=int, required=True, help="The wanted quantity of stocks"
)
@catch_exception(handle=SaxoException)
def set_stop_limit_order(config, limit_price, stop_price, code, country_code, quantity):
    client = SaxoClient(Configuration(config))
    stock = client.get_stock(code=code, market=country_code)
    account = select_account(client)
    validate_buy_order(account, client, limit_price, quantity)
    client.set_order(
        account_key=account.key,
        price=limit_price,
        stop_price=stop_price,
        quantiy=quantity,
        order="stoplimit",
        direction="buy",
        stock_code=stock["Identifier"],
    )
