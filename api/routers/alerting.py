from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_dynamodb_client, get_saxo_client
from api.models.alerting import (
    AlertsResponse,
    RunAlertsRequest,
    RunAlertsResponse,
)
from api.services.alerting_service import AlertingService
from client.aws_client import DynamoDBClient
from client.saxo_client import SaxoClient
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
        description=(
            "Filter alerts by alert type " "(e.g., 'combo', 'congestion20')"
        ),
    ),
    country_code: Optional[str] = Query(
        None,
        description=(
            "Filter alerts by country/exchange code "
            "(e.g., 'xpar', 'xnas', or empty for crypto)"
        ),
    ),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertsResponse:
    """
    Get all active alerts from the last 7 days.

    Alerts are automatically expired by DynamoDB TTL after 7 days.
    Supports filtering by asset_code, alert_type, and country_code
    via query parameters.
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


@router.post("/run", response_model=RunAlertsResponse)
async def run_alerts(
    request: RunAlertsRequest,
    service: AlertingService = Depends(get_alerting_service),
    saxo_client: SaxoClient = Depends(get_saxo_client),
) -> RunAlertsResponse:
    """
    Run on-demand alert detection for a specific asset.

    Executes all detection algorithms (combo, congestion, candle patterns)
    on the specified asset and stores results in DynamoDB.

    **Cooldown**: 5-minute cooldown per asset. Requests within cooldown
    return a response with status="error" and the next_allowed_at timestamp.

    **Deduplication**: Only one alert per type per day is stored. Running
    detection twice on the same day won't create duplicate alerts.

    Args:
        request: RunAlertsRequest with asset_code, country_code, exchange
        service: AlertingService dependency
        saxo_client: SaxoClient or MockSaxoClient dependency

    Returns:
        RunAlertsResponse with execution results, alerts, and cooldown info

    Raises:
        HTTPException 500: If detection fails due to internal error
    """
    logger.info(
        f"Running on-demand alert detection for {request.asset_code} "
        f"(country_code={request.country_code}, exchange={request.exchange})"
    )

    try:
        response = service.run_on_demand_detection(request, saxo_client)

        # Log based on response status
        match response.status:
            case "success":
                logger.info(
                    f"Detected {response.alerts_detected} alerts for "
                    f"{request.asset_code} in {response.execution_time_ms}ms"
                )
            case "no_alerts":
                logger.info(
                    f"No alerts detected for {request.asset_code} "
                    f"in {response.execution_time_ms}ms"
                )
            case "error" if "recently run" in response.message:
                logger.info(
                    f"Cooldown active for {request.asset_code}: "
                    f"{response.message}"
                )
            case "error":
                logger.warning(
                    f"Alert detection returned error for "
                    f"{request.asset_code}: {response.message}"
                )

        return response

    except Exception as e:
        logger.error(
            f"Unexpected error during on-demand detection for "
            f"{request.asset_code}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Alert detection failed: {str(e)}",
        )
