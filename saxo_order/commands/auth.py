import re
import subprocess

import click
from click.core import Context

from client.saxo_auth_client import SaxoAuthClient
from saxo_order.commands import catch_exception
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("auth")


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
    configuration = Configuration(ctx.obj["config"])
    auth_client = SaxoAuthClient(configuration)
    print(auth_client.login())
    subprocess.run(["open", auth_client.login()])
    url = input("What's the url provide by saxo ?\n")
    match = re.search(r"\?code=([\w-]+)", url)
    if not match:
        print("The url doesn't contain a code")
        exit(1)
    access_token, refresh_token = auth_client.access_token(match.group(1))
    if write is None:
        should_write: str = input("Do you want to save the access token ? (Y/n)\n")
    if write == "y" or should_write == "Y" or should_write == "y":
        configuration.save_tokens(access_token, refresh_token)
