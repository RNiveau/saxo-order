import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.indicator import (
    get_binance_client,
    get_candles_service,
    get_saxo_client,
)
from model import Candle, UnitTime
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
        "Description": "Interparfums SA",
    }

    def override_get_saxo_client():
        return mock_client

    app.dependency_overrides[get_saxo_client] = override_get_saxo_client
    yield mock_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_binance_client():
    """Mock BinanceClient - autouse so all tests have it."""
    mock_client = MagicMock()

    def override_get_binance_client():
        return mock_client

    app.dependency_overrides[get_binance_client] = override_get_binance_client
    yield mock_client
    # Don't delete - mock_saxo_client clears all overrides


@pytest.fixture
def mock_candles_service():
    """Mock CandlesService with get_latest_candle method."""
    mock_service = MagicMock()
    # Default: return a candle with close price of 100.0
    mock_service.get_latest_candle.return_value = Candle(
        open=100.0,
        close=100.0,
        lower=99.0,
        higher=101.0,
        date=datetime.datetime.now(datetime.UTC),
    )

    def override_get_candles_service():
        return mock_service

    app.dependency_overrides[get_candles_service] = (
        override_get_candles_service
    )
    yield mock_service
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
        self, mock_saxo_client, mock_candles_service, mock_historical_data
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
        assert "description" in data
        assert "current_price" in data
        assert "variation_pct" in data
        assert "unit_time" in data
        assert "moving_averages" in data

        # Check asset symbol, description, and unit_time
        assert data["asset_symbol"] == "itp:xpar"
        assert data["description"] == "Interparfums SA"
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
        # get_asset is called twice: once in get_asset_indicators,
        # once in get_price_and_variation
        assert mock_saxo_client.get_asset.call_count == 2
        mock_saxo_client.get_asset.assert_called_with("itp", "xpar")

        # get_historical_data is called twice: once with count=210 for MAs,
        # once with count=3 for price/variation
        assert mock_saxo_client.get_historical_data.call_count == 2
        mock_saxo_client.get_historical_data.assert_any_call(
            saxo_uic=123, asset_type="Stock", horizon=1440, count=210
        )
        mock_saxo_client.get_historical_data.assert_any_call(
            saxo_uic=123, asset_type="Stock", horizon=1440, count=3
        )

    def test_get_asset_indicators_with_default_country_code(
        self, mock_saxo_client, mock_candles_service, mock_historical_data
    ):
        """Test indicator retrieval with default country_code."""
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_symbol"] == "itp:xpar"

        # get_asset is called twice
        assert mock_saxo_client.get_asset.call_count == 2
        mock_saxo_client.get_asset.assert_called_with("itp", "xpar")

    def test_get_asset_indicators_insufficient_data(
        self, mock_saxo_client, mock_candles_service
    ):
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

    def test_get_asset_indicators_asset_not_found(
        self, mock_saxo_client, mock_candles_service
    ):
        """Test when asset is not found."""
        mock_saxo_client.get_asset.side_effect = SaxoException(
            "Stock itp:xpar doesn't exist"
        )

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 400
        assert "doesn't exist" in response.json()["detail"]

    def test_get_asset_indicators_unexpected_error(
        self, mock_saxo_client, mock_candles_service
    ):
        """Test handling of unexpected errors."""
        mock_saxo_client.get_asset.side_effect = Exception("Network error")

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_get_asset_indicators_price_above_below_ma(
        self, mock_saxo_client, mock_candles_service, mock_historical_data
    ):
        """Test is_above flag reflects price position relative to MA."""
        # Set high current price via latest candle
        mock_candles_service.get_latest_candle.return_value = Candle(
            open=120.0,
            close=120.0,
            lower=119.0,
            higher=121.0,
            date=datetime.datetime.now(datetime.UTC),
        )

        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

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
        self, mock_saxo_client, mock_candles_service, mock_historical_data
    ):
        """Test that variation percentage is calculated correctly."""
        # Set current price to 105.0 via latest candle
        mock_candles_service.get_latest_candle.return_value = Candle(
            open=105.0,
            close=105.0,
            lower=104.0,
            higher=106.0,
            date=datetime.datetime.now(datetime.UTC),
        )

        # Most recent complete candle (index 0) has close of 100.0
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 200
        data = response.json()

        assert data["current_price"] == 105.0
        # Variation: (105 - 100) / 100 * 100 = 5.0%
        assert data["variation_pct"] == 5.0

    def test_get_asset_indicators_variation_same_period(
        self, mock_saxo_client, mock_candles_service, mock_historical_data
    ):
        """Test variation when latest candle is from same period.

        E.g., on Sunday, both latest and most recent complete are Friday.
        """
        # Friday's date
        friday_date = datetime.datetime(2024, 1, 5, 16, 0, 0)

        # Latest candle is from Friday (last trading day)
        mock_candles_service.get_latest_candle.return_value = Candle(
            open=100.0,
            close=100.0,
            lower=99.0,
            higher=101.0,
            date=friday_date,
        )

        # Historical data: candles[0] is Friday, candles[1] is Thursday
        modified_data = mock_historical_data.copy()
        modified_data[0]["Time"] = friday_date  # Friday
        modified_data[0]["Close"] = 100.0
        modified_data[1]["Time"] = datetime.datetime(
            2024, 1, 4, 16, 0, 0
        )  # Thursday
        modified_data[1]["Close"] = 95.0

        mock_saxo_client.get_historical_data.return_value = modified_data

        response = client.get("/api/indicator/asset/itp")

        assert response.status_code == 200
        data = response.json()

        assert data["current_price"] == 100.0
        # Since latest candle is from same day as candles[0] (both Friday),
        # variation should be calculated against candles[1] (Thursday)
        # Variation: (100 - 95) / 95 * 100 = 5.26%
        assert data["variation_pct"] == 5.26

    def test_get_asset_indicators_missing_code(self):
        """Test request without required code parameter."""
        response = client.get("/api/indicator/asset/")

        # FastAPI will redirect to /api/indicator/asset without trailing slash
        # or return 404
        assert response.status_code in [404, 307]

    def test_get_asset_indicators_weekly_unit_time(
        self, mock_saxo_client, mock_candles_service, mock_historical_data
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
        # get_historical_data is called twice: once with count=210,
        # once with count=3
        assert mock_saxo_client.get_historical_data.call_count == 2
        mock_saxo_client.get_historical_data.assert_any_call(
            saxo_uic=123, asset_type="Stock", horizon=10080, count=210
        )
        mock_saxo_client.get_historical_data.assert_any_call(
            saxo_uic=123, asset_type="Stock", horizon=10080, count=3
        )

        # Check all MAs have weekly unit_time
        for ma in data["moving_averages"]:
            assert ma["unit_time"] == "weekly"

    def test_get_asset_indicators_monthly_unit_time(
        self, mock_saxo_client, mock_candles_service, mock_historical_data
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
        # get_historical_data is called twice: once with count=210,
        # once with count=3
        assert mock_saxo_client.get_historical_data.call_count == 2
        mock_saxo_client.get_historical_data.assert_any_call(
            saxo_uic=123, asset_type="Stock", horizon=43200, count=210
        )
        mock_saxo_client.get_historical_data.assert_any_call(
            saxo_uic=123, asset_type="Stock", horizon=43200, count=3
        )

        # Check all MAs have monthly unit_time
        for ma in data["moving_averages"]:
            assert ma["unit_time"] == "monthly"

    def test_get_asset_indicators_binance_symbol(
        self, mock_binance_client, mock_candles_service
    ):
        """Test indicator retrieval for Binance cryptocurrency."""
        mock_candles = []
        for i in range(210):
            mock_candles.append(
                Candle(
                    open=50000.0 + i,
                    close=50000.0 + i,
                    lower=49900.0 + i,
                    higher=50100.0 + i,
                    ut=UnitTime.D,
                    date=datetime.datetime(2024, 1, 1, 0, 0, 0)
                    + datetime.timedelta(days=210 - i),
                )
            )

        mock_binance_client.get_candles.return_value = mock_candles
        mock_binance_client.get_latest_candle.return_value = Candle(
            open=52000.0,
            close=52100.0,
            lower=51900.0,
            higher=52200.0,
            ut=UnitTime.M15,
            date=datetime.datetime.now(datetime.UTC),
        )

        response = client.get(
            "/api/indicator/asset/BTCUSDT?exchange=binance&unit_time=daily"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["asset_symbol"] == "BTCUSDT"
        assert data["description"] == "BTCUSDT"
        assert data["current_price"] == 52100.0
        assert data["currency"] == "USD"
        assert data["unit_time"] == "daily"

        assert len(data["moving_averages"]) == 4
        ma_periods = [ma["period"] for ma in data["moving_averages"]]
        assert sorted(ma_periods) == [7, 20, 50, 200]

        mock_binance_client.get_candles.assert_called_once_with(
            "BTCUSDT", UnitTime.D, limit=210
        )
        mock_binance_client.get_latest_candle.assert_called_once_with(
            "BTCUSDT"
        )

    def test_get_asset_indicators_binance_variation(
        self, mock_binance_client, mock_candles_service
    ):
        """Test variation calculation for Binance assets."""
        mock_candles = []
        for i in range(210):
            mock_candles.append(
                Candle(
                    open=100.0,
                    close=100.0,
                    lower=99.0,
                    higher=101.0,
                    ut=UnitTime.D,
                    date=datetime.datetime(2024, 1, 1, 0, 0, 0)
                    + datetime.timedelta(days=210 - i),
                )
            )

        mock_binance_client.get_candles.return_value = mock_candles
        mock_binance_client.get_latest_candle.return_value = Candle(
            open=105.0,
            close=110.0,
            lower=104.0,
            higher=111.0,
            ut=UnitTime.M15,
            date=datetime.datetime.now(datetime.UTC),
        )

        response = client.get("/api/indicator/asset/ETHUSDT?exchange=binance")

        assert response.status_code == 200
        data = response.json()

        assert data["current_price"] == 110.0
        assert data["variation_pct"] == 10.0

    def test_get_asset_indicators_exchange_parameter(
        self, mock_saxo_client, mock_candles_service, mock_historical_data
    ):
        """Test that exchange parameter correctly routes to appropriate client."""
        mock_saxo_client.get_historical_data.return_value = (
            mock_historical_data
        )

        response_saxo = client.get(
            "/api/indicator/asset/itp?exchange=saxo&country_code=xpar"
        )

        assert response_saxo.status_code == 200
        assert response_saxo.json()["asset_symbol"] == "itp:xpar"

        mock_saxo_client.get_asset.call_count >= 1

    def test_get_asset_indicators_country_code_optional_for_binance(
        self, mock_binance_client, mock_candles_service
    ):
        """Test that country_code is ignored for Binance assets."""
        mock_candles = []
        for i in range(210):
            mock_candles.append(
                Candle(
                    open=100.0,
                    close=100.0,
                    lower=99.0,
                    higher=101.0,
                    ut=UnitTime.D,
                    date=datetime.datetime(2024, 1, 1, 0, 0, 0)
                    + datetime.timedelta(days=i),
                )
            )

        mock_binance_client.get_candles.return_value = mock_candles
        mock_binance_client.get_latest_candle.return_value = Candle(
            open=100.0,
            close=100.0,
            lower=99.0,
            higher=101.0,
            ut=UnitTime.M15,
            date=datetime.datetime.now(datetime.UTC),
        )

        response = client.get(
            "/api/indicator/asset/BTCUSDT?exchange=binance"
            "&country_code=ignored"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_symbol"] == "BTCUSDT"

        mock_binance_client.get_candles.assert_called_once()
        mock_binance_client.get_latest_candle.assert_called_once()
