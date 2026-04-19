from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    last_order_timestamp: Optional[int] = Field(
        None, description="Unix timestamp of most recent order placement"
    )
    last_order_direction: Optional[str] = Field(
        None, description="Direction of most recent order (BUY/SELL)"
    )
    last_order_quantity: Optional[float] = Field(
        None, description="Quantity of most recent order"
    )


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
    x1_date: Optional[str] = Field(
        None, description="First reference point date (for inclined)"
    )
    x1_price: Optional[float] = Field(
        None, description="First reference point price (for inclined)"
    )
    x2_date: Optional[str] = Field(
        None, description="Second reference point date (for inclined)"
    )
    x2_price: Optional[float] = Field(
        None, description="Second reference point price (for inclined)"
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


class AllWorkflowOrderItem(BaseModel):
    """Cross-workflow order item for the all-orders list endpoint."""

    id: str = Field(..., description="Order record UUID")
    workflow_id: str = Field(..., description="Parent workflow UUID")
    workflow_name: str = Field(..., description="Workflow display name")
    placed_at: int = Field(..., description="Unix epoch timestamp (seconds)")
    order_code: str = Field(..., description="Asset code (e.g., 'FRA40.I')")
    order_price: float = Field(..., gt=0, description="Order entry price")
    order_quantity: float = Field(..., gt=0, description="Order quantity")
    order_direction: str = Field(..., description="BUY or SELL")


class PointInput(BaseModel):
    date: str
    price: float = Field(..., gt=0)


class WorkflowIndicatorInput(BaseModel):
    name: str
    ut: str
    value: Optional[float] = None
    zone_value: Optional[float] = None
    x1: Optional[PointInput] = None
    x2: Optional[PointInput] = None


class WorkflowCloseInput(BaseModel):
    direction: str
    ut: str
    spread: float = Field(..., gt=0)


class WorkflowConditionInput(BaseModel):
    indicator: WorkflowIndicatorInput
    close: WorkflowCloseInput
    element: Optional[str] = None


class WorkflowTriggerInput(BaseModel):
    ut: str
    location: str
    order_direction: str
    quantity: float = Field(..., gt=0)


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    index: str = Field(..., min_length=1)
    cfd: str = Field(..., min_length=1)
    enable: bool = True
    dry_run: bool = True
    is_us: bool = False
    end_date: Optional[str] = None
    conditions: List[WorkflowConditionInput] = Field(..., min_length=1)
    trigger: WorkflowTriggerInput

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class WorkflowOrderListItem(BaseModel):
    """Simplified workflow order for API list responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8",
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "placed_at": 1740220200,
                "order_code": "FRA40.I",
                "order_price": 7850.25,
                "order_quantity": 10.0,
                "order_direction": "BUY",
            }
        }
    )

    id: str = Field(..., description="Order record UUID")
    workflow_id: str = Field(..., description="Parent workflow UUID")
    placed_at: int = Field(..., description="Unix epoch timestamp (seconds)")
    order_code: str = Field(..., description="Asset code (e.g., 'FRA40.I')")
    order_price: float = Field(..., gt=0, description="Order entry price")
    order_quantity: float = Field(..., gt=0, description="Order quantity")
    order_direction: str = Field(..., description="BUY or SELL")
