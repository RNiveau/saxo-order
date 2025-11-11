from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_binance_client, get_saxo_client
from api.main import app
from model import AssetType
from model.asset import Asset
from utils.exception import SaxoException

client = TestClient(app)


@pytest.fixture
def mock_saxo_client():
    """Mock SaxoClient for testing."""
    mock_client = MagicMock()

    def override_get_saxo_client():
        return mock_client

    app.dependency_overrides[get_saxo_client] = override_get_saxo_client
    yield mock_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_binance_client():
    """Mock BinanceClient for testing."""
    mock_client = MagicMock()
    mock_client.search.return_value = []

    def override_get_binance_client():
        return mock_client

    app.dependency_overrides[get_binance_client] = override_get_binance_client
    yield mock_client
    app.dependency_overrides.clear()


class TestSearchEndpoint:
    def test_search_success(self, mock_saxo_client, mock_binance_client):
        """Test successful search with results."""
        mock_saxo_client.search.return_value = [
            Asset(
                symbol="AAPL:xnas",
                description="Apple Inc.",
                asset_type=AssetType.STOCK,
                exchange="saxo",
                identifier=211,
            ),
            Asset(
                symbol="AAPL:xnys",
                description="Apple Inc.",
                asset_type=AssetType.STOCK,
                exchange="saxo",
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
                exchange="saxo",
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
                exchange="binance",
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

    def test_search_multiple_results(
        self, mock_saxo_client, mock_binance_client
    ):
        """Test search returning multiple diverse results."""
        mock_saxo_client.search.return_value = [
            Asset(
                symbol="MSFT:xnas",
                description="Microsoft Corporation",
                asset_type=AssetType.STOCK,
                exchange="saxo",
                identifier=100,
            ),
            Asset(
                symbol="MSFT:xnys",
                description="Microsoft Corp",
                asset_type=AssetType.STOCK,
                exchange="saxo",
                identifier=101,
            ),
            Asset(
                symbol="MSF:xpar",
                description="Microsoft ETF",
                asset_type=AssetType.ETF,
                exchange="saxo",
                identifier=102,
            ),
        ]

        response = client.get("/api/search?keyword=MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
