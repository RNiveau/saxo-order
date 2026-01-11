from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertItemResponse(BaseModel):
    id: str = Field(
        description="Composite identifier (asset_code_country_code or just asset_code)"
    )
    alert_type: str = Field(description="Type of alert pattern detected")
    asset_code: str = Field(description="Asset symbol or ticker")
    asset_description: str = Field(description="Human-readable asset name")
    exchange: str = Field(description="Exchange name (e.g., 'saxo', 'binance')")
    country_code: Optional[str] = Field(
        default=None,
        description="Exchange or country code (null for crypto assets)",
    )
    date: datetime = Field(
        description="ISO 8601 timestamp when alert was generated"
    )
    data: Dict[str, Any] = Field(
        description="Alert-specific data payload (structure varies by alert_type)"
    )
    age_hours: int = Field(
        description="Hours since alert was generated (calculated field)",
        ge=0,
        le=168,
    )


class AlertsResponse(BaseModel):
    alerts: List[AlertItemResponse] = Field(description="List of alert items")
    total_count: int = Field(
        description="Total number of alerts returned (after filtering)", ge=0
    )
    available_filters: Dict[str, List[str]] = Field(
        description="Available filter values based on current data"
    )
