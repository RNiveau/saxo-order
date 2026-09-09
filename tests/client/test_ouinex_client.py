from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest

from client.ouinex_client import OuinexClient
from model.enum import AssetType, Currency, Direction, Exchange
from model.workflow import UnitTime
from utils.exception import OuinexException


def make_response(
    status_code: int = 200, json_data: Optional[dict] = None
) -> MagicMock:
    """Build a fake requests.Response with the given status and JSON body."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = ""
    if status_code >= 400:
        import requests

        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} error"
        )
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.fixture
def client_and_session() -> Tuple[OuinexClient, MagicMock]:
    """OuinexClient with a mocked GraphQL transport session."""
    ouinex = OuinexClient(
        key="api-key",
        secret="secret-key",
        graphql_url="https://live-api.ouinex.com/graphql",
    )
    session = MagicMock()
    ouinex.session = session
    return ouinex, session


SIGN_IN_OK = {
    "data": {
        "signIn": {
            "accessToken": "jwt-token",
            "refreshToken": "refresh-token",
            "expiresIn": 3600,
        }
    }
}


class TestOuinexClientAuth:
    def test_sign_in_stores_access_token(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)

        client._sign_in()

        assert client._access_token == "jwt-token"
        assert client._token_expiry > 0

    def test_sign_in_raises_on_missing_token(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(
            200, {"data": {"signIn": {}}}
        )

        with pytest.raises(OuinexException):
            client._sign_in()

    def test_sign_in_raises_on_graphql_error(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(
            200, {"errors": [{"message": "bad credentials"}]}
        )

        with pytest.raises(OuinexException):
            client._sign_in()

    def test_ensure_token_signs_in_when_missing(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)

        client._ensure_token()

        assert client._access_token == "jwt-token"
        assert session.post.call_count == 1

    def test_ensure_token_reuses_valid_token(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)
        client._ensure_token()
        session.post.reset_mock()

        client._ensure_token()

        session.post.assert_not_called()


class TestOuinexClientExecute:
    def test_execute_sends_bearer_and_returns_data(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, {"data": {"instruments": []}}),
        ]

        result = client._execute("query { instruments { instrument_id } }")

        assert result == {"instruments": []}
        auth_call = session.post.call_args_list[-1]
        assert (
            auth_call.kwargs["headers"]["Authorization"] == "Bearer jwt-token"
        )

    def test_execute_refreshes_token_on_401(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(401, {}),
            make_response(200, SIGN_IN_OK),
            make_response(200, {"data": {"ok": True}}),
        ]

        result = client._execute("query { ok }")

        assert result == {"ok": True}

    def test_execute_raises_on_graphql_error(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, {"errors": [{"message": "boom"}]}),
        ]

        with pytest.raises(OuinexException):
            client._execute("query { ok }")


def instrument(instrument_id: str, base: str, quote: str) -> dict:
    return {
        "instrument_id": instrument_id,
        "name": f"{base}/{quote}",
        "base_currency": {"currency_id": base},
        "quote_currency": {"currency_id": quote},
    }


INSTRUMENTS_OK = {
    "data": {
        "instruments": [
            instrument("BTCUSD", "BTC", "USD"),
            instrument("ETHUSD", "ETH", "USD"),
            instrument("BTCUSD_CONV", "BTC", "USD"),
        ]
    }
}


class TestOuinexClientSearch:
    def test_search_returns_crypto_assets(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, INSTRUMENTS_OK)

        results = client.search("btc")

        assert len(results) == 1
        asset = results[0]
        assert asset.symbol == "BTCUSD"
        assert asset.description == "BTC/USD"
        assert asset.exchange == Exchange.OUINEX
        assert asset.asset_type == AssetType.CRYPTO
        assert asset.identifier is None

    def test_search_matches_quote_currency(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, INSTRUMENTS_OK)

        results = client.search("usd")

        assert {asset.symbol for asset in results} == {"BTCUSD", "ETHUSD"}
        assert all(asset.exchange == Exchange.OUINEX for asset in results)

    def test_search_does_not_sign_in(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, INSTRUMENTS_OK)

        client.search("btc")

        assert session.post.call_count == 1
        assert session.post.call_args.kwargs["headers"] == {}
        assert client._access_token is None


CLOSED_ORDERS_OK = {
    "data": {
        "closedOrders": [
            {
                "symbol": "BTCUSD",
                "baseCurrency": "BTC",
                "quoteCurrency": "USD",
                "side": "BUY",
                "price": 50000,
                "quantity": 0.1,
                "fee": 0.001,
                "feeCurrency": "BTC",
                "executedAt": 1700000000000,
            },
            {
                "symbol": "ETHUSD",
                "baseCurrency": "ETH",
                "quoteCurrency": "USD",
                "side": "SELL",
                "price": 3000,
                "quantity": 2,
                "fee": 1.5,
                "feeCurrency": "USD",
                "executedAt": 1700000000000,
            },
        ]
    }
}


class TestOuinexClientReport:
    def test_get_report_all_maps_trades(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, CLOSED_ORDERS_OK),
        ]

        orders = client.get_report_all("2023/01/01", usdeur_rate=0.5)

        assert len(orders) == 2

        buy = orders[0]
        assert buy.code == "BTC"
        assert buy.direction == Direction.BUY
        assert buy.asset_type == AssetType.CRYPTO
        assert buy.currency == Currency.USD
        # Buy fee paid in base asset reduces quantity
        assert buy.quantity == pytest.approx(0.099)
        assert buy.taxes is not None
        assert buy.taxes.cost == pytest.approx(0.001 * (50000 * 0.5))

        sell = orders[1]
        assert sell.direction == Direction.SELL
        # Sell fee paid in quote currency -> EUR cost
        assert sell.taxes is not None
        assert sell.taxes.cost == pytest.approx(1.5 * 0.5)

    def test_buy_fee_in_base_asset_reduces_quantity_and_costs_eur(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        # Real example: buy 550 XRP @ 1.1430 USDC, fee 0.5390 XRP.
        # Final quantity received is 550 - 0.539 = 549.461 XRP and the fee
        # is reported in EUR at the trade price.
        client, session = client_and_session
        xrp_trade = {
            "data": {
                "closedOrders": [
                    {
                        "symbol": "XRP/USDC",
                        "baseCurrency": "XRP",
                        "quoteCurrency": "USDC",
                        "side": "BUY",
                        "price": 1.1430,
                        "quantity": 550,
                        "fee": 0.5390,
                        "feeCurrency": "XRP",
                        "executedAt": 1700000000000,
                    }
                ]
            }
        }
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, xrp_trade),
        ]

        orders = client.get_report_all("2023/01/01", usdeur_rate=0.9)

        order = orders[0]
        assert order.quantity == pytest.approx(549.461)
        assert order.taxes is not None
        assert order.taxes.cost == pytest.approx(0.5390 * 1.1430 * 0.9)

    def test_get_report_filters_by_symbol(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, CLOSED_ORDERS_OK),
        ]

        orders = client.get_report("ETH", "2023/01/01", usdeur_rate=0.5)

        assert len(orders) == 1
        assert orders[0].code == "ETH"


def price_bars(bars: list) -> dict:
    return {"data": {"priceBars": bars}}


class TestOuinexClientCandles:
    def test_get_candles_native_newest_first_and_rounded(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        bars = [
            {
                "open": 1.11111,
                "high": 2.22222,
                "low": 0.99999,
                "close": 1.23456,
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "open": 1.23456,
                "high": 2.5,
                "low": 1.0,
                "close": 2.0,
                "timestamp": "2024-01-02T00:00:00Z",
            },
        ]
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, price_bars(bars)),
        ]

        candles = client.get_candles("BTCUSD", UnitTime.D, limit=200)

        assert len(candles) == 2
        # Newest first (index 0 = latest timestamp)
        assert candles[0].close == 2.0
        assert candles[1].close == 1.2346
        assert candles[0].ut == UnitTime.D
        # Instrument id and periodicity forwarded to the query
        variables = session.post.call_args_list[-1].kwargs["json"]["variables"]
        assert variables["instrumentId"] == "BTCUSD"
        assert variables["periodicity"] == "1d"

    def test_get_latest_candle_returns_minute_bar(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(
                200,
                price_bars(
                    [
                        {
                            "open": 1.14,
                            "high": 1.20,
                            "low": 1.10,
                            "close": 1.15,
                            "timestamp": "2024-01-02T09:31:00Z",
                        }
                    ]
                ),
            ),
        ]

        candle = client.get_latest_candle("XRPUSD")

        assert candle.close == 1.15
        variables = session.post.call_args_list[-1].kwargs["json"]["variables"]
        assert variables["periodicity"] == "1m"

    def test_get_candles_weekly_aggregates_from_daily(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        daily = [
            {
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11,
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "open": 11,
                "high": 13,
                "low": 8,
                "close": 12,
                "timestamp": "2024-01-02T00:00:00Z",
            },
            {
                "open": 12,
                "high": 14,
                "low": 10,
                "close": 13,
                "timestamp": "2024-01-03T00:00:00Z",
            },
            {
                "open": 13,
                "high": 15,
                "low": 11,
                "close": 14,
                "timestamp": "2024-01-08T00:00:00Z",
            },
            {
                "open": 14,
                "high": 16,
                "low": 12,
                "close": 15,
                "timestamp": "2024-01-09T00:00:00Z",
            },
        ]
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, price_bars(daily)),
        ]

        candles = client.get_candles("BTCUSD", UnitTime.W, limit=200)

        assert len(candles) == 2
        # Newest week first
        assert candles[0].ut == UnitTime.W
        assert candles[0].open == 13
        assert candles[0].close == 15
        assert candles[0].higher == 16
        assert candles[0].lower == 11
        # Previous week aggregated across three daily bars
        assert candles[1].open == 10
        assert candles[1].close == 13
        assert candles[1].higher == 14
        assert candles[1].lower == 8
        # Daily periodicity requested for aggregation
        variables = session.post.call_args_list[-1].kwargs["json"]["variables"]
        assert variables["periodicity"] == "1d"
