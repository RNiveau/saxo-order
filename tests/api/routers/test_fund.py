from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_saxo_client
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_saxo_client():
    """Mock SaxoClient returning no Saxo accounts."""
    mock_client = MagicMock()
    mock_client.get_accounts.return_value = {"Data": []}

    def override_get_saxo_client():
        return mock_client

    app.dependency_overrides[get_saxo_client] = override_get_saxo_client
    yield mock_client
    app.dependency_overrides.clear()


class TestAccountsEndpoint:
    def test_accounts_includes_binance_and_ouinex(self):
        response = client.get("/api/fund/accounts")

        assert response.status_code == 200
        accounts = response.json()["accounts"]
        by_id = {acc["account_id"]: acc for acc in accounts}

        assert "binance_main" in by_id
        assert "ouinex_main" in by_id

        ouinex = by_id["ouinex_main"]
        assert ouinex["account_key"] == "ouinex"
        assert ouinex["account_name"] == "Ouinex"
