from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.watchlist import WatchlistItem, WatchlistResponse
from api.routers.watchlist import get_dynamodb_client, get_watchlist_service

client = TestClient(app)


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDBClient."""
    mock_client = MagicMock()

    # Default mock behavior - successful addition
    mock_client.add_to_watchlist.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }

    def override_get_dynamodb_client():
        return mock_client

    app.dependency_overrides[get_dynamodb_client] = (
        override_get_dynamodb_client
    )
    yield mock_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_watchlist_service():
    """Mock WatchlistService."""
    mock_service = MagicMock()

    # Default mock data
    mock_service.get_watchlist.return_value = WatchlistResponse(
        items=[
            WatchlistItem(
                id="1",
                asset_symbol="itp:xpar",
                country_code="xpar",
                current_price=100.0,
                variation_pct=5.0,
                added_at="2024-01-01T00:00:00Z",
            ),
            WatchlistItem(
                id="2",
                asset_symbol="DAX.I:xetr",
                country_code="xetr",
                current_price=15000.0,
                variation_pct=-2.5,
                added_at="2024-01-02T00:00:00Z",
            ),
        ],
        total=2,
    )

    def override_get_watchlist_service():
        return mock_service

    app.dependency_overrides[get_watchlist_service] = (
        override_get_watchlist_service
    )
    yield mock_service
    app.dependency_overrides.clear()


class TestWatchlistEndpoint:
    def test_get_watchlist_success(self, mock_watchlist_service):
        """Test successful retrieval of watchlist."""
        response = client.get("/api/watchlist")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "items" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Check first item
        item1 = data["items"][0]
        assert item1["id"] == "1"
        assert item1["asset_symbol"] == "itp:xpar"
        assert item1["current_price"] == 100.0
        assert item1["variation_pct"] == 5.0

        # Verify service was called
        mock_watchlist_service.get_watchlist.assert_called_once()

    def test_get_watchlist_empty(self, mock_watchlist_service):
        """Test retrieval of empty watchlist."""
        mock_watchlist_service.get_watchlist.return_value = WatchlistResponse(
            items=[], total=0
        )

        response = client.get("/api/watchlist")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_watchlist_unexpected_error(self, mock_watchlist_service):
        """Test handling of unexpected errors in get watchlist."""
        mock_watchlist_service.get_watchlist.side_effect = Exception(
            "Database error"
        )

        response = client.get("/api/watchlist")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_add_to_watchlist_success(self, mock_dynamodb_client):
        """Test successfully adding an asset to watchlist."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "123",
                "asset_symbol": "itp:xpar",
                "country_code": "xpar",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "message" in data
        assert "asset_id" in data
        assert "asset_symbol" in data

        # Check response values
        assert data["asset_id"] == "123"
        assert data["asset_symbol"] == "itp:xpar"
        assert "itp:xpar" in data["message"]

        # Verify DynamoDB client was called correctly
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "123", "itp:xpar", "xpar"
        )

    def test_add_to_watchlist_with_default_country_code(
        self, mock_dynamodb_client
    ):
        """Test adding asset with default country code."""
        response = client.post(
            "/api/watchlist",
            json={"asset_id": "456", "asset_symbol": "aapl:xnas"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "456"
        assert data["asset_symbol"] == "aapl:xnas"

        # Verify default country code was used
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "456", "aapl:xnas", "xpar"
        )

    def test_add_to_watchlist_missing_required_fields(self):
        """Test request with missing required fields."""
        # Missing asset_id and asset_symbol
        response = client.post("/api/watchlist", json={})

        assert response.status_code == 422  # Validation error

    def test_add_to_watchlist_missing_asset_id(self):
        """Test request with missing asset_id."""
        response = client.post(
            "/api/watchlist",
            json={"asset_symbol": "itp:xpar", "country_code": "xpar"},
        )

        assert response.status_code == 422  # Validation error

    def test_add_to_watchlist_missing_asset_symbol(self):
        """Test request with missing asset_symbol."""
        response = client.post(
            "/api/watchlist",
            json={"asset_id": "123", "country_code": "xpar"},
        )

        assert response.status_code == 422  # Validation error

    def test_add_to_watchlist_unexpected_error(self, mock_dynamodb_client):
        """Test handling of unexpected errors."""
        mock_dynamodb_client.add_to_watchlist.side_effect = Exception(
            "DynamoDB error"
        )

        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "789",
                "asset_symbol": "test:xpar",
                "country_code": "xpar",
            },
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_add_to_watchlist_various_asset_symbols(
        self, mock_dynamodb_client
    ):
        """Test adding various types of asset symbols."""
        test_cases = [
            ("1", "itp:xpar", "xpar"),
            ("2", "DAX.I:xetr", "xetr"),
            ("3", "aapl:xnas", "xnas"),
            ("4", "btcusd:crypto", "crypto"),
        ]

        for asset_id, asset_symbol, country_code in test_cases:
            response = client.post(
                "/api/watchlist",
                json={
                    "asset_id": asset_id,
                    "asset_symbol": asset_symbol,
                    "country_code": country_code,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["asset_id"] == asset_id
            assert data["asset_symbol"] == asset_symbol

    def test_add_to_watchlist_duplicate_asset(self, mock_dynamodb_client):
        """Test adding the same asset twice.

        Should succeed - DynamoDB put_item overwrites existing items.
        """
        request_data = {
            "asset_id": "123",
            "asset_symbol": "itp:xpar",
            "country_code": "xpar",
        }

        # First addition
        response1 = client.post("/api/watchlist", json=request_data)
        assert response1.status_code == 200

        # Second addition (same asset)
        response2 = client.post("/api/watchlist", json=request_data)
        assert response2.status_code == 200

        # Both should succeed
        assert mock_dynamodb_client.add_to_watchlist.call_count == 2
