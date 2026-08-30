"""Clients for the MCP tools, with an honest account of where data came from.

The API layer's ``get_saxo_client`` substitutes ``MockSaxoClient`` on a
missing token *and* on any initialisation failure, records it in a log line,
and hands back a bare client. A caller cannot tell what it got. For an
assistant reading the result that is the difference between real analysis and
confident nonsense, so this module returns the provenance alongside the
client and lets the tool boundary decide what to do about it.
"""

import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncIterator, Optional, Tuple, Union

import aioboto3

from client.aws_client import DynamoDBClient
from client.mock_saxo_client import MockSaxoClient
from client.saxo_client import SaxoClient
from model import Market, MarketName, Provenance
from model.market import DaxCfdMarket, EuCfdMarket, EUMarket, USMarket
from utils.configuration import Configuration
from utils.logger import Logger

logger = Logger.get_logger("mcp_dependencies")

AWS_REGION = "eu-west-1"

MARKETS = {
    MarketName.EU: EUMarket,
    MarketName.US: USMarket,
    MarketName.DAX_CFD: DaxCfdMarket,
    MarketName.EU_CFD: EuCfdMarket,
}


@lru_cache()
def get_configuration() -> Configuration:
    return Configuration(os.getenv("CONFIG_FILE", "config.yml"))


def resolve_market_client() -> (
    Tuple[Union[SaxoClient, MockSaxoClient], Provenance]
):
    """The market client to use right now, and what its data is worth.

    Deliberately not cached. A token that expires an hour into a session has
    to change the answer: a client resolved once at startup would keep
    reporting LIVE while the data underneath had turned simulated, and the
    refusal gate would wave it through. Constructing a client is cheap next
    to the request it is about to make.
    """
    config = get_configuration()

    if not config.access_token:
        logger.warning("No access token: only simulated data is available")
        return MockSaxoClient(config), Provenance.SIMULATED

    try:
        return SaxoClient(config), Provenance.LIVE
    except Exception as e:
        logger.warning(
            f"Saxo client unavailable ({e}): only simulated data is available"
        )
        return MockSaxoClient(config), Provenance.SIMULATED


def resolve_market(name: Optional[MarketName]) -> Optional[Market]:
    """The session hours for a named market, or None when unnamed.

    None is passed straight through to the candle builders, where it means
    "leave the forming period out rather than guess its hours".
    """
    if name is None:
        return None
    return MARKETS[name]()


@asynccontextmanager
async def dynamodb_client() -> AsyncIterator[DynamoDBClient]:
    """One DynamoDB resource for the life of the server.

    ``DynamoDBClient`` needs an active aioboto3 resource; the CLI's
    ``create_dynamodb_client`` opens and closes one per invocation, which for
    a long-running server would mean a new resource on every tool call. This
    is the same shape as the API's lifespan instead.

    Reaching AWS locally needs AWS_PROFILE exported - see quickstart.md.
    """
    session = aioboto3.Session()
    async with session.resource(
        "dynamodb", region_name=AWS_REGION
    ) as resource:
        yield DynamoDBClient(dynamodb_resource=resource)
