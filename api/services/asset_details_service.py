from typing import List

from api.models.asset_details import AssetDetailResponse, AssetListResponse
from client.aws_client import DynamoDBClient
from utils.logger import Logger

logger = Logger.get_logger("asset_details_service")


class AssetDetailsService:
    """Service for managing asset details and exclusions."""

    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb_client = dynamodb_client

    def get_asset_details(self, asset_id: str) -> AssetDetailResponse:
        """
        Get details for a single asset.

        Args:
            asset_id: Asset identifier

        Returns:
            AssetDetailResponse with asset details
        """
        detail = self.dynamodb_client.get_asset_detail(asset_id)

        if not detail:
            logger.info(f"Asset {asset_id} not found in asset_details table")
            return AssetDetailResponse(asset_id=asset_id, is_excluded=False)

        return AssetDetailResponse(
            asset_id=detail.get("asset_id", asset_id),
            tradingview_url=detail.get("tradingview_url"),
            updated_at=detail.get("updated_at"),
            is_excluded=detail.get("is_excluded", False),
        )

    def update_exclusion(
        self, asset_id: str, is_excluded: bool
    ) -> AssetDetailResponse:
        """
        Update exclusion status for an asset.

        Args:
            asset_id: Asset identifier
            is_excluded: True to exclude, False to un-exclude

        Returns:
            Updated AssetDetailResponse

        Raises:
            Exception: If update fails
        """
        success = self.dynamodb_client.update_asset_exclusion(
            asset_id, is_excluded
        )

        if not success:
            logger.error(f"Failed to update exclusion for {asset_id}")
            raise Exception(f"Failed to update exclusion for {asset_id}")

        logger.info(
            f"Updated exclusion for {asset_id}: is_excluded={is_excluded}"
        )

        return self.get_asset_details(asset_id)

    def get_all_excluded_assets(self) -> List[AssetDetailResponse]:
        """
        Get all excluded assets.

        Returns:
            List of excluded AssetDetailResponse objects
        """
        all_assets = self.dynamodb_client.get_all_asset_details()
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

    def get_all_assets_with_details(self) -> AssetListResponse:
        """
        Get all assets with details and counts.

        Returns:
            AssetListResponse with all assets and counts
        """
        all_assets = self.dynamodb_client.get_all_asset_details()

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
