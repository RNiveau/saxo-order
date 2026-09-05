from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import (
    get_binance_client,
    get_ouinex_client,
    get_saxo_client,
)
from api.main import app
from model import AssetType
from model.asset import Asset
from model.enum import Exchange
from utils.exception import SaxoException

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_saxo_client():
    """Mock SaxoClient for testing."""
    mock_client = MagicMock()

    def override_get_saxo_client():
        return mock_client

    app.dependency_overrides[get_saxo_client] = override_get_saxo_client
    yield mock_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_binance_client():
    """Mock BinanceClient for testing."""
    mock_client = MagicMock()
    mock_client.search.return_value = []

    def override_get_binance_client():
        return mock_client

    app.dependency_overrides[get_binance_client] = override_get_binance_client
    yield mock_client


@pytest.fixture(autouse=True)
def mock_ouinex_client():
    """Mock OuinexClient for testing."""
    mock_client = MagicMock()
    mock_client.search.return_value = []

    def override_get_ouinex_client():
        return mock_client

    app.dependency_overrides[get_ouinex_client] = override_get_ouinex_client
    yield mock_client


class TestSearchEndpoint:
    def test_search_success(self, mock_saxo_client, mock_binance_client):
        """Test successful search with results."""
        mock_saxo_client.search.return_value = [
            Asset(
                symbol="AAPL:xnas",
                description="Apple Inc.",
                asset_type=AssetType.STOCK,
                exchange=Exchange.SAXO,
                identifier=211,
            ),
            Asset(
                symbol="AAPL:xnys",
                description="Apple Inc.",
                asset_type=AssetType.STOCK,
                exchange=Exchange.SAXO,
                identifier=212,
            ),
        ]

        response = client.get("/api/search?keyword=AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["symbol"] == "AAPL:xnas"
        assert data["results"][0]["description"] == "Apple Inc."
        assert data["results"][0]["identifier"] == 211
        assert data["results"][0]["asset_type"] == "Stock"
        assert data["results"][0]["exchange"] == "saxo"

    def test_search_with_asset_type_filter(
        self, mock_saxo_client, mock_binance_client
    ):
        """Test search with asset type filter."""
        mock_saxo_client.search.return_value = [
            Asset(
                symbol="SPY:arcx",
                description="SPDR S&P 500 ETF Trust",
                asset_type=AssetType.ETF,
                exchange=Exchange.SAXO,
                identifier=1234,
            )
        ]

        response = client.get("/api/search?keyword=SPY&asset_type=ETF")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["asset_type"] == "Etf"
        mock_saxo_client.search.assert_called_once_with(
            keyword="SPY", asset_type="ETF"
        )

    def test_search_no_results(self, mock_saxo_client, mock_binance_client):
        """Test search that returns no results from both exchanges."""
        mock_saxo_client.search.side_effect = SaxoException(
            "Nothing found for INVALID"
        )
        mock_binance_client.search.return_value = []

        response = client.get("/api/search?keyword=INVALID")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0

    def test_search_missing_keyword(self):
        """Test search without keyword parameter."""
        response = client.get("/api/search")

        assert response.status_code == 422  # Validation error

    def test_search_empty_keyword(self):
        """Test search with empty keyword."""
        response = client.get("/api/search?keyword=")

        assert response.status_code == 422  # Validation error (min_length=1)

    def test_search_saxo_exception(
        self, mock_saxo_client, mock_binance_client
    ):
        """Test handling of SaxoException - should return binance results."""
        mock_saxo_client.search.side_effect = SaxoException("API error")
        mock_binance_client.search.return_value = [
            Asset(
                symbol="BTCUSDT",
                description="BTC/USDT",
                asset_type=AssetType.CRYPTO,
                exchange=Exchange.BINANCE,
                identifier=None,
            )
        ]

        response = client.get("/api/search?keyword=test")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["exchange"] == "binance"

    def test_search_unexpected_exception(
        self, mock_saxo_client, mock_binance_client
    ):
        """Test unexpected exception - should still return results."""
        mock_saxo_client.search.side_effect = Exception("Unexpected error")
        mock_binance_client.search.return_value = []

        response = client.get("/api/search?keyword=test")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_search_includes_ouinex_results(
        self, mock_saxo_client, mock_binance_client, mock_ouinex_client
    ):
        """Search results include Ouinex items alongside other providers."""
        mock_saxo_client.search.return_value = []
        mock_ouinex_client.search.return_value = [
            Asset(
                symbol="BTCUSD",
                description="BTC/USD",
                asset_type=AssetType.CRYPTO,
                exchange=Exchange.OUINEX,
                identifier=42,
            )
        ]

        response = client.get("/api/search?keyword=btc")

        assert response.status_code == 200
        data = response.json()
        exchanges = [item["exchange"] for item in data["results"]]
        assert "ouinex" in exchanges
        ouinex_item = next(
            item for item in data["results"] if item["exchange"] == "ouinex"
        )
        assert ouinex_item["asset_type"] == "Crypto"

    def test_search_ouinex_failure_keeps_other_results(
        self, mock_saxo_client, mock_binance_client, mock_ouinex_client
    ):
        """A Ouinex client error must not break Saxo/Binance results."""
        mock_saxo_client.search.return_value = [
            Asset(
                symbol="AAPL:xnas",
                description="Apple Inc.",
                asset_type=AssetType.STOCK,
                exchange=Exchange.SAXO,
                identifier=211,
            )
        ]
        mock_binance_client.search.return_value = [
            Asset(
                symbol="BTCUSDT",
                description="BTC/USDT",
                asset_type=AssetType.CRYPTO,
                exchange=Exchange.BINANCE,
                identifier=None,
            )
        ]
        mock_ouinex_client.search.side_effect = Exception("Ouinex down")

        response = client.get("/api/search?keyword=test")

        assert response.status_code == 200
        data = response.json()
        exchanges = {item["exchange"] for item in data["results"]}
        assert "saxo" in exchanges
        assert "binance" in exchanges
        assert "ouinex" not in exchanges
