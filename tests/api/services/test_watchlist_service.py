from unittest.mock import MagicMock

import pytest

from api.models.watchlist import WatchlistTag
from api.services.watchlist_service import WatchlistService
from client.aws_client import DynamoDBClient


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDBClient."""
    return MagicMock(spec=DynamoDBClient)


@pytest.fixture
def mock_indicator_service():
    """Mock IndicatorService."""
    mock_service = MagicMock()
    # Mock get_price_and_variation to return consistent values
    mock_service.get_price_and_variation.return_value = (100.0, 5.0)
    # Mock saxo_client.get_asset
    mock_service.saxo_client.get_asset.return_value = {
        "Description": "Test Asset",
        "CurrencyCode": "EUR",
    }
    return mock_service


@pytest.fixture
def watchlist_service(mock_dynamodb_client, mock_indicator_service):
    """Create WatchlistService with mocked dependencies."""
    return WatchlistService(mock_dynamodb_client, mock_indicator_service)


class TestWatchlistServiceFiltering:
    def test_get_watchlist_excludes_long_term(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test that get_watchlist filters out long-term tagged assets."""
        # Setup: DynamoDB returns items with various label combinations
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "short1",
                "asset_symbol": "itp:xpar",
                "description": "Short-term asset",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["short-term"],
                "asset_identifier": 123,
                "asset_type": "Stock",
            },
            {
                "id": "long1",
                "asset_symbol": "aapl:xnas",
                "description": "Long-term asset",
                "country_code": "xnas",
                "added_at": "2024-01-02T00:00:00Z",
                "labels": ["long-term"],
                "asset_identifier": 456,
                "asset_type": "Stock",
            },
            {
                "id": "both1",
                "asset_symbol": "msft:xnas",
                "description": "Both tags asset",
                "country_code": "xnas",
                "added_at": "2024-01-03T00:00:00Z",
                "labels": ["short-term", "long-term"],
                "asset_identifier": 789,
                "asset_type": "Stock",
            },
            {
                "id": "none1",
                "asset_symbol": "googl:xnas",
                "description": "No tags asset",
                "country_code": "xnas",
                "added_at": "2024-01-04T00:00:00Z",
                "labels": [],
                "asset_identifier": 101,
                "asset_type": "Stock",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute: Call get_watchlist
        result = watchlist_service.get_watchlist()

        # Assert: Only items without long-term tag are returned
        assert result.total == 2
        assert len(result.items) == 2

        returned_ids = {item.id for item in result.items}
        # Items with short-term only and no tags should be included
        assert "short1" in returned_ids
        assert "none1" in returned_ids
        # Items with long-term tag should be excluded
        assert "long1" not in returned_ids
        # Items with BOTH tags should be excluded (long-term takes precedence)
        assert "both1" not in returned_ids

    def test_get_all_watchlist_includes_all_items(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test that get_all_watchlist returns all items."""
        # Setup: Same data as above
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "short1",
                "asset_symbol": "itp:xpar",
                "description": "Short-term asset",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["short-term"],
                "asset_identifier": 123,
                "asset_type": "Stock",
            },
            {
                "id": "long1",
                "asset_symbol": "aapl:xnas",
                "description": "Long-term asset",
                "country_code": "xnas",
                "added_at": "2024-01-02T00:00:00Z",
                "labels": ["long-term"],
                "asset_identifier": 456,
                "asset_type": "Stock",
            },
            {
                "id": "both1",
                "asset_symbol": "msft:xnas",
                "description": "Both tags asset",
                "country_code": "xnas",
                "added_at": "2024-01-03T00:00:00Z",
                "labels": ["short-term", "long-term"],
                "asset_identifier": 789,
                "asset_type": "Stock",
            },
            {
                "id": "none1",
                "asset_symbol": "googl:xnas",
                "description": "No tags asset",
                "country_code": "xnas",
                "added_at": "2024-01-04T00:00:00Z",
                "labels": [],
                "asset_identifier": 101,
                "asset_type": "Stock",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute: Call get_all_watchlist
        result = watchlist_service.get_all_watchlist()

        # Assert: ALL items are returned
        assert result.total == 4
        assert len(result.items) == 4

        returned_ids = {item.id for item in result.items}
        assert "short1" in returned_ids
        assert "long1" in returned_ids
        assert "both1" in returned_ids
        assert "none1" in returned_ids

    def test_filtering_uses_enum_value(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test that filtering uses WatchlistTag enum value."""
        # Setup: Item with long-term tag
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "test1",
                "asset_symbol": "test:xpar",
                "description": "Test",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": [WatchlistTag.LONG_TERM.value],
                "asset_identifier": 123,
                "asset_type": "Stock",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute
        result = watchlist_service.get_watchlist()

        # Assert: Item is filtered out
        assert result.total == 0
        assert len(result.items) == 0

    def test_get_watchlist_excludes_crypto_without_short_term(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test crypto assets without short-term tag excluded from sidebar."""
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "crypto1",
                "asset_symbol": "BTCUSDT",
                "description": "BTC/USDT",
                "country_code": "",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["crypto"],
                "asset_identifier": None,
                "asset_type": None,
                "exchange": "binance",
            },
            {
                "id": "crypto_short",
                "asset_symbol": "ETHUSDT",
                "description": "ETH/USDT",
                "country_code": "",
                "added_at": "2024-01-02T00:00:00Z",
                "labels": ["crypto", "short-term"],
                "asset_identifier": None,
                "asset_type": None,
                "exchange": "binance",
            },
            {
                "id": "saxo1",
                "asset_symbol": "itp:xpar",
                "description": "Interparfums",
                "country_code": "xpar",
                "added_at": "2024-01-03T00:00:00Z",
                "labels": [],
                "asset_identifier": 123,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        result = watchlist_service.get_watchlist()

        assert result.total == 2
        returned_ids = {item.id for item in result.items}
        assert "crypto_short" in returned_ids
        assert "saxo1" in returned_ids
        assert "crypto1" not in returned_ids

    def test_get_all_watchlist_includes_crypto_assets(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test that get_all_watchlist includes all crypto assets."""
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "crypto1",
                "asset_symbol": "BTCUSDT",
                "description": "BTC/USDT",
                "country_code": "",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["crypto"],
                "asset_identifier": None,
                "asset_type": None,
                "exchange": "binance",
            },
            {
                "id": "crypto_short",
                "asset_symbol": "ETHUSDT",
                "description": "ETH/USDT",
                "country_code": "",
                "added_at": "2024-01-02T00:00:00Z",
                "labels": ["crypto", "short-term"],
                "asset_identifier": None,
                "asset_type": None,
                "exchange": "binance",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        result = watchlist_service.get_all_watchlist()

        assert result.total == 2
        returned_ids = {item.id for item in result.items}
        assert "crypto1" in returned_ids
        assert "crypto_short" in returned_ids

    def test_get_long_term_positions_filters_correctly(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test that get_long_term_positions returns only long-term
        tagged assets."""
        # Setup: DynamoDB returns items with various label combinations
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "long1",
                "asset_symbol": "itp:xpar",
                "description": "Long-term asset 1",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["long-term", "homepage"],
                "asset_identifier": 123,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
            {
                "id": "short1",
                "asset_symbol": "aapl:xnas",
                "description": "Short-term asset",
                "country_code": "xnas",
                "added_at": "2024-01-02T00:00:00Z",
                "labels": ["short-term"],
                "asset_identifier": 456,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
            {
                "id": "long2",
                "asset_symbol": "btcusdt",
                "description": "Bitcoin",
                "country_code": "",
                "added_at": "2024-01-03T00:00:00Z",
                "labels": ["long-term", "crypto"],
                "asset_identifier": None,
                "asset_type": None,
                "exchange": "binance",
            },
            {
                "id": "none1",
                "asset_symbol": "googl:xnas",
                "description": "No tags asset",
                "country_code": "xnas",
                "added_at": "2024-01-04T00:00:00Z",
                "labels": [],
                "asset_identifier": 789,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute: Call get_long_term_positions
        result = watchlist_service.get_long_term_positions()

        # Assert: Only items with long-term tag are returned
        assert result.total == 2
        assert len(result.items) == 2

        returned_ids = {item.id for item in result.items}
        assert "long1" in returned_ids
        assert "long2" in returned_ids
        assert "short1" not in returned_ids
        assert "none1" not in returned_ids

    def test_get_long_term_positions_empty_when_no_items(
        self, watchlist_service, mock_dynamodb_client
    ):
        """Test that get_long_term_positions returns empty when no
        long-term items exist."""
        # Setup: DynamoDB returns items without long-term tag
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "short1",
                "asset_symbol": "itp:xpar",
                "description": "Short-term only",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["short-term"],
                "asset_identifier": 123,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute
        result = watchlist_service.get_long_term_positions()

        # Assert: Empty result
        assert result.total == 0
        assert len(result.items) == 0

    def test_get_long_term_positions_enriches_prices(
        self, watchlist_service, mock_dynamodb_client, mock_indicator_service
    ):
        """Test that get_long_term_positions enriches items with prices."""
        # Setup: DynamoDB returns long-term items
        mock_dynamodb_client.get_watchlist.return_value = [
            {
                "id": "long1",
                "asset_symbol": "itp:xpar",
                "description": "Test Asset",
                "country_code": "xpar",
                "added_at": "2024-01-01T00:00:00Z",
                "labels": ["long-term"],
                "asset_identifier": 123,
                "asset_type": "Stock",
                "exchange": "saxo",
            },
        ]

        mock_dynamodb_client.get_tradingview_link.return_value = None

        # Execute
        result = watchlist_service.get_long_term_positions()

        # Assert: Item is enriched with price data
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].current_price == 100.0
        assert result.items[0].variation_pct == 5.0
