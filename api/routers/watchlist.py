from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_candles_service, get_saxo_client
from api.models.watchlist import (
    AddToWatchlistRequest,
    AddToWatchlistResponse,
    WatchlistResponse,
)
from api.services.indicator_service import IndicatorService
from api.services.watchlist_service import WatchlistService
from client.aws_client import AwsClient, DynamoDBClient
from client.saxo_client import SaxoClient
from services.candles_service import CandlesService
from utils.logger import Logger

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
logger = Logger.get_logger("watchlist_router")


def get_dynamodb_client() -> DynamoDBClient:
    """
    Create DynamoDBClient instance.
    Validates AWS context before allowing access.
    """
    if not AwsClient.is_aws_context():
        raise HTTPException(
            status_code=403,
            detail="AWS context not available. "
            "Set AWS_PROFILE environment variable.",
        )
    return DynamoDBClient()


def get_watchlist_service(
    saxo_client: SaxoClient = Depends(get_saxo_client),
    candles_service: CandlesService = Depends(get_candles_service),
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
) -> WatchlistService:
    """
    Create WatchlistService instance.
    This is a dependency that can be injected into FastAPI endpoints.
    """
    indicator_service = IndicatorService(saxo_client, candles_service)
    return WatchlistService(dynamodb_client, indicator_service)


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Get all watchlist items with current prices and variations.

    Returns:
        WatchlistResponse with all watchlist items
    """
    try:
        return watchlist_service.get_watchlist()
    except Exception as e:
        logger.error(f"Unexpected error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=AddToWatchlistResponse)
async def add_to_watchlist(
    request: AddToWatchlistRequest,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
):
    """
    Add an asset to the watchlist.

    Args:
        request: AddToWatchlistRequest with asset details

    Returns:
        AddToWatchlistResponse with success message
    """
    try:
        dynamodb_client.add_to_watchlist(
            request.asset_id, request.asset_symbol, request.country_code
        )

        return AddToWatchlistResponse(
            message=f"Asset {request.asset_symbol} added to watchlist",
            asset_id=request.asset_id,
            asset_symbol=request.asset_symbol,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error adding to watchlist {request.asset_symbol}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")
