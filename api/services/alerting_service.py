import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cachetools import TTLCache

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
        self._alerts_cache: TTLCache = TTLCache(maxsize=1, ttl=3600)
        self._cache_lock = asyncio.Lock()

    async def get_all_alerts(
        self,
        asset_code: Optional[str] = None,
        alert_type: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> AlertsResponse:
        cache_key = "alerts_base_data"

        async with self._cache_lock:
            if cache_key in self._alerts_cache:
                logger.debug("Using cached alerts data")
                cached_data = self._alerts_cache[cache_key]
                all_alerts = cached_data["all_alerts"]
                tradingview_links = cached_data["tradingview_links"]
            else:
                logger.info("Cache miss - fetching alerts from DynamoDB")
                all_alerts = await self.dynamodb_client.get_all_alerts()
                excluded_asset_ids = (
                    await self.dynamodb_client.get_excluded_assets()
                )
                original_count = len(all_alerts)
                all_alerts = [
                    alert
                    for alert in all_alerts
                    if (
                        f"{alert.asset_code}:{alert.country_code}"
                        if alert.country_code
                        else alert.asset_code
                    )
                    not in excluded_asset_ids
                ]
                filtered_count = original_count - len(all_alerts)

                if filtered_count > 0:
                    logger.info(
                        f"Filtered {filtered_count} alerts "
                        f"from excluded assets"
                    )

                tradingview_links = (
                    await self.dynamodb_client.get_all_tradingview_links()
                )

                self._alerts_cache[cache_key] = {
                    "all_alerts": all_alerts,
                    "tradingview_links": tradingview_links,
                }
                logger.info(
                    f"Cached {len(all_alerts)} alerts with "
                    f"{len(tradingview_links)} TradingView links"
                )

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

        filtered_alerts.sort(key=lambda a: a.date, reverse=True)

        alert_items = []
        for alert in filtered_alerts:
            asset_id = (
                f"{alert.asset_code}:{alert.country_code}"
                if alert.country_code
                else alert.asset_code
            )
            tradingview_url = tradingview_links.get(asset_id)
            alert_items.append(self._to_response(alert, tradingview_url))

        filters = self._calculate_filters(all_alerts)

        return AlertsResponse(
            alerts=alert_items,
            total_count=len(alert_items),
            available_filters=filters,
        )

    def _to_response(
        self, alert: Alert, tradingview_url: Optional[str] = None
    ) -> AlertItemResponse:
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
            age_hours=max(0, int(age.total_seconds() / 3600)),
            tradingview_url=tradingview_url,
        )

    def _calculate_filters(self, alerts: List[Alert]) -> Dict[str, List[str]]:
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

    def invalidate_cache(self) -> None:
        self._alerts_cache.clear()
        logger.info("Alerts cache invalidated")

    async def _is_cooldown_active(
        self, asset_code: str, country_code: Optional[str]
    ) -> tuple[bool, Optional[datetime]]:
        last_run_at = await self.dynamodb_client.get_last_run_at(
            asset_code, country_code
        )

        if last_run_at is None:
            return False, None

        now = datetime.now()
        cooldown_duration = timedelta(minutes=5)
        next_allowed_at = last_run_at + cooldown_duration

        is_active = now < next_allowed_at
        return is_active, next_allowed_at if is_active else None

    async def run_on_demand_detection(
        self,
        request: RunAlertsRequest,
        saxo_client: SaxoClient,
    ) -> RunAlertsResponse:
        start_time = time.time()

        is_cooldown, next_allowed_at = await self._is_cooldown_active(
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

        try:
            detected_alerts = await run_detection_for_asset(
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

        if detected_alerts:
            self.invalidate_cache()

        await self.dynamodb_client.update_last_run_at(
            request.asset_code, request.country_code
        )

        next_allowed_at = datetime.now() + timedelta(minutes=5)

        tradingview_url = None
        try:
            tradingview_url = await self.dynamodb_client.get_tradingview_link(
                request.asset_code
            )
        except Exception as e:
            logger.warning(
                f"Failed to get TradingView link for {request.asset_code}: {e}"
            )

        alert_responses = [
            self._to_response(alert, tradingview_url)
            for alert in detected_alerts
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
