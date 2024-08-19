import datetime
import json
import os
from typing import Dict, List, Optional

import click
from click.core import Context
from slack_sdk import WebClient

from client import client_helper
from client.saxo_client import SaxoClient
from model import AssetType, Candle, UnitTime
from saxo_order.commands import catch_exception
from services import indicator_service
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.helper import build_daily_candle_from_hours
from utils.logger import Logger

logger = Logger.get_logger("alerting")


@click.command()
@click.pass_context
@click.option(
    "--code",
    type=str,
    help="The code of the stock",
)
@click.option(
    "--country-code",
    type=str,
    required=True,
    default="xpar",
    help="The country code of the asset",
)
@catch_exception(handle=SaxoException)
def alerting(ctx: Context, code: str, country_code: str) -> None:
    config = ctx.obj["config"]
    if code is not None and code != "":
        saxo_client = SaxoClient(Configuration(config))
        asset = saxo_client.get_asset(code, country_code)
        run_alerting(
            config,
            [{"name": asset["Description"], "saxo_uic": asset["Identifier"]}],
        )
    else:
        run_alerting(config)


def run_alerting(config: str, assets: Optional[List[Dict]] = None) -> None:

    if assets is None:
        if os.path.isfile("stocks.json"):
            with open("stocks.json", "r") as f:
                assets = json.load(f)
        else:
            print("Fill the stocks.json file first")
            raise click.Abort()

    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)
    slack_client = WebClient(token=configuration.slack_token)
    slack_messages: Dict[str, List[str]] = {
        "double_top": [],
        "container_candle": [],
        "combo": [],
        "double_inside_bar": [],
    }
    has_message = False
    for asset in assets:
        logger.debug(f"scan {asset['name']}")
        try:
            if "saxo_uic" in asset:
                candles = _build_candles(saxo_client, asset)
                if (
                    len(assets) == 1
                    and (
                        candle := _run_double_top(saxo_client, asset, candles)
                    )
                    is not None
                ):
                    date = (
                        candle.date.strftime("%Y-%m-%d")
                        if candle.date is not None
                        else ""
                    )
                    slack_messages["double_top"].append(
                        f"{asset['name']}: {date} at {candle.close}"
                    )
                    has_message = True
                if (
                    candle := _run_containing_candle(asset, candles)
                ) is not None:
                    date = (
                        candle.date.strftime("%Y-%m-%d")
                        if candle.date is not None
                        else ""
                    )
                    slack_messages["container_candle"].append(
                        f"{asset['name']}: {date} at {candle.close}"
                    )
                    has_message = True
                if (
                    candle := _run_double_inside_bar(asset, candles)
                ) is not None:
                    date = (
                        candle.date.strftime("%Y-%m-%d")
                        if candle.date is not None
                        else ""
                    )
                    slack_messages["double_inside_bar"].append(
                        f"{asset['name']}: {date} at {candle.close}"
                    )
                    has_message = True
                if (combo := indicator_service.combo(candles)) is not None:
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    slack_messages["combo"].append(
                        f"{asset['name']}: combo {combo.direction} "
                        f"{combo.strength} {date} at {combo.price} "
                        f"(has been triggered ? {combo.has_been_triggered})"
                    )
                    has_message = True
        except SaxoException as e:
            logger.error(f"{asset['name']} can't be scanned {e}")
    if has_message is False and len(assets) > 1:
        slack_client.chat_postMessage(
            channel="#stock",
            text="No alert for today",
        )
    else:
        for indicator in slack_messages.keys():
            if len(slack_messages[indicator]) > 0:
                message = f"Indicator {indicator} \n```"
                for slack in slack_messages[indicator]:
                    message += f"{slack}\n"
                message += "```"
                slack_client.chat_postMessage(
                    channel="#stock",
                    text=message,
                )


def _run_double_inside_bar(
    asset: Dict, candles: List[Candle]
) -> Optional[Candle]:
    if indicator_service.double_inside_bar(candles):
        logger.debug(f"{asset['name']}, {candles[0]}")
        return candles[0]
    return None


def _run_containing_candle(
    asset: Dict,
    candles: List[Candle],
) -> Optional[Candle]:
    containing_candle = indicator_service.containing_candle(candles)
    if containing_candle is not None:
        logger.debug(f"{asset['name']}, {containing_candle}")
        return containing_candle
    return None


def _run_double_top(
    saxo_client: SaxoClient,
    asset: Dict,
    candles: List[Candle],
) -> Optional[Candle]:
    detail = saxo_client.get_asset_detail(asset["saxo_uic"], AssetType.STOCK)
    if "TickSizeScheme" not in detail:
        tick = 0.0
    else:
        tick = client_helper.get_tick_size(
            detail["TickSizeScheme"], candles[0].close
        )
    double_top_candle = indicator_service.double_top(candles, tick)
    if (
        double_top_candle is not None
        and double_top_candle.date is not None
        and (datetime.datetime.now() - double_top_candle.date).days <= 2
    ):
        logger.debug(f"{asset['name']}, {double_top_candle}")
        return double_top_candle
    return None


def _build_candles(saxo_client: SaxoClient, asset: Dict) -> List[Candle]:
    data = saxo_client.get_historical_data(
        asset_type=AssetType.STOCK,
        saxo_uic=asset["saxo_uic"],
        horizon=1440,
        count=250,
    )
    candles = client_helper.map_data_to_candles(data, ut=UnitTime.D)
    today = datetime.datetime.now()
    if (
        candles[0].date is not None
        and today.day != candles[0].date.day
        and today.weekday() < 5
    ):
        hour_data = saxo_client.get_historical_data(
            asset_type=AssetType.STOCK,
            saxo_uic=asset["saxo_uic"],
            horizon=60,
            count=10,
        )
        hour_candles = client_helper.map_data_to_candles(
            hour_data, ut=UnitTime.H1
        )
        hour_candle = build_daily_candle_from_hours(hour_candles, today.day)
        if hour_candle is not None:
            candles.insert(0, hour_candle)
    return candles
