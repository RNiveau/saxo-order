# Tasks: Workflow Orders List Page

**Input**: Design documents from `/specs/014-workflow-orders-list/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: No test tasks — not requested in spec; no frontend testing framework configured.

**Scope**: 5 backend files modified, 2 new frontend files, 3 existing frontend files modified.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[US1]**: View All Workflow Orders at a Glance (P1)
- **[US2]**: Filter Orders by Workflow or Direction (P2)

---

## Phase 1: Setup

> No setup required — no new dependencies, no new directories, no new DynamoDB tables. `workflow_orders` table and IAM policies already exist (spec 010). Proceed directly to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend models and DynamoDB client method that both user stories depend on.

**⚠️ CRITICAL**: Phase 3 and 4 cannot begin until T001–T003 are complete.

- [ ] T001 [P] Add `AllWorkflowOrderItem` Pydantic model (fields: `id`, `workflow_id`, `workflow_name`, `placed_at: int`, `order_code`, `order_price`, `order_quantity`, `order_direction`) to `model/workflow_api.py` after the existing `WorkflowOrderListItem` class
- [ ] T002 Add `AllWorkflowOrdersResponse` Pydantic model (fields: `orders: List[AllWorkflowOrderItem]`, `total_count: int`, `limit: int`) to `api/models/workflow.py`; import `AllWorkflowOrderItem` from `model.workflow_api` (depends on T001)
- [ ] T003 [P] Add `get_all_workflow_orders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]` method to `client/aws_client.py`: scan `workflow_orders` table (same pagination loop pattern as `get_all_workflows`), sort results by `placed_at` descending in Python, apply limit after sort

**Checkpoint**: Models importable; `get_all_workflow_orders` scannable against real DynamoDB — foundation ready for user story work.

---

## Phase 3: User Story 1 — View All Workflow Orders at a Glance (Priority: P1) 🎯 MVP

**Goal**: A dedicated `/workflow-orders` page loads all orders from all workflows, sorted newest first, with each row showing timestamp, workflow name, asset code, direction badge, price, quantity.

**Independent Test**: Navigate to `http://localhost:5173/workflow-orders`, verify a flat list of all orders appears sorted by most recent first. See `quickstart.md` steps 1–5 and 13–15.

### Implementation

- [ ] T004 [US1] Add `get_all_orders(self, limit: int = 100) -> List[AllWorkflowOrderItem]` method to `services/workflow_service.py`: call `self.dynamodb_client.get_all_workflow_orders(limit=limit)`, convert each dict to `AllWorkflowOrderItem` using a new `_convert_all_order_to_item` private method; import `AllWorkflowOrderItem` from `model.workflow_api` (depends on T001, T003)
- [ ] T005 [US1] Add `GET /api/workflow/orders` endpoint to `api/routers/workflow.py`: `limit: int = Query(100, ge=1, le=100)`, call `workflow_service.get_all_orders(limit=limit)`, return `AllWorkflowOrdersResponse`; import `AllWorkflowOrdersResponse` from `api.models.workflow` (depends on T002, T004)
- [ ] T006 [P] [US1] Add `AllWorkflowOrderItem` interface, `AllWorkflowOrdersResponse` interface, and `workflowService.getAllOrders(limit: number = 100): Promise<AllWorkflowOrdersResponse>` method (calls `GET /api/workflow/orders?limit={limit}`) to `frontend/src/services/api.ts`
- [ ] T007 [US1] Create `frontend/src/pages/WorkflowOrders.tsx`: fetch all orders via `workflowService.getAllOrders()` on mount, render a `<table>` with columns (Date, Workflow, Asset, Direction, Price, Quantity), show loading state while fetching, show empty state ("No recent workflow orders") when `orders.length === 0` (depends on T006)
- [ ] T008 [P] [US1] Create `frontend/src/pages/WorkflowOrders.css`: style the orders table (`.workflow-orders-table`, `.direction-badge.buy`, `.direction-badge.sell`), page header (`.workflow-orders-header`), loading and empty states — mirror the style patterns from `frontend/src/pages/Workflows.css`
- [ ] T009 [P] [US1] Add `import WorkflowOrders from './pages/WorkflowOrders'` and `<Route path="/workflow-orders" element={<WorkflowOrders />} />` to `frontend/src/App.tsx` (depends on T007)
- [ ] T010 [P] [US1] Add a nav link `<NavLink to="/workflow-orders">` with icon `📋` and label "Workflow Orders" to `frontend/src/components/Sidebar.tsx`, placed after the existing "Workflows" link (depends on T007)

**Checkpoint**: `curl http://localhost:8000/api/workflow/orders` returns orders JSON; navigating to `/workflow-orders` renders the table; link visible in sidebar.

---

## Phase 4: User Story 2 — Filter Orders by Workflow or Direction (Priority: P2)

**Goal**: Two dropdown filters above the table — one for workflow name (populated from loaded order data), one for direction (All / BUY / SELL). Selecting a filter updates the visible rows instantly client-side.

