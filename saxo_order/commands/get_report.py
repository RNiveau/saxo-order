import click
from click.core import Context

from client.gsheet_client import GSheetClient
from client.saxo_client import SaxoClient
from saxo_order.commands import catch_exception
from saxo_order.commands.input_helper import select_account, update_order
from saxo_order.service import calculate_currency, calculate_taxes
from utils.configuration import Configuration
from utils.exception import SaxoException


@click.command()
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
    client = SaxoClient(configuration)
    gsheet_client = GSheetClient(
        key_path=configuration.gsheet_creds_path,
        spreadsheet_id=configuration.spreadsheet_id,
    )
    account = select_account(client)
    orders = client.get_report(account, from_date)
    for index, order in enumerate(orders):
        print(
            f"[{index + 1}]: {order.date.strftime('%Y-%m-%d')}: {order.name} - {order.direction} {order.quantity} at {order.price}€ -> {order.price * order.quantity:.2f}€"
        )
        if order.underlying is not None:
            print(f"    - Underlying {order.underlying.price}€")
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
                calculate_currency(order, configuration.currencies_rate)
                gsheet_client.create_order(account=account, order=order)
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
                    order.taxes = calculate_taxes(order)
                    order.stopped = click.prompt(
                        "Has the order been stopped ?", type=bool, default=False
                    )
                    order.be_stopped = click.prompt(
                        "Has the order been BE stopped ?", type=bool, default=False
                    )
                calculate_currency(order, configuration.currencies_rate)
                gsheet_client.update_order(
                    order=order,
                    line_to_update=line_to_update,
                )
