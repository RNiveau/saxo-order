from unittest.mock import MagicMock, patch

import pytest

from model import Account, Direction, Order, OrderType
from saxo_order.services.order_service import OrderService
from utils.exception import SaxoException


@pytest.fixture
def mock_client():
    """Mock SaxoClient for testing."""
    return MagicMock()


@pytest.fixture
def mock_configuration():
    """Mock Configuration for testing."""
    return MagicMock()


@pytest.fixture
def order_service(mock_client, mock_configuration):
    """Create OrderService instance with mocked dependencies."""
    return OrderService(mock_client, mock_configuration)


@pytest.fixture
def mock_account():
    """Mock Account for testing."""
    return Account(
        key="test-account-123",
        name="Test Account",
        fund=10000.0,
        available_fund=8000.0,
    )


@pytest.fixture
def mock_asset():
    """Mock asset data from Saxo API."""
    return {
        "Identifier": 12345,
        "Description": "Test Stock Inc.",
        "AssetType": "Stock",
        "CurrencyCode": "EUR",
    }


class TestOrderService:
    def test_create_order_success(
        self, order_service, mock_client, mock_account, mock_asset
    ):
        """Test successful order creation."""
        mock_client.get_asset.return_value = mock_asset
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_client.get_account.return_value = mock_account
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 100000.0
        mock_client.set_order.return_value = {"OrderId": "ORD-123"}

        result = order_service.create_order(
            code="TEST",
            price=100.0,
            quantity=5,
            order_type="limit",
            direction="buy",
            stop=95.0,
            objective=115.0,
            account_key=mock_account.key,
        )

        assert result["success"] is True
        assert result["order"].code == "TEST"
        assert result["order"].price == 100.0
        assert result["order"].quantity == 5
        assert result["account"].key == mock_account.key
        mock_client.set_order.assert_called_once()

    def test_create_order_market_type(
        self, order_service, mock_client, mock_account, mock_asset
    ):
        """Test order creation with market order type."""
        mock_client.get_asset.return_value = mock_asset
        mock_client.get_price.return_value = 105.5
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_client.get_account.return_value = mock_account
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 100000.0
        mock_client.set_order.return_value = {"OrderId": "ORD-124"}

        result = order_service.create_order(
            code="TEST",
            price=100.0,
            quantity=5,
            order_type="market",
            direction="buy",
            stop=95.0,
            objective=120.0,
            account_key=mock_account.key,
        )

        assert result["order"].price == 105.5
        mock_client.get_price.assert_called_once_with(
            mock_asset["Identifier"], mock_asset["AssetType"]
        )

    def test_create_order_validation_failure(
        self, order_service, mock_client, mock_account, mock_asset
    ):
        """Test order creation with validation failure."""
        mock_client.get_asset.return_value = mock_asset
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_client.get_account.return_value = mock_account
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 10000.0

        with patch(
            "saxo_order.services.order_service.apply_rules",
            return_value="Not enough money for this order",
        ):
            with pytest.raises(SaxoException) as exc_info:
                order_service.create_order(
                    code="TEST",
                    price=5000.0,
                    quantity=100,
                    order_type="limit",
                    direction="buy",
                    stop=4900.0,
                    objective=5500.0,
                    account_key=mock_account.key,
                )

            assert "Not enough money" in str(exc_info.value)

    def test_create_oco_order_success(
        self, order_service, mock_client, mock_account, mock_asset
    ):
        """Test successful OCO order creation."""
        mock_client.get_asset.return_value = mock_asset
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_client.get_account.return_value = mock_account
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 10000.0
        mock_client.set_oco_order.return_value = {"OrderId": "OCO-123"}

        result = order_service.create_oco_order(
            code="TEST",
            quantity=10,
            limit_price=105.0,
            limit_direction="sell",
            stop_price=95.0,
            stop_direction="sell",
            stop=90.0,
            objective=110.0,
            account_key=mock_account.key,
        )

        assert result["success"] is True
        assert result["limit_order"].price == 105.0
        assert result["stop_order"].price == 95.0
        mock_client.set_oco_order.assert_called_once()

    def test_create_stop_limit_order_success(
        self, order_service, mock_client, mock_account, mock_asset
    ):
        """Test successful stop-limit order creation."""
        mock_client.get_asset.return_value = mock_asset
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_client.get_account.return_value = mock_account
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 100000.0
        mock_client.set_order.return_value = {"OrderId": "SL-123"}

        result = order_service.create_stop_limit_order(
            code="TEST",
            quantity=5,
            limit_price=100.0,
            stop_price=95.0,
            stop=90.0,
            objective=115.0,
            account_key=mock_account.key,
        )

        assert result["success"] is True
        assert result["order"].type == OrderType.STOP_LIMIT
        assert result["order"].direction == Direction.BUY
        mock_client.set_order.assert_called_once()

    def test_get_account_by_key(
        self, order_service, mock_client, mock_account
    ):
        """Test getting account by key."""
        mock_client.get_accounts.return_value = {
            "Data": [
                {"AccountKey": mock_account.key, "AccountId": "ACC-1"},
                {"AccountKey": "other-key", "AccountId": "ACC-2"},
            ]
        }
        mock_client.get_account.return_value = mock_account

        account = order_service._get_account(mock_account.key)

        assert account.key == mock_account.key
        mock_client.get_account.assert_called_once_with(mock_account.key)

    def test_get_account_default(
        self, order_service, mock_client, mock_account
    ):
        """Test getting default account when no key provided."""
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": mock_account.key}]
        }
        mock_client.get_account.return_value = mock_account

        account = order_service._get_account(None)

        assert account.key == mock_account.key

    def test_get_account_not_found(self, order_service, mock_client):
        """Test exception when account not found."""
        mock_client.get_accounts.return_value = {
            "Data": [{"AccountKey": "different-key"}]
        }

        with pytest.raises(SaxoException) as exc_info:
            order_service._get_account("non-existent-key")

        assert "not found" in str(exc_info.value)

    def test_get_account_no_accounts(self, order_service, mock_client):
        """Test exception when no accounts available."""
        mock_client.get_accounts.return_value = {"Data": []}

        with pytest.raises(SaxoException) as exc_info:
            order_service._get_account(None)

        assert "No accounts available" in str(exc_info.value)

    def test_validate_buy_order_success(
        self, order_service, mock_client, mock_account
    ):
        """Test successful buy order validation."""
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 10000.0

        order = Order(
            code="TEST",
            price=100.0,
            quantity=10,
            stop=95.0,
            objective=110.0,
        )

        with patch(
            "saxo_order.services.order_service.apply_rules", return_value=None
        ):
            order_service._validate_buy_order(mock_account, order)

    def test_validate_buy_order_failure(
        self, order_service, mock_client, mock_account
    ):
        """Test buy order validation failure."""
        mock_client.get_open_orders.return_value = []
        mock_client.get_total_amount.return_value = 10000.0

        order = Order(
            code="TEST",
            price=100.0,
            quantity=10,
            stop=95.0,
            objective=105.0,
        )

        with patch(
            "saxo_order.services.order_service.apply_rules",
            return_value="Ratio earn / lost must be greater than 1.5",
        ):
            with pytest.raises(SaxoException) as exc_info:
                order_service._validate_buy_order(mock_account, order)

            assert "Ratio" in str(exc_info.value)
