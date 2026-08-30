"""Candle series for a resolved instrument, newest first.

This is the scheduled scan's reconstruction, lifted out of
``saxo_order/commands/alerting.py`` so the scan and the MCP asset-analysis
server share one implementation rather than two that can drift apart.

It is deliberately not ``CandlesService``: that path rebuilds a daily series
from 30m data, which is a different algorithm and a far more expensive one -
for the 235 daily bars ``macd0lag`` needs it asks for roughly 16,000 30m bars,
which ``get_historical_data`` pages out into a dozen or so requests. See
``specs/030-mcp-asset-analysis/research.md`` section 10.
"""

import datetime
from typing import List, Optional

from client import client_helper
from client.saxo_client import SaxoClient
from model import AssetType, Candle, Market, UnitTime
from utils.helper import (
    build_current_weekly_candle_from_daily,
    build_daily_candles_from_h1,
)
from utils.logger import Logger

logger = Logger.get_logger("candle_source")

DAILY_HORIZON = 1440
DAILY_CANDLES_COUNT = 250
HOURLY_HORIZON = 60
HOURLY_CANDLES_COUNT = 10

WEEKLY_HORIZON = 10080
# 60 is what the weekly criteria set reads; the margin absorbs the forming
# week and any gap the provider returns.
WEEKLY_CANDLES_COUNT = 70


def build_daily_series(
    saxo_client: SaxoClient,
    saxo_uic: str | int,
    asset_type: str = AssetType.STOCK,
    market: Optional[Market] = None,
    count: int = DAILY_CANDLES_COUNT,
) -> List[Candle]:
    """The asset's daily bars, newest first, including the day now trading.

    The provider does not return the current day, so it is rebuilt from the
    hourly series. ``market`` decides the session hours that rebuild uses;
    when it is None the top-up is skipped rather than assembled against
    guessed hours, and the caller sees only completed days.
    """
    data = saxo_client.get_historical_data(
        asset_type=asset_type,
        saxo_uic=saxo_uic,
        horizon=DAILY_HORIZON,
        count=count,
    )
    candles = client_helper.map_data_to_candles(data, ut=UnitTime.D)
    today = datetime.datetime.now()
    if (
        len(candles) > 0
        and candles[0].date is not None
        and today.day != candles[0].date.day
        and today.weekday() < 5
    ):
        if market is None:
            logger.debug(
                f"No market for {saxo_uic}, the forming day is left out"
            )
            return candles
        hour_data = saxo_client.get_historical_data(
            asset_type=asset_type,
            saxo_uic=saxo_uic,
            horizon=HOURLY_HORIZON,
            count=HOURLY_CANDLES_COUNT,
        )
        hour_candles = client_helper.map_data_to_candles(
            hour_data, ut=UnitTime.H1
        )
        daily_candles = build_daily_candles_from_h1(hour_candles, market)
        if daily_candles:
            candles.insert(0, daily_candles[0])
    return candles


def build_weekly_series(
    saxo_client: SaxoClient,
    saxo_uic: str | int,
    daily_candles: List[Candle],
    asset_type: str = AssetType.STOCK,
) -> List[Candle]:
    """The asset's weekly bars, newest first, including the week now forming.

    The provider does not return the week currently trading, and the daily
    candles the caller already fetched are exactly the elapsed days of it - so
    the forming bar is assembled from those rather than bought a second time.
    That keeps the weekly timeframe at one extra request per asset.

    This is deliberately not CandlesService.build_weekly_candles, which does
    the same thing from a code and a Market: that path re-resolves the asset
    and fetches its own daily candles for the forming week, three requests
    per asset where this is one. Reuniting them would mean giving the service
    a uic-keyed entry point and a way to be handed candles it already has.

    It also drops that path's `today.weekday() < 5` guard, which is safe here
    in both weekend cases: Saturday and Sunday share their ISO week with the
    week that just closed, so either the provider has published that bar and
    the prepend is skipped, or it has not and the bar assembled from the
    week's dailies is the complete week rather than a partial one.
    """
    data = saxo_client.get_historical_data(
        asset_type=asset_type,
        saxo_uic=saxo_uic,
        horizon=WEEKLY_HORIZON,
        count=WEEKLY_CANDLES_COUNT,
    )
    candles = client_helper.map_data_to_candles(data, ut=UnitTime.W)
    today = datetime.datetime.now(datetime.UTC)
    if (
        len(candles) > 0
        and candles[0].date is not None
        and candles[0].date.isocalendar()[:2] != today.isocalendar()[:2]
    ):
        forming = build_current_weekly_candle_from_daily(daily_candles)
        if forming is not None:
            candles.insert(0, forming)
    return candles
