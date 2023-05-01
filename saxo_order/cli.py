import click
import re

from client.saxo_client import SaxoClient
from client.saxo_auth_client import SaxoAuthClient
from utils.configuration import Configuration



@click.command()
@click.option('--price', type=float, required=True, help='The price of the order')
@click.option('--code', type=str, required=True, help='The code of the order')
@click.option('--order-type', type=click.Choice(['limit', 'stop']), help='The order type', default="limit")
def set_order(price, code, order_type):
    click.echo(f'Setting order price to {price} and code to {code}')
    # Your code to handle the order goes here

@click.command()
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
        with open('access_token', 'w') as f:
            f.write(f"{access_token}\n")

