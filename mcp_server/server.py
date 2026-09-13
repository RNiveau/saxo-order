"""The local MCP server for asset analysis.

Read-only. It resolves instruments, returns bars, computes indicators and
runs the project's own setup detections, all over the same code the
scheduled scan uses. It cannot place, amend or cancel an order, and it
writes nothing.

Started as a stdio subprocess by an MCP client (see .mcp.json). stdout is
the protocol wire, so nothing here may print - logging goes to stderr.
"""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional

from mcp.server import MCPServer

from client.aws_client import AwsClient, DynamoDBClient
from mcp_server.errors import market_tool, tool_boundary
from mcp_server.models import IndicatorSnapshot, InstrumentRef
from mcp_server.tools import assets, indicators
from model import AssetType, IndicatorName, MarketName, UnitTime
from model.enum import Exchange
from utils.logger import Logger

logger = Logger.get_logger("mcp_server")

INSTRUCTIONS = """\
Read-only technical analysis over this trading project's own indicators and
setup detections.

Resolve an instrument by name first; its instrument_id and asset_type feed
every other tool. Market data is refused when only simulated data is
available - that refusal is deliberate, so prefer fixing the credential over
passing allow_simulated.
"""


@dataclass
class ServerContext:
    """What the tools need for the life of the server.

    ``dynamodb`` is None when the alert store could not be reached. That is
    not fatal: the stored-context tools report their own unavailability
    while the market-data tools carry on, so a missing AWS_PROFILE costs
    you the alert history and nothing else.

    The client arrives already connected and is passed to the tools that
    need it, which is how the rest of this project injects clients. What
    stays in the client layer is how the connection is made - nothing here
    touches aioboto3.
    """

    dynamodb: Optional[DynamoDBClient] = None


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[ServerContext]:
    """Open what the tools need, and get out of the way of real errors.

    The ``yield`` deliberately sits outside the ``except``. Inside it, an
    exception raised by the server while this context is active gets thrown
    back in at the yield point, caught here, and followed by a second yield -
    which ``@asynccontextmanager`` turns into "generator didn't stop after
    athrow()", losing the actual cause and mislabelling it as a storage
    problem.
    """
    async with AsyncExitStack() as stack:
        store: Optional[DynamoDBClient] = None
        if not AwsClient.is_aws_context():
            logger.warning(
                "AWS_PROFILE is not set, so the alert store is unreachable: "
                "stored-context tools will report themselves unavailable, "
                "market data is unaffected"
            )
        else:
            try:
                store = await stack.enter_async_context(DynamoDBClient())
                logger.info(
                    "Alert store connected (credentials are not checked "
                    "until the first read)"
                )
            except Exception as e:
                logger.warning(
                    f"Alert store unavailable ({e}): stored-context tools "
                    "will report themselves unavailable, market data is "
                    "unaffected"
                )
        yield ServerContext(dynamodb=store)


mcp: MCPServer = MCPServer(
    "saxo-analysis",
    instructions=INSTRUCTIONS,
    lifespan=lifespan,
)


@mcp.tool()
@tool_boundary
async def search_asset(
    query: str,
    exchange: Exchange = Exchange.SAXO,
) -> List[InstrumentRef]:
    """Find tradeable instruments matching a name or symbol.

    Start here: the instrument_id and asset_type this returns are what the
    other market tools need. An empty list means nothing matched, which is
    an answer rather than a failure.
    """
    return await assets.search_asset(query=query, exchange=exchange)


@mcp.tool()
@market_tool
async def get_indicators(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime = UnitTime.D,
    include: Optional[List[IndicatorName]] = None,
    exchange: Exchange = Exchange.SAXO,
    market: Optional[MarketName] = None,
    allow_simulated: bool = False,
) -> IndicatorSnapshot:
    """An instrument's technical state for one timeframe, in one call.

    Moving averages and their slopes, Bollinger bands, ATR, ADX and the
    lag-reduced MACD, plus the last price and its variation. Pass `include`
    to ask for a subset - the history fetched is sized to what you asked
    for, so a short average does not pay for the MACD's 235 bars.

    An indicator the available history cannot support is returned with
    unavailable_reason rather than omitted, so a missing number is never
    ambiguous.
    """
    return await indicators.build_snapshot(
        instrument_id=instrument_id,
        asset_type=asset_type,
        unit_time=unit_time,
        include=include,
        exchange=exchange,
        market=market,
    )


def main() -> None:
    """Entry point for the ``k-mcp`` script. Blocks for the server's life."""
    mcp.run()


if __name__ == "__main__":
    main()
