import click
import re
from functools import wraps, partial

from client.saxo_client import SaxoClient
from client.saxo_auth_client import SaxoAuthClient
from utils.configuration import Configuration
from utils.exception import SaxoException


def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            print(e)
            click.Abort()

    return wrapper


@click.command()
@click.option("--price", type=float, required=True, help="The price of the order")
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
@click.option(
    "--order-type",
    type=click.Choice(["limit", "stop"]),
    help="The order type",
    default="limit",
)
@click.option(
    "--buy-or-sell",
    type=click.Choice(["buy", "sell"]),
    required=True,
    default="buy",
    help="The direction of the order",
)
@catch_exception(handle=SaxoException)
def set_order(price, code, country_code, quantity, order_type, buy_or_sell):
    client = SaxoClient(Configuration())
    stock = client.get_stock(code=code, market=country_code)
    client.set_order(
        account_key="pblq5VW3dXTuCost|ihUfw==",
        price=price,
        quantiy=quantity,
        order=order_type,
        direction=buy_or_sell,
        stock_code=stock["Identifier"],
    )


@click.command()
@catch_exception(handle=SaxoException)
def auth():
    auth_client = SaxoAuthClient(Configuration())
    print(auth_client.login())
    url = input("What's the url provide by saxo ?\n")
    match = re.search(r"\?code=([\w-]+)", url)
    if not match:
        print("The url doesn't contain a code")
        exit(1)
    access_token = auth_client.access_token(match.group(1))
    should_write = input("Do you want to save the access token ? (Y/n)\n")
    if should_write == "Y" or should_write == "y":
        with open("access_token", "w") as f:
            f.write(f"{access_token}\n")
