from datetime import datetime
from typing import Dict, List, Optional

from api.models.alerting import AlertItemResponse, AlertsResponse
from client.aws_client import DynamoDBClient
from model import Alert
from utils.logger import Logger

logger = Logger.get_logger("alerting_api_service")


class AlertingService:
    """Service for managing alerts via API."""

    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb_client = dynamodb_client

    def get_all_alerts(
        self,
        asset_code: Optional[str] = None,
        alert_type: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> AlertsResponse:
        """
        Get all alerts from DynamoDB with optional filtering.

        Args:
            asset_code: Optional filter by asset code
            alert_type: Optional filter by alert type
            country_code: Optional filter by country code

        Returns:
            AlertsResponse with filtered alerts and available filter options
        """
        # Fetch all alerts from DynamoDB
        all_alerts: List[Alert] = self.dynamodb_client.get_all_alerts()

        # Apply filters
        filtered_alerts = all_alerts
        if asset_code:
            filtered_alerts = [
                alert
                for alert in filtered_alerts
                if alert.asset_code == asset_code
            ]
        if alert_type:
            filtered_alerts = [
                alert
                for alert in filtered_alerts
                if alert.alert_type.value == alert_type
            ]
        if country_code is not None:
            filtered_alerts = [
                alert
                for alert in filtered_alerts
                if alert.country_code == country_code
            ]

        # Sort by date descending (newest first)
        filtered_alerts.sort(key=lambda a: a.date, reverse=True)

        # Transform to response models
        alert_items = [self._to_response(alert) for alert in filtered_alerts]

        # Calculate available filters from ALL alerts (not filtered)
        filters = self._calculate_filters(all_alerts)

        return AlertsResponse(
            alerts=alert_items,
            total_count=len(alert_items),
            available_filters=filters,
        )

    def _to_response(self, alert: Alert) -> AlertItemResponse:
        """
        Transform Alert domain model to AlertItemResponse API model.

        Args:
            alert: Alert domain model

        Returns:
            AlertItemResponse with calculated age_hours
        """
        age = datetime.now() - alert.date
        return AlertItemResponse(
            id=alert.id,
            alert_type=alert.alert_type.value,
            asset_code=alert.asset_code,
            asset_description=alert.asset_description,
            exchange=alert.exchange,
            country_code=alert.country_code,
            date=alert.date,
            data=alert.data,
            age_hours=int(age.total_seconds() / 3600),
        )

    def _calculate_filters(self, alerts: List[Alert]) -> Dict[str, List[str]]:
        """
        Calculate available filter values from alerts.

        Args:
            alerts: List of alerts to extract filter values from

        Returns:
            Dictionary with available asset_codes, alert_types, and country_codes
        """
        asset_codes = sorted(set(alert.asset_code for alert in alerts))
        alert_types = sorted(set(alert.alert_type.value for alert in alerts))
        country_codes = sorted(
            set(alert.country_code or "" for alert in alerts)
        )

        return {
            "asset_codes": asset_codes,
            "alert_types": alert_types,
            "country_codes": country_codes,
        }
