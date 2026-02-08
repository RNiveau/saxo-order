from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import (
    get_binance_client,
    get_candles_service,
    get_dynamodb_client,
    get_saxo_client,
)
from api.models.watchlist import (
    AddToWatchlistRequest,
    AddToWatchlistResponse,
    CheckWatchlistResponse,
    RemoveFromWatchlistResponse,
    UpdateLabelsRequest,
    UpdateLabelsResponse,
    WatchlistResponse,
    WatchlistTag,
)
from api.services.indicator_service import IndicatorService
from api.services.watchlist_service import WatchlistService
from client.aws_client import DynamoDBClient
from client.binance_client import BinanceClient
from client.saxo_client import SaxoClient
from model import AssetType
from services.candles_service import CandlesService
from utils.logger import Logger

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
logger = Logger.get_logger("watchlist_router")


def get_watchlist_service(
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    candles_service: CandlesService = Depends(get_candles_service),
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
) -> WatchlistService:
    """
    Create WatchlistService instance.
    This is a dependency that can be injected into FastAPI endpoints.
    """
    indicator_service = IndicatorService(
        saxo_client, binance_client, candles_service
    )
    return WatchlistService(dynamodb_client, indicator_service)


@router.get("/check/{asset_id}", response_model=CheckWatchlistResponse)
async def check_watchlist(
    asset_id: str,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
):
    """
    Check if an asset is in the watchlist.

    Args:
        asset_id: ID of the asset to check

    Returns:
        CheckWatchlistResponse with in_watchlist boolean
    """
    try:
        in_watchlist = dynamodb_client.is_in_watchlist(asset_id)

        return CheckWatchlistResponse(
            in_watchlist=in_watchlist,
            asset_id=asset_id,
        )
    except Exception as e:
        logger.error(f"Unexpected error checking watchlist {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Get watchlist items for sidebar display (excludes long-term tagged assets).

    Returns:
        WatchlistResponse with watchlist items excluding long-term
    """
    try:
        return watchlist_service.get_watchlist()
    except Exception as e:
        logger.error(f"Unexpected error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/all", response_model=WatchlistResponse)
async def get_all_watchlist(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Get ALL watchlist items including long-term tagged assets.

    Returns:
        WatchlistResponse with all watchlist items
    """
    try:
        return watchlist_service.get_all_watchlist()
    except Exception as e:
        logger.error(f"Unexpected error getting all watchlist: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/long-term", response_model=WatchlistResponse)
async def get_long_term_positions(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Get long-term tagged positions for the dedicated menu.

    Returns:
        WatchlistResponse with long-term positions enriched with current prices
    """
    try:
        return watchlist_service.get_long_term_positions()
    except Exception as e:
        logger.error(f"Unexpected error getting long-term positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=AddToWatchlistResponse)
async def add_to_watchlist(
    request: AddToWatchlistRequest,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
    saxo_client: SaxoClient = Depends(get_saxo_client),
):
    """
    Add an asset to the watchlist.

    Args:
        request: AddToWatchlistRequest with asset details

    Returns:
        AddToWatchlistResponse with success message
    """
    try:
        # For Saxo assets, fetch from API to get real description and metadata
        # For Binance assets, use provided description
        if request.exchange == "saxo":
            asset = saxo_client.get_asset(
                request.asset_id, request.country_code
            )
            description = asset["Description"]
            asset_identifier = asset["Identifier"]
            asset_type = asset["AssetType"]
        else:
            # Binance assets - use provided description and set crypto type
            description = request.description
            asset_identifier = None
            asset_type = AssetType.CRYPTO.value

        # Auto-add crypto tag for Binance assets
        labels = request.labels.copy() if request.labels else []
        if (
            request.exchange == "binance"
            and WatchlistTag.CRYPTO.value not in labels
        ):
            labels.append(WatchlistTag.CRYPTO.value)

        # Auto-add crypto tag for Binance assets
        labels = request.labels.copy() if request.labels else []
        if (
            request.exchange == "binance"
            and WatchlistTag.CRYPTO.value not in labels
        ):
            labels.append(WatchlistTag.CRYPTO.value)

        dynamodb_client.add_to_watchlist(
            request.asset_id,
            request.asset_symbol,
            description,
            request.country_code,
            asset_identifier=asset_identifier,
            asset_type=asset_type,
            labels=labels,
            exchange=request.exchange,
        )

        return AddToWatchlistResponse(
            message=f"Asset {description} added to watchlist",
            asset_id=request.asset_id,
            asset_symbol=request.asset_symbol,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error adding to watchlist {request.asset_symbol}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{asset_id}", response_model=RemoveFromWatchlistResponse)
async def remove_from_watchlist(
    asset_id: str,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
):
    """
    Remove an asset from the watchlist.

    Args:
        asset_id: ID of the asset to remove

    Returns:
        RemoveFromWatchlistResponse with success message
    """
    try:
        dynamodb_client.remove_from_watchlist(asset_id)

        return RemoveFromWatchlistResponse(
            message="Asset removed from watchlist",
            asset_id=asset_id,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error removing from watchlist {asset_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{asset_id}/labels", response_model=UpdateLabelsResponse)
async def update_watchlist_labels(
    asset_id: str,
    request: UpdateLabelsRequest,
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Update labels for a watchlist item.

    Args:
        asset_id: ID of the asset to update
        request: UpdateLabelsRequest with new labels

    Returns:
        UpdateLabelsResponse with success message
    """
    try:
        # Check if asset exists in watchlist
        if not dynamodb_client.is_in_watchlist(asset_id):
            raise HTTPException(
                status_code=404, detail="Asset not found in watchlist"
            )

        # Enforce 6-asset limit for homepage tag
        if WatchlistTag.HOMEPAGE.value in request.labels:
            all_items = dynamodb_client.get_watchlist()
            homepage_count = sum(
                1
                for item in all_items
                if item.get("id") != asset_id
                and WatchlistTag.HOMEPAGE.value in item.get("labels", [])
            )
            if homepage_count >= 6:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Cannot add homepage tag: "
                        "maximum of 6 assets allowed"
                    ),
                )

        # Enforce mutual exclusivity between SLWIN and SHORT_TERM tags
        labels = watchlist_service.enforce_tag_mutual_exclusivity(
            request.labels.copy()
        )

        dynamodb_client.update_watchlist_labels(asset_id, labels)

        return UpdateLabelsResponse(
            message="Labels updated successfully",
            asset_id=asset_id,
            labels=labels,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating labels for {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
