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
