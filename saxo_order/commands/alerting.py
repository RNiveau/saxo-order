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


def _parse_asset_code(code: str) -> Tuple[str, Optional[str]]:
    """
    Parse asset code to extract asset_code and country_code.

    Args:
        code: Asset code which may contain country code
              (e.g., "SAN:xpar" or "SAN")

    Returns:
        Tuple of (asset_code, country_code).
        country_code is None if not present.

    Examples:
        "SAN:xpar" -> ("SAN", "xpar")
        "SAN" -> ("SAN", None)
    """
    if ":" in code:
        parts = code.split(":", 1)
        return parts[0], parts[1]
    return code, None


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


def run_detection_for_asset(
    asset_code: str,
    country_code: Optional[str],
    exchange: str,
    asset_description: str,
    saxo_uic: Optional[str],
    saxo_client: SaxoClient,
    dynamodb_client: DynamoDBClient,
) -> List[Alert]:
    """
    Run all detection algorithms for a single asset and store results.

    Args:
        asset_code: Asset identifier (e.g., "SAN", "ITP")
        country_code: Country code (e.g., "xpar") or None
        exchange: Exchange identifier ("saxo" or "binance")
        asset_description: Human-readable asset name
        saxo_uic: Saxo UIC for the asset (None for non-Saxo assets)
        saxo_client: Saxo API client
        dynamodb_client: DynamoDB client for storage

    Returns:
        List of detected Alert objects
    """
    asset_alerts: List[Alert] = []

    if saxo_uic is None:
        logger.warning(f"No saxo_uic for {asset_code}, skipping detection")
        return asset_alerts

    try:
        # Build candles for detection
        asset_dict = {
            "name": asset_description,
            "code": asset_code,
            "saxo_uic": saxo_uic,
        }
        candles = _build_candles(saxo_client, asset_dict)

        # Run CONGESTION20 detection
        congestion_result = _run_congestion_indicator(
            asset_dict, candles, 20, 2
        )
        if congestion_result is not None and len(congestion_result[0]) > 0:
            touch_points = [
                f"{c.date.strftime('%Y-%m-%d') if c.date else 'Unknown'}: "
                + f"{c.higher} {c.lower}"
                for c in congestion_result[0]
            ]
            asset_alerts.append(
                Alert(
                    alert_type=AlertType.CONGESTION20,
                    date=datetime.datetime.now(),
                    data={
                        "touch_points": touch_points,
                        "candles": [
                            {
                                "date": (
                                    c.date.isoformat() if c.date else None
                                ),
                                "higher": c.higher,
                                "lower": c.lower,
                            }
                            for c in congestion_result[0]
                        ],
                    },
                    asset_code=asset_code,
                    asset_description=asset_description,
                    exchange=exchange,
                    country_code=country_code,
                )
            )

        # Run CONGESTION100 detection
        congestion_result = _run_congestion_indicator(
            asset_dict, candles, 100, 3
        )
        if congestion_result is not None and len(congestion_result[0]) > 0:
            touch_points = [
                f"{c.date.strftime('%Y-%m-%d') if c.date else 'Unknown'}: "
                + f"{c.higher} {c.lower}"
                for c in congestion_result[0]
            ]
            asset_alerts.append(
                Alert(
                    alert_type=AlertType.CONGESTION100,
                    date=datetime.datetime.now(),
                    data={
                        "touch_points": touch_points,
                        "candles": [
                            {
                                "date": (
                                    c.date.isoformat() if c.date else None
                                ),
                                "higher": c.higher,
                                "lower": c.lower,
                            }
                            for c in congestion_result[0]
                        ],
                    },
                    asset_code=asset_code,
                    asset_description=asset_description,
                    exchange=exchange,
                    country_code=country_code,
                )
            )

        # Run DOUBLE_TOP detection
        if (
            candle := _run_double_top(saxo_client, asset_dict, candles)
        ) is not None:
            asset_alerts.append(
                Alert(
                    alert_type=AlertType.DOUBLE_TOP,
                    date=(
                        candle.date if candle.date else datetime.datetime.now()
                    ),
                    data={
                        "close": candle.close,
                        "open": candle.open,
                        "higher": candle.higher,
                        "lower": candle.lower,
                    },
                    asset_code=asset_code,
                    asset_description=asset_description,
                    exchange=exchange,
                    country_code=country_code,
                )
            )

        # Run CONTAINING_CANDLE detection
        if (candle := _run_containing_candle(asset_dict, candles)) is not None:
            asset_alerts.append(
                Alert(
                    alert_type=AlertType.CONTAINING_CANDLE,
                    date=(
                        candle.date if candle.date else datetime.datetime.now()
                    ),
                    data={
                        "close": candle.close,
                        "open": candle.open,
                        "higher": candle.higher,
                        "lower": candle.lower,
                    },
                    asset_code=asset_code,
                    asset_description=asset_description,
                    exchange=exchange,
                    country_code=country_code,
                )
            )

        # Run DOUBLE_INSIDE_BAR detection
        if (candle := _run_double_inside_bar(asset_dict, candles)) is not None:
            asset_alerts.append(
                Alert(
                    alert_type=AlertType.DOUBLE_INSIDE_BAR,
                    date=(
                        candle.date if candle.date else datetime.datetime.now()
                    ),
                    data={
                        "close": candle.close,
                        "open": candle.open,
                        "higher": candle.higher,
                        "lower": candle.lower,
                    },
                    asset_code=asset_code,
                    asset_description=asset_description,
                    exchange=exchange,
                    country_code=country_code,
                )
            )

        # Run COMBO detection
        if (combo := indicator_service.combo(candles)) is not None:
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
                    asset_code=asset_code,
                    asset_description=asset_description,
                    exchange=exchange,
                    country_code=country_code,
                )
            )

        # Store alerts in DynamoDB if any were detected
        if len(asset_alerts) > 0:
            dynamodb_client.store_alerts(
                asset_code,
                country_code,
                asset_alerts,
            )

    except SaxoException as e:
        logger.error(f"{asset_description} can't be scanned: {e}")

    return asset_alerts


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

        # Parse asset code to separate asset_code and country_code
        parsed_asset_code, parsed_country_code = _parse_asset_code(
            asset["code"]
        )
        # Prefer explicit country_code from asset dict, fallback to parsed
        final_country_code = asset.get("country_code") or parsed_country_code

        # Call extracted detection function
        asset_alerts = run_detection_for_asset(
            asset_code=parsed_asset_code,
            country_code=final_country_code,
            exchange="saxo",
            asset_description=asset["name"],
            saxo_uic=asset.get("saxo_uic"),
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        # Build Slack messages from detected alerts
        for alert in asset_alerts:
            has_message = True
            if alert.alert_type == AlertType.CONGESTION20:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                touch_points = alert.data.get("touch_points", [])
                slack_messages["congestion"].append(
                    f"{asset['name']}: Congestion detected on {date}\n"
                    + "Touch points:\n"
                    + "\n".join(touch_points)
                )
            elif alert.alert_type == AlertType.CONGESTION100:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                touch_points = alert.data.get("touch_points", [])
                slack_messages["congestion"].append(
                    f"{asset['name']}: Congestion detected on {date}\n"
                    + "Touch points:\n"
                    + "\n".join(touch_points)
                )
            elif alert.alert_type == AlertType.DOUBLE_TOP:
                date = alert.date.strftime("%Y-%m-%d") if alert.date else ""
                slack_messages["double_top"].append(
                    f"{asset['name']}: {date} at {alert.data.get('close')}"
                )
            elif alert.alert_type == AlertType.CONTAINING_CANDLE:
                date = alert.date.strftime("%Y-%m-%d") if alert.date else ""
                slack_messages["container_candle"].append(
                    f"{asset['name']}: {date} at {alert.data.get('close')}"
                )
            elif alert.alert_type == AlertType.DOUBLE_INSIDE_BAR:
                date = alert.date.strftime("%Y-%m-%d") if alert.date else ""
                slack_messages["double_inside_bar"].append(
                    f"{asset['name']}: {date} at {alert.data.get('close')}"
                )
            elif alert.alert_type == AlertType.COMBO:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                direction = alert.data.get("direction")
                strength = alert.data.get("strength")
                price = alert.data.get("price")
                triggered = alert.data.get("has_been_triggered")
                slack_messages["combo"].append(
                    f"{asset['name']}: combo {direction} "
                    f"{strength} {date} at {price} "
                    f"(has been triggered ? {triggered})"
                )
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
