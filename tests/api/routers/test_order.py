from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.order import get_configuration, get_saxo_client
from model import Account
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
def mock_configuration():
    """Mock Configuration for testing."""
    mock_config = MagicMock()

    def override_get_configuration():
        return mock_config

    app.dependency_overrides[get_configuration] = override_get_configuration
    yield mock_config
    app.dependency_overrides.clear()


@pytest.fixture
def mock_account():
    """Mock Account for testing."""
    return Account(
        key="test-account-123",
        name="Test Account",
        fund=10000.0,
        available_fund=8000.0,
    )


class TestOrderEndpoint:
    def test_create_order_success(
        self, mock_saxo_client, mock_configuration, mock_account
    ):
        """Test successful order creation."""
        mock_saxo_client.get_asset.return_value = {
            "Identifier": 12345,
            "Description": "Test Stock",
            "AssetType": "Stock",
            "CurrencyCode": "EUR",
        }
        mock_saxo_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_saxo_client.get_account.return_value = mock_account
        mock_saxo_client.get_open_orders.return_value = []
        mock_saxo_client.get_total_amount.return_value = 100000.0
        mock_saxo_client.set_order.return_value = {"OrderId": "ORD-123"}

        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 5,
                "order_type": "limit",
                "direction": "Buy",
                "stop": 95.0,
                "objective": 115.0,
                "comment": "Test order",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "TEST" in data["message"]
        assert data["order_id"] == "ORD-123"

    def test_create_order_validation_error(
        self, mock_saxo_client, mock_configuration, mock_account
    ):
        """Test order creation with validation error."""
        mock_saxo_client.get_asset.return_value = {
            "Identifier": 12345,
            "Description": "Test Stock",
            "AssetType": "Stock",
            "CurrencyCode": "EUR",
        }
        mock_saxo_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_saxo_client.get_account.return_value = mock_account
        mock_saxo_client.get_open_orders.return_value = []
        mock_saxo_client.get_total_amount.return_value = 10000.0
        mock_saxo_client.set_order.side_effect = SaxoException(
            "Not enough money for this order"
        )

        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 5000.0,
                "quantity": 100,
                "order_type": "limit",
                "direction": "Buy",
                "stop": 4900.0,
                "objective": 5500.0,
            },
        )

        assert response.status_code == 400
        assert "Not enough money" in response.json()["detail"]

    def test_create_order_invalid_request(self):
        """Test order creation with invalid request data."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": -100.0,
                "quantity": 10,
                "order_type": "limit",
                "direction": "Buy",
            },
        )

        assert response.status_code == 422

    def test_create_order_missing_required_fields(self):
        """Test order creation with missing required fields."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
            },
        )

        assert response.status_code == 422

    def test_create_order_invalid_order_type(self):
        """Test order creation with invalid order type."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 10,
                "order_type": "invalid",
                "direction": "Buy",
            },
        )

        assert response.status_code == 422

    def test_create_order_invalid_direction(self):
        """Test order creation with invalid direction."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 10,
                "order_type": "limit",
                "direction": "invalid",
            },
        )

        assert response.status_code == 422


class TestOcoOrderEndpoint:
    def test_create_oco_order_success(
        self, mock_saxo_client, mock_configuration, mock_account
    ):
        """Test successful OCO order creation."""
        mock_saxo_client.get_asset.return_value = {
            "Identifier": 12345,
            "Description": "Test Stock",
            "AssetType": "Stock",
            "CurrencyCode": "EUR",
        }
        mock_saxo_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_saxo_client.get_account.return_value = mock_account
        mock_saxo_client.get_open_orders.return_value = []
        mock_saxo_client.get_total_amount.return_value = 10000.0
        mock_saxo_client.set_oco_order.return_value = {"OrderId": "OCO-123"}

        response = client.post(
            "/api/orders/oco",
            json={
                "code": "TEST",
                "quantity": 10,
                "limit_price": 105.0,
                "limit_direction": "Sell",
                "stop_price": 95.0,
                "stop_direction": "Sell",
                "stop": 90.0,
                "objective": 110.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "OCO order" in data["message"]
        assert data["order_id"] == "OCO-123"

    def test_create_oco_order_validation_error(
        self, mock_saxo_client, mock_configuration, mock_account
    ):
        """Test OCO order creation with validation error."""
        mock_saxo_client.get_asset.return_value = {
            "Identifier": 12345,
            "Description": "Test Stock",
            "AssetType": "Stock",
            "CurrencyCode": "EUR",
        }
        mock_saxo_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_saxo_client.get_account.return_value = mock_account
        mock_saxo_client.set_oco_order.side_effect = SaxoException(
            "Validation failed"
        )

        response = client.post(
            "/api/orders/oco",
            json={
                "code": "TEST",
                "quantity": 10,
                "limit_price": 105.0,
                "limit_direction": "Sell",
                "stop_price": 95.0,
                "stop_direction": "Sell",
            },
        )

        assert response.status_code == 400
        assert "Validation failed" in response.json()["detail"]


class TestStopLimitOrderEndpoint:
    def test_create_stop_limit_order_success(
        self, mock_saxo_client, mock_configuration, mock_account
    ):
        """Test successful stop-limit order creation."""
        mock_saxo_client.get_asset.return_value = {
            "Identifier": 12345,
            "Description": "Test Stock",
            "AssetType": "Stock",
            "CurrencyCode": "EUR",
        }
        mock_saxo_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_saxo_client.get_account.return_value = mock_account
        mock_saxo_client.get_open_orders.return_value = []
        mock_saxo_client.get_total_amount.return_value = 100000.0
        mock_saxo_client.set_order.return_value = {"OrderId": "SL-123"}

        response = client.post(
            "/api/orders/stop-limit",
            json={
                "code": "TEST",
                "quantity": 5,
                "limit_price": 100.0,
                "stop_price": 95.0,
                "stop": 90.0,
                "objective": 115.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Stop-limit order" in data["message"]
        assert data["order_id"] == "SL-123"

    def test_create_stop_limit_order_validation_error(
        self, mock_saxo_client, mock_configuration, mock_account
    ):
        """Test stop-limit order creation with validation error."""
        mock_saxo_client.get_asset.return_value = {
            "Identifier": 12345,
            "Description": "Test Stock",
            "AssetType": "Stock",
            "CurrencyCode": "EUR",
        }
        mock_saxo_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_saxo_client.get_account.return_value = mock_account
        mock_saxo_client.set_order.side_effect = SaxoException(
            "Ratio earn / lost must be greater than 1.5"
        )

        response = client.post(
            "/api/orders/stop-limit",
            json={
                "code": "TEST",
                "quantity": 10,
                "limit_price": 100.0,
                "stop_price": 95.0,
                "stop": 92.0,
                "objective": 105.0,
            },
        )

        assert response.status_code == 400
        assert "Ratio" in response.json()["detail"]

    def test_create_stop_limit_order_missing_fields(self):
        """Test stop-limit order creation with missing fields."""
        response = client.post(
            "/api/orders/stop-limit",
            json={
                "code": "TEST",
                "quantity": 10,
            },
        )

        assert response.status_code == 422
