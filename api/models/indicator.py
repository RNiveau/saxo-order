from typing import List

from pydantic import BaseModel, Field


class MovingAverageInfo(BaseModel):
    period: int = Field(
        description="Moving average period (e.g., 7, 20, 50, 200)"
    )
    value: float = Field(description="Moving average value")
    is_above: bool = Field(
        description="True if current price is above MA, False if below"
    )
    unit_time: str = Field(
        description="Unit time of the moving average (daily, weekly, monthly)"
    )


class AssetIndicatorsResponse(BaseModel):
    asset_symbol: str = Field(description="Asset symbol queried")
    current_price: float = Field(description="Current price (latest close)")
    variation_pct: float = Field(
        description="Percentage variation from previous period's close"
    )
    unit_time: str = Field(
        description="Unit time used for calculations (daily, weekly, monthly)"
    )
    moving_averages: List[MovingAverageInfo] = Field(
        description="List of moving averages with their values and position"
    )
