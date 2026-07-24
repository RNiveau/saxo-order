from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest

from client.ouinex_client import OuinexClient
from model.enum import AssetType, Currency, Direction, Exchange
from utils.exception import OuinexException


def make_response(
    status_code: int = 200, json_data: Optional[dict] = None
) -> MagicMock:
    """Build a fake requests.Response with the given status and JSON body."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
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

        result = client._execute("query { instruments { id } }")

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


INSTRUMENTS_OK = {
    "data": {
        "instruments": [
            {
                "id": 1,
                "symbol": "BTCUSD",
                "baseCurrency": "BTC",
                "quoteCurrency": "USD",
            },
            {
                "id": 2,
                "symbol": "ETHUSD",
                "baseCurrency": "ETH",
                "quoteCurrency": "USD",
            },
        ]
    }
}


class TestOuinexClientSearch:
    def test_search_returns_crypto_assets(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, INSTRUMENTS_OK),
        ]

        results = client.search("btc")

        assert len(results) == 1
        asset = results[0]
        assert asset.symbol == "BTCUSD"
        assert asset.description == "BTC/USD"
        assert asset.exchange == Exchange.OUINEX
        assert asset.asset_type == AssetType.CRYPTO
        assert asset.identifier == 1

    def test_search_matches_quote_currency(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, INSTRUMENTS_OK),
        ]

        results = client.search("usd")

        assert {asset.symbol for asset in results} == {"BTCUSD", "ETHUSD"}
        assert all(asset.exchange == Exchange.OUINEX for asset in results)


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
