import click
from click.core import Context

import saxo_order.commands.alerting as alerting
import saxo_order.commands.auth as auth
import saxo_order.commands.available_funds as available_funds
import saxo_order.commands.binance as binance_commands
import saxo_order.commands.fundamental as get_score
import saxo_order.commands.get_report as get_report
import saxo_order.commands.internal as internal_command
import saxo_order.commands.search as search
import saxo_order.commands.set_oco_order as set_oco_order
import saxo_order.commands.set_order as set_order
import saxo_order.commands.set_stop_limit_order as set_stop_limit_order
import saxo_order.commands.shortcuts as shortcurts
import saxo_order.commands.workflow as workflow


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


@click.group()
@click.option(
    "--quantity",
    type=float,
    required=True,
    help="The wanted quantity of stocks",
    prompt="What is the quantity of product ?",
)
@click.pass_context
def shortcut(ctx: Context, quantity: float):
    ctx.obj["quantity"] = quantity


@click.group()
@click.pass_context
def binance(ctx: Context):
    pass


@click.group()
@click.pass_context
def internal(ctx: Context):
    pass


k_order.add_command(set)
k_order.add_command(shortcut)
k_order.add_command(binance)
k_order.add_command(internal)

k_order.add_command(alerting.alerting)
k_order.add_command(get_score.get_score)
k_order.add_command(auth.auth)
k_order.add_command(available_funds.available_funds)
k_order.add_command(get_report.get_report)
k_order.add_command(search.search)
k_order.add_command(workflow.workflow)

set.add_command(set_order.set_order)
set.add_command(set_oco_order.set_oco_order)
set.add_command(set_stop_limit_order.set_stop_limit_order)

shortcut.add_command(shortcurts.dax)
shortcut.add_command(shortcurts.cac)
shortcut.add_command(shortcurts.sp500)
shortcut.add_command(shortcurts.russell)
shortcut.add_command(shortcurts.nasdaq)
shortcut.add_command(shortcurts.nikkei)

binance.add_command(binance_commands.get_report)
binance.add_command(binance_commands.get_stacking_report)

internal.add_command(internal_command.refresh_stocks_list)
internal.add_command(internal_command.technical)
internal.add_command(internal_command.sync_workflows)
