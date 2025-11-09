from typing import Optional

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
