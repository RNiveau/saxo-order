"""Clients for the MCP tools, with an honest account of where data came from.

The API layer's ``get_saxo_client`` substitutes ``MockSaxoClient`` on a
missing token *and* on any initialisation failure, records it in a log line,
and hands back a bare client. A caller cannot tell what it got. For an
assistant reading the result that is the difference between real analysis and
confident nonsense, so this module returns the provenance alongside the
client and lets the tool boundary decide what to do about it.
"""

import asyncio
import os
from functools import lru_cache
from typing import Optional, Set, Tuple, Union

from cachetools import TTLCache

from client.mock_saxo_client import MockSaxoClient
from client.saxo_client import SaxoClient
from model import Market, MarketName, Provenance
from model.market import EUMarket, USMarket
from utils.configuration import Configuration
from utils.logger import Logger

logger = Logger.get_logger("mcp_dependencies")

# How often the access token is re-read from storage. Long enough that a
# burst of tool calls costs one read, short enough that authenticating
# mid-session is picked up without restarting the server.
TOKEN_REFRESH_TTL_SECONDS = 30

_token_refresh_gate: TTLCache = TTLCache(
    maxsize=1, ttl=TOKEN_REFRESH_TTL_SECONDS
)

_live_client: Optional[SaxoClient] = None
_closing: Set[asyncio.Task] = set()

MARKETS = {
    MarketName.EU: EUMarket,
    MarketName.US: USMarket,
}


@lru_cache()
def get_configuration() -> Configuration:
    return Configuration(os.getenv("CONFIG_FILE", "config.yml"))


def resolve_market_client() -> (
    Tuple[Union[SaxoClient, MockSaxoClient], Provenance]
):
    """The market client to use right now, and what its data is worth.

    Not cached, and it re-reads the token every time. Both halves matter:
    ``Configuration`` reads the token once in its constructor, so a cached
    configuration behind an uncached client would still freeze provenance at
    boot. The common case is the damaging one - start the server before
    authenticating and every market tool is refused for the rest of the
    session, while the refusal message tells you to refresh a token it will
    never look at again.

    Provenance answers "could a live client be built", not "does the token
    still work" - checking that would mean a network round trip on every
    call. An expired token therefore reports LIVE and fails on first use
    with the venue's own message, which the tool boundary passes through
    intact. That is the safe direction: a readable error, never fabricated
    candles wearing a live label.
    """
    config = get_configuration()
    _refresh_tokens(config)

    if not config.access_token:
        logger.warning("No access token: only simulated data is available")
        return MockSaxoClient(config), Provenance.SIMULATED

    try:
        return _shared_live_client(config), Provenance.LIVE
    except Exception as e:
        logger.warning(
            f"Saxo client unavailable ({e}): only simulated data is available"
        )
        return MockSaxoClient(config), Provenance.SIMULATED


def _shared_live_client(config: Configuration) -> SaxoClient:
    """One live client for the server's life, so its connection pool and
    caches outlive a single tool call. It follows the token just re-read,
    and is rebuilt only when the configuration itself was replaced."""
    global _live_client
    if _live_client is not None and _live_client.configuration is not config:
        _discard(_live_client)
        _live_client = None
    if _live_client is None:
        _live_client = SaxoClient(config)
    else:
        _live_client.set_access_token(config.access_token)
    return _live_client


def _discard(client: SaxoClient) -> None:
    """Close a replaced client: on the running loop when there is one,
    keeping a reference so the task is not collected before it runs."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(client.aclose())
        return
    task = loop.create_task(client.aclose())
    _closing.add(task)
    task.add_done_callback(_closing.discard)


async def close_market_client() -> None:
    """Release the live client's connections, at server shutdown."""
    global _live_client
    if _closing:
        await asyncio.gather(*_closing)
    if _live_client is not None:
        await _live_client.aclose()
        _live_client = None


def _refresh_tokens(config: Configuration) -> None:
    """Re-read the access token, at most once per TTL window.

    ``load_tokens`` is not always a cheap file read. With ``AWS_PROFILE``
    set - which is exactly the setup this server documents for reaching
    DynamoDB - ``Configuration`` holds an ``S3Client``, and every call is a
    blocking ``get_object`` against S3. Doing that per tool call would put a
    synchronous network round trip on the event loop for every question the
    assistant asks.

    A failure to re-read is not a failure of the call. The token already in
    hand is very probably still good, so a blip in token storage should not
    turn into "your market tool failed"; the gate is set either way so a
    sustained outage costs one attempt per window rather than one per call.
    """
    if _token_refresh_gate.get("refreshed"):
        return
    try:
        config.load_tokens()
    except Exception as e:
        logger.warning(
            f"Could not re-read the access token ({e}); "
            "continuing with the one already loaded"
        )
    _token_refresh_gate["refreshed"] = True


def resolve_market(name: Optional[MarketName]) -> Optional[Market]:
    """The session hours for a named market, or None when unnamed.

    None is passed straight through to the candle builders, where it means
    "leave the forming period out rather than guess its hours".
    """
    if name is None:
        return None
    return MARKETS[name]()
