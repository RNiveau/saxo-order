import click
import re

from client.saxo_auth_client import SaxoAuthClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from saxo_order.commands import catch_exception
from click.core import Context


@click.command()
@click.option(
    "--write",
    default="y",
    type=click.Choice(["y", "n"]),
    help="Write the access token ?",
)
@catch_exception(handle=SaxoException)
@click.pass_context
def auth(ctx: Context, write: bool):
    auth_client = SaxoAuthClient(Configuration(ctx.obj["config"]))
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
