from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_asset_details_service
from api.models.asset_details import (
    AssetDetailResponse,
    AssetExclusionUpdateRequest,
    AssetListResponse,
)
from api.services.asset_details_service import AssetDetailsService
from utils.logger import Logger

router = APIRouter(prefix="/api/asset-details", tags=["asset-details"])
logger = Logger.get_logger("asset_details_router")


@router.get("/excluded/list", response_model=AssetListResponse)
async def list_excluded_assets(
    service: AssetDetailsService = Depends(get_asset_details_service),
):
    """
    Get all excluded assets.

    Returns:
        AssetListResponse with only excluded assets
    """
    try:
        excluded = service.get_all_excluded_assets()
        return AssetListResponse(
            assets=excluded,
            count=len(excluded),
            excluded_count=len(excluded),
            active_count=0,
        )
    except Exception as e:
        logger.error(f"Unexpected error getting excluded assets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=AssetListResponse)
async def list_all_assets(
    service: AssetDetailsService = Depends(get_asset_details_service),
):
    """
    Get all assets with details including exclusion status.

    Returns:
        AssetListResponse with all assets and counts
    """
    try:
        return service.get_all_assets_with_details()
    except Exception as e:
        logger.error(f"Unexpected error getting all assets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset_details(
    asset_id: str,
    service: AssetDetailsService = Depends(get_asset_details_service),
):
    """
    Get asset details including TradingView URL and exclusion status.

    Args:
        asset_id: ID of the asset (e.g., 'itp', 'DAX.I')

    Returns:
        AssetDetailResponse with asset details
    """
    try:
        return service.get_asset_details(asset_id)
    except Exception as e:
        logger.error(f"Unexpected error getting asset details {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{asset_id}/exclusion", response_model=AssetDetailResponse)
async def update_asset_exclusion(
    asset_id: str,
    request: AssetExclusionUpdateRequest,
    service: AssetDetailsService = Depends(get_asset_details_service),
):
    """
    Update exclusion status for an asset.

    Args:
        asset_id: ID of the asset
        request: Exclusion update request body

    Returns:
        Updated AssetDetailResponse
    """
    try:
        return service.update_exclusion(asset_id, request.is_excluded)
    except Exception as e:
        logger.error(
            f"Unexpected error updating exclusion for {asset_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")
