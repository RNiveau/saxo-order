import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from api.models.alerting import (
    AlertItemResponse,
    AlertsResponse,
    RunAlertsRequest,
    RunAlertsResponse,
)
from client.aws_client import DynamoDBClient
from client.saxo_client import SaxoClient
from model import Alert
from saxo_order.commands.alerting import run_detection_for_asset
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
            Dictionary with available asset_codes, alert_types,
            and country_codes
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

    def _get_last_run_at(
        self, asset_code: str, country_code: Optional[str]
    ) -> Optional[datetime]:
        """
        Get the last execution timestamp for an asset from DynamoDB.

        Args:
            asset_code: Asset identifier
            country_code: Country code (or None for crypto)

        Returns:
            Last execution timestamp or None if never executed
        """
        country_code_value = self.dynamodb_client._normalize_country_code(
            country_code
        )

        response = self.dynamodb_client.dynamodb.Table("alerts").get_item(
            Key={"asset_code": asset_code, "country_code": country_code_value}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            logger.error(f"DynamoDB get_item error: {response}")
            return None

        if "Item" not in response:
            return None

        last_run_at_str = response["Item"].get("last_run_at")
        if not last_run_at_str:
            return None

        try:
            return datetime.fromisoformat(last_run_at_str)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid last_run_at format for {asset_code}: "
                f"{last_run_at_str}"
            )
            return None

    def _is_cooldown_active(
        self, asset_code: str, country_code: Optional[str]
    ) -> tuple[bool, Optional[datetime]]:
        """
        Check if cooldown period is active for an asset.

        Args:
            asset_code: Asset identifier
            country_code: Country code (or None for crypto)

        Returns:
            Tuple of (is_active, next_allowed_at)
            - is_active: True if within 5-minute cooldown
            - next_allowed_at: When next execution is allowed (or None)
        """
        last_run_at = self._get_last_run_at(asset_code, country_code)

        if last_run_at is None:
            return False, None

        now = datetime.now()
        cooldown_duration = timedelta(minutes=5)
        next_allowed_at = last_run_at + cooldown_duration

        is_active = now < next_allowed_at
        return is_active, next_allowed_at if is_active else None

    def _update_last_run_at(
        self, asset_code: str, country_code: Optional[str]
    ) -> None:
        """
        Update the last execution timestamp for an asset in DynamoDB.

        Args:
            asset_code: Asset identifier
            country_code: Country code (or None for crypto)
        """
        country_code_value = self.dynamodb_client._normalize_country_code(
            country_code
        )
        now = datetime.now()

        response = self.dynamodb_client.dynamodb.Table("alerts").update_item(
            Key={"asset_code": asset_code, "country_code": country_code_value},
            UpdateExpression="SET last_run_at = :last_run_at",
            ExpressionAttributeValues={":last_run_at": now.isoformat()},
            ReturnValues="UPDATED_NEW",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            logger.error(f"DynamoDB update_item error: {response}")

    def run_on_demand_detection(
        self,
        request: RunAlertsRequest,
        saxo_client: SaxoClient,
    ) -> RunAlertsResponse:
        """
        Execute on-demand alert detection with cooldown enforcement.

        Args:
            request: RunAlertsRequest with asset_code, country_code, exchange
            saxo_client: SaxoClient for data fetching

        Returns:
            RunAlertsResponse with execution results and cooldown info
        """
        start_time = time.time()

        # Check cooldown
        is_cooldown, next_allowed_at = self._is_cooldown_active(
            request.asset_code, request.country_code
        )

        if is_cooldown and next_allowed_at is not None:
            execution_time_ms = int((time.time() - start_time) * 1000)
            minutes_remaining = int(
                (next_allowed_at - datetime.now()).total_seconds() / 60
            )

            return RunAlertsResponse(
                status="error",
                alerts_detected=0,
                alerts=[],
                execution_time_ms=execution_time_ms,
                message=(
                    f"Alerts recently run. "
                    f"Please wait {minutes_remaining} minutes "
                    "before running again."
                ),
                next_allowed_at=next_allowed_at,
            )

        # Get asset description from Saxo API
        try:
            asset_info = saxo_client.get_asset(
                request.asset_code, request.country_code
            )
            asset_description = asset_info.get(
                "Description", request.asset_code
            )
            saxo_uic = asset_info.get("Identifier")
        except Exception as e:
            logger.error(
                f"Failed to fetch asset info for {request.asset_code}: {e}"
            )
            execution_time_ms = int((time.time() - start_time) * 1000)
            return RunAlertsResponse(
                status="error",
                alerts_detected=0,
                alerts=[],
                execution_time_ms=execution_time_ms,
                message=f"Failed to fetch asset information: {str(e)}",
                next_allowed_at=datetime.now() + timedelta(minutes=5),
            )

        # Run detection algorithms
        try:
            detected_alerts = run_detection_for_asset(
                asset_code=request.asset_code,
                country_code=request.country_code,
                exchange=request.exchange,
                asset_description=asset_description,
                saxo_uic=saxo_uic,
                saxo_client=saxo_client,
                dynamodb_client=self.dynamodb_client,
            )
        except Exception as e:
            logger.error(
                f"Detection failed for {request.asset_code}: {e}",
                exc_info=True,
            )
            execution_time_ms = int((time.time() - start_time) * 1000)
            return RunAlertsResponse(
                status="error",
                alerts_detected=0,
                alerts=[],
                execution_time_ms=execution_time_ms,
                message=f"Alert detection failed: {str(e)}",
                next_allowed_at=datetime.now() + timedelta(minutes=5),
            )

        # Update last_run_at timestamp
        self._update_last_run_at(request.asset_code, request.country_code)

        # Calculate next allowed execution time
        next_allowed_at = datetime.now() + timedelta(minutes=5)

        # Transform alerts to response format
        alert_responses = [
            self._to_response(alert) for alert in detected_alerts
        ]

        execution_time_ms = int((time.time() - start_time) * 1000)

        if len(detected_alerts) > 0:
            status = "success"
            message = f"Detected {len(detected_alerts)} new alerts"
        else:
            status = "no_alerts"
            message = "No new alerts detected"

        return RunAlertsResponse(
            status=status,
            alerts_detected=len(detected_alerts),
            alerts=alert_responses,
            execution_time_ms=execution_time_ms,
            message=message,
            next_allowed_at=next_allowed_at,
        )
