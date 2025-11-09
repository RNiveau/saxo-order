from fastapi import APIRouter, Depends, HTTPException

from api.models.asset_details import AssetDetailResponse
from client.aws_client import AwsClient, DynamoDBClient
from utils.logger import Logger

router = APIRouter(prefix="/api/asset-details", tags=["asset-details"])
logger = Logger.get_logger("asset_details_router")


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


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset_details(
    asset_id: str,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
):
    """
    Get asset details including TradingView URL.

    Args:
        asset_id: ID of the asset (e.g., 'itp', 'DAX.I')

    Returns:
        AssetDetailResponse with asset details
    """
    try:
        detail = dynamodb_client.get_asset_detail(asset_id)

        if not detail:
            return AssetDetailResponse(asset_id=asset_id)

        return AssetDetailResponse(
            asset_id=detail.get("asset_id", asset_id),
            tradingview_url=detail.get("tradingview_url"),
            updated_at=detail.get("updated_at"),
        )
    except Exception as e:
        logger.error(f"Unexpected error getting asset details {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
