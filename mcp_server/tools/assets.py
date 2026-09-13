"""Resolving a human name to an instrument, and reading its bars.

Both tools answer "what am I looking at": one turns a name into the
identity every other tool needs, the other shows the price action behind
the indicators.
"""

import asyncio
import datetime
import functools
from typing import List, Optional

from mcp.server.mcpserver.exceptions import ToolError

from client.saxo_client import SaxoClient
from mcp_server import formatters
from mcp_server.dependencies import resolve_market, resolve_market_client
from mcp_server.errors import current_market_client
from mcp_server.models import BarSeries, InstrumentRef, ResponseMeta
from mcp_server.tools.market_request import (
    DAYS_FOR_FORMING_WEEK,
    check_market_request,
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


def _now(tz: Optional[datetime.timezone] = None) -> datetime.datetime:
    """The clock, indirected so tests can pin it.

    Patching ``datetime.datetime`` directly would rebind it for every module
    in the process, since ``assets.datetime`` is the stdlib module itself.
    """
    return datetime.datetime.now(tz)


def _newest_bar_is_forming(candles: List[Candle], unit_time: UnitTime) -> bool:
    """Whether row 0 is the period now trading rather than a closed one.

    The provider publishes neither the current day nor the current week, so
    a newest bar inside the period now running can only be one the candle
    builders reconstructed. Each half compares against the clock the
    matching builder uses - naive local for the day, UTC for the week - and
    both stop at the weekend, where the newest bar is the one that closed on
    Friday however the calendar reads: ISO weeks run to Sunday, so a
    Saturday would otherwise report last week's completed bar as live.
    """
    if not candles or candles[0].date is None:
        return False
    if unit_time is UnitTime.W:
        now = _now(datetime.UTC)
        return (
            now.weekday() < 5
            and candles[0].date.isocalendar()[:2] == now.isocalendar()[:2]
        )
    return candles[0].date.date() == _now().date()


async def get_candles(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime,
    count: int,
    exchange: Exchange,
    market: Optional[MarketName],
) -> BarSeries:
    """Fetch the bars and shape them for the wire. Kept apart from the tool."""
    check_market_request(unit_time, exchange, market)

    client, provenance = current_market_client()
    resolved_market = resolve_market(market)
    # Buying more than the answer can carry would be paid for and thrown
    # away by to_rows, which caps at the same MAX_BAR_COUNT.
    depth = min(count, formatters.MAX_BAR_COUNT)

    daily = await asyncio.to_thread(
        functools.partial(
            candle_source.build_daily_series,
            client,
            instrument_id,
            market=resolved_market,
            asset_type=asset_type,
            count=(
                DAYS_FOR_FORMING_WEEK if unit_time is UnitTime.W else depth
            ),
        )
    )
    if unit_time is UnitTime.W:
        candles = await asyncio.to_thread(
            functools.partial(
                candle_source.build_weekly_series,
                client,
                instrument_id,
                daily_candles=daily,
                asset_type=asset_type,
                count=depth,
            )
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

    rows = formatters.to_rows(candles, count)
    return BarSeries(
        meta=ResponseMeta(
            provenance=provenance,
            exchange=exchange,
            unit_time=unit_time,
            last_bar_date=formatters.last_bar_date(candles),
            # The fetch was capped too, so a count above the cap was
            # overridden whether or not rows were dropped afterwards.
            truncated=formatters.exceeds_cap(count),
            forming_period_included=resolved_market is not None,
        ),
        instrument_id=instrument_id,
        rows=rows,
        current_incomplete=(
            resolved_market is not None
            and _newest_bar_is_forming(candles, unit_time)
        ),
        count=len(rows),
    )
