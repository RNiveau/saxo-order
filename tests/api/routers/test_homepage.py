from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.homepage import HomepageItemResponse, HomepageResponse
from api.models.indicator import AssetIndicatorsResponse, MovingAverageInfo
from api.routers.homepage import get_indicator_service
from api.routers.watchlist import get_dynamodb_client
from model import Currency

client = TestClient(app)


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDBClient."""
    mock_client = MagicMock()

    mock_client.get_watchlist.return_value = [
        {
            "id": "itp",
            "asset_symbol": "itp:xpar",
            "description": "Interparfums SA",
            "country_code": "xpar",
            "labels": ["homepage", "short-term"],
            "exchange": "saxo",
            "tradingview_url": (
                "https://www.tradingview.com/chart/" "?symbol=EURONEXT:ITP"
            ),
        },
        {
            "id": "bnb",
            "asset_symbol": "BNBUSDT",
            "description": "Binance Coin",
            "country_code": "",
            "labels": ["homepage", "crypto"],
            "exchange": "binance",
        },
        {
            "id": "dax",
            "asset_symbol": "DAX.I:xetr",
            "description": "DAX Index",
            "country_code": "xetr",
            "labels": ["short-term"],
            "exchange": "saxo",
        },
    ]

    def override_get_dynamodb_client():
        return mock_client

    app.dependency_overrides[get_dynamodb_client] = (
        override_get_dynamodb_client
    )
    yield mock_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_indicator_service():
    """Mock IndicatorService."""
    mock_service = MagicMock()

    def get_indicators_side_effect(code, country_code, unit_time, exchange):
        if code == "itp":
            return AssetIndicatorsResponse(
                asset_symbol="itp:xpar",
                description="Interparfums SA",
                current_price=100.5,
                variation_pct=2.5,
                currency=Currency.EURO,
                unit_time="daily",
                moving_averages=[
                    MovingAverageInfo(
                        period=7, value=98.0, is_above=True, unit_time="daily"
                    ),
                    MovingAverageInfo(
                        period=20,
                        value=95.0,
                        is_above=True,
                        unit_time="daily",
                    ),
                    MovingAverageInfo(
                        period=50,
                        value=92.0,
                        is_above=True,
                        unit_time="daily",
                    ),
                    MovingAverageInfo(
                        period=200,
                        value=85.0,
                        is_above=True,
                        unit_time="daily",
                    ),
                ],
            )
        elif code == "BNBUSDT":
            return AssetIndicatorsResponse(
                asset_symbol="BNBUSDT",
                description="Binance Coin",
                current_price=250.0,
                variation_pct=-1.5,
                currency=Currency.USD,
                unit_time="daily",
                moving_averages=[
                    MovingAverageInfo(
                        period=7,
                        value=255.0,
                        is_above=False,
                        unit_time="daily",
                    ),
                    MovingAverageInfo(
                        period=20,
                        value=260.0,
                        is_above=False,
                        unit_time="daily",
                    ),
                    MovingAverageInfo(
                        period=50,
                        value=270.0,
                        is_above=False,
                        unit_time="daily",
                    ),
                    MovingAverageInfo(
                        period=200,
                        value=280.0,
                        is_above=False,
                        unit_time="daily",
                    ),
                ],
            )
        else:
            raise Exception(f"Unexpected code: {code}")

    mock_service.get_asset_indicators.side_effect = get_indicators_side_effect

    def override_get_indicator_service():
        return mock_service

    app.dependency_overrides[get_indicator_service] = (
        override_get_indicator_service
    )
    yield mock_service
    app.dependency_overrides.clear()


def test_get_homepage_success(mock_dynamodb_client, mock_indicator_service):
    """Test successful homepage fetch with MA50 data."""
    response = client.get("/api/homepage")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2

    itp_item = next(item for item in data["items"] if item["id"] == "itp")
    assert itp_item["asset_symbol"] == "itp:xpar"
    assert itp_item["description"] == "Interparfums SA"
    assert itp_item["current_price"] == 100.5
    assert itp_item["variation_pct"] == 2.5
    assert itp_item["currency"] == "EUR"
    assert itp_item["ma50_value"] == 92.0
    assert itp_item["is_above_ma50"] is True
    assert (
        itp_item["tradingview_url"]
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:ITP"
    )

    bnb_item = next(item for item in data["items"] if item["id"] == "bnb")
    assert bnb_item["asset_symbol"] == "BNBUSDT"
    assert bnb_item["description"] == "Binance Coin"
    assert bnb_item["current_price"] == 250.0
    assert bnb_item["variation_pct"] == -1.5
    assert bnb_item["currency"] == "USD"
    assert bnb_item["ma50_value"] == 270.0
    assert bnb_item["is_above_ma50"] is False
    assert bnb_item["exchange"] == "binance"


def test_get_homepage_empty(mock_dynamodb_client, mock_indicator_service):
    """Test empty homepage when no assets have homepage tag."""
    mock_dynamodb_client.get_watchlist.return_value = [
        {
            "id": "dax",
            "asset_symbol": "DAX.I:xetr",
            "description": "DAX Index",
            "country_code": "xetr",
            "labels": ["short-term"],
            "exchange": "saxo",
        }
    ]

    response = client.get("/api/homepage")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_get_homepage_sorted_alphabetically(
    mock_dynamodb_client, mock_indicator_service
):
    """Test that homepage items are sorted by description."""
    mock_dynamodb_client.get_watchlist.return_value = [
        {
            "id": "bnb",
            "asset_symbol": "BNBUSDT",
            "description": "Binance Coin",
            "country_code": "",
            "labels": ["homepage"],
            "exchange": "binance",
        },
        {
            "id": "itp",
            "asset_symbol": "itp:xpar",
            "description": "Interparfums SA",
            "country_code": "xpar",
            "labels": ["homepage"],
            "exchange": "saxo",
        },
    ]

    response = client.get("/api/homepage")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["description"] == "Binance Coin"
    assert data["items"][1]["description"] == "Interparfums SA"


def test_get_homepage_handles_enrichment_errors(
    mock_dynamodb_client, mock_indicator_service
):
    """
    Test that enrichment errors for individual assets don't break
    the entire response.
    """
    mock_dynamodb_client.get_watchlist.return_value = [
        {
            "id": "itp",
            "asset_symbol": "itp:xpar",
            "description": "Interparfums SA",
            "country_code": "xpar",
            "labels": ["homepage"],
            "exchange": "saxo",
        },
        {
            "id": "error_asset",
            "asset_symbol": "ERROR:xpar",
            "description": "Error Asset",
            "country_code": "xpar",
            "labels": ["homepage"],
            "exchange": "saxo",
        },
    ]

    def get_indicators_with_error(code, country_code, unit_time, exchange):
        if code == "itp":
            return AssetIndicatorsResponse(
                asset_symbol="itp:xpar",
                description="Interparfums SA",
                current_price=100.5,
                variation_pct=2.5,
                currency=Currency.EURO,
                unit_time="daily",
                moving_averages=[
                    MovingAverageInfo(
                        period=50,
                        value=92.0,
                        is_above=True,
                        unit_time="daily",
                    )
                ],
            )
        else:
            raise Exception("Failed to fetch indicators")

    mock_indicator_service.get_asset_indicators.side_effect = (
        get_indicators_with_error
    )

    response = client.get("/api/homepage")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "itp"
