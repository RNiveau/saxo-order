from pydantic import BaseModel, Field


class SetTradingViewLinkRequest(BaseModel):
    tradingview_url: str = Field(
        description="TradingView URL for the asset",
        min_length=1,
    )


class SetTradingViewLinkResponse(BaseModel):
    message: str = Field(description="Success message")
    asset_id: str = Field(description="Asset ID that was updated")
    tradingview_url: str = Field(description="TradingView URL that was set")
