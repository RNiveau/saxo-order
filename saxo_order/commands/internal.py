import json

import click
from click.core import Context

from client.saxo_client import SaxoClient
from saxo_order.commands import catch_exception
from utils.configuration import Configuration
from utils.exception import SaxoException


@click.command
@click.pass_context
@catch_exception(handle=SaxoException)
def refresh_stocks_list(ctx: Context):
    configuration = Configuration(ctx.obj["config"])
    client = SaxoClient(configuration)

    stocks = [
        "Accor",
        "Air liquide",
        "Airbus",
        "Arcelormittal",
        "Axa",
        "BNP",
        "Bouygues",
        "Capgemini",
        "Carrefour",
        "Crédit Agricole",
        "Danone",
        "Dassault Systemes",
        "Edenred",
        "Engie",
        "Essilor",
        "Eurofins",
        "Hermes",
        "Kering",
        "Legrand",
        "Loreal",
        "LVMH",
        "Michelin",
        "Orange",
        "Pernod-Ricard",
        "Publicis",
        "Renault",
        "Safran",
        "Saint gobain",
        "Sanofi",
        "Schneider",
        "Societe Generale",
        "Stellantis",
        "STMicroelectronics",
        "Teleperformance",
        "Thales",
        "Total",
        "Unibail",
        "Veolia",
        "Vinci",
        "Vivendi",
    ]
    records = []
    for stock in stocks:
        result = list(
            filter(lambda x: "xpar" in x["Symbol"], client.search(stock, "Stock"))
        )
        if len(result) >= 1:
            records.append(
                {
                    "name": result[0]["Description"],
                    "code": result[0]["Symbol"],
                    "saxo_uic": result[0]["Identifier"],
                }
            )
        else:
            records.append({"name": stock})
            print(f"Doesn't find {stock}")
    print(json.dumps(records))
