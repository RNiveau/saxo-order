from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowTriggerResponse(BaseModel):
    workflow_name: str = Field(
        description="Name of the workflow that fired today"
    )
    direction: str = Field(
        description="Order direction as the Direction enum name (BUY/SELL)"
    )
    order_price: float = Field(
        description="Price of the order the workflow produced"
    )
    trigger_close: Optional[float] = Field(
        default=None,
        description="Market close when the workflow fired, if recorded",
    )
    placed_at: int = Field(description="Epoch seconds when the workflow fired")
    dry_run: bool = Field(
        description="True when the rule fired without committing capital"
    )


class TriagedAssetResponse(BaseModel):
    asset_code: str = Field(description="Asset symbol or ticker")
    asset_description: str = Field(description="Human-readable asset name")
    exchange: str = Field(
        description="Exchange name (e.g., 'saxo', 'binance')"
    )
    country_code: Optional[str] = Field(
        default=None,
        description="Exchange or country code (null for crypto assets)",
    )
    conviction: str = Field(description="Conviction tier: high/watch/noise")
    rank: Optional[int] = Field(
        default=None,
        description="1-based rank within high+watch (null for noise)",
    )
    rationale: str = Field(description="One-line rationale (empty for noise)")
    patterns: List[str] = Field(
        description="Distinct patterns that fired on this asset"
    )
    ma50_slope: Optional[float] = Field(
        default=None, description="MA50 slope used in ranking"
    )
    tradingview_url: Optional[str] = Field(
        default=None, description="Custom TradingView URL if configured"
    )
    workflow_triggers: Optional[List[WorkflowTriggerResponse]] = Field(
        default=None,
        description=(
            "Same-day workflow firings that corroborated this asset. "
            "Omitted when the asset has none."
        ),
    )


class AlertDigestResponse(BaseModel):
    run_date: str = Field(description="Run date (YYYY-MM-DD)")
    created_at: int = Field(description="Run timestamp (epoch seconds)")
    summary: str = Field(description="Overall headline for the day")
    counts: Dict[str, int] = Field(
        description="Tier counts: {high, watch, noise}"
    )
    triaged_assets: List[TriagedAssetResponse] = Field(
        description="Ranked assets for this run"
    )
    fallback_used: bool = Field(
        description="True if the deterministic fallback produced this digest"
    )
    model: str = Field(
        description="Reasoning model used, or 'deterministic-fallback'"
    )


class AlertDigestListResponse(BaseModel):
    digests: List[AlertDigestResponse] = Field(
        description="Full digests for the recent window, newest-first"
    )
