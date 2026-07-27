from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest

from client.ouinex_client import OuinexClient
from model.enum import AssetType, Exchange
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
