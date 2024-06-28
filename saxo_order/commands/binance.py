from datetime import datetime
from typing import Dict

import click
from click.core import Context

from client.binance_client import BinanceClient
from client.gsheet_client import GSheetClient
from model import Account, Currency, ReportOrder, StackingReport
from saxo_order.commands import catch_exception
from saxo_order.commands.input_helper import update_order
from saxo_order.service import calculate_currency
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("binance")


@click.command
@click.option(
    "--from-date",
    type=str,
    required=True,
    help="What is the start date",
    prompt="What is the start date ? (YYYY/MM/DD)",
)
@click.option(
    "--update-gsheet",
    type=bool,
    required=True,
    help="Do you want to update the gsheet ?",
    prompt="Do you want to update the gsheet ?",
)
@click.pass_context
@catch_exception(handle=SaxoException)
def get_report(ctx: Context, from_date: str, update_gsheet: bool):
    configuration = Configuration(ctx.obj["config"])
    gsheet_client = GSheetClient(
        key_path=configuration.gsheet_creds_path,
        spreadsheet_id=configuration.spreadsheet_id,
    )
    client = BinanceClient(configuration.binance_keys[0], configuration.binance_keys[1])
    orders = client.get_report_all(from_date, configuration.currencies_rate["usdeur"])
    account = Account("", "Coinbase")
    if len(orders) == 0:
        print("No order to report")
        exit(0)
    show_report(orders, configuration.currencies_rate)
    if update_gsheet:
        while True:
            index = click.prompt("Which row to manage (0 = exit) ? ", type=int)
            if index == 0:
                return
            create_or_update = click.prompt(
                "Create or update ?", type=click.Choice(["c", "u"])
            )
            order = orders[index - 1]
            if create_or_update == "c":
                update_order(order=order, conditional_order=None, validate_input=False)
                report_order = calculate_currency(order, configuration.currencies_rate)
                assert isinstance(report_order, ReportOrder)
                gsheet_client.create_order(
                    account=account, order=report_order, original_order=order
                )
            else:
                line_to_update = click.prompt(
                    "Which line needs to be updated ?", type=int
                )
                order.open_position = click.prompt(
                    "This update open a position ?", type=bool, default=False
                )
                if order.open_position:
                    update_order(
                        order=order, conditional_order=None, validate_input=False
                    )
                else:
                    order.stopped = click.prompt(
                        "Has the order been stopped ?", type=bool, default=False
                    )
                    order.be_stopped = click.prompt(
                        "Has the order been BE stopped ?", type=bool, default=False
                    )
                report_order = calculate_currency(order, configuration.currencies_rate)
                assert isinstance(report_order, ReportOrder)
                gsheet_client.update_order(
                    order=report_order,
                    original_order=order,
                    line_to_update=line_to_update,
                )
            show_report(orders, configuration.currencies_rate)


def show_report(orders, currencies_rate):
    for index, order in enumerate(orders):
        if order.currency != Currency.EURO:
            currency_order = calculate_currency(order, currencies_rate)
            print(
                f"[{index + 1}]: {order.date.strftime('%Y-%m-%d')}: {order.name} - {order.direction} {order.quantity} at {order.price:.4f}$ ({currency_order.price:.4f}€) -> {order.price * order.quantity:.4f}$ ({currency_order.price * order.quantity:.4f}€)"
            )

        else:
            print(
                f"[{index + 1}]: {order.date.strftime('%Y-%m-%d')}: {order.name} - {order.direction} {order.quantity} at {order.price:.4f}$ -> {order.price * order.quantity:.4f}$"
            )


@click.command
@click.option(
    "--file",
    type=str,
    required=True,
    help="Where is the csv file ?",
    prompt="Where is the csv file ?",
)
@click.option(
    "--type",
    type=click.Choice(["Locked", "Flexible"]),
    required=True,
    help="Flexible or Locked",
    prompt="Flexible or Locked file report",
)
@click.pass_context
@catch_exception(handle=SaxoException)
def get_stacking_report(ctx: Context, file: str, type: str):
    coin_column = 1 if type == "Locked" else 2
    value_column = 2 if type == "Locked" else 3
    with open(file, "r") as f:
        lines = f.readlines()
    cryptos: Dict = {}
    lines.pop(0)
    for line in lines:
        tab = line.split(",")
        quantity = float(tab[value_column])
        try:
            date = datetime.strptime(tab[0], "%Y-%m-%d")
        except Exception:
            date = datetime.strptime(tab[0], "%Y-%m-%d %H:%M:%S")
        stacking = StackingReport(
            asset=tab[coin_column], date=date.strftime("%m/%Y"), quantity=quantity
        )
        if stacking.id in cryptos:
            cryptos[stacking.id].quantity += quantity
        else:
            cryptos[stacking.id] = stacking
    for crypto in cryptos.values():
        print(
            f"{crypto.asset};{crypto.date};{crypto.quantity:.10f};{type}".replace(
                ".", ","
            )
        )
