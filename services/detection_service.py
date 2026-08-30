"""Detectors that need more than a bare ``indicator_service`` call.

Lifted out of ``saxo_order/commands/alerting.py`` so the scheduled scan and
the MCP asset-analysis server run the same code. Each of these carries
behaviour that exists nowhere else - a tick size the indicator cannot compute
for itself, a recency window, a touch-point table - and calling the underlying
indicator directly would quietly widen what counts as a hit. See
``specs/030-mcp-asset-analysis/research.md`` section 10 and the PR #716 review.

Nothing here persists anything: the caller decides what to do with a hit.

These take a ``saxo_uic`` rather than the scan's asset dict: the MCP server
resolves an instrument to a uic and has no such dict, and a shared module
should not require one caller to fake the other's data shape. ``name`` is
only ever a log label.
"""

import datetime
from typing import List, Optional, Tuple

from client import client_helper
from client.saxo_client import SaxoClient
from model import AlertType, AssetType, Candle
from services import congestion_indicator, indicator_service
from utils.logger import Logger

logger = Logger.get_logger("detection_service")

# A double top or bottom older than this is history, not a signal.
DOUBLE_PATTERN_MAX_AGE_DAYS = 2

# (alert type, candles read, touch points needed). The two lengths look at
# the same series over different horizons, so they are one table rather than
# two call sites.
CONGESTION_SETTINGS: Tuple[Tuple[AlertType, int, int], ...] = (
    (AlertType.CONGESTION20, 20, 2),
    (AlertType.CONGESTION100, 100, 3),
)


def _tick_size(
    saxo_client: SaxoClient,
    saxo_uic: str | int,
    asset_type: str,
    price: float,
) -> float:
    detail = saxo_client.get_asset_detail(saxo_uic, asset_type)
    if "TickSizeScheme" not in detail:
        return 0.0
    return client_helper.get_tick_size(detail["TickSizeScheme"], price)


def _is_recent(candle: Optional[Candle]) -> bool:
    return (
        candle is not None
        and candle.date is not None
        and (datetime.datetime.now() - candle.date).days
        <= DOUBLE_PATTERN_MAX_AGE_DAYS
    )


def run_double_top(
    saxo_client: SaxoClient,
    saxo_uic: str | int,
    candles: List[Candle],
    asset_type: str = AssetType.STOCK,
    name: str = "",
) -> Optional[Candle]:
    """A double top formed within the last few days, or None.

    The recency window is the reason this is not a plain
    ``indicator_service.double_top`` call: the indicator will happily report a
    pattern from weeks ago, which is not something to alert on today.
    """
    tick = _tick_size(saxo_client, saxo_uic, asset_type, candles[0].close)
    double_top_candle = indicator_service.double_top(candles, tick)
    if _is_recent(double_top_candle):
        logger.debug(f"{name or saxo_uic}, {double_top_candle}")
        return double_top_candle
    return None


def run_double_bottom(
    saxo_client: SaxoClient,
    saxo_uic: str | int,
    candles: List[Candle],
    asset_type: str = AssetType.STOCK,
    name: str = "",
) -> Optional[Candle]:
    """A double bottom formed within the last few days, or None."""
    tick = _tick_size(saxo_client, saxo_uic, asset_type, candles[0].close)
    double_bottom_candle = indicator_service.double_bottom(candles, tick)
    if _is_recent(double_bottom_candle):
        logger.debug(f"{name or saxo_uic}, {double_bottom_candle}")
        return double_bottom_candle
    return None


def run_congestion_indicator(
    candles: List[Candle],
    candle_length: int = 20,
    minimal_touch_points: int = 3,
    name: str = "",
) -> Optional[Tuple[List[Candle], List[Candle]]]:
    indicator = congestion_indicator.calculate_congestion_indicator(
        candles=candles[:candle_length],
        minimal_touch_points=minimal_touch_points,
    )
    if len(indicator[0]) > 0:
        logger.debug(f"{name}, {indicator}")
        return indicator
    return None
