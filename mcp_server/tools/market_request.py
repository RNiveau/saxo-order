"""What every market-data tool settles before it fetches anything.

The supported timeframes, the depth the forming week costs, and the three
refusals that apply identically to candles, indicators and detections. They
live here rather than in one of the tool modules because they are properties
of the shared candle sourcing: two tools disagreeing about which timeframes
exist, or about how deep the forming week is, would be a bug the schema
still advertises as a feature.
"""

from typing import Optional

from mcp.server.mcpserver.exceptions import ToolError

from model import MarketName, UnitTime
from model.enum import Exchange

SUPPORTED_UNIT_TIMES = (UnitTime.D, UnitTime.W)

# Enough completed days to cover the week now forming; the weekly series
# only reads the current ISO week out of them, so fetching the indicators'
# full daily depth here would buy history nothing looks at.
DAYS_FOR_FORMING_WEEK = 10


def check_market_request(
    unit_time: UnitTime,
    exchange: Exchange,
    market: Optional[MarketName],
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
    if unit_time is UnitTime.W and market is None:
        raise ToolError(
            "The weekly timeframe needs a market: the week now forming is "
            "assembled from the days elapsed in it, and without session "
            "hours those days are incomplete, which would understate the "
            "bar's close, high and low with no way to tell. Pass market, "
            "or ask for the daily timeframe."
        )
