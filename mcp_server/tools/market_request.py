"""What every market-data tool settles before it fetches anything.

The supported timeframes, the depth the forming week costs, the refusals
that apply identically to candles, indicators and detections, and the market
an instrument trades on when the caller does not name it. They
live here rather than in one of the tool modules because they are properties
of the shared candle sourcing: two tools disagreeing about which timeframes
exist, or about how deep the forming week is, would be a bug the schema
still advertises as a feature.
"""

from typing import Optional

from mcp.server.mcpserver.exceptions import ToolError

from model import AssetType, MarketName, Provenance, UnitTime
from model.enum import Exchange
from utils.exception import SaxoException
from utils.helper import market_name_from_symbol
from utils.logger import Logger

logger = Logger.get_logger("mcp_tools_market_request")

SUPPORTED_UNIT_TIMES = (UnitTime.D, UnitTime.W)

# Enough completed days to cover the week now forming; the weekly series
# only reads the current ISO week out of them, so fetching the indicators'
# full daily depth here would buy history nothing looks at.
DAYS_FOR_FORMING_WEEK = 10


def check_market_request(
    unit_time: UnitTime,
    exchange: Exchange,
) -> None:
    """Refuse a request this server cannot answer honestly."""
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


async def derive_market(
    client, instrument_id: int, asset_type: AssetType
) -> Optional[MarketName]:
    """The instrument's session hours, read from its listing symbol.

    None when the venue cannot say, so the caller falls back to leaving the
    forming period out rather than guessing.
    """
    try:
        detail = await client.get_asset_detail(instrument_id, asset_type.value)
    except SaxoException as e:
        logger.warning(
            f"Could not read the symbol of instrument {instrument_id}: {e}"
        )
        return None
    return market_name_from_symbol(detail.get("Symbol"))


async def settle_market(
    client,
    provenance: Provenance,
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime,
    market: Optional[MarketName],
) -> Optional[MarketName]:
    """The market to build bars against: the caller's, else the listing's."""
    if market is None and provenance is Provenance.LIVE:
        market = await derive_market(client, instrument_id, asset_type)
    if unit_time is UnitTime.W and market is None:
        raise ToolError(
            "The weekly timeframe needs a market: the week now forming is "
            "assembled from the days elapsed in it, and without session "
            "hours those days are incomplete, which would understate the "
            "bar's close, high and low with no way to tell. The instrument's "
            "market could not be read from the venue; pass market, or ask "
            "for the daily timeframe."
        )
    return market
