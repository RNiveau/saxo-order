# Data Model: Workflow Orders List Page

**Feature**: 014-workflow-orders-list
**Date**: 2026-02-24

## Overview

No new DynamoDB tables or schema changes. All data is read from the existing `workflow_orders` table. One new domain model is added to expose `workflow_name` in the cross-workflow list response.

---

## Existing DynamoDB Table: `workflow_orders`

| Field | Type | Notes |
|-------|------|-------|
| `workflow_id` | String (PK) | UUID of the parent workflow |
| `placed_at` | Number (SK) | Unix epoch timestamp (seconds) |
| `id` | String | UUID of this order record |
| `workflow_name` | String | Display name captured at order placement time |
| `order_code` | String | Asset code (e.g. `FRA40.I`) |
| `order_price` | Decimal | Entry price (> 0) |
| `order_quantity` | Decimal | Order size (> 0) |
| `order_direction` | String | `BUY` or `SELL` |
| `order_type` | String | `LIMIT` or `OPEN_STOP` |
| `asset_type` | String (optional) | Asset classification (e.g. `CfdOnIndex`) |
| `trigger_close` | Decimal (optional) | Trigger candle close price |
| `execution_context` | String (optional) | Lambda event ID or CLI user |
| `ttl` | Number | Unix epoch — auto-deleted 7 days after `placed_at` |

**Access pattern (new)**: Full table scan → sort by `placed_at` descending → apply limit

---

## New Backend Model: `AllWorkflowOrderItem`

Location: `model/workflow_api.py`

Extends the data exposed by `WorkflowOrderListItem` with `workflow_name`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | ✅ | Order record UUID |
| `workflow_id` | str | ✅ | Parent workflow UUID |
| `workflow_name` | str | ✅ | Workflow display name at order placement time |
| `placed_at` | int | ✅ | Unix epoch timestamp (seconds) |
| `order_code` | str | ✅ | Asset code |
| `order_price` | float | ✅ | Entry price (> 0) |
| `order_quantity` | float | ✅ | Order quantity (> 0) |
| `order_direction` | str | ✅ | `BUY` or `SELL` |

> Note: `placed_at` is stored as epoch (Number) in DynamoDB and returned as `int`. This matches the existing `OrderHistoryItem` TypeScript interface which also uses `placed_at: number`.

---

## New API Response Model: `AllWorkflowOrdersResponse`

Location: `api/models/workflow.py`

| Field | Type | Description |
|-------|------|-------------|
| `orders` | `List[AllWorkflowOrderItem]` | Flat list of all orders, sorted newest first |
| `total_count` | int | Number of orders returned |
| `limit` | int | Requested limit (echoed back) |

---

## New Frontend TypeScript Interfaces

Location: `frontend/src/services/api.ts`

### `AllWorkflowOrderItem`

```ts
export interface AllWorkflowOrderItem {
  id: string;
  workflow_id: string;
  workflow_name: string;
  placed_at: number;       // epoch seconds
  order_code: string;
  order_price: number;
  order_quantity: number;
  order_direction: string; // "BUY" | "SELL"
}
```

### `AllWorkflowOrdersResponse`

```ts
export interface AllWorkflowOrdersResponse {
  orders: AllWorkflowOrderItem[];
  total_count: number;
  limit: number;
}
```

---

## Unchanged Models

| Model | Location | Status |
|-------|----------|--------|
| `WorkflowOrderListItem` | `model/workflow_api.py` | Unchanged |
| `WorkflowOrderHistoryResponse` | `api/models/workflow.py` | Unchanged |
| `OrderHistoryItem` | `frontend/src/services/api.ts` | Unchanged |
| `OrderHistoryResponse` | `frontend/src/services/api.ts` | Unchanged |
