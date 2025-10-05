from typing import List

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    symbol: str = Field(description="Trading symbol/code")
    description: str = Field(
        description="Name or description of the instrument"
    )
    identifier: int = Field(description="Unique identifier in Saxo system")
    asset_type: str = Field(description="Type of asset (Stock, ETF, etc.)")


class SearchResponse(BaseModel):
    results: List[SearchResultItem] = Field(
        description="List of search results matching the keyword"
    )
    total: int = Field(description="Total number of results found")
