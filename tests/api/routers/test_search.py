from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.search import get_saxo_client
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


class TestSearchEndpoint:
    def test_search_success(self, mock_saxo_client):
        """Test successful search with results."""
        # Mock search response
        mock_saxo_client.search.return_value = [
            {
                "Symbol": "AAPL:xnas",
                "Description": "Apple Inc.",
                "Identifier": 211,
                "AssetType": "Stock",
            },
            {
                "Symbol": "AAPL:xnys",
                "Description": "Apple Inc.",
                "Identifier": 212,
                "AssetType": "Stock",
            },
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

    def test_search_with_asset_type_filter(self, mock_saxo_client):
        """Test search with asset type filter."""
        mock_saxo_client.search.return_value = [
            {
                "Symbol": "SPY:arcx",
                "Description": "SPDR S&P 500 ETF Trust",
                "Identifier": 1234,
                "AssetType": "ETF",
            }
        ]

        response = client.get("/api/search?keyword=SPY&asset_type=ETF")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["asset_type"] == "ETF"
        mock_saxo_client.search.assert_called_once_with(
            keyword="SPY", asset_type="ETF"
        )

    def test_search_no_results(self, mock_saxo_client):
        """Test search that returns no results (SaxoException)."""
        # Mock SaxoException for no results
        mock_saxo_client.search.side_effect = SaxoException(
            "Nothing found for INVALID"
        )

        response = client.get("/api/search?keyword=INVALID")

        assert response.status_code == 400
        assert "Nothing found for INVALID" in response.json()["detail"]

    def test_search_missing_keyword(self):
        """Test search without keyword parameter."""
        response = client.get("/api/search")

        assert response.status_code == 422  # Validation error

    def test_search_empty_keyword(self):
        """Test search with empty keyword."""
        response = client.get("/api/search?keyword=")

        assert response.status_code == 422  # Validation error (min_length=1)

    def test_search_saxo_exception(self, mock_saxo_client):
        """Test handling of SaxoException."""
        mock_saxo_client.search.side_effect = SaxoException("API error")

        response = client.get("/api/search?keyword=test")

        assert response.status_code == 400
        assert "API error" in response.json()["detail"]

    def test_search_unexpected_exception(self, mock_saxo_client):
        """Test handling of unexpected exception."""
        mock_saxo_client.search.side_effect = Exception("Unexpected error")

        response = client.get("/api/search?keyword=test")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_search_multiple_results(self, mock_saxo_client):
        """Test search returning multiple diverse results."""
        mock_saxo_client.search.return_value = [
            {
                "Symbol": "MSFT:xnas",
                "Description": "Microsoft Corporation",
                "Identifier": 100,
                "AssetType": "Stock",
            },
            {
                "Symbol": "MSFT:xnys",
                "Description": "Microsoft Corp",
                "Identifier": 101,
                "AssetType": "Stock",
            },
            {
                "Symbol": "MSF:xpar",
                "Description": "Microsoft ETF",
                "Identifier": 102,
                "AssetType": "ETF",
            },
        ]

        response = client.get("/api/search?keyword=MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
