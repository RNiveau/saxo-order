# Research: Workflow Orders List Page

**Feature**: 014-workflow-orders-list
**Date**: 2026-02-24

## Decision 1: Cross-workflow query strategy (scan vs GSI)

**Decision**: DynamoDB table scan on `workflow_orders` + Python sort by `placed_at` descending

**Rationale**: The `workflow_orders` table has `workflow_id` as PK and `placed_at` as SK. There is no GSI on `placed_at` alone. A scan is acceptable because:
- The 7-day TTL bounds the dataset to at most ~7 days of orders
- Typical order volume for automated workflows is low (tens to low hundreds per week)
- A scan is the same pattern already used for `workflows`, `watchlist`, `alerts`, and `asset_details` tables (see `client/aws_client.py`)
- Adding a GSI would require infrastructure changes (Pulumi), which is out of scope for MVP

**Alternatives considered**:
- Add a GSI on `placed_at` — rejected (requires Pulumi infra change, out of scope, premature optimisation for the dataset size)
- Query per workflow then merge in service — rejected (requires fetching all workflow IDs first, then N queries; more complex and slower than one scan for ≤ 100 records)

---

## Decision 2: New model vs extending WorkflowOrderListItem

**Decision**: New `AllWorkflowOrderItem` model in `model/workflow_api.py` that mirrors `WorkflowOrderListItem` and adds `workflow_name: str`

**Rationale**: Adding `workflow_name` to the existing `WorkflowOrderListItem` would propagate the field into the existing `WorkflowOrderHistoryResponse` (per-workflow endpoint). That endpoint doesn't need `workflow_name` (it's already scoped to one workflow) and modifying it risks breaking the existing frontend `OrderHistoryItem` interface. A separate model keeps the two endpoints fully independent.

**Alternatives considered**:
- Extend `WorkflowOrderListItem` with optional `workflow_name` — rejected (adds nullable field to a model where it's always available; confusing semantics)
- Reuse `WorkflowOrderDetail` — rejected (includes too many fields not needed for a list view)

---

## Decision 3: Client-side vs server-side filtering

**Decision**: Client-side filtering in the React component using `Array.filter()`

**Rationale**: The dataset is bounded (≤ 100 records, 7-day TTL). Fetching once and filtering locally avoids extra API round-trips and keeps the UI instant (< 100 ms filter response). Server-side filtering would require additional query parameters on the new endpoint and more backend logic for no practical benefit at this scale.

**Alternatives considered**:
- Server-side filter by `workflow_id` query param — rejected (adds backend complexity for a bounded dataset; not needed for MVP)
- Server-side filter by `order_direction` — rejected (same reasoning)

---

## Decision 4: Route path and sidebar placement

**Decision**: Route `/workflow-orders`, nav link added below "Workflows" in the sidebar

**Rationale**: `/workflow-orders` is descriptive and consistent with the existing `/workflows` route. Placing it immediately below the Workflows link groups related navigation items visually and logically.

**Alternatives considered**:
- Nested route under `/workflows/orders` — rejected (would require React Router nesting changes and the page is standalone, not a sub-view of a specific workflow)
- Separate sidebar section — rejected (over-engineering for a single link)

---

## Decision 5: Scope of backend test additions

**Decision**: No new tests added in this feature

**Rationale**: The backend uses pytest. The new `get_all_workflow_orders` scan method follows the exact same pattern as `get_all_workflows` which is already tested. Adding tests was not requested in the spec and the constitution notes "no mock testing". Covering the new endpoint in the existing test suite can be done in a follow-up.

---

## Decision 6: Where to deduplicate to one order per workflow

**Decision**: Deduplicate server-side in `services/workflow_service.get_all_orders()`. Group the scanned rows by `workflow_id` and keep the row with the largest `placed_at` per group, then sort and truncate.

**Rationale**:
- Keeps the contract honest: the API returns what the frontend renders — no client-side dedup needed.
- Truncation must happen **after** dedup so the `limit` always represents distinct workflows, not raw orders. Truncating first could discard a workflow's most recent order entirely.
- Same layer that already converts dicts to `AllWorkflowOrderItem`, so adding a single dict-collapse step there has minimal code surface.
- Single in-memory pass over the scan result is trivially cheap at the expected scale (≤ a few hundred orders).

**Alternatives considered**:
- **Client-side dedup in React** — rejected: contract becomes misleading (`total_count` would not match the visible row count), and every consumer of the endpoint would have to repeat the logic.
- **DynamoDB-side query per workflow** — rejected: requires fetching the workflow ID list first (extra round trip) then N queries. Slower and more complex than one scan + dict collapse for the bounded dataset.
- **Dedup in the client layer (`aws_client.get_all_workflow_orders`)** — rejected: that layer is responsible for raw external-API access. Deduplication is a business rule that belongs in the service layer per the constitution's Layered Architecture Discipline.

---

## Confirmed unchanged files

- `pulumi/` — no infrastructure changes
- `model/workflow_api.py` `WorkflowOrderListItem` class — not modified
- `api/routers/workflow.py` existing routes — not modified
- `frontend/src/components/WorkflowDetailModal.tsx` — not modified
- `App.css` — not modified
