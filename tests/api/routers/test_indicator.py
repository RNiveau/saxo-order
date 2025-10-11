import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.indicator import get_saxo_client
from utils.exception import SaxoException

client = TestClient(app)


@pytest.fixture
def mock_saxo_client():
    """Mock SaxoClient with get_asset and get_historical_data methods."""
    mock_client = MagicMock()
    mock_client.get_asset.return_value = {
        "Identifier": 123,
        "AssetType": "Stock",
        "Symbol": "ITP:xpar",
    }

    def override_get_saxo_client():
        return mock_client

    app.dependency_overrides[get_saxo_client] = override_get_saxo_client
    yield mock_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_historical_data():
    """Generate mock historical data with 210 candles."""
    data = []
    base_price = 100.0

    for i in range(210):
        # Create a simple price pattern
        price = base_price + (i * 0.1)
        data.append(
            {
                "Time": datetime.datetime(2024, 1, 1, 0, 0, 0)
                + datetime.timedelta(days=210 - i),
                "Open": price,
                "High": price + 1,
                "Low": price - 1,
                "Close": price,
            }
        )

    return data


class TestIndicatorEndpoint:
    def test_get_asset_indicators_success(
        self, mock_saxo_client, mock_historical_data
    ):
        """Test successful retrieval of indicators for an asset."""
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response = client.get("/api/indicator/asset/itp?country_code=xpar")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "asset_symbol" in data
        assert "current_price" in data
        assert "variation_pct" in data
        assert "unit_time" in data
        assert "moving_averages" in data

        # Check asset symbol and unit_time
        assert data["asset_symbol"] == "itp:xpar"
        assert data["unit_time"] == "daily"

        # Check we have all 4 moving averages
        assert len(data["moving_averages"]) == 4
        ma_periods = [ma["period"] for ma in data["moving_averages"]]
        assert sorted(ma_periods) == [7, 20, 50, 200]

        # Check each MA has required fields
        for ma in data["moving_averages"]:
            assert "period" in ma
            assert "value" in ma
            assert "is_above" in ma
            assert "unit_time" in ma
            assert ma["unit_time"] == "daily"
            assert isinstance(ma["is_above"], bool)
            assert isinstance(ma["value"], (int, float))

        # Verify SaxoClient was called correctly
        mock_saxo_client.get_asset.assert_called_once_with("itp", "xpar")
        mock_saxo_client.get_historical_data.assert_called_once_with(
            saxo_uic=123, asset_type="Stock", horizon=1440, count=210
        )

    def test_get_asset_indicators_with_default_country_code(
        self, mock_saxo_client, mock_historical_data
    ):
        """Test indicator retrieval with default country_code."""
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_symbol"] == "itp:xpar"
        mock_saxo_client.get_asset.assert_called_once_with("itp", "xpar")

    def test_get_asset_indicators_insufficient_data(self, mock_saxo_client):
        """Test when there's insufficient historical data."""
        # Return only 50 candles (need 200 for MA200)
        short_data = []
        for i in range(50):
            short_data.append(
                {
                    "Time": datetime.datetime(2024, 1, 1, 0, 0, 0)
                    + datetime.timedelta(days=50 - i),
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.0,
                }
            )

        mock_saxo_client.get_historical_data.return_value = short_data

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 400
        assert "Insufficient data" in response.json()["detail"]

    def test_get_asset_indicators_asset_not_found(self, mock_saxo_client):
        """Test when asset is not found."""
        mock_saxo_client.get_asset.side_effect = SaxoException(
            "Stock itp:xpar doesn't exist"
        )

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 400
        assert "doesn't exist" in response.json()["detail"]

    def test_get_asset_indicators_unexpected_error(self, mock_saxo_client):
        """Test handling of unexpected errors."""
        mock_saxo_client.get_asset.side_effect = Exception("Network error")

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_get_asset_indicators_price_above_below_ma(
        self, mock_saxo_client, mock_historical_data
    ):
        """Test is_above flag reflects price position relative to MA."""
        # Modify data so current price (newest candle) is clearly positioned
        # Current price will be at index 0 after sorting
        modified_data = mock_historical_data.copy()
        modified_data[0]["Close"] = 120.0  # High current price

        mock_saxo_client.get_historical_data.return_value = modified_data

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 200
        data = response.json()

        # Current price should be 120.0
        assert data["current_price"] == 120.0

        # All MAs should be below current price (price is high)
        for ma in data["moving_averages"]:
            assert (
                ma["is_above"] is True
            ), f"MA{ma['period']} should be below price"

    def test_get_asset_indicators_variation_calculation(
        self, mock_saxo_client, mock_historical_data
    ):
        """Test that variation percentage is calculated correctly."""
        modified_data = mock_historical_data.copy()
        # Set yesterday's close (index 1) to 100.0
        # Set today's close (index 0) to 105.0
        # Expected variation: (105 - 100) / 100 * 100 = 5.0%
        modified_data[0]["Close"] = 105.0
        modified_data[1]["Close"] = 100.0

        mock_saxo_client.get_historical_data.return_value = modified_data

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 200
        data = response.json()

        assert data["current_price"] == 105.0
        assert data["variation_pct"] == 5.0

    def test_get_asset_indicators_missing_code(self):
        """Test request without required code parameter."""
        response = client.get("/api/indicator/asset/")

        # FastAPI will redirect to /api/indicator/asset without trailing slash
        # or return 404
        assert response.status_code in [404, 307]

    def test_get_asset_indicators_weekly_unit_time(
        self, mock_saxo_client, mock_historical_data
    ):
        """Test indicator retrieval with weekly unit time."""
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response = client.get(
            "/api/indicator/asset/itp?country_code=xpar&unit_time=weekly"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unit_time"] == "weekly"
        assert data["asset_symbol"] == "itp:xpar"

        # Verify correct horizon was used (10080 = 7 days in minutes)
        mock_saxo_client.get_historical_data.assert_called_once_with(
            saxo_uic=123, asset_type="Stock", horizon=10080, count=210
        )

        # Check all MAs have weekly unit_time
        for ma in data["moving_averages"]:
            assert ma["unit_time"] == "weekly"

    def test_get_asset_indicators_monthly_unit_time(
        self, mock_saxo_client, mock_historical_data
    ):
        """Test indicator retrieval with monthly unit time."""
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response = client.get(
            "/api/indicator/asset/itp?country_code=xpar&unit_time=monthly"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unit_time"] == "monthly"
        assert data["asset_symbol"] == "itp:xpar"

        # Verify correct horizon was used (43200 = 30 days in minutes)
        mock_saxo_client.get_historical_data.assert_called_once_with(
            saxo_uic=123, asset_type="Stock", horizon=43200, count=210
        )

        # Check all MAs have monthly unit_time
        for ma in data["moving_averages"]:
            assert ma["unit_time"] == "monthly"

    def test_get_asset_indicators_invalid_unit_time(self, mock_saxo_client):
        """Test request with invalid unit_time parameter."""
        response = client.get("/api/indicator/asset/itp?unit_time=h1")

        # Should return 400 error for unsupported unit_time
        assert response.status_code == 400
        assert "Unsupported unit_time" in response.json()["detail"]
