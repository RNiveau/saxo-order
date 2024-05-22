import json

import click
from click.core import Context

from client.saxo_client import SaxoClient
from model import AssetType
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
        "Air france klm",
        "Alstom",
        "Arkema",
        "Biomerieux",
        "Bureau veritas",
        "Eiffage",
        "Euronext",
        "Forvia",
        "Gecina",
        "Getlink",
        "Klepierre",
        "Pluxee",
        "Rexel",
        "Sartorius stedim biotech",
        "Scor se",
        "Sodexo",
        "Soitec",
        "Solvay",
        "Valeo",
        "Worldline",
        "Alten",
        "Amundi",
        "Aperam",
        "Argan",
        "Atos",
        "Ald",
        "Beneteau",
        "Bic",
        "Bollore",
        "Carmila",
        #        "Cgg",
        "Coface",
        "Covivio",
        "Dassault aviation",
        "Derichebourg",
        "Elior",
        "Elis",
        "Eramet",
        "Eurazeo",
        "Euroapi",
        "Eutelsat",
        "Fdj",
        "Groupe adp",
        "Gtt",
        "Icade",
        "Id logistics",
        "Imerys",
        "Interparfums",
        "Ipsen",
        "Ipsos",
        "Jcdecaux",
        "Lectra",
        "Metropole TV",
        "Maurel & prom",
        "Mercialys",
        "Mersen",
        "Neoen",
        "Nexans",
        "Nexity",
        "Orpea",
        "Plastic omnium",
        "Remy cointreau",
        "Rubis",
        "Seb",
        "Solutions 30",
        "Sopra steria group",
        "Spie",
        "Technip energies",
        "Tf1",
        "Trigano",
        "Ubisoft",
        "Vallourec",
        "Valneva se",
        "Verallia",
        "Vicat",
        "Virbac",
        "Vusiongroup",
        "Wendel",
        "X-fab",
    ]
    records = []
    for stock in stocks:
        results = client.search(stock, AssetType.STOCK)
        if len(results) > 1:
            results = list(
                filter(
                    lambda x: "xpar" in x["Symbol"]
                    or "xams" in x["Symbol"]
                    or "xnas" in x["Symbol"],
                    results,
                )
            )
        if len(results) >= 1:
            records.append(
                {
                    "name": results[0]["Description"],
                    "code": results[0]["Symbol"],
                    "saxo_uic": results[0]["Identifier"],
                }
            )
        else:
            records.append({"name": stock})
            print(f"Doesn't find {stock}")
    print(json.dumps(records))
