# Data Model: Workflow Order History Tracking

**Feature**: 010-workflow-execution-tracking
**Date**: 2026-02-22
**Status**: Phase 1 Design

This document defines the data structures and domain models for tracking workflow order placements.

---

## Entity Relationship Overview

```
Workflow (existing)
    ↓ 1:N
WorkflowOrder (new)
    → References Workflow via workflow_id (UUID)
    → Self-contained order details (no external joins)
```

---

## 1. WorkflowOrder (Domain Model)

**Purpose**: Represents a single order placed by a workflow

**Location**: `model/workflow.py` (new class)

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | str (UUID) | Yes | Unique order record identifier | UUID v4 format |
| `workflow_id` | str (UUID) | Yes | Reference to parent workflow | Must exist in workflows table |
| `workflow_name` | str | Yes | Workflow display name (denormalized) | 1-200 chars |
| `placed_at` | int | Yes | Order placement timestamp | Unix epoch seconds |
| `order_code` | str | Yes | Asset code (e.g., "FRA40.I") | 1-50 chars |
| `order_price` | Decimal | Yes | Order entry price | > 0 |
| `order_quantity` | Decimal | Yes | Order quantity/size | > 0 |
| `order_direction` | str (enum) | Yes | Buy or Sell | Direction.BUY \| Direction.SELL |
| `order_type` | str (enum) | Yes | Order type | OrderType.LIMIT \| OrderType.OPEN_STOP |
| `asset_type` | str (enum) | No | Asset classification | AssetType enum values |
| `trigger_close` | Decimal | No | Trigger candle close price | >= 0 |
| `execution_context` | str | No | Lambda event ID or CLI user | 1-200 chars |
| `ttl` | int | Yes | TTL expiration timestamp | Unix epoch (placed_at + 604800) |

**Python Dataclass Definition**:

```python
# model/workflow.py

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from model.order import Direction, OrderType
from model.asset import AssetType

@dataclass
class WorkflowOrder:
    """Domain model for a workflow order placement event."""

    id: str  # UUID
    workflow_id: str  # UUID
    workflow_name: str
    placed_at: int  # Unix epoch seconds
    order_code: str
    order_price: Decimal
    order_quantity: Decimal
    order_direction: Direction
    order_type: OrderType
    asset_type: Optional[AssetType] = None
    trigger_close: Optional[Decimal] = None
    execution_context: Optional[str] = None
    ttl: int  # Unix epoch (placed_at + 7 days)

    def __post_init__(self):
        """Validate order data after initialization."""
        if self.order_price <= 0:
            raise ValueError("order_price must be positive")
        if self.order_quantity <= 0:
            raise ValueError("order_quantity must be positive")
        if self.ttl <= self.placed_at:
            raise ValueError("ttl must be greater than placed_at")
```

**Business Rules**:
- Order records are immutable after creation (no updates)
- TTL must be exactly 7 days (604800 seconds) from placed_at
- workflow_name is denormalized for display without joins
- order_direction and order_type must use existing enums from model/

**State Transitions**: None (orders are immutable, write-once)

---

## 2. WorkflowOrderListItem (API Response Model)

**Purpose**: Simplified order data for list views and API responses

**Location**: `model/workflow_api.py` (new class)

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | Yes | Order record ID |
| `workflow_id` | str | Yes | Parent workflow ID |
| `placed_at` | str | Yes | ISO 8601 timestamp |
| `order_code` | str | Yes | Asset code |
| `order_price` | float | Yes | Entry price |
| `order_quantity` | float | Yes | Order size |
| `order_direction` | str | Yes | BUY or SELL |

**Pydantic Model Definition**:

```python
# model/workflow_api.py

from pydantic import BaseModel, Field

class WorkflowOrderListItem(BaseModel):
    """Simplified workflow order for API list responses."""

    id: str = Field(..., description="Order record UUID")
    workflow_id: str = Field(..., description="Parent workflow UUID")
    placed_at: str = Field(..., description="ISO 8601 timestamp")
    order_code: str = Field(..., description="Asset code (e.g., 'FRA40.I')")
    order_price: float = Field(..., gt=0, description="Order entry price")
    order_quantity: float = Field(..., gt=0, description="Order quantity")
    order_direction: str = Field(..., description="BUY or SELL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8",
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "placed_at": "2026-02-22T14:30:00Z",
                "order_code": "FRA40.I",
                "order_price": 7850.25,
                "order_quantity": 10.0,
                "order_direction": "BUY"
            }
        }
```

**Conversion from Domain Model**:

