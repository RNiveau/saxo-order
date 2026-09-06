"""Resolving a human name to an instrument, and reading its bars.

Both tools answer "what am I looking at": one turns a name into the
identity every other tool needs, the other shows the price action behind
the indicators.
"""

import asyncio
import datetime
from typing import List, Optional

from mcp.server.mcpserver.exceptions import ToolError

from client.saxo_client import SaxoClient
from mcp_server import formatters
from mcp_server.dependencies import resolve_market, resolve_market_client
from mcp_server.errors import current_market_client
from mcp_server.models import BarSeries, InstrumentRef, ResponseMeta
from mcp_server.tools.indicators import (
    DAYS_FOR_FORMING_WEEK,
    SUPPORTED_UNIT_TIMES,
)
from model import AssetType, Candle, MarketName, Provenance, UnitTime
from model.enum import Exchange
from services import candle_source
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("mcp_tools_assets")

NOTHING_FOUND = "Nothing found for"


async def search_asset(
    query: str,
    exchange: Exchange = Exchange.SAXO,
) -> List[InstrumentRef]:
    """Find tradeable instruments matching a name or symbol.

    Start here. The instrument_id and asset_type this returns are what every
    other market tool needs; nothing else resolves a name for you.

    Returns an empty list when nothing matches - that is an answer, not a
    failure. An instrument that exists but cannot be analysed comes back
    with unavailable_reason set rather than being dropped.
    """
    if exchange is not Exchange.SAXO:
        raise ToolError(
            f"{exchange.value} is not supported yet; this server currently "
            "resolves instruments on saxo only"
        )

    client, provenance = resolve_market_client()
    if provenance is Provenance.SIMULATED or not isinstance(
        client, SaxoClient
    ):
        # MockSaxoClient has no catalogue to search, and inventing one would
        # hand back instruments that do not exist - worse than refusing.
        raise ToolError(
            "Instrument resolution needs a live venue connection, and only "
            "simulated data is available. Refresh the Saxo access token."
        )
    try:
        assets = await asyncio.to_thread(client.search, query)
    except SaxoException as e:
        # The client raises rather than returning [] when nothing matches,
        # so without this every empty search would read as a venue failure.
        if NOTHING_FOUND in str(e):
            logger.info(f"No instrument matches {query!r}")
            return []
        raise

    return [
        InstrumentRef(
            code=asset.symbol,
            description=asset.description,
            exchange=asset.exchange,
            asset_type=(
                asset.asset_type
                if isinstance(asset.asset_type, AssetType)
                else AssetType(asset.asset_type)
            ),
            instrument_id=asset.identifier,
            unavailable_reason=(
                None
                if asset.identifier is not None
                else "the venue returned no identifier, so it cannot be "
                "analysed"
            ),
        )
        for asset in assets
    ]


def _newest_bar_is_forming(candles: List[Candle], unit_time: UnitTime) -> bool:
    """Whether row 0 is the period now trading rather than a closed one.

    The provider never publishes the current day or week, so a newest bar
    dated today (or in today's ISO week) can only be the one the candle
    builders reconstructed. Each half compares against the clock the
    matching builder uses, naive local for the day and UTC for the week.
    """
    if not candles or candles[0].date is None:
        return False
    if unit_time is UnitTime.W:
        now = datetime.datetime.now(datetime.UTC)
        return candles[0].date.isocalendar()[:2] == now.isocalendar()[:2]
    return candles[0].date.date() == datetime.datetime.now().date()


async def get_candles(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime,
    count: int,
    exchange: Exchange,
    market: Optional[MarketName],
) -> BarSeries:
    """Fetch the bars and shape them for the wire. Kept apart from the tool."""
    if unit_time not in SUPPORTED_UNIT_TIMES:
        raise ToolError(
            f"{unit_time.value} is not supported; this server reads "
            + " and ".join(u.value for u in SUPPORTED_UNIT_TIMES)
        )
    if exchange is not Exchange.SAXO:
        raise ToolError(
            f"{exchange.value} is not supported yet; this server reads "
            "market data from saxo only. Labelling a saxo answer with "
            "another venue would be worse than refusing - an instrument id "
            "means something different on each."
        )
    if unit_time is UnitTime.W and market is None:
        raise ToolError(
            "The weekly timeframe needs a market: the week now forming is "
            "assembled from the days elapsed in it, and without session "
            "hours those days are incomplete, which would understate the "
            "bar's close, high and low with no way to tell. Pass market, "
            "or ask for the daily timeframe."
        )

    client, provenance = current_market_client()
    resolved_market = resolve_market(market)
    # Buying more than the answer can carry would be paid for and thrown
    # away by to_rows, which caps at the same MAX_BAR_COUNT.
    depth = max(1, min(count, formatters.MAX_BAR_COUNT))

    daily = await asyncio.to_thread(
        candle_source.build_daily_series,
        client,
        instrument_id,
        resolved_market,
        asset_type,
        DAYS_FOR_FORMING_WEEK if unit_time is UnitTime.W else depth,
    )
    if unit_time is UnitTime.W:
        candles = await asyncio.to_thread(
            candle_source.build_weekly_series,
            client,
            instrument_id,
            daily,
            asset_type,
            depth,
        )
    else:
        candles = daily

    if not candles and provenance is Provenance.SIMULATED:
        # An empty series is a legitimate answer from a live venue, but the
        # mock returns [] for every instrument - reporting that as "no
        # history" would be a fabrication of a different kind.
        raise ToolError(
            "The simulated client returns no candles, so there are no bars "
            "to show. Opting in to simulated data does not make this tool "
            "work - refresh the Saxo access token."
        )

    rows, truncated = formatters.to_rows(candles, count)
    forming = resolved_market is not None and _newest_bar_is_forming(
        candles, unit_time
    )
    return BarSeries(
        meta=ResponseMeta(
            provenance=provenance,
            exchange=exchange,
            unit_time=unit_time,
            last_bar_date=formatters.last_bar_date(candles),
            truncated=truncated,
            forming_period_included=forming,
        ),
        instrument_id=instrument_id,
        rows=rows,
        current_incomplete=forming,
        count=len(rows),
    )
