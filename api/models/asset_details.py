from typing import List, Optional

from pydantic import BaseModel, Field


class AssetDetailResponse(BaseModel):
    asset_id: str = Field(description="Asset ID")
    tradingview_url: Optional[str] = Field(
        default=None,
        description="TradingView URL for the asset",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when last updated",
    )
    is_excluded: Optional[bool] = Field(
        default=False,
        description="True if asset is excluded from alerting",
    )


class AssetExclusionUpdateRequest(BaseModel):
    is_excluded: bool = Field(description="Exclusion status")


class AssetListResponse(BaseModel):
    assets: List[AssetDetailResponse] = Field(description="List of assets")
    count: int = Field(description="Total number of assets")
    excluded_count: Optional[int] = Field(
        default=None, description="Number of excluded assets"
    )
    active_count: Optional[int] = Field(
        default=None, description="Number of active assets"
    )
