import datetime
from unittest.mock import MagicMock

import pytest

from api.services.alerting_service import AlertingService
from client.aws_client import DynamoDBClient
from model import Alert, AlertType


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDBClient."""
    return MagicMock(spec=DynamoDBClient)


@pytest.fixture
def alerting_service(mock_dynamodb_client):
    """Create AlertingService with mocked dependencies."""
    return AlertingService(mock_dynamodb_client)


class TestAlertExclusionFiltering:
    def test_get_all_alerts_with_no_exclusions(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test get_all_alerts with no excluded assets returns all alerts."""
        # Setup: No excluded assets
        mock_dynamodb_client.get_excluded_assets.return_value = []

        # Setup: Sample alerts
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.DOUBLE_TOP,
                date=datetime.datetime(2026, 1, 26, 9, 0, 0),
                data={"ma50_slope": 8.3},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        # Execute
        response = alerting_service.get_all_alerts()

        # Assert: All alerts returned
        assert response.total_count == 2
        assert len(response.alerts) == 2

    def test_get_all_alerts_with_some_exclusions(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test get_all_alerts filters out excluded asset alerts."""
        # Setup: SAN:xpar is excluded (must match full asset_id format)
        mock_dynamodb_client.get_excluded_assets.return_value = ["SAN:xpar"]

        # Setup: Alerts for both SAN and ITP
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.DOUBLE_TOP,
                date=datetime.datetime(2026, 1, 26, 9, 0, 0),
                data={"ma50_slope": 8.3},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        # Execute
        response = alerting_service.get_all_alerts()

        # Assert: Only ITP alert returned (SAN filtered out)
        assert response.total_count == 1
        assert len(response.alerts) == 1
        assert response.alerts[0].asset_code == "ITP"

    def test_get_all_alerts_with_all_excluded(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test get_all_alerts returns empty when all alerts are excluded."""
        # Setup: All assets excluded (must match full asset_id format)
        mock_dynamodb_client.get_excluded_assets.return_value = [
            "SAN:xpar",
            "ITP:xpar",
            "BNP:xpar",
        ]

        # Setup: Alerts from excluded assets
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.DOUBLE_TOP,
                date=datetime.datetime(2026, 1, 26, 9, 0, 0),
                data={"ma50_slope": 8.3},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        # Execute
        response = alerting_service.get_all_alerts()

        # Assert: No alerts returned
        assert response.total_count == 0
        assert len(response.alerts) == 0

    def test_get_all_alerts_filters_dont_include_excluded(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test available filters don't include excluded assets."""
        # Setup: SAN is excluded
        mock_dynamodb_client.get_excluded_assets.return_value = ["SAN:xpar"]

        # Setup: Alerts for both SAN and ITP
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.DOUBLE_TOP,
                date=datetime.datetime(2026, 1, 26, 9, 0, 0),
                data={"ma50_slope": 8.3},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        # Execute
        response = alerting_service.get_all_alerts()

        # Assert: SAN not in available filters
        assert "ITP" in response.available_filters["asset_codes"]
        assert "SAN" not in response.available_filters["asset_codes"]

    def test_get_all_alerts_with_user_filter_and_exclusion(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test both user filters and exclusions are applied correctly."""
        # Setup: SAN is excluded
        mock_dynamodb_client.get_excluded_assets.return_value = ["SAN:xpar"]

        # Setup: Multiple alerts with different types
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 9, 0, 0),
                data={"ma50_slope": 8.3},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.DOUBLE_TOP,
                date=datetime.datetime(2026, 1, 26, 8, 0, 0),
                data={"ma50_slope": 5.1},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        # Execute: Filter by alert_type=combo
        response = alerting_service.get_all_alerts(alert_type="combo")

        # Assert: Only ITP COMBO alert (SAN excluded, DOUBLE_TOP filtered)
        assert response.total_count == 1
        assert response.alerts[0].asset_code == "ITP"
        assert response.alerts[0].alert_type == "combo"

    def test_get_all_alerts_empty_table(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test get_all_alerts with no alerts in database."""
        mock_dynamodb_client.get_excluded_assets.return_value = []
        mock_dynamodb_client.get_all_alerts.return_value = []

        response = alerting_service.get_all_alerts()

        assert response.total_count == 0
        assert len(response.alerts) == 0
        assert response.available_filters["asset_codes"] == []
        assert response.available_filters["alert_types"] == []


class TestAlertsCaching:
    def test_get_all_alerts_uses_cache_on_second_call(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test that get_all_alerts uses cache on subsequent calls."""
        mock_dynamodb_client.get_excluded_assets.return_value = []
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        response1 = alerting_service.get_all_alerts()
        response2 = alerting_service.get_all_alerts()

        assert response1.total_count == 1
        assert response2.total_count == 1
        mock_dynamodb_client.get_all_alerts.assert_called_once()
        mock_dynamodb_client.get_excluded_assets.assert_called_once()
        mock_dynamodb_client.get_all_tradingview_links.assert_called_once()

    def test_cache_invalidation_clears_cache(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test that cache invalidation forces fresh data fetch."""
        mock_dynamodb_client.get_excluded_assets.return_value = []
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        response1 = alerting_service.get_all_alerts()
        assert response1.total_count == 1

        alerting_service.invalidate_cache()

        response2 = alerting_service.get_all_alerts()
        assert response2.total_count == 1

        assert mock_dynamodb_client.get_all_alerts.call_count == 2
        assert mock_dynamodb_client.get_excluded_assets.call_count == 2
        assert mock_dynamodb_client.get_all_tradingview_links.call_count == 2

    def test_cache_with_different_filters_uses_same_base_data(
        self, alerting_service, mock_dynamodb_client
    ):
        """Test that different filters use the same cached base data."""
        mock_dynamodb_client.get_excluded_assets.return_value = []
        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 1, 26, 10, 0, 0),
                data={"ma50_slope": 15.2},
                asset_code="SAN",
                asset_description="Santander",
                exchange="saxo",
                country_code="xpar",
            ),
            Alert(
                alert_type=AlertType.DOUBLE_TOP,
                date=datetime.datetime(2026, 1, 26, 9, 0, 0),
                data={"ma50_slope": 8.3},
                asset_code="ITP",
                asset_description="Interparfums",
                exchange="saxo",
                country_code="xpar",
            ),
        ]
        mock_dynamodb_client.get_all_alerts.return_value = alerts
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        response1 = alerting_service.get_all_alerts(asset_code="SAN")
        response2 = alerting_service.get_all_alerts(asset_code="ITP")
        response3 = alerting_service.get_all_alerts(alert_type="combo")

        assert response1.total_count == 1
        assert response1.alerts[0].asset_code == "SAN"
        assert response2.total_count == 1
        assert response2.alerts[0].asset_code == "ITP"
        assert response3.total_count == 1
        assert response3.alerts[0].alert_type == "combo"

        mock_dynamodb_client.get_all_alerts.assert_called_once()
        mock_dynamodb_client.get_excluded_assets.assert_called_once()
        mock_dynamodb_client.get_all_tradingview_links.assert_called_once()
