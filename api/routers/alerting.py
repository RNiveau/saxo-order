from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_dynamodb_client
from api.models.alerting import AlertsResponse
from api.services.alerting_service import AlertingService
from client.aws_client import DynamoDBClient
from utils.logger import Logger

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = Logger.get_logger("alerting_router")


def get_alerting_service(
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
) -> AlertingService:
    """
    Create AlertingService instance.
    This is a dependency that can be injected into FastAPI endpoints.
    """
    return AlertingService(dynamodb_client)


@router.get("", response_model=AlertsResponse)
async def get_alerts(
    asset_code: Optional[str] = Query(
        None,
        description="Filter alerts by asset code (e.g., 'ITP', 'BTCUSDT')",
    ),
    alert_type: Optional[str] = Query(
        None,
        description="Filter alerts by alert type (e.g., 'combo', 'congestion20')",
    ),
    country_code: Optional[str] = Query(
        None,
        description="Filter alerts by country/exchange code (e.g., 'xpar', 'xnas', or empty for crypto)",
    ),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertsResponse:
    """
    Get all active alerts from the last 7 days.

    Alerts are automatically expired by DynamoDB TTL after 7 days.
    Supports filtering by asset_code, alert_type, and country_code via query parameters.
    Results are sorted by date descending (newest first).

    Args:
        asset_code: Optional filter by specific asset code
        alert_type: Optional filter by specific alert type
        country_code: Optional filter by country/exchange code
        service: AlertingService dependency

    Returns:
        AlertsResponse with filtered alerts and available filter options
    """
    logger.info(
        f"Getting alerts with filters: asset_code={asset_code}, "
        f"alert_type={alert_type}, country_code={country_code}"
    )
    return service.get_all_alerts(asset_code, alert_type, country_code)
