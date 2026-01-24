from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertItemResponse(BaseModel):
    id: str = Field(
        description=(
            "Composite identifier "
            "(asset_code_country_code or just asset_code)"
        )
    )
    alert_type: str = Field(description="Type of alert pattern detected")
    asset_code: str = Field(description="Asset symbol or ticker")
    asset_description: str = Field(description="Human-readable asset name")
    exchange: str = Field(
        description="Exchange name (e.g., 'saxo', 'binance')"
    )
    country_code: Optional[str] = Field(
        default=None,
        description="Exchange or country code (null for crypto assets)",
    )
    date: datetime = Field(
        description="ISO 8601 timestamp when alert was generated"
    )
    data: Dict[str, Any] = Field(
        description=(
            "Alert-specific data payload " "(structure varies by alert_type)"
        )
    )
    age_hours: int = Field(
        description="Hours since alert was generated (calculated field)",
        ge=0,
    )
    tradingview_url: Optional[str] = Field(
        default=None,
        description="Custom TradingView URL for this asset (if configured)",
    )


class AlertsResponse(BaseModel):
    alerts: List[AlertItemResponse] = Field(description="List of alert items")
    total_count: int = Field(
        description="Total number of alerts returned (after filtering)", ge=0
    )
    available_filters: Dict[str, List[str]] = Field(
        description="Available filter values based on current data"
    )


class RunAlertsRequest(BaseModel):
    asset_code: str = Field(
        description="Asset identifier code (e.g., 'ITP', 'SAN', 'BTCUSDT')",
        min_length=1,
        max_length=20,
    )
    country_code: Optional[str] = Field(
        default=None,
        description=(
            "Country/market code (e.g., 'xpar', 'xnys'). "
            "Null for crypto assets."
        ),
        min_length=2,
        max_length=10,
    )
    exchange: str = Field(
        description="Exchange identifier ('saxo' or 'binance')",
        pattern="^(saxo|binance)$",
    )


class RunAlertsResponse(BaseModel):
    status: str = Field(
        description="Execution outcome status",
        pattern="^(success|no_alerts|error)$",
    )
    alerts_detected: int = Field(
        description="Count of newly detected alerts (0 or more)", ge=0
    )
    alerts: List[AlertItemResponse] = Field(
        description="Array of newly detected alerts (empty if none found)"
    )
    execution_time_ms: int = Field(
        description="Detection execution duration in milliseconds", ge=0
    )
    message: str = Field(description="Human-readable status message")
    next_allowed_at: datetime = Field(
        description=(
            "ISO 8601 timestamp when next execution is allowed "
            "(5 minutes from now)"
        )
    )
