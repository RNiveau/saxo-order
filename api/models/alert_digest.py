from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