**Independent Test**: Load the page with orders from 2+ workflows, apply workflow filter, verify count changes. Apply direction filter, verify only matching rows shown. Clear both filters, verify full list restored. See `quickstart.md` steps 6–12.

### Implementation

- [ ] T011 [US2] Add `workflowFilter` (string, default `''`) and `directionFilter` (string, default `'all'`) state variables to `frontend/src/pages/WorkflowOrders.tsx`; derive `filteredOrders` by applying both filters to the loaded `orders` array; replace the table's data source with `filteredOrders`; derive `workflowNames` as `[...new Set(orders.map(o => o.workflow_name))]` for the dropdown options (depends on T007)
- [ ] T012 [US2] Add a filter toolbar row above the table in `frontend/src/pages/WorkflowOrders.tsx`: a `<select>` for workflow (options: "All workflows" + each unique name) bound to `workflowFilter`, and a `<select>` for direction (options: All / BUY / SELL) bound to `directionFilter` (depends on T011)
- [ ] T013 [P] [US2] Add `.workflow-orders-filters`, `.filter-select` styles to `frontend/src/pages/WorkflowOrders.css`: flex row layout, consistent select styling matching the existing Workflows filter bar

**Checkpoint**: Both dropdowns visible; filtering by workflow and direction updates the table instantly; "All" / "all" option restores full list.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T014 [P] Run `poetry run mypy .` and `poetry run flake8` from repo root; fix any new type or lint errors introduced in `model/workflow_api.py`, `api/models/workflow.py`, `client/aws_client.py`, `services/workflow_service.py`, `api/routers/workflow.py`
- [ ] T015 [P] Run `npm run build` and `npm run lint` in `frontend/`; fix any TypeScript or ESLint errors from new/modified files
- [ ] T016 Run all acceptance scenarios from `specs/014-workflow-orders-list/quickstart.md` (steps 1–15) manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No dependencies — start immediately
- **Phase 3 (US1)**: Depends on T001 + T003 complete (T004); T002 + T004 complete (T005); T006 independent of backend
- **Phase 4 (US2)**: Depends on T007 (WorkflowOrders.tsx must exist before adding filter state)
- **Phase 5 (Polish)**: Depends on all Phase 3 + 4 tasks complete

### Execution Graph

```
T001 [P] ──┬──> T002 ──> T005
           └──> T004 ──> T005
T003 [P] ──────> T004

T006 [P] ──> T007 ──┬──> T009 [P]
                    └──> T010 [P]
T008 [P] (alongside T007)

T007 ──> T011 ──> T012
T013 [P] (alongside T011/T012)

T014 [P] ┐
T015 [P] ├── (after all implementation tasks)
T016     ┘
```

### Parallel Opportunities

```bash
# Phase 2 — launch together:
Task: "AllWorkflowOrderItem model in model/workflow_api.py"           # T001
Task: "get_all_workflow_orders() in client/aws_client.py"             # T003

# Phase 3 — backend vs frontend in parallel:
Task: "get_all_orders() in services/workflow_service.py"             # T004 (after T001+T003)
Task: "AllWorkflowOrderItem TS interface + getAllOrders() in api.ts"  # T006 [P]

# Phase 3 — page + CSS in parallel:
Task: "Create WorkflowOrders.tsx"                                     # T007 (after T006)
Task: "Create WorkflowOrders.css"                                     # T008 [P]

# Phase 3 — route + sidebar in parallel (after T007):
Task: "Add /workflow-orders route in App.tsx"                        # T009 [P]
Task: "Add Workflow Orders nav link in Sidebar.tsx"                  # T010 [P]

# Phase 5 — lint/build in parallel:
Task: "Backend mypy + flake8"                                         # T014 [P]
Task: "Frontend build + lint"                                         # T015 [P]
```

---

## Implementation Strategy

### MVP (User Story 1 only — Phase 2 + Phase 3)

1. Complete Phase 2 (T001 → T002, T003) — foundational models + client method
2. Complete Phase 3 (T004 → T005 backend; T006 → T007 → T009 + T010 frontend)
3. Complete Phase 5 lint/build (T014, T015)
4. **STOP and VALIDATE**: Confirm the page loads orders at `/workflow-orders`
5. Proceed to Phase 4 (US2) once US1 is stable

### Incremental Delivery

1. Phase 2 complete → backend models and scan method ready
2. US1 complete → working page, accessible from sidebar → deploy/demo
3. US2 complete → filters working → deploy/demo

### Commit strategy

```
feat: add workflow orders list page with cross-workflow view
```

---

## Notes

- `[P]` = different files, no shared in-progress dependency
- `[US1]` / `[US2]` map every task to its user story for traceability
- No test tasks — not requested; no frontend test framework
- `WorkflowOrderListItem` and existing per-workflow endpoint are **not modified**
- `App.css` and DynamoDB infrastructure are **not modified**
