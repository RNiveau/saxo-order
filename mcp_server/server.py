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
from typing import AsyncIterator

from mcp.server import MCPServer

from client.aws_client import AwsClient, dynamodb_session
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

    ``store_available`` is False when the alert store could not be reached.
    That is not fatal: the stored-context tools report their own
    unavailability while the market-data tools carry on, so a missing
    AWS_PROFILE costs you the alert history and nothing else.

    There is no client here. The connection and everything that speaks to
    it live in client/aws_client.py; tools ask that module for the data
    they want rather than being handed something to drive.
    """

    store_available: bool = False


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
        available = False
        if not AwsClient.is_aws_context():
            logger.warning(
                "AWS_PROFILE is not set, so the alert store is unreachable: "
                "stored-context tools will report themselves unavailable, "
                "market data is unaffected"
            )
        else:
            try:
                await stack.enter_async_context(dynamodb_session())
                available = True
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
        yield ServerContext(store_available=available)


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
