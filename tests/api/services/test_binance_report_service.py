from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from api.services.binance_report_service import BinanceReportService
from model import Currency, Direction, ReportOrder, Signal, Strategy


@pytest.fixture
def mock_binance_client():
    """Create a mock BinanceClient."""
    client = Mock()
    return client


@pytest.fixture
def mock_configuration():
    """Create a mock Configuration."""
    config = Mock()
    config.currencies_rate = {"usdeur": 0.92}
    config.gsheet_creds_path = "/path/to/creds.json"
    config.spreadsheet_id = "test_spreadsheet_id"
    return config


@pytest.fixture
def binance_report_service(mock_binance_client, mock_configuration):
    """Create a BinanceReportService instance with mocks."""
    with patch("api.services.binance_report_service.GSheetClient"):
        service = BinanceReportService(mock_binance_client, mock_configuration)
        service.gsheet_client = MagicMock()
        return service


@pytest.fixture
def sample_orders():
    """Create sample ReportOrder objects for testing."""
    return [
        ReportOrder(
            code="BTC",
            name="Bitcoin",
            price=50000.0,
            quantity=0.1,
            date=datetime(2024, 1, 1, 10, 0, 0),
            direction=Direction.BUY,
            asset_type="Crypto",
            currency=Currency.USD,
        ),
        ReportOrder(
            code="ETH",
            name="Ethereum",
            price=3000.0,
            quantity=1.0,
            date=datetime(2024, 1, 2, 10, 0, 0),
            direction=Direction.SELL,
            asset_type="Crypto",
            currency=Currency.USD,
        ),
    ]


