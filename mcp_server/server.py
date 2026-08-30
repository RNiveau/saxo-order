"""The local MCP server for asset analysis.

Read-only. It resolves instruments, returns bars, computes indicators and
runs the project's own setup detections, all over the same code the
scheduled scan uses. It cannot place, amend or cancel an order, and it
writes nothing.

Started as a stdio subprocess by an MCP client (see .mcp.json). stdout is
the protocol wire, so nothing here may print - logging goes to stderr.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from mcp.server import MCPServer

from client.aws_client import DynamoDBClient
from mcp_server.dependencies import dynamodb_client
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

    ``dynamodb`` is None when the store could not be reached. That is not
    fatal: the stored-context tools report their own unavailability while
    the market-data tools carry on, so a missing AWS_PROFILE costs you the
    alert history and nothing else.
    """

    dynamodb: Optional[DynamoDBClient] = None


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[ServerContext]:
    try:
        async with dynamodb_client() as client:
            logger.info("DynamoDB ready")
            yield ServerContext(dynamodb=client)
    except Exception as e:
        logger.warning(
            f"DynamoDB unavailable ({e}): stored-context tools will report "
            "themselves unavailable, market data is unaffected"
        )
        yield ServerContext(dynamodb=None)


mcp: MCPServer = MCPServer(
    "saxo-analysis",
    instructions=INSTRUCTIONS,
    lifespan=lifespan,
)


def main() -> None:
    """Entry point for the ``k-mcp`` script. Blocks for the server's life."""
    mcp.run()


if __name__ == "__main__":
    main()
