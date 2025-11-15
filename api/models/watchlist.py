from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from model import Currency


class WatchlistTag(str, Enum):
    SHORT_TERM = "short-term"
    LONG_TERM = "long-term"


class AddToWatchlistRequest(BaseModel):
    asset_id: str = Field(description="Unique identifier for the asset")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    description: str = Field(description="Asset description/name")
    country_code: str = Field(
        default="xpar", description="Country code (e.g., 'xpar')"
    )
    labels: List[str] = Field(
        default_factory=list,
        description="Labels for the asset (e.g., ['short-term'])",
    )


class AddToWatchlistResponse(BaseModel):
    message: str = Field(description="Success message")
    asset_id: str = Field(description="Asset ID that was added")
    asset_symbol: str = Field(description="Asset symbol that was added")


class WatchlistItem(BaseModel):
    id: str = Field(description="Unique identifier for the watchlist item")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    description: str = Field(description="Asset description/name")
    country_code: str = Field(description="Country code (e.g., 'xpar')")
    current_price: float = Field(description="Current price of the asset")
    variation_pct: float = Field(
        description="Percentage variation from previous period"
    )
    currency: Currency = Field(
        description="Currency code (e.g., 'EUR', 'USD')"
    )
    added_at: str = Field(description="ISO timestamp when added to watchlist")
    labels: List[str] = Field(
        default_factory=list,
        description="Labels for the asset (e.g., ['short-term'])",
    )
    tradingview_url: Optional[str] = Field(
        default=None,
        description="Custom TradingView URL for this asset",
    )


class WatchlistResponse(BaseModel):
    items: List[WatchlistItem] = Field(description="List of watchlist items")
    total: int = Field(description="Total number of items in watchlist")


class RemoveFromWatchlistResponse(BaseModel):
    message: str = Field(description="Success message")
    asset_id: str = Field(description="Asset ID that was removed")


class CheckWatchlistResponse(BaseModel):
    in_watchlist: bool = Field(description="Whether asset is in watchlist")
    asset_id: str = Field(description="Asset ID that was checked")


class UpdateLabelsRequest(BaseModel):
    labels: List[str] = Field(description="Labels to set for the asset")


class UpdateLabelsResponse(BaseModel):
    message: str = Field(description="Success message")
    asset_id: str = Field(description="Asset ID that was updated")
    labels: List[str] = Field(description="Updated labels")
