from fastapi import APIRouter, Depends, HTTPException

from api.models.tradingview import (
    SetTradingViewLinkRequest,
    SetTradingViewLinkResponse,
)
from client.aws_client import AwsClient, DynamoDBClient
from utils.logger import Logger

router = APIRouter(
    prefix="/api/asset-details/{asset_id}/tradingview",
    tags=["tradingview"],
)
logger = Logger.get_logger("tradingview_router")


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


@router.put("", response_model=SetTradingViewLinkResponse)
async def set_tradingview_link(
    asset_id: str,
    request: SetTradingViewLinkRequest,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
):
    """
    Set or update TradingView URL for an asset.

    Args:
        asset_id: ID of the asset (e.g., 'itp', 'DAX.I')
        request: SetTradingViewLinkRequest with tradingview_url

    Returns:
        SetTradingViewLinkResponse with success message
    """
    try:
        dynamodb_client.set_asset_detail(asset_id, request.tradingview_url)

        return SetTradingViewLinkResponse(
            message=f"TradingView URL updated for {asset_id}",
            asset_id=asset_id,
            tradingview_url=request.tradingview_url,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error setting TradingView link for {asset_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")
