import click

import saxo_order.commands.auth as auth
import saxo_order.commands.available_funds as available_funds
import saxo_order.commands.get_report as get_report
import saxo_order.commands.search as search
import saxo_order.commands.set_oco_order as set_oco_order
import saxo_order.commands.set_order as set_order
import saxo_order.commands.set_stop_limit_order as set_stop_limit_order
from click.core import Context


@click.group()
@click.option(
    "--config",
    type=str,
    required=True,
    default="config.yml",
    envvar="SAXO_CONFIG",
    help="The path to config file",
)
@click.pass_context
def k_order(ctx: Context, config: str):
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@click.group()
@click.option(
    "--code",
    type=str,
    required=True,
    help="The code of the stock",
    prompt="What is the code of the product ?",
)
@click.option(
    "--country-code",
    type=str,
    required=True,
    default="xpar",
    help="The country code of the stock",
)
@click.option(
    "--quantity",
    type=float,
    required=True,
    help="The wanted quantity of stocks",
    prompt="What is the quantity of product ?",
)
@click.pass_context
def set(
    ctx: Context,
    code: str,
    country_code: str,
    quantity: float,
):
    ctx.obj["code"] = code
    ctx.obj["country_code"] = country_code
    ctx.obj["quantity"] = quantity


k_order.add_command(set)
k_order.add_command(auth.auth)
k_order.add_command(available_funds.available_funds)
k_order.add_command(get_report.get_report)
k_order.add_command(search.search)

set.add_command(set_order.set_order)
set.add_command(set_oco_order.set_oco_order)
set.add_command(set_stop_limit_order.set_stop_limit_order)
