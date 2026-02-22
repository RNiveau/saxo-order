from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from model.workflow_api import WorkflowOrderListItem


class WorkflowIndicatorInfo(BaseModel):
    name: str = Field(description="Indicator name (e.g., ma50, bbb, bbh)")
    unit_time: str = Field(description="Unit time (e.g., h1, h4, daily)")
    value: Optional[float] = Field(
        None, description="Indicator value if applicable"
    )
    zone_value: Optional[float] = Field(
        None, description="Zone value if applicable"
    )


class WorkflowCloseInfo(BaseModel):
    direction: str = Field(description="Direction (above/below)")
    unit_time: str = Field(description="Unit time (e.g., h1, h4)")
    spread: float = Field(description="Spread value")


class WorkflowConditionInfo(BaseModel):
    indicator: WorkflowIndicatorInfo = Field(
        description="Indicator configuration"
    )
    close: WorkflowCloseInfo = Field(description="Close configuration")
    element: Optional[str] = Field(
        None, description="Element (close/high/low) if specified"
    )


class WorkflowTriggerInfo(BaseModel):
    unit_time: str = Field(description="Trigger unit time")
    signal: str = Field(description="Signal type (e.g., breakout)")
    location: str = Field(description="Location (higher/lower)")
    order_direction: str = Field(description="Order direction (buy/sell)")
    quantity: float = Field(description="Order quantity")


class WorkflowInfo(BaseModel):
    name: str = Field(description="Workflow name")
    index: str = Field(description="Asset index/symbol")
    cfd: str = Field(description="CFD symbol")
    enabled: bool = Field(description="Whether workflow is enabled")
    dry_run: bool = Field(description="Whether workflow is in dry run mode")
    end_date: Optional[str] = Field(
        None, description="End date if specified (YYYY-MM-DD)"
    )
    is_us: bool = Field(
        default=False, description="Whether this is a US market asset"
    )
    conditions: List[WorkflowConditionInfo] = Field(
        description="List of workflow conditions"
    )
    trigger: WorkflowTriggerInfo = Field(description="Trigger configuration")


class AssetWorkflowsResponse(BaseModel):
    asset_symbol: str = Field(description="Asset symbol queried")
    total: int = Field(description="Total number of workflows found")
    workflows: List[WorkflowInfo] = Field(
        description="List of workflows for this asset"
    )


class WorkflowOrderDetail(BaseModel):
    """Complete workflow order details for API single retrieval."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8",
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "workflow_name": "DAX Breakout Strategy",
                "placed_at": "2026-02-22T14:30:00Z",
                "order_code": "FRA40.I",
                "order_price": 7850.25,
                "order_quantity": 10.0,
                "order_direction": "BUY",
                "order_type": "LIMIT",
                "asset_type": "CfdOnIndex",
                "trigger_close": 7845.50,
                "execution_context": "lambda-event-123abc",
            }
        }
    )

    id: str = Field(..., description="Order record UUID")
    workflow_id: str = Field(..., description="Parent workflow UUID")
    workflow_name: str = Field(..., description="Workflow display name")
    placed_at: str = Field(..., description="ISO 8601 timestamp")
    order_code: str = Field(..., description="Asset code")
    order_price: float = Field(..., gt=0, description="Order entry price")
    order_quantity: float = Field(..., gt=0, description="Order quantity")
    order_direction: str = Field(..., description="BUY or SELL")
    order_type: str = Field(..., description="LIMIT or OPEN_STOP")
    asset_type: Optional[str] = Field(None, description="Asset classification")
    trigger_close: Optional[float] = Field(
        None, description="Trigger candle close"
    )
    execution_context: Optional[str] = Field(
        None, description="Execution source"
    )


class WorkflowOrderHistoryResponse(BaseModel):
    """Paginated response for workflow order history."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "orders": [
                    {
                        "id": "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8",
                        "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                        "placed_at": "2026-02-22T14:30:00Z",
                        "order_code": "FRA40.I",
                        "order_price": 7850.25,
                        "order_quantity": 10.0,
                        "order_direction": "BUY",
                    }
                ],
                "total_count": 1,
                "limit": 20,
            }
        }
    )

    workflow_id: str = Field(..., description="Workflow UUID")
    orders: List[WorkflowOrderListItem] = Field(
        default_factory=list,
        description="List of orders (sorted newest first)",
    )
    total_count: int = Field(..., ge=0, description="Total orders in history")
    limit: int = Field(..., ge=1, le=100, description="Requested limit")
