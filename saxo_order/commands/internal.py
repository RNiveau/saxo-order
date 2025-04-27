import json

import click
from click.core import Context
from slack_sdk import WebClient

from client.aws_client import AwsClient
from client.saxo_client import SaxoClient
from engines.workflow_loader import load_workflows
from model import AssetType
from saxo_order.commands import catch_exception
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("internal")


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


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def technical(ctx: Context):
    configuration = Configuration(ctx.obj["config"])
    # from services.candles_service import CandlesService

    # candles_service = CandlesService(SaxoClient(configuration))
    saxo_client = SaxoClient(configuration)
    # candles = candles_service.build_hour_candles(
    #     "DAX.I", "CAC.I", UnitTime.H4, 7, 15, 1000, 0)
    # print(candles)
    # DAX.I, CAC40.I, US500.I
    import datetime

    # from client.client_helper import map_data_to_candles
    # candles = candles_service.build_hour_candles(
    #     "US500.I",
    #     "US500.I",
    #     UnitTime.H1,
    #     13,
    #     20,
    #     750,
    #     30,
    #     datetime.datetime(2024, 7, 29, 14),
    # )
    # print(candles)
    asset = saxo_client.get_asset("viri", "xpar")
    candles = saxo_client.get_historical_data(
        asset_type=asset["AssetType"],
        saxo_uic=asset["Identifier"],
        horizon=1440,
        count=12,
        date=datetime.datetime(2025, 4, 26),
    )
    # with open("tests/services/files/candles_viridien.obj", "w") as f:
    #     f.write(str(candles))
    # should return 03/03 and 06/03

    # print(candles)

    from client.client_helper import map_data_to_candles
    from model import UnitTime
    from services.congestion_indicator import calculate_congestion_indicator

    candles = map_data_to_candles(candles, ut=UnitTime.D)
    with open("tests/services/files/candles_viridien3.obj", "w") as f:
        f.write(str(candles))

    # with open("tests/services/files/candles_viridien.obj", "w") as f:
    #     f.write(str(candles))
    congestion = calculate_congestion_indicator(candles)
    print(f"Congestion indicator: {congestion}")

    # asset = saxo_client.get_asset("gle", "xpar")
    # candles = saxo_client.get_historical_data(
    #     asset_type=asset["AssetType"],
    #     saxo_uic=asset["Identifier"],
    #     horizon=1440,
    #     count=100,
    #     date=datetime.datetime(2025, 3, 5),
    # )
    # # candles = candles[:-3]    # print(candles)
    # candles = map_data_to_candles(candles, ut=UnitTime.D)
    # congestion = calculate_congestion_indicator(candles)
    # print(f"Congestion indicator: {congestion}")

    # from client.client_helper import map_data_to_candles

    # candles = map_data_to_candles(candles, ut=UnitTime.D)
    # print(candles)
    # print(len(candles))
    # macd0lag(candles)
    # from services.indicator_service import slope_percentage
    # print(slope_percentage(0, 29.65260, 10, 29.53320))


@click.command()
@click.pass_context
@click.option(
    "--direction",
    type=click.Choice(["from", "to"]),
    required=True,
    default="from",
    help="Sync workflows.yml between aws and local",
    prompt="What is the sync direction ? (from aws, to aws)",
)
@catch_exception(handle=SaxoException)
def sync_workflows(ctx: Context, direction: str):
    if AwsClient.is_aws_context() is False:
        print("Configure aws token first")
        raise click.Abort()
    aws_client = AwsClient()
    if direction == "from":
        workflows_yml = aws_client.get_workflows()
        with open("workflows.yml", "w") as file:
            file.write(workflows_yml)
    else:
        with open("workflows.yml", "r") as file:
            aws_client.save_workflows(file.read())

    configuration = Configuration(ctx.obj["config"])
    workflows = load_workflows()
    slack_client = WebClient(token=configuration.slack_token)
    slack_message = "Workflows currently active:\n```"
    for workflow in workflows:
        if workflow.enable is True:
            slack_message += (
                f"{workflow.name} {workflow.conditions[0].indicator}\n"
            )
    slack_client.chat_postMessage(
        channel="#current-workflows",
        text=f"{slack_message}```",
    )
    print("Workflows file is synchronized")
