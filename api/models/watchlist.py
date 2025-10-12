from typing import List

from pydantic import BaseModel, Field


class AddToWatchlistRequest(BaseModel):
    asset_id: str = Field(description="Unique identifier for the asset")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    country_code: str = Field(
        default="xpar", description="Country code (e.g., 'xpar')"
    )


class AddToWatchlistResponse(BaseModel):
    message: str = Field(description="Success message")
    asset_id: str = Field(description="Asset ID that was added")
    asset_symbol: str = Field(description="Asset symbol that was added")


class WatchlistItem(BaseModel):
    id: str = Field(description="Unique identifier for the watchlist item")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    country_code: str = Field(description="Country code (e.g., 'xpar')")
    current_price: float = Field(description="Current price of the asset")
    variation_pct: float = Field(
        description="Percentage variation from previous period"
    )
    added_at: str = Field(description="ISO timestamp when added to watchlist")


class WatchlistResponse(BaseModel):
    items: List[WatchlistItem] = Field(description="List of watchlist items")
    total: int = Field(description="Total number of items in watchlist")
