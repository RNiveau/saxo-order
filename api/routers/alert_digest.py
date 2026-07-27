from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_dynamodb_client
from api.models.alert_digest import (
    AlertDigestListResponse,
    AlertDigestResponse,
)
from api.services.alert_digest_service import AlertDigestService
from client.aws_client import DynamoDBClient
from utils.logger import Logger

router = APIRouter(prefix="/api/alert-digests", tags=["alert-digests"])
logger = Logger.get_logger("alert_digest_router")


def get_alert_digest_service(
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
) -> AlertDigestService:
    return AlertDigestService(dynamodb_client)


@router.get("", response_model=AlertDigestListResponse)
async def list_alert_digests(
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=365,
        description="Maximum number of digests to return (default all)",
    ),
    service: AlertDigestService = Depends(get_alert_digest_service),
) -> AlertDigestListResponse:
    """
    List recent alert-triage digests, newest-first.

    Returns full digests (including per-asset payloads) so the homepage
    carousel can page client-side without per-day round-trips.
    """
    digests = await service.list_recent(limit=limit)
    return AlertDigestListResponse(digests=digests)


@router.get("/{run_date}", response_model=AlertDigestResponse)
async def get_alert_digest(
    run_date: str,
    service: AlertDigestService = Depends(get_alert_digest_service),
) -> AlertDigestResponse:
    """Get the brief for a specific run date (YYYY-MM-DD)."""
    digest = await service.get_by_run_date(run_date)
    if digest is None:
        raise HTTPException(
            status_code=404,
            detail=f"No digest found for run date {run_date}",
        )
    return digest
