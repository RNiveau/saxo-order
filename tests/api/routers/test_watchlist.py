from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.watchlist import WatchlistItem, WatchlistResponse
from api.routers.watchlist import (
    get_dynamodb_client,
    get_saxo_client,
    get_watchlist_service,
)
from model import Currency

client = TestClient(app)


@pytest.fixture
def mock_saxo_client():
    """Mock SaxoClient."""
    mock_client = MagicMock()

    # Default mock behavior - return asset with description
    mock_client.get_asset.return_value = {
        "Identifier": 123,
        "AssetType": "Stock",
        "Symbol": "ITP:xpar",
        "Description": "Interparfums SA",
        "CurrencyCode": "EUR",
    }

    def override_get_saxo_client():
        return mock_client

    app.dependency_overrides[get_saxo_client] = override_get_saxo_client
    yield mock_client
    app.dependency_overrides.clear()


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
                description="Interparfums SA",
                country_code="xpar",
                current_price=100.0,
                variation_pct=5.0,
                currency=Currency.EURO,
                added_at="2024-01-01T00:00:00Z",
                labels=[],
            ),
            WatchlistItem(
                id="2",
                asset_symbol="DAX.I:xetr",
                description="DAX Index",
                country_code="xetr",
                current_price=15000.0,
                variation_pct=-2.5,
                currency=Currency.EURO,
                added_at="2024-01-02T00:00:00Z",
                labels=["short-term"],
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

    def test_add_to_watchlist_success(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test successfully adding an asset to watchlist."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "123",
                "asset_symbol": "itp:xpar",
                "description": "Interparfums SA",
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
        assert "Interparfums SA" in data["message"]

        # Verify Saxo client was called to fetch asset
        mock_saxo_client.get_asset.assert_called_once_with("123", "xpar")

        # Verify DynamoDB client was called correctly with fetched description
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "123",
            "itp:xpar",
            "Interparfums SA",
            "xpar",
            asset_identifier=123,
            asset_type="Stock",
            labels=[],
            exchange="saxo",
        )

    def test_add_to_watchlist_with_default_country_code(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test adding asset with default country code."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "456",
                "asset_symbol": "aapl:xnas",
                "description": "Apple Inc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "456"
        assert data["asset_symbol"] == "aapl:xnas"

        # Verify Saxo client was called with default country code
        mock_saxo_client.get_asset.assert_called_once_with("456", "xpar")

        # Verify default country code was used
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "456",
            "aapl:xnas",
            "Interparfums SA",
            "xpar",
            asset_identifier=123,
            asset_type="Stock",
            labels=[],
            exchange="saxo",
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
            json={
                "asset_symbol": "itp:xpar",
                "description": "Test",
                "country_code": "xpar",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_add_to_watchlist_missing_asset_symbol(self):
        """Test request with missing asset_symbol."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "123",
                "description": "Test",
                "country_code": "xpar",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_add_to_watchlist_unexpected_error(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test handling of unexpected errors."""
        mock_dynamodb_client.add_to_watchlist.side_effect = Exception(
            "DynamoDB error"
        )

        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "789",
                "asset_symbol": "test:xpar",
                "description": "Test Asset",
                "country_code": "xpar",
            },
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_add_to_watchlist_various_asset_symbols(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test adding various types of asset symbols."""
        test_cases = [
            ("1", "itp:xpar", "Interparfums SA", "xpar"),
            ("2", "DAX.I:xetr", "DAX Index", "xetr"),
            ("3", "aapl:xnas", "Apple Inc", "xnas"),
            ("4", "btcusd:crypto", "Bitcoin USD", "crypto"),
        ]

        for asset_id, asset_symbol, description, country_code in test_cases:
            response = client.post(
                "/api/watchlist",
                json={
                    "asset_id": asset_id,
                    "asset_symbol": asset_symbol,
                    "description": description,
                    "country_code": country_code,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["asset_id"] == asset_id
            assert data["asset_symbol"] == asset_symbol

    def test_add_to_watchlist_duplicate_asset(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test adding the same asset twice.

        Should succeed - DynamoDB put_item overwrites existing items.
        """
        request_data = {
            "asset_id": "123",
            "asset_symbol": "itp:xpar",
            "description": "Interparfums SA",
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

    def test_add_to_watchlist_with_labels(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test adding asset with labels."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "123",
                "asset_symbol": "itp:xpar",
                "description": "Interparfums SA",
                "country_code": "xpar",
                "labels": ["short-term"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "123"

        # Verify labels were passed to DynamoDB
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "123",
            "itp:xpar",
            "Interparfums SA",
            "xpar",
            asset_identifier=123,
            asset_type="Stock",
            labels=["short-term"],
            exchange="saxo",
        )

    def test_update_labels_success(self, mock_dynamodb_client):
        """Test successfully updating labels for a watchlist item."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.update_watchlist_labels.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        response = client.patch(
            "/api/watchlist/123/labels",
            json={"labels": ["short-term"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Labels updated successfully"
        assert data["asset_id"] == "123"
        assert data["labels"] == ["short-term"]

        # Verify methods were called
        mock_dynamodb_client.is_in_watchlist.assert_called_once_with("123")
        mock_dynamodb_client.update_watchlist_labels.assert_called_once_with(
            "123", ["short-term"]
        )

    def test_update_labels_not_found(self, mock_dynamodb_client):
        """Test updating labels for non-existent watchlist item."""
        mock_dynamodb_client.is_in_watchlist.return_value = False

        response = client.patch(
            "/api/watchlist/999/labels",
            json={"labels": ["short-term"]},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Asset not found in watchlist"

    def test_update_labels_empty_list(self, mock_dynamodb_client):
        """Test updating labels with empty list (removing all labels)."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.update_watchlist_labels.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        response = client.patch(
            "/api/watchlist/123/labels",
            json={"labels": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["labels"] == []

        mock_dynamodb_client.update_watchlist_labels.assert_called_once_with(
            "123", []
        )

    def test_update_labels_multiple_labels(self, mock_dynamodb_client):
        """Test updating with multiple labels."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.update_watchlist_labels.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        response = client.patch(
            "/api/watchlist/123/labels",
            json={"labels": ["short-term", "high-priority", "tech"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["labels"] == ["short-term", "high-priority", "tech"]

    def test_get_all_watchlist_success(self, mock_watchlist_service):
        """Test retrieval of all watchlist items including long-term."""
        mock_watchlist_service.get_all_watchlist.return_value = (
            WatchlistResponse(
                items=[
                    WatchlistItem(
                        id="1",
                        asset_symbol="itp:xpar",
                        description="Interparfums SA",
                        country_code="xpar",
                        current_price=100.0,
                        variation_pct=5.0,
                        currency=Currency.EURO,
                        added_at="2024-01-01T00:00:00Z",
                        labels=["short-term"],
                    ),
                    WatchlistItem(
                        id="2",
                        asset_symbol="aapl:xnas",
                        description="Apple Inc",
                        country_code="xnas",
                        current_price=150.0,
                        variation_pct=2.0,
                        currency=Currency.USD,
                        added_at="2024-01-02T00:00:00Z",
                        labels=["long-term"],
                    ),
                ],
                total=2,
            )
        )

        response = client.get("/api/watchlist/all")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Verify both short-term and long-term items are included
        items = {item["id"]: item for item in data["items"]}
        assert "1" in items
        assert "2" in items
        assert items["1"]["labels"] == ["short-term"]
        assert items["2"]["labels"] == ["long-term"]

        mock_watchlist_service.get_all_watchlist.assert_called_once()

    def test_get_watchlist_excludes_long_term(self, mock_watchlist_service):
        """Test that watchlist endpoint excludes long-term assets."""
        # Mock service to return mixed items - simulating what the service
        # would return AFTER filtering out long-term tags
        mock_watchlist_service.get_watchlist.return_value = WatchlistResponse(
            items=[
                WatchlistItem(
                    id="short1",
                    asset_symbol="itp:xpar",
                    description="Interparfums SA",
                    country_code="xpar",
                    current_price=100.0,
                    variation_pct=5.0,
                    currency=Currency.EURO,
                    added_at="2024-01-01T00:00:00Z",
                    labels=["short-term"],
                ),
                WatchlistItem(
                    id="none1",
                    asset_symbol="googl:xnas",
                    description="Alphabet Inc",
                    country_code="xnas",
                    current_price=150.0,
                    variation_pct=2.0,
                    currency=Currency.USD,
                    added_at="2024-01-04T00:00:00Z",
                    labels=[],
                ),
            ],
            total=2,
        )

        # Mock get_all_watchlist to show what items exist in DB
        mock_watchlist_service.get_all_watchlist.return_value = (
            WatchlistResponse(
                items=[
                    WatchlistItem(
                        id="short1",
                        asset_symbol="itp:xpar",
                        description="Interparfums SA",
                        country_code="xpar",
                        current_price=100.0,
                        variation_pct=5.0,
                        currency=Currency.EURO,
                        added_at="2024-01-01T00:00:00Z",
                        labels=["short-term"],
                    ),
                    WatchlistItem(
                        id="long1",
                        asset_symbol="aapl:xnas",
                        description="Apple Inc",
                        country_code="xnas",
                        current_price=180.0,
                        variation_pct=1.5,
                        currency=Currency.USD,
                        added_at="2024-01-02T00:00:00Z",
                        labels=["long-term"],
                    ),
                    WatchlistItem(
                        id="both1",
                        asset_symbol="msft:xnas",
                        description="Microsoft Corp",
                        country_code="xnas",
                        current_price=380.0,
                        variation_pct=0.8,
                        currency=Currency.USD,
                        added_at="2024-01-03T00:00:00Z",
                        labels=["short-term", "long-term"],
                    ),
                    WatchlistItem(
                        id="none1",
                        asset_symbol="googl:xnas",
                        description="Alphabet Inc",
                        country_code="xnas",
                        current_price=150.0,
                        variation_pct=2.0,
                        currency=Currency.USD,
                        added_at="2024-01-04T00:00:00Z",
                        labels=[],
                    ),
                ],
                total=4,
            )
        )

        # Test regular endpoint - should exclude long-term
        response = client.get("/api/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        returned_ids = {item["id"] for item in data["items"]}
        assert "short1" in returned_ids
        assert "none1" in returned_ids
        assert "long1" not in returned_ids
        assert "both1" not in returned_ids

        # Test /all endpoint - should include everything
        response_all = client.get("/api/watchlist/all")
        assert response_all.status_code == 200
        data_all = response_all.json()
        assert data_all["total"] == 4
        all_ids = {item["id"] for item in data_all["items"]}
        assert "short1" in all_ids
        assert "long1" in all_ids
        assert "both1" in all_ids
        assert "none1" in all_ids

    def test_add_to_watchlist_with_long_term_label(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test adding asset with long-term label."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "456",
                "asset_symbol": "msft:xnas",
                "description": "Microsoft Corp",
                "country_code": "xnas",
                "labels": ["long-term"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "456"

        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "456",
            "msft:xnas",
            "Interparfums SA",
            "xnas",
            asset_identifier=123,
            asset_type="Stock",
            labels=["long-term"],
            exchange="saxo",
        )

    def test_add_binance_asset_auto_adds_crypto_tag(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test that adding a Binance asset automatically adds crypto tag."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "BTCUSDT",
                "asset_symbol": "BTCUSDT",
                "description": "BTC/USDT",
                "country_code": "",
                "exchange": "binance",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "BTCUSDT"

        # Binance assets should NOT call Saxo client
        mock_saxo_client.get_asset.assert_not_called()

        # Should use provided description and set asset_type to Crypto
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "BTCUSDT",
            "BTCUSDT",
            "BTC/USDT",
            "",
            asset_identifier=None,
            asset_type="Crypto",
            labels=["crypto"],
            exchange="binance",
        )

    def test_add_binance_asset_preserves_existing_labels(
        self, mock_saxo_client, mock_dynamodb_client
    ):
        """Test that crypto tag is added while preserving other labels."""
        response = client.post(
            "/api/watchlist",
            json={
                "asset_id": "ETHUSDT",
                "asset_symbol": "ETHUSDT",
                "description": "ETH/USDT",
                "country_code": "",
                "exchange": "binance",
                "labels": ["short-term"],
            },
        )

        assert response.status_code == 200

        # Binance assets should NOT call Saxo client
        mock_saxo_client.get_asset.assert_not_called()

        # Should use provided description and preserve existing labels
        mock_dynamodb_client.add_to_watchlist.assert_called_once_with(
            "ETHUSDT",
            "ETHUSDT",
            "ETH/USDT",
            "",
            asset_identifier=None,
            asset_type="Crypto",
            labels=["short-term", "crypto"],
            exchange="binance",
        )

    def test_update_labels_with_both_tags(self, mock_dynamodb_client):
        """Test updating labels with both short-term and long-term tags."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.update_watchlist_labels.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        response = client.patch(
            "/api/watchlist/123/labels",
            json={"labels": ["short-term", "long-term"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["labels"] == ["short-term", "long-term"]

        mock_dynamodb_client.update_watchlist_labels.assert_called_once_with(
            "123", ["short-term", "long-term"]
        )

    def test_update_labels_homepage_limit_enforced(self, mock_dynamodb_client):
        """Test that 6-asset limit is enforced for homepage tag."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "asset1",
                "asset_symbol": "asset1:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset2",
                "asset_symbol": "asset2:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset3",
                "asset_symbol": "asset3:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset4",
                "asset_symbol": "asset4:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset5",
                "asset_symbol": "asset5:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset6",
                "asset_symbol": "asset6:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset7",
                "asset_symbol": "asset7:xpar",
                "labels": ["short-term"],
            },
        ]

        response = client.patch(
            "/api/watchlist/asset7/labels",
            json={"labels": ["homepage", "short-term"]},
        )

        assert response.status_code == 400
        data = response.json()
        assert "maximum of 6 assets allowed" in data["detail"].lower()
        mock_dynamodb_client.update_watchlist_labels.assert_not_called()

    def test_update_labels_homepage_limit_allows_existing(
        self, mock_dynamodb_client
    ):
        """Test that existing homepage assets can update their labels."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "asset1",
                "asset_symbol": "asset1:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset2",
                "asset_symbol": "asset2:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset3",
                "asset_symbol": "asset3:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset4",
                "asset_symbol": "asset4:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset5",
                "asset_symbol": "asset5:xpar",
                "labels": ["homepage"],
            },
            {
                "id": "asset6",
                "asset_symbol": "asset6:xpar",
                "labels": ["homepage", "short-term"],
            },
        ]

        response = client.patch(
            "/api/watchlist/asset6/labels",
            json={"labels": ["homepage", "long-term"]},
        )

        assert response.status_code == 200
        mock_dynamodb_client.update_watchlist_labels.assert_called_once_with(
            "asset6", ["homepage", "long-term"]
        )

    def test_update_labels_homepage_removal_works(self, mock_dynamodb_client):
        """Test that removing homepage tag works."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "asset1",
                "asset_symbol": "asset1:xpar",
                "labels": ["homepage"],
            }
        ]

        response = client.patch(
            "/api/watchlist/asset1/labels",
            json={"labels": ["short-term"]},
        )

        assert response.status_code == 200
        mock_dynamodb_client.update_watchlist_labels.assert_called_once_with(
            "asset1", ["short-term"]
        )

    def test_update_labels_homepage_with_other_tags(
        self, mock_dynamodb_client
    ):
        """Test that homepage tag can coexist with other tags."""
        mock_dynamodb_client.is_in_watchlist.return_value = True
        mock_dynamodb_client.get_watchlist.return_value = []

        response = client.patch(
            "/api/watchlist/asset1/labels",
            json={"labels": ["homepage", "short-term", "crypto"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "homepage" in data["labels"]
        assert "short-term" in data["labels"]
        assert "crypto" in data["labels"]
        mock_dynamodb_client.update_watchlist_labels.assert_called_once_with(
            "asset1", ["homepage", "short-term", "crypto"]
        )


class TestGetLongTermPositions:
    """Tests for GET /api/watchlist/long-term endpoint."""

    def test_get_long_term_endpoint_returns_200(
        self, mock_dynamodb_client, mock_saxo_client
    ):
        """Test that GET /api/watchlist/long-term returns 200 with items."""
        # Setup: Mock DynamoDB to return long-term items
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "long1",
                "asset_symbol": "itp:xpar",
                "description": "Interparfums",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["long-term"],
                "asset_identifier": 123,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute: Call endpoint
        response = client.get("/api/watchlist/long-term")

        # Assert: Success response
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "long1"

    def test_get_long_term_endpoint_empty_response(
        self, mock_dynamodb_client, mock_saxo_client
    ):
        """Test that GET /api/watchlist/long-term returns empty when no
        long-term items."""
        # Setup: Mock DynamoDB to return no long-term items
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "short1",
                "asset_symbol": "aapl:xnas",
                "description": "Apple",
                "country_code": "xnas",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["short-term"],
                "asset_identifier": 456,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute
        response = client.get("/api/watchlist/long-term")

        # Assert: Empty result
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
