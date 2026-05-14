# Implementation Plan: Workflow Orders List Page

**Branch**: `014-workflow-orders-list` | **Date**: 2026-02-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-workflow-orders-list/spec.md`

## Summary

Add a dedicated "Workflow Orders" page that shows, for each workflow, its **single most recent order** in a filterable list (one row per workflow). The `workflow_orders` DynamoDB table already exists (spec 010) and stores `workflow_name` per item. This feature adds:

1. **Backend**: a scan-based method to retrieve all orders across workflows + a server-side dedup step that keeps, for each `workflow_id`, the row with the largest `placed_at` + a new `GET /api/workflow/orders` endpoint
2. **Frontend**: a new page with workflow-name and direction filters (client-side, applied to the already-deduplicated response), a new route, and a sidebar nav link

No infrastructure changes. No new DynamoDB tables. No new packages.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI + Pydantic v2 (backend), React Router DOM v7+, Vite 7+, Axios (frontend)
**Storage**: AWS DynamoDB `workflow_orders` table — existing, unchanged
**Testing**: pytest (backend) — no frontend testing framework configured
**Target Platform**: Linux / AWS Lambda (backend), Web browser (frontend)
**Project Type**: Web application — backend API + frontend SPA
**Performance Goals**: Page loads all orders in < 2 s; client-side filter updates < 100 ms
**Constraints**: No GSI on `placed_at`; scan + Python sort is acceptable (dataset bounded by 7-day TTL, ≤ 100 records expected); no pagination for MVP
**Scale/Scope**: 5 backend file edits + 3 new frontend files + 2 frontend file edits

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Layered Architecture | ✅ PASS | Router → Service → Client chain preserved. New `get_all_workflow_orders` on client; new `get_all_orders` on service; new route on router. Frontend API calls go through `workflowService` in `services/api.ts`. |
| II | Clean Code First | ✅ PASS | Scan + Python sort + dict-based dedup reuses existing patterns. No new abstractions. |
| III | Configuration-Driven | ✅ PASS | No new env vars or config keys required. |
| IV | Safe Deployment | ✅ PASS | No infrastructure changes. DynamoDB table and IAM policies already exist. |
| V | Domain Model Integrity | ✅ PASS | `workflow_name` is already stored in every DynamoDB item by `record_workflow_order`. New model `AllWorkflowOrderItem` extends the domain cleanly. |

**All gates pass. Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/014-workflow-orders-list/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   └── all-workflow-orders-api.yaml
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
# Backend — existing files modified
model/workflow_api.py              ← add AllWorkflowOrderItem model
api/models/workflow.py             ← add AllWorkflowOrdersResponse model
client/aws_client.py               ← add get_all_workflow_orders()
services/workflow_service.py       ← add get_all_orders()
api/routers/workflow.py            ← add GET /api/workflow/orders endpoint

# Frontend — new files
frontend/src/pages/WorkflowOrders.tsx     ← new page component
frontend/src/pages/WorkflowOrders.css     ← new page styles

# Frontend — existing files modified
frontend/src/services/api.ts              ← add AllWorkflowOrderItem, AllWorkflowOrdersResponse, getAllOrders()
frontend/src/App.tsx                      ← add /workflow-orders route
frontend/src/components/Sidebar.tsx       ← add "Workflow Orders" nav link
```

**Structure Decision**: Web application (Option 2). Backend follows existing layered pattern. Frontend follows existing page + service pattern. No new directories created.

## Phase 0: Research

See [research.md](./research.md) — all decisions resolved.

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md).

### API Contracts

See [contracts/all-workflow-orders-api.yaml](./contracts/all-workflow-orders-api.yaml).

New endpoint: `GET /api/workflow/orders?limit=100`

Existing endpoints are **unchanged**.

### Quickstart

See [quickstart.md](./quickstart.md).

## Implementation Approach

### Backend

**`client/aws_client.py`** — new method:
```python
def get_all_workflow_orders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    # Scan workflow_orders table (same pattern as get_all_workflows)
    # Sort result by placed_at descending in Python
    # Apply limit after sort
```

> The client returns ALL rows from the scan (deduplication is the service's responsibility, see below). The optional `limit` here is a safety cap; the service will pass no limit so it can dedupe before truncation.

**`model/workflow_api.py`** — new model:
```python
class AllWorkflowOrderItem(BaseModel):
    # All fields from WorkflowOrderListItem + workflow_name: str
```

**`services/workflow_service.py`** — new method (deduplicates by `workflow_id`, keeping the row with the largest `placed_at`):
```python
def get_all_orders(self, limit: int = 100) -> List[AllWorkflowOrderItem]:
    orders_data = self.dynamodb_client.get_all_workflow_orders()  # no limit yet
    latest_by_workflow: Dict[str, Dict[str, Any]] = {}
    for order in orders_data:
        workflow_id = order["workflow_id"]
        existing = latest_by_workflow.get(workflow_id)
        if existing is None or order["placed_at"] > existing["placed_at"]:
            latest_by_workflow[workflow_id] = order
    deduped = sorted(
        latest_by_workflow.values(),
        key=lambda o: o["placed_at"],
        reverse=True,
    )[:limit]
    return [self._convert_all_order_to_item(order) for order in deduped]
```

> Limit is applied **after** deduplication so the user always sees the top-N most-recent workflows, never N rows from a single noisy workflow.

**`api/models/workflow.py`** — new response model:
```python
class AllWorkflowOrdersResponse(BaseModel):
    orders: List[AllWorkflowOrderItem]
    total_count: int
    limit: int
```

**`api/routers/workflow.py`** — new route:
```python
@router.get("/orders", response_model=AllWorkflowOrdersResponse)
async def get_all_workflow_orders(limit: int = Query(100, ge=1, le=100), ...):
```

### Frontend

**`services/api.ts`** — new interfaces + service method:
- `AllWorkflowOrderItem` (includes `workflow_name`)
- `AllWorkflowOrdersResponse`
- `workflowService.getAllOrders(limit: number): Promise<AllWorkflowOrdersResponse>`

**`pages/WorkflowOrders.tsx`**:
- Fetches from `workflowService.getAllOrders()`
- Client-side filter state: selected `workflowName` (dropdown from unique names in results) + `direction` (All / BUY / SELL)
- Table rows: timestamp, workflow name, asset code, BUY/SELL badge, price, quantity
- Empty state when no orders or no filter match

**`App.tsx`**: add `<Route path="/workflow-orders" element={<WorkflowOrders />} />`

**`Sidebar.tsx`**: add nav link with 📋 icon to `/workflow-orders`
