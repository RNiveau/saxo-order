"""One boundary every MCP tool goes through.

Two jobs, both of which have to be impossible to forget rather than a rule
each tool remembers to follow.

**Readable failures.** The SDK re-raises anything that is not a ``ToolError``
as ``UnexpectedToolError("Error executing tool <name>")`` and withholds the
original message from the model - so a bare ``SaxoException("Missing candles
to calcule the ma")`` reaches the assistant as a blank wall. Known failures
are translated here so they arrive with their text intact.

**No simulated data by accident.** ``resolve_market_client`` may hand back a
``MockSaxoClient``. ``market_tool`` refuses the call unless the request opted
in, so a tool cannot serve fabricated candles by forgetting a check.

The client is passed through a context variable rather than an argument
because a tool's signature *is* its JSON schema - an injected ``client``
parameter would show up as something the model is expected to supply.
"""

import functools
from contextvars import ContextVar
from typing import (
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from botocore.exceptions import BotoCoreError, ClientError
from mcp.server.mcpserver.exceptions import ToolError
from requests.exceptions import RequestException

from client.mock_saxo_client import MockSaxoClient
from client.saxo_client import SaxoClient
from mcp_server.dependencies import resolve_market_client
from model import Provenance
from utils.exception import OuinexException, SaxoException
from utils.logger import Logger

logger = Logger.get_logger("mcp_errors")

MarketClient = Union[SaxoClient, MockSaxoClient]

# Failures we know how to describe. Anything outside this list is a genuine
# crash and is left to the SDK, which logs a traceback server-side - a bug
# should look like a bug, not like a tidy explanation.
KNOWN_FAILURES: Tuple[Type[Exception], ...] = (
    SaxoException,
    OuinexException,
    RequestException,
    BotoCoreError,
    ClientError,
    RuntimeError,
)

_market_client: ContextVar[Optional[Tuple[MarketClient, Provenance]]] = (
    ContextVar("market_client", default=None)
)

F = TypeVar("F", bound=Callable[..., Any])


def current_market_client() -> Tuple[MarketClient, Provenance]:
    """The client resolved for the tool call in progress."""
    resolved = _market_client.get()
    if resolved is None:
        raise RuntimeError(
            "No market client in context: this tool needs @market_tool"
        )
    return resolved


def tool_boundary(func: F) -> F:
    """Translate known failures into messages the model can act on."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ToolError:
            raise
        except KNOWN_FAILURES as e:
            logger.info(f"{func.__name__} failed: {e}")
            raise ToolError(str(e) or e.__class__.__name__) from e

    return cast(F, wrapper)


def market_tool(func: F) -> F:
    """A tool that reads market data: resolve the client, refuse fakes.

    ``allow_simulated`` is read from the call's own arguments and never
    remembered, so opting in once does not opt in for the rest of the
    session.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        client, provenance = resolve_market_client()
        if provenance is Provenance.SIMULATED and not kwargs.get(
            "allow_simulated", False
        ):
            raise ToolError(
                "Live market data is unavailable, so this would be answered "
                "from simulated data. Refresh the Saxo access token, or pass "
                "allow_simulated=true to accept fabricated values for this "
                "one call."
            )
        token = _market_client.set((client, provenance))
        try:
            return await func(*args, **kwargs)
        finally:
            _market_client.reset(token)

    return cast(F, tool_boundary(wrapper))
