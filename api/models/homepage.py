from typing import List, Optional

from pydantic import BaseModel, Field

from model import Currency


class HomepageItemResponse(BaseModel):
    id: str = Field(description="Unique identifier for the watchlist item")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    description: str = Field(description="Asset description/name")
    current_price: float = Field(description="Current price of the asset")
    variation_pct: float = Field(
        description="Percentage variation from previous period"
    )
    currency: Currency = Field(
        description="Currency code (e.g., 'EUR', 'USD')"
    )
    tradingview_url: Optional[str] = Field(
        default=None,
        description="Custom TradingView URL for this asset",
    )
    exchange: str = Field(
        default="saxo",
        description="Exchange (saxo or binance)",
    )
    ma50_value: float = Field(description="50-day moving average value")
    is_above_ma50: bool = Field(
        description="Whether current price is above MA50"
    )


class HomepageResponse(BaseModel):
    items: List[HomepageItemResponse] = Field(
        description="List of homepage items"
    )
    total: int = Field(description="Total number of items on homepage")