```python
# services/workflow_service.py

def _convert_order_to_list_item(
    self, order: WorkflowOrder
) -> WorkflowOrderListItem:
    """Convert domain model to API list item."""
    return WorkflowOrderListItem(
        id=order.id,
        workflow_id=order.workflow_id,
        placed_at=datetime.datetime.fromtimestamp(
            order.placed_at, tz=datetime.timezone.utc
        ).isoformat(),
        order_code=order.order_code,
        order_price=float(order.order_price),
        order_quantity=float(order.order_quantity),
        order_direction=order.order_direction.name,
    )
```

---

## 3. WorkflowOrderDetail (API Response Model)

**Purpose**: Complete order details for single order retrieval

**Location**: `api/models/workflow.py` (new class)

**Attributes**: All fields from WorkflowOrderListItem plus:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow_name` | str | Yes | Workflow display name |
| `order_type` | str | Yes | LIMIT or OPEN_STOP |
| `asset_type` | str | No | Asset classification |
| `trigger_close` | float | No | Trigger candle close price |
| `execution_context` | str | No | Lambda event ID or CLI user |

**Pydantic Model Definition**:

```python
# api/models/workflow.py

from pydantic import BaseModel, Field
from typing import Optional

class WorkflowOrderDetail(BaseModel):
    """Complete workflow order details for API single retrieval."""

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
    trigger_close: Optional[float] = Field(None, description="Trigger candle close")
    execution_context: Optional[str] = Field(None, description="Execution source")

    class Config:
        json_schema_extra = {
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
                "execution_context": "lambda-event-123abc"
            }
        }
```

---

## 4. WorkflowOrderHistoryResponse (API Response Model)

**Purpose**: Paginated list response for order history endpoint

**Location**: `api/models/workflow.py` (new class)

**Pydantic Model Definition**:

```python
# api/models/workflow.py

from pydantic import BaseModel, Field
from typing import List

class WorkflowOrderHistoryResponse(BaseModel):
    """Paginated response for workflow order history."""

    workflow_id: str = Field(..., description="Workflow UUID")
    orders: List[WorkflowOrderListItem] = Field(
        default_factory=list,
        description="List of orders (sorted newest first)"
    )
    total_count: int = Field(..., ge=0, description="Total orders in history")
    limit: int = Field(..., ge=1, le=100, description="Requested limit")

    class Config:
        json_schema_extra = {
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
                        "order_direction": "BUY"
                    }
                ],
                "total_count": 1,
                "limit": 20
            }
        }
```

---

## 5. Updated WorkflowListItem (Existing Model Extension)

**Purpose**: Add last order fields to existing workflow list response

**Location**: `model/workflow_api.py` (modify existing class)

**New Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `last_order_timestamp` | str \| None | No | ISO 8601 timestamp of most recent order |
| `last_order_direction` | str \| None | No | BUY or SELL |
| `last_order_quantity` | float \| None | No | Order quantity |

**Modified Pydantic Model**:

```python
# model/workflow_api.py (MODIFY existing class)

class WorkflowListItem(BaseModel):
    """Workflow summary for list views."""

    id: str
    name: str
    index: str
    cfd: str
    enable: bool
    dry_run: bool
    is_us: bool
    end_date: Optional[str] = None
    primary_indicator: Optional[str] = None
    primary_unit_time: Optional[str] = None
    created_at: str
    updated_at: str

    # NEW FIELDS (Phase 1):
    last_order_timestamp: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of most recent order placement"
    )
    last_order_direction: Optional[str] = Field(
        None,
        description="Direction of last order (BUY or SELL)"
    )
    last_order_quantity: Optional[float] = Field(
        None,
        gt=0,
        description="Quantity of last order"
    )
```

**Backend Service Logic**:

```python
# services/workflow_service.py (MODIFY existing method)

def list_workflows(self) -> List[WorkflowListItem]:
    """List all workflows with last order information."""
    workflows = self._get_cached_workflows()
    workflow_items = []

    for wf in workflows:
        # Get last order for this workflow
        last_order = self._get_last_order_for_workflow(wf["id"])

        workflow_items.append(
            WorkflowListItem(
                id=wf["id"],
                name=wf["name"],
                # ... existing fields ...
                # NEW: Add last order fields
                last_order_timestamp=last_order.get("placed_at") if last_order else None,
                last_order_direction=last_order.get("order_direction") if last_order else None,
                last_order_quantity=last_order.get("order_quantity") if last_order else None,
            )
        )

    return workflow_items

