from typing import List, Optional

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    symbol: str = Field(description="Trading symbol/code")
    description: str = Field(
        description="Name or description of the instrument"
    )
    identifier: Optional[int] = Field(
        default=None,
        description="Unique identifier in Saxo system (None for Binance)",
    )
    asset_type: str = Field(
        description="Type of asset (Stock, ETF, Crypto, etc.)"
    )
    exchange: str = Field(description="Exchange name (saxo or binance)")


class SearchResponse(BaseModel):
    results: List[SearchResultItem] = Field(
        description="List of search results matching the keyword"
    )
    total: int = Field(description="Total number of results found")
