import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from api.dependencies import get_dynamodb_client, get_saxo_client
from api.main import app
from client.aws_client import DynamoDBClient
from client.saxo_client import SaxoClient

SAXO_LATENCY_SECONDS = 1.0


@pytest.fixture
def slow_saxo_client():
    async def slow_get_accounts():
        await asyncio.sleep(SAXO_LATENCY_SECONDS)
        return {"Data": []}

    saxo_client = MagicMock(spec=SaxoClient)
    saxo_client.get_accounts.side_effect = slow_get_accounts
    app.dependency_overrides[get_saxo_client] = lambda: saxo_client
    yield saxo_client
    app.dependency_overrides.clear()


@pytest.fixture
def dynamodb_client():
    client = AsyncMock(spec=DynamoDBClient)
    client.get_watchlist_item.return_value = (True, [])
    app.dependency_overrides[get_dynamodb_client] = lambda: client
    return client


async def test_the_router_awaits_the_saxo_client(
    slow_saxo_client, dynamodb_client
):
    """While a Saxo-backed route awaits its client, another route answers.

    This proves the router awaits the client rather than calling it
    synchronously; the real client's own non-blocking I/O is covered by
    the client tests.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        saxo_request = asyncio.create_task(client.get("/api/fund/accounts"))
        await asyncio.sleep(0.1)

        started = time.perf_counter()
        response = await client.get("/api/watchlist/check/itp:xpar")
        elapsed = time.perf_counter() - started

        assert response.status_code == 200
        assert response.json()["in_watchlist"] is True
        assert not saxo_request.done()
        assert elapsed < SAXO_LATENCY_SECONDS / 2

        saxo_response = await saxo_request
        assert saxo_response.status_code == 200
    slow_saxo_client.get_accounts.assert_awaited_once()