def _get_last_order_for_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
    """Get most recent order for a workflow (cached)."""
    orders = self.dynamodb_client.get_workflow_orders(workflow_id, limit=1)
    if orders:
        return orders[0]
    return None
```

---

## 6. DynamoDB Table Schema

**Table Name**: `workflow_orders`

**Primary Key**:
- **Partition Key**: `workflow_id` (String) - Workflow UUID
- **Sort Key**: `placed_at` (Number) - Unix epoch timestamp

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | S | Order record UUID (not a key) |
| `workflow_id` | S | Partition key |
| `placed_at` | N | Sort key (epoch seconds) |
| `workflow_name` | S | Denormalized workflow name |
| `order_code` | S | Asset code |
| `order_price` | N | Entry price (as Decimal) |
| `order_quantity` | N | Order quantity (as Decimal) |
| `order_direction` | S | BUY or SELL |
| `order_type` | S | LIMIT or OPEN_STOP |
| `asset_type` | S | Asset classification (optional) |
| `trigger_close` | N | Trigger candle close (optional) |
| `execution_context` | S | Lambda/CLI identifier (optional) |
| `ttl` | N | TTL expiration timestamp |

**Indexes**: None (partition + sort key sufficient)

**TTL Configuration**:
- Attribute: `ttl`
- Enabled: True
- Expiration: 7 days (604800 seconds) from `placed_at`

**Access Patterns**:
1. Query orders by workflow_id, sorted by placed_at DESC
2. Get single order by id (Scan, but rare operation)
3. Get last order for workflow (Query with limit=1)

---

## 7. Data Validation Rules

**WorkflowOrder Creation**:
- `workflow_id` must exist in workflows table (FK validation)
- `order_price` and `order_quantity` must be positive
- `order_direction` must be valid Direction enum value
- `order_type` must be valid OrderType enum value
- `ttl` must equal `placed_at + 604800`

**API Input Validation**:
- workflow_id must be valid UUID format
- limit parameter must be 1-100 (default 20)
- Timestamps must be valid ISO 8601 format

**DynamoDB Write Validation**:
- Convert float to Decimal for price/quantity fields
- Convert enum values to strings before storage
- Use reserved word protection for 'ttl' attribute

---

## 8. Data Conversion Patterns

### Domain Model ← DynamoDB Item:

```python
def _dynamodb_to_domain(item: Dict[str, Any]) -> WorkflowOrder:
    """Convert DynamoDB item to domain model."""
    return WorkflowOrder(
        id=item["id"],
        workflow_id=item["workflow_id"],
        workflow_name=item["workflow_name"],
        placed_at=int(item["placed_at"]),
        order_code=item["order_code"],
        order_price=Decimal(str(item["order_price"])),
        order_quantity=Decimal(str(item["order_quantity"])),
        order_direction=Direction[item["order_direction"]],
        order_type=OrderType[item["order_type"]],
        asset_type=AssetType[item["asset_type"]] if item.get("asset_type") else None,
        trigger_close=Decimal(str(item["trigger_close"])) if item.get("trigger_close") else None,
        execution_context=item.get("execution_context"),
        ttl=int(item["ttl"]),
    )
```

### Domain Model → DynamoDB Item:

```python
def _domain_to_dynamodb(order: WorkflowOrder) -> Dict[str, Any]:
    """Convert domain model to DynamoDB item."""
    item = {
        "id": order.id,
        "workflow_id": order.workflow_id,
        "workflow_name": order.workflow_name,
        "placed_at": order.placed_at,
        "order_code": order.order_code,
        "order_price": float(order.order_price),
        "order_quantity": float(order.order_quantity),
        "order_direction": order.order_direction.name,
        "order_type": order.order_type.name,
        "ttl": order.ttl,
    }

    if order.asset_type:
        item["asset_type"] = order.asset_type.name
    if order.trigger_close:
        item["trigger_close"] = float(order.trigger_close)
    if order.execution_context:
        item["execution_context"] = order.execution_context

    return DynamoDBClient._convert_floats_to_decimal(item)
```

---

## Summary

This data model design:
- ✅ Uses existing domain models (Direction, OrderType, AssetType enums)
- ✅ Follows existing patterns (WorkflowListItem extension)
- ✅ Provides immutable order records (write-once, no updates)
- ✅ Enables efficient queries (partition + sort key)
- ✅ Includes TTL for automatic cleanup
- ✅ Separates domain models from API models (clean architecture)
- ✅ Validates all business rules at creation time

**Next**: Create API contracts (OpenAPI specification) based on these models.
