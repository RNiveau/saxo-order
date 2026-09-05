"""Resolving a human name to something the other tools can use."""

import asyncio
from typing import List

from mcp.server.mcpserver.exceptions import ToolError

from client.saxo_client import SaxoClient
from mcp_server.dependencies import resolve_market_client
from mcp_server.models import InstrumentRef
from model import AssetType, Provenance
from model.enum import Exchange
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
