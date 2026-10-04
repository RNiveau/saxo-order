import asyncio
import datetime
import json
from typing import Callable, List
from unittest.mock import AsyncMock

import httpx
import pytest

from client import saxo_client as saxo_client_module
from client.saxo_auth_client import SaxoAuthClient
from client.saxo_client import SaxoClient
from model import (
    Account,
    ConditionalOrder,
    Direction,
    Order,
    OrderType,
    TriggerOrder,
)
from tests.utils.configuration import MockConfiguration
from utils.configuration import Configuration
from utils.exception import SaxoException

SAXO_URL = "https://saxo.test/"


class HttpConfiguration(MockConfiguration):
    def __init__(self):
        super().__init__()
        self.refresh_token = "refresh_token"

    @property
    def saxo_url(self) -> str:
        return SAXO_URL

    @property
    def auth_url(self) -> str:
        return "https://auth.test/"


def build_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> SaxoClient:
    return SaxoClient(
        configuration=HttpConfiguration(),
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture(autouse=True)
def no_api_mode(monkeypatch):
    monkeypatch.delenv("API_MODE", raising=False)


@pytest.fixture
def no_backoff(mocker) -> AsyncMock:
    return mocker.patch.object(
        saxo_client_module.asyncio, "sleep", new_callable=AsyncMock
    )


class TestSaxoClient:
    @pytest.mark.parametrize(
        "stock_code, price, quantity, type, direction, stop_price,"
        "conditional_order, expected",
        [
            (
                12345,
                10,
                9,
                OrderType.LIMIT,
                Direction.BUY,
                None,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "Limit",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.STOP,
                Direction.BUY,
                100,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "Stop",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.OPEN_STOP,
                Direction.SELL,
                None,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "StopIfTraded",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Sell",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.STOP_LIMIT,
                Direction.BUY,
                8,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 8,
                    "Uic": 12345,
                    "OrderType": "StopLimit",
                    "BuySell": "Buy",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "StopLimitPrice": 10,
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.MARKET,
                Direction.BUY,
                8,
                None,
                {
                    "Amount": 9,
                    "Uic": 12345,
                    "OrderType": "Market",
                    "OrderDuration": {"DurationType": "DayOrder"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9.5,
                OrderType.MARKET,
                Direction.BUY,
                8,
                ConditionalOrder(
                    1,
                    trigger=TriggerOrder.BELLOW,
                    price=40.7,
                    asset_type="ETF",
                ),
                {
                    "Amount": 9.5,
                    "Uic": 12345,
                    "OrderType": "Market",
                    "OrderDuration": {"DurationType": "DayOrder"},
                    "BuySell": "Buy",
                    "Orders": [
                        {
                            "AccountKey": "account",
                            "AssetType": "ETF",
                            "ManualOrder": True,
                            "BuySell": "Buy",
                            "OrderType": "TriggerLimit",
                            "Uic": 1,
                            "OrderDuration": {
                                "DurationType": "GoodTillCancel"
                            },
                            "TriggerOrderData": {
                                "LowerPrice": 40.7,
                                "PriceType": "LastTraded",
                            },
                        }
                    ],
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.LIMIT,
                Direction.BUY,
                8,
                ConditionalOrder(
                    1, trigger=TriggerOrder.ABOVE, price=40, asset_type="ETF"
                ),
                {
                    "Amount": 9,
                    "Uic": 12345,
                    "OrderPrice": 10,
                    "OrderType": "Limit",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                    "Orders": [
                        {
                            "AccountKey": "account",
                            "AssetType": "ETF",
                            "ManualOrder": True,
                            "BuySell": "Sell",
                            "OrderType": "TriggerLimit",
                            "Uic": 1,
                            "OrderDuration": {
                                "DurationType": "GoodTillCancel"
                            },
                            "TriggerOrderData": {
                                "LowerPrice": 40,
                                "PriceType": "LastTraded",
                            },
                        }
                    ],
                },
            ),
        ],
    )
    async def test_set_order(
        self,
        stock_code: int,
        price: float,
        quantity: float,
        type: OrderType,
        direction: Direction,
        stop_price: float,
        conditional_order: ConditionalOrder,
        expected: dict,
    ):
        requests: List[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={})

        expected.update(
            {
                "AccountKey": "account",
                "AssetType": "Stock",
                "ManualOrder": True,
            }
        )
        order = Order(
            asset_type="Stock",
            code=str(stock_code),
            direction=direction,
            type=type,
            price=price,
            quantity=quantity,
        )
        async with build_client(handler) as client:
            await client.set_order(
                account=Account(key="account", name="account"),
                order=order,
                saxo_uic=stock_code,
                stop_price=stop_price,
                conditional_order=conditional_order,
            )

        assert len(requests) == 1
        assert requests[0].method == "POST"
        assert str(requests[0].url) == f"{SAXO_URL}trade/v2/orders"
        assert json.loads(requests[0].content) == expected

    async def test_is_day_open(self, mocker):
        client = SaxoClient(configuration=MockConfiguration())
        mocker.patch.object(
            client,
            "get_historical_data",
            new_callable=AsyncMock,
            return_value=[{"Time": datetime.datetime(2023, 11, 11, 0, 0, 0)}],
        )
        assert (
            await client.is_day_open(
                "DAX.I", "STOCK", datetime.datetime(2023, 11, 11)
            )
            is True
        )
        assert (
            await client.is_day_open(
                "DAX.I", "STOCK", datetime.datetime(2023, 11, 12)
            )
            is False
        )
        await client.aclose()


class TestTokenRefresh:
    async def test_concurrent_401s_refresh_the_token_once(self, mocker):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.headers["Authorization"] == "Bearer new_token":
                return httpx.Response(200, json={"Data": [{"id": 1}]})
            return httpx.Response(401, json={})

        async def slow_refresh(self):
            await asyncio.sleep(0.05)
            return "new_token", "new_refresh_token"

        refresh = mocker.patch.object(
            SaxoAuthClient,
            "refresh_token",
            autospec=True,
            side_effect=slow_refresh,
        )
        save_tokens = mocker.patch.object(Configuration, "save_tokens")

        async with build_client(handler) as client:
            results = await asyncio.gather(
                *(client.get_open_orders() for _ in range(5))
            )

        assert results == [[{"id": 1}]] * 5
        assert refresh.call_count == 1
        save_tokens.assert_called_once_with("new_token", "new_refresh_token")

    async def test_a_401_after_refresh_is_reported_as_expired(self, mocker):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={})

        mocker.patch.object(
            SaxoAuthClient,
            "refresh_token",
            new_callable=AsyncMock,
            return_value=("new_token", "new_refresh_token"),
        )
        mocker.patch.object(Configuration, "save_tokens")

        async with build_client(handler) as client:
            with pytest.raises(SaxoException, match="access_token is expired"):
                await client.get_open_orders()


class TestResilience:
    async def test_a_5xx_is_retried_then_succeeds(self, no_backoff):
        statuses = iter([503, 200])
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            status = next(statuses)
            return httpx.Response(status, json={"TotalValue": 1000.0})

        async with build_client(handler) as client:
            assert await client.get_total_amount() == 1000.0

        assert len(calls) == 2
        no_backoff.assert_awaited_once()

    async def test_rate_limit_waits_without_blocking_the_loop(
        self, mocker, no_backoff
    ):
        blocking_sleep = mocker.patch("time.sleep")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"TotalValue": 1000.0},
                headers={
                    "X-RateLimit-ChartMinute-Remaining": "1",
                    "X-RateLimit-ChartMinute-Reset": "3",
                },
            )

        async with build_client(handler) as client:
            await client.get_total_amount()

        no_backoff.assert_awaited_once_with(4)
        blocking_sleep.assert_not_called()

    async def test_get_asset_is_cached(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(
                200,
                json={
                    "Data": [
                        {"Symbol": "ITP:xpar", "Identifier": 42},
                        {"Symbol": "ITPX:xpar", "Identifier": 43},
                    ]
                },
            )

        async with build_client(handler) as client:
            first = await client.get_asset("itp", "xpar")
            second = await client.get_asset("itp", "xpar")

        assert first == second == {"Symbol": "ITP:xpar", "Identifier": 42}
        assert len(calls) == 1


class TestSaxoAuthClient:
    async def test_login_returns_the_redirect_location(self, monkeypatch):
        location = "http://localhost?code=abc-123"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"Location": location})

        auth_client = SaxoAuthClient(HttpConfiguration())
        monkeypatch.setattr(
            auth_client,
            "_http",
            lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

        assert await auth_client.login() == location