class TestBinanceReportService:
    """Test suite for BinanceReportService."""

    def test_get_binance_account(self, binance_report_service):
        """Test that _get_binance_account returns correct pseudo-account."""
        account = binance_report_service._get_binance_account()

        assert account.key == "binance"
        assert account.name == "Binance"
        assert account.fund == 0
        assert account.client_key == "binance"

    def test_get_orders_report(
        self, binance_report_service, mock_binance_client, sample_orders
    ):
        """Test get_orders_report fetches from Binance API."""
        mock_binance_client.get_report_all.return_value = sample_orders

        result = binance_report_service.get_orders_report(
            "binance_main", "2024-01-01"
        )

        assert result == sample_orders
        mock_binance_client.get_report_all.assert_called_once_with(
            "2024-01-01", 0.92
        )

    def test_get_orders_report_caching(
        self, binance_report_service, mock_binance_client, sample_orders
    ):
        """Test that get_orders_report uses caching."""
        mock_binance_client.get_report_all.return_value = sample_orders

        # First call
        result1 = binance_report_service.get_orders_report(
            "binance_main", "2024-01-01"
        )
        # Second call with same params should use cache
        result2 = binance_report_service.get_orders_report(
            "binance_main", "2024-01-01"
        )

        assert result1 == result2
        # Should only call the API once due to caching
        assert mock_binance_client.get_report_all.call_count == 1

    def test_convert_order_to_eur_with_usd(
        self, binance_report_service, sample_orders
    ):
        """Test currency conversion from USD to EUR."""
        order = sample_orders[0]  # BTC order in USD

        price_eur, total_eur, price_original, total_original = (
            binance_report_service.convert_order_to_eur(order)
        )

        # Price should be converted (50000 * 0.92 = 46000)
        assert price_eur == pytest.approx(46000.0, rel=1e-2)
        # Total should be converted (50000 * 0.1 * 0.92 = 4600)
        assert total_eur == pytest.approx(4600.0, rel=1e-2)
        # Original values should be preserved
        assert price_original == 50000.0
        assert total_original == pytest.approx(5000.0, rel=1e-2)

    def test_convert_order_to_eur_with_eur(self, binance_report_service):
        """Test that EUR orders are not converted."""
        order = ReportOrder(
            code="TEST",
            name="Test",
            price=100.0,
            quantity=10.0,
            date=datetime(2024, 1, 1, 10, 0, 0),
            direction=Direction.BUY,
            asset_type="Crypto",
            currency=Currency.EURO,
        )

        price_eur, total_eur, price_original, total_original = (
            binance_report_service.convert_order_to_eur(order)
        )

        assert price_eur == 100.0
        assert total_eur == 1000.0
        assert price_original is None
        assert total_original is None

    def test_calculate_summary(self, binance_report_service, sample_orders):
        """Test summary statistics calculation."""
        summary = binance_report_service.calculate_summary(sample_orders)

        assert summary["total_orders"] == 2
        assert summary["buy_orders"] == 1
        assert summary["sell_orders"] == 1
        # Values should be in EUR (converted at 0.92 rate)
        assert summary["total_volume_eur"] > 0
        assert summary["buy_volume_eur"] > 0
        assert summary["sell_volume_eur"] > 0

    def test_calculate_summary_empty_list(self, binance_report_service):
        """Test summary calculation with empty order list."""
        summary = binance_report_service.calculate_summary([])

        assert summary["total_orders"] == 0
        assert summary["total_volume_eur"] == 0
        assert summary["total_fees_eur"] == 0
        assert summary["buy_orders"] == 0
        assert summary["sell_orders"] == 0

    def test_create_gsheet_order_requires_strategy(
        self, binance_report_service, sample_orders
    ):
        """Test that create_gsheet_order requires strategy."""
        order = sample_orders[0]

        with pytest.raises(ValueError, match="Strategy is required"):
            binance_report_service.create_gsheet_order(
                account_id="binance_main",
                order=order,
                stop=49000.0,
                objective=55000.0,
                strategy=None,
                signal=Signal.BBB,
            )

    def test_create_gsheet_order_requires_signal(
        self, binance_report_service, sample_orders
    ):
        """Test that create_gsheet_order requires signal."""
        order = sample_orders[0]

        with pytest.raises(ValueError, match="Signal is required"):
            binance_report_service.create_gsheet_order(
                account_id="binance_main",
                order=order,
                stop=49000.0,
                objective=55000.0,
                strategy=Strategy.SW,
                signal=None,
            )

    def test_create_gsheet_order_success(
        self, binance_report_service, sample_orders
    ):
        """Test successful order creation in Google Sheets."""
        order = sample_orders[0]
        binance_report_service.gsheet_client = MagicMock()

        binance_report_service.create_gsheet_order(
            account_id="binance_main",
            order=order,
            stop=49000.0,
            objective=55000.0,
            strategy=Strategy.SW,
            signal=Signal.BBB,
            comment="Test comment",
        )

        # Verify gsheet_client.create_order was called
        binance_report_service.gsheet_client.create_order.assert_called_once()
        call_args = binance_report_service.gsheet_client.create_order.call_args

        # Check account parameter
        account = call_args[1]["account"]
        assert account.name == "Binance"

        # Check order was updated with inputs
        created_order = call_args[1]["order"]
        # Note: stop and objective are converted to EUR (49000 * 0.92 = 45080)
        assert created_order.stop == pytest.approx(45080.0, rel=1e-2)
        assert created_order.objective == pytest.approx(50600.0, rel=1e-2)
        assert created_order.comment == "Test comment"
        assert created_order.open_position is True

    def test_update_gsheet_order_close_position(
        self, binance_report_service, sample_orders
    ):
        """Test updating order to close position."""
        order = sample_orders[0]
        binance_report_service.gsheet_client = MagicMock()

        binance_report_service.update_gsheet_order(
            account_id="binance_main",
            order=order,
            line_number=10,
            close=True,
            stopped=False,
            be_stopped=False,
        )

        # Verify gsheet_client.update_order was called
        binance_report_service.gsheet_client.update_order.assert_called_once()
        call_args = binance_report_service.gsheet_client.update_order.call_args

        # Check order was updated correctly
        updated_order = call_args[1]["order"]
        assert updated_order.open_position is False
        assert updated_order.stopped is False
        assert updated_order.be_stopped is False

    def test_update_gsheet_order_with_stop_and_objective(
        self, binance_report_service, sample_orders
    ):
        """Test updating order with new stop and objective."""
        order = sample_orders[0]
        binance_report_service.gsheet_client = MagicMock()

        binance_report_service.update_gsheet_order(
            account_id="binance_main",
            order=order,
            line_number=10,
            close=False,
            stop=48000.0,
            objective=60000.0,
            strategy=Strategy.INTRA,
            signal=Signal.FIBO,
            comment="Updated comment",
        )

        binance_report_service.gsheet_client.update_order.assert_called_once()
        call_args = binance_report_service.gsheet_client.update_order.call_args

        updated_order = call_args[1]["order"]
        # Note: stop and objective are converted to EUR (48000 * 0.92 = 44160)
        assert updated_order.stop == pytest.approx(44160.0, rel=1e-2)
        assert updated_order.objective == pytest.approx(55200.0, rel=1e-2)
        assert updated_order.comment == "Updated comment"
        assert updated_order.open_position is True
