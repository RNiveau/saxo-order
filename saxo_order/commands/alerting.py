import datetime
import json
import os
from typing import Dict, List, Optional, Tuple

import click
from click.core import Context
from slack_sdk import WebClient

from client import client_helper
from client.aws_client import DynamoDBClient
from client.saxo_client import SaxoClient
from model import Alert, AlertType, AssetType, Candle, UnitTime
from saxo_order.commands import catch_exception
from services import congestion_indicator, indicator_service
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
            [
                {
                    "name": asset["Description"],
                    "code": asset["Symbol"],
                    "saxo_uic": asset["Identifier"],
                }
            ],
        )
    else:
        run_alerting(config)


def run_alerting(config: str, assets: Optional[List[Dict]] = None) -> None:

    if assets is None:
        assets = _load_assets()

    if assets is None or len(assets) == 0:
        logger.error("No stocks to alert")
        raise click.Abort()

    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)
    slack_client = WebClient(token=configuration.slack_token)
    dynamodb_client = DynamoDBClient()

    dynamodb_client.clear_alerts()

    slack_messages: Dict[str, List[str]] = {
        "double_top": [],
        "container_candle": [],
        "combo": [],
        "double_inside_bar": [],
        "congestion": [],
    }
    has_message = False
    for asset in assets:
        logger.debug(f"scan {asset['name']}")
        asset_alerts: List[Alert] = []
        try:
            if "saxo_uic" in asset:
                candles = _build_candles(saxo_client, asset)
                congestion_indicator = _run_congestion_indicator(
                    asset, candles, 20, 2
                )
                if (
                    congestion_indicator is not None
                    and len(congestion_indicator[0]) > 0
                ):
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    touch_points = [
                        f"{c.date.strftime('%Y-%m-%d') if c.date else 'Unknown'}: "  # noqa: E501
                        + f"{c.higher} {c.lower}"
                        for c in congestion_indicator[0]
                    ]
                    slack_messages["congestion"].append(
                        f"{asset['name']}: Congestion detected on {date}\n"
                        + "Touch points:\n"
                        + "\n".join(touch_points)
                    )
                    has_message = True
                    asset_alerts.append(
                        Alert(
                            alert_type=AlertType.CONGESTION20,
                            date=datetime.datetime.now(),
                            data={
                                "touch_points": touch_points,
                                "candles": [
                                    {
                                        "date": (
                                            c.date.isoformat()
                                            if c.date
                                            else None
                                        ),
                                        "higher": c.higher,
                                        "lower": c.lower,
                                    }
                                    for c in congestion_indicator[0]
                                ],
                            },
                            asset_code=asset["code"],
                            country_code=asset.get("country_code"),
                        )
                    )
                congestion_indicator = _run_congestion_indicator(
                    asset, candles, 100, 3
                )
                if (
                    congestion_indicator is not None
                    and len(congestion_indicator[0]) > 0
                ):
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    touch_points = [
                        f"{c.date.strftime('%Y-%m-%d') if c.date else 'Unknown'}: "  # noqa: E501
                        + f"{c.higher} {c.lower}"
                        for c in congestion_indicator[0]
                    ]
                    slack_messages["congestion"].append(
                        f"{asset['name']}: Congestion detected on {date}\n"
                        + "Touch points:\n"
                        + "\n".join(touch_points)
                    )
                    has_message = True
                    asset_alerts.append(
                        Alert(
                            alert_type=AlertType.CONGESTION100,
                            date=datetime.datetime.now(),
                            data={
                                "touch_points": touch_points,
                                "candles": [
                                    {
                                        "date": (
                                            c.date.isoformat()
                                            if c.date
                                            else None
                                        ),
                                        "higher": c.higher,
                                        "lower": c.lower,
                                    }
                                    for c in congestion_indicator[0]
                                ],
                            },
                            asset_code=asset["code"],
                            country_code=asset.get("country_code"),
                        )
                    )
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
                    asset_alerts.append(
                        Alert(
                            alert_type=AlertType.DOUBLE_TOP,
                            date=(
                                candle.date
                                if candle.date
                                else datetime.datetime.now()
                            ),
                            data={
                                "close": candle.close,
                                "open": candle.open,
                                "higher": candle.higher,
                                "lower": candle.lower,
                            },
                            asset_code=asset["code"],
                            country_code=asset.get("country_code"),
                        )
                    )
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
                    asset_alerts.append(
                        Alert(
                            alert_type=AlertType.CONTAINING_CANDLE,
                            date=(
                                candle.date
                                if candle.date
                                else datetime.datetime.now()
                            ),
                            data={
                                "close": candle.close,
                                "open": candle.open,
                                "higher": candle.higher,
                                "lower": candle.lower,
                            },
                            asset_code=asset["code"],
                            country_code=asset.get("country_code"),
                        )
                    )
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
                    asset_alerts.append(
                        Alert(
                            alert_type=AlertType.DOUBLE_INSIDE_BAR,
                            date=(
                                candle.date
                                if candle.date
                                else datetime.datetime.now()
                            ),
                            data={
                                "close": candle.close,
                                "open": candle.open,
                                "higher": candle.higher,
                                "lower": candle.lower,
                            },
                            asset_code=asset["code"],
                            country_code=asset.get("country_code"),
                        )
                    )
                if (combo := indicator_service.combo(candles)) is not None:
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    slack_messages["combo"].append(
                        f"{asset['name']}: combo {combo.direction} "
                        f"{combo.strength} {date} at {combo.price} "
                        f"(has been triggered ? {combo.has_been_triggered})"
                    )
                    has_message = True
                    asset_alerts.append(
                        Alert(
                            alert_type=AlertType.COMBO,
                            date=datetime.datetime.now(),
                            data={
                                "price": combo.price,
                                "direction": combo.direction.value,
                                "strength": combo.strength.value,
                                "has_been_triggered": combo.has_been_triggered,
                                "details": combo.details,
                            },
                            asset_code=asset["code"],
                            country_code=asset.get("country_code"),
                        )
                    )
                if len(asset_alerts) > 0:
                    dynamodb_client.store_alerts(
                        asset["code"],
                        asset.get("country_code"),
                        asset_alerts,
                    )
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
                for index, slack in enumerate(slack_messages[indicator]):
                    if index % 10 == 0 and index != 0:
                        slack_client.chat_postMessage(
                            channel="#stock",
                            text=f"{message}\n```",
                        )
                        message = f"Indicator {indicator} \n```"
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


def _run_congestion_indicator(
    asset: Dict,
    candles: List[Candle],
    candle_length: int = 20,
    minimal_touch_points: int = 3,
) -> Optional[Tuple[List[Candle], List[Candle]]]:
    indicator = congestion_indicator.calculate_congestion_indicator(
        candles=candles[:candle_length],
        minimal_touch_points=minimal_touch_points,
    )
    if len(indicator[0]) > 0:
        logger.debug(f"{asset['name']}, {indicator}")
        return indicator
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
        len(candles) > 0
        and candles[0].date is not None
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


def _load_assets() -> List[Dict]:
    if os.path.isfile("stocks.json"):
        with open("stocks.json", "r") as f:
            assets = json.load(f)
        logger.debug("Stocks file loaded")
    else:
        logger.error("Fill the stocks.json file first")
        raise click.Abort()
    if os.path.isfile("followup-stocks.json"):
        with open("followup-stocks.json", "r") as f:
            assets += json.load(f)
        logger.debug("Followup stocks file loaded")
    else:
        logger.warning("Fill the followup-stocks.json to include other stocks")
    return assets
