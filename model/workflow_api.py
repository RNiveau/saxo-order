from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkflowListItem(BaseModel):
    """Summarized workflow representation for table display"""

    id: str = Field(..., description="Unique workflow identifier (UUID)")
    name: str = Field(..., description="Human-readable workflow name")
    index: str = Field(..., description="Target index symbol")
    cfd: str = Field(..., description="CFD symbol for order execution")
    enable: bool = Field(..., description="Whether workflow is active")
    dry_run: bool = Field(
        ..., description="Whether workflow is in dry run mode"
    )
    is_us: bool = Field(..., description="Whether workflow targets US market")
    end_date: Optional[str] = Field(
        None, description="Optional expiration date (ISO 8601)"
    )
    primary_indicator: Optional[str] = Field(
        None, description="Indicator type from first condition"
    )
    primary_unit_time: Optional[str] = Field(
        None, description="Unit time from first condition"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class IndicatorDetail(BaseModel):
    """Technical analysis indicator specification"""

    name: str = Field(..., description="Indicator type")
    ut: str = Field(..., description="Unit time for indicator calculation")
    value: Optional[float] = Field(
        None, description="Fixed indicator value (for polarite/zone)"
    )
    zone_value: Optional[float] = Field(
        None, description="Zone upper bound (for zone indicator)"
    )


class CloseDetail(BaseModel):
    """Close candle evaluation parameters"""

    direction: str = Field(
        ..., description="Whether to check above or below indicator"
    )
    ut: str = Field(..., description="Unit time for close candle retrieval")
    spread: float = Field(..., description="Tolerance in points")


class ConditionDetail(BaseModel):
    """Evaluation rule with indicator and close parameters"""

    indicator: IndicatorDetail
    close: CloseDetail
    element: Optional[str] = Field(
        None, description="Specific candle element to check (close, high, low)"
    )


class TriggerDetail(BaseModel):
    """Order generation parameters"""

    ut: str = Field(..., description="Unit time for trigger candle retrieval")
    signal: str = Field(..., description="Signal type")
    location: str = Field(
        ..., description="Where to place order relative to indicator"
    )
    order_direction: str = Field(..., description="Buy or sell direction")
    quantity: float = Field(..., description="Order quantity")


class WorkflowDetail(BaseModel):
    """Complete workflow configuration with all nested structures"""

    id: str = Field(..., description="Unique workflow identifier (UUID)")
    name: str = Field(..., description="Human-readable workflow name")
    index: str = Field(..., description="Target index symbol")
    cfd: str = Field(..., description="CFD symbol for order execution")
    enable: bool = Field(..., description="Whether workflow is active")
    dry_run: bool = Field(
        ..., description="Whether workflow is in dry run mode"
    )
    is_us: bool = Field(..., description="Whether workflow targets US market")
    end_date: Optional[str] = Field(
        None, description="Optional expiration date (ISO 8601)"
    )
    conditions: List[ConditionDetail] = Field(
        ..., description="List of evaluation conditions"
    )
    trigger: TriggerDetail = Field(
        ..., description="Order generation parameters"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class WorkflowListResponse(BaseModel):
    """Paginated response for workflow list endpoint"""

    workflows: List[WorkflowListItem] = Field(
        ..., description="List of workflows for current page"
    )
    total: int = Field(
        ..., description="Total number of workflows matching filters"
    )
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
