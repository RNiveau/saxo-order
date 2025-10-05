from typing import List, Optional

from pydantic import BaseModel, Field


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
