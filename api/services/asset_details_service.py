from typing import List

from api.models.asset_details import AssetDetailResponse, AssetListResponse
from client.aws_client import DynamoDBClient
from utils.logger import Logger

logger = Logger.get_logger("asset_details_service")


class AssetDetailsService:
    """Service for managing asset details and exclusions."""

    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb_client = dynamodb_client

    async def get_asset_details(self, asset_id: str) -> AssetDetailResponse:
        detail = await self.dynamodb_client.get_asset_detail(asset_id)

        if not detail:
            logger.info(f"Asset {asset_id} not found in asset_details table")
            return AssetDetailResponse(asset_id=asset_id, is_excluded=False)

        return AssetDetailResponse(
            asset_id=detail.get("asset_id", asset_id),
            tradingview_url=detail.get("tradingview_url"),
            updated_at=detail.get("updated_at"),
            is_excluded=detail.get("is_excluded", False),
        )

    async def update_exclusion(
        self, asset_id: str, is_excluded: bool
    ) -> AssetDetailResponse:
        success = await self.dynamodb_client.update_asset_exclusion(
            asset_id, is_excluded
        )

        if not success:
            logger.error(f"Failed to update exclusion for {asset_id}")
            raise Exception(f"Failed to update exclusion for {asset_id}")

        logger.info(
            f"Updated exclusion for {asset_id}: is_excluded={is_excluded}"
        )

        return await self.get_asset_details(asset_id)

    async def get_all_excluded_assets(self) -> List[AssetDetailResponse]:
        all_assets = await self.dynamodb_client.get_all_asset_details()
        excluded = [
            AssetDetailResponse(
                asset_id=asset["asset_id"],
                tradingview_url=asset.get("tradingview_url"),
                updated_at=asset.get("updated_at"),
                is_excluded=asset.get("is_excluded", False),
            )
            for asset in all_assets
            if asset.get("is_excluded", False) is True
        ]

        logger.info(f"Found {len(excluded)} excluded assets")
        return excluded

    async def get_all_assets_with_details(self) -> AssetListResponse:
        all_assets = await self.dynamodb_client.get_all_asset_details()

        assets = [
            AssetDetailResponse(
                asset_id=asset["asset_id"],
                tradingview_url=asset.get("tradingview_url"),
                updated_at=asset.get("updated_at"),
                is_excluded=asset.get("is_excluded", False),
            )
            for asset in all_assets
        ]

        excluded_count = sum(1 for a in assets if a.is_excluded)
        active_count = len(assets) - excluded_count

        logger.info(
            f"Retrieved {len(assets)} assets "
            f"({excluded_count} excluded, {active_count} active)"
        )

        return AssetListResponse(
            assets=assets,
            count=len(assets),
            excluded_count=excluded_count,
            active_count=active_count,
        )
