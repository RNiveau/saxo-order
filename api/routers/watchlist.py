from fastapi import APIRouter, Depends, HTTPException

from api.models.watchlist import AddToWatchlistRequest, AddToWatchlistResponse
from client.aws_client import AwsClient, DynamoDBClient
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
