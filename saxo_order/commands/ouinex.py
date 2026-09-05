import click
from click.core import Context

from api.services.ouinex_report_service import OuinexReportService
from client.ouinex_client import OuinexClient
from saxo_order.commands import catch_exception
from saxo_order.commands.binance import show_report
from saxo_order.commands.input_helper import update_order
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("ouinex")


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
    client = OuinexClient(
        configuration.ouinex_keys[0],
        configuration.ouinex_keys[1],
        configuration.ouinex_graphql_url,
    )

    report_service = OuinexReportService(client, configuration)
    orders = report_service.get_orders_report("ouinex_main", from_date)

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
                update_order(
                    order=order, conditional_order=None, validate_input=False
                )
                report_service.create_gsheet_order(
                    account_id="ouinex_main",
                    order=order,
                    stop=order.stop,
                    objective=order.objective,
                    strategy=order.strategy,
                    signal=order.signal,
                    comment=order.comment,
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
                        order=order,
                        conditional_order=None,
                        validate_input=False,
                    )
                else:
                    order.stopped = click.prompt(
                        "Has the order been stopped ?",
                        type=bool,
                        default=False,
                    )
                    order.be_stopped = click.prompt(
                        "Has the order been BE stopped ?",
                        type=bool,
                        default=False,
                    )
                report_service.update_gsheet_order(
                    account_id="ouinex_main",
                    order=order,
                    line_number=line_to_update,
                    close=not order.open_position,
                    stopped=order.stopped,
                    be_stopped=order.be_stopped,
                    stop=order.stop,
                    objective=order.objective,
                    strategy=order.strategy,
                    signal=order.signal,
                    comment=order.comment,
                )
            show_report(orders, configuration.currencies_rate)
