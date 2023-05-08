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
@click.option(
    "--config",
    type=str,
    required=True,
    default="config.yml",
    help="The path to config file",
)
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
def set_order(config, price, code, country_code, quantity, order_type, buy_or_sell):
    client = SaxoClient(Configuration(config))
    stock = client.get_stock(code=code, market=country_code)
    account_key = select_account(client)
    client.set_order(
        account_key=account_key,
        price=price,
        quantiy=quantity,
        order=order_type,
        direction=buy_or_sell,
        stock_code=stock["Identifier"],
    )


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
    account_key = select_account(client)
    client.set_order(
        account_key=account_key,
        price=limit_price,
        stop_price=stop_price,
        quantiy=quantity,
        order="stoplimit",
        direction="buy",
        stock_code=stock["Identifier"],
    )


@click.command()
@click.option(
    "--config",
    type=str,
    required=True,
    default="config.yml",
    help="The path to config file",
)
@click.option("--write", type=click.Choice(["y", "n"]), help="Write the access token ?")
@catch_exception(handle=SaxoException)
def auth(config, write):
    auth_client = SaxoAuthClient(Configuration(config))
    print(auth_client.login())
    url = input("What's the url provide by saxo ?\n")
    match = re.search(r"\?code=([\w-]+)", url)
    if not match:
        print("The url doesn't contain a code")
        exit(1)
    access_token = auth_client.access_token(match.group(1))
    if write is None:
        should_write = input("Do you want to save the access token ? (Y/n)\n")
    if write == "y" or should_write == "Y" or should_write == "y":
        with open("access_token", "w") as f:
            f.write(f"{access_token}\n")


def select_account(client: SaxoClient) -> str:
    accounts = client.get_accounts()
    prompt = "Select the account (select with ID):\n"
    for account in accounts["Data"]:
        if "DisplayName" in account:
            prompt += f"- {account['DisplayName']} | {account['AccountId']}\n"
        else:
            prompt += f"- NoName | {account['AccountId']}\n"
    id = input(prompt)
    account = list(filter(lambda x: x["AccountId"] == id, accounts["Data"]))
    if len(account) != 1:
        raise SaxoException("Wrong account selection")
    return account[0]["AccountKey"]
