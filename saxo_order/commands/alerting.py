import datetime
import json
import logging
import os

import click
from click.core import Context
from slack_sdk import WebClient

from client import client_helper
from client.saxo_client import SaxoClient
from model import AssetType, UnitTime
from saxo_order.commands import catch_exception
from services import indicator_service
from utils.configuration import Configuration
from utils.exception import SaxoException

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def alerting(ctx: Context):
    logger.setLevel(logging.DEBUG)

    if os.path.isfile("stocks.json"):
        with open("stocks.json", "r") as f:
            stocks = json.load(f)
    else:
        click.Abort("Fill the stocks.json file first")
        exit(1)

    configuration = Configuration(ctx.obj["config"])
    saxo_client = SaxoClient(configuration)
    slack_client = WebClient(token=configuration.slack_token)
    for stock in stocks:
        if "saxo_uic" in stock:
            data = saxo_client.get_historical_data(
                asset_type=AssetType.STOCK,
                saxo_uic=stock["saxo_uic"],
                horizon=1440,
                count=20,
            )
            data = client_helper.map_data_to_candle(data, ut=UnitTime.D)
            detail = saxo_client.get_asset_detail(stock["saxo_uic"], AssetType.STOCK)
            tick = client_helper.get_tick_size(detail["TickSizeScheme"], data[0].close)
            double_top_candle = indicator_service.double_top(data, tick)
            if (
                double_top_candle is not None
                and double_top_candle.date is not None
                and (datetime.datetime.now() - double_top_candle.date).days <= 2
            ):
                logger.debug(f"{stock['name']}, {double_top_candle}")
                slack_client.chat_postMessage(
                    channel="#stock",
                    text=f"{stock['name']} has created a double top {double_top_candle.date.strftime('%Y-%m-%d')}",
                )
