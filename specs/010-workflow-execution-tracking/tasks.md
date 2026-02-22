# Tasks: Workflow Order History Tracking

**Input**: Design documents from `/specs/010-workflow-execution-tracking/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No test tasks included - not explicitly requested in specification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Web app structure**: Backend at repository root, Frontend in `frontend/` directory
- Backend: `engines/`, `client/`, `services/`, `api/`, `model/`, `pulumi/`, `tests/`
- Frontend: `frontend/src/` with `pages/`, `components/`, `services/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create DynamoDB table and prepare infrastructure

- [x] T001 Create workflow_orders DynamoDB table definition in pulumi/dynamodb.py
- [ ] T002 Deploy workflow_orders table with TTL enabled via Pulumi (pulumi up) - REQUIRES MANUAL DEPLOYMENT
- [ ] T003 [P] Verify table creation and TTL configuration in AWS console or CLI - REQUIRES MANUAL VERIFICATION

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain models and client infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create WorkflowOrder domain model dataclass in model/workflow.py
- [x] T005 [P] Create WorkflowOrderListItem Pydantic model in model/workflow_api.py
- [x] T006 [P] Create WorkflowOrderDetail Pydantic model in api/models/workflow.py
- [x] T007 [P] Create WorkflowOrderHistoryResponse Pydantic model in api/models/workflow.py
- [x] T008 Implement record_workflow_order() method in client/aws_client.py
- [x] T009 Implement get_workflow_orders() method in client/aws_client.py (query with ScanIndexForward=False)
- [x] T010 Update WorkflowEngine.__init__() to accept dynamodb_client parameter in engines/workflow_engine.py
- [x] T011 Add order tracking call in WorkflowEngine.run() after order signal generation (lines ~145) in engines/workflow_engine.py
- [x] T012 Update WorkflowEngine instantiation in lambda_function.py to inject DynamoDBClient
- [x] T013 Update WorkflowEngine instantiation in saxo_order/commands/workflow.py to inject DynamoDBClient

**Checkpoint**: Foundation ready - domain models exist, DynamoDB client can write/read orders, WorkflowEngine tracks orders

---

## Phase 3: User Story 1 - View Workflow Order History (Priority: P1) 🎯 MVP

**Goal**: Users can view the complete order history (up to 7 days) for any workflow in the detail modal

**Independent Test**: Trigger a workflow to place an order (manually insert test data if needed), open workflow detail modal, verify order appears in "Order History" section with correct timestamp, price, quantity, and direction

### Implementation for User Story 1

**Backend API:**

- [x] T014 [P] [US1] Implement get_workflow_order_history() method in services/workflow_service.py
- [x] T015 [P] [US1] Create conversion helper _convert_order_to_list_item() in services/workflow_service.py
- [x] T016 [US1] Add GET /api/workflow/workflows/{workflow_id}/orders endpoint in api/routers/workflow.py
- [x] T017 [US1] Add error handling for workflow not found and DynamoDB errors in api/routers/workflow.py

**Frontend Service:**

- [x] T018 [P] [US1] Add OrderHistoryItem TypeScript interface in frontend/src/services/api.ts
- [x] T019 [P] [US1] Add OrderHistoryResponse TypeScript interface in frontend/src/services/api.ts
- [x] T020 [US1] Implement getWorkflowOrderHistory() method in workflowService in frontend/src/services/api.ts

**Frontend UI:**

- [x] T021 [P] [US1] Add order history state (orderHistory, orderHistoryLoading) in frontend/src/components/WorkflowDetailModal.tsx
- [x] T022 [US1] Add useEffect to load order history on modal open in frontend/src/components/WorkflowDetailModal.tsx
- [x] T023 [US1] Add "Order History" section markup after Trigger section in frontend/src/components/WorkflowDetailModal.tsx
- [x] T024 [P] [US1] Create order history table with columns (Date, Direction, Quantity, Price, Asset) in frontend/src/components/WorkflowDetailModal.tsx
- [x] T025 [P] [US1] Add formatDate() helper for timestamp display in frontend/src/components/WorkflowDetailModal.tsx
- [x] T026 [P] [US1] Add empty state display "No orders placed yet" in frontend/src/components/WorkflowDetailModal.tsx

**Frontend Styling:**

- [x] T027 [P] [US1] Add CSS for .order-history-table in frontend/src/components/WorkflowDetailModal.css
- [x] T028 [P] [US1] Add CSS for .order-direction-badge (.order-direction-buy, .order-direction-sell) in frontend/src/components/WorkflowDetailModal.css
- [x] T029 [P] [US1] Add CSS for .order-history-empty in frontend/src/components/WorkflowDetailModal.css

**Checkpoint**: User Story 1 complete - Users can open workflow detail modal and see full order history (last 7 days) with formatted dates and direction badges

---

## Phase 4: User Story 2 - Identify Active Workflows (Priority: P2)

**Goal**: Users can see when each workflow last placed an order in the workflows list view to identify which workflows are actively trading

**Independent Test**: View workflows list page, verify "Last Order" column shows timestamp (e.g., "2 hours ago") for workflows with orders, and shows "-" for workflows with no orders

### Implementation for User Story 2

**Backend Models:**

- [x] T030 [P] [US2] Extend WorkflowListItem model with last_order_timestamp field in model/workflow_api.py
- [x] T031 [P] [US2] Extend WorkflowListItem model with last_order_direction field in model/workflow_api.py
- [x] T032 [P] [US2] Extend WorkflowListItem model with last_order_quantity field in model/workflow_api.py

**Backend Service:**

- [x] T033 [US2] Implement _get_last_order_for_workflow() method in services/workflow_service.py (query with limit=1)
- [x] T034 [US2] Update list_workflows() method to fetch and populate last_order fields in services/workflow_service.py

**Frontend Table:**

- [x] T035 [P] [US2] Add "Last Order" column header after "End Date" in frontend/src/components/WorkflowTable.tsx
- [x] T036 [P] [US2] Add formatRelativeTime() helper function in frontend/src/components/WorkflowTable.tsx
- [x] T037 [US2] Add last order cell with formatRelativeTime(workflow.last_order_timestamp) in frontend/src/components/WorkflowTable.tsx

**Frontend Styling:**

- [x] T038 [P] [US2] Add CSS for last order column styling in frontend/src/components/WorkflowTable.css

**Checkpoint**: User Story 2 complete - Workflows list shows "Last Order" column with relative timestamps, users can identify active workflows at a glance

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Integration, testing, and documentation

**Integration:**

- [ ] T039 [P] Test end-to-end: Trigger workflow → verify order recorded in DynamoDB → verify appears in UI modal (US1) and list (US2) - REQUIRES MANUAL TESTING
- [ ] T040 [P] Test with DynamoDB Local using quickstart.md setup instructions - REQUIRES MANUAL TESTING
- [ ] T041 [P] Test TTL configuration (verify ttl field is set correctly on order records) - REQUIRES MANUAL TESTING
- [ ] T042 Test graceful degradation when DynamoDB unavailable (order placement should continue, tracking fails silently) - REQUIRES MANUAL TESTING

**Error Handling:**

- [x] T043 [P] Add error logging for DynamoDB write failures in client/dynamodb_client.py
- [x] T044 [P] Add error logging for order tracking failures in engines/workflow_engine.py
- [ ] T045 Test frontend behavior when API returns empty order history - REQUIRES MANUAL TESTING

**Documentation:**

- [ ] T046 [P] Update CLAUDE.md with workflow_orders table and new API endpoints (if needed beyond agent context update) - OPTIONAL
- [x] T047 [P] Add comments explaining TTL calculation in client/dynamodb_client.py
- [ ] T048 Verify quickstart.md instructions work end-to-end - REQUIRES MANUAL TESTING

**Code Quality:**

- [x] T049 [P] Run Black formatter on modified Python files
- [x] T050 [P] Run isort on modified Python files
- [x] T051 [P] Run MyPy type checking on modified Python files
- [x] T052 [P] Run ESLint on modified TypeScript files in frontend/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
  - Creates DynamoDB infrastructure
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
  - Creates domain models, DynamoDB client methods, WorkflowEngine integration
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (P1): View order history in modal - Can start after Phase 2
  - User Story 2 (P2): Show last order in list - Can start after Phase 2
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**:
  - **Depends on**: Foundational phase (domain models, DynamoDB client, order tracking)
  - **No dependencies on**: User Story 2
  - **Delivers**: Full order history in workflow detail modal

- **User Story 2 (P2)**:
  - **Depends on**: Foundational phase (domain models, DynamoDB client, order tracking)
  - **No dependencies on**: User Story 1 (but shares same backend infrastructure)
  - **Delivers**: Last order timestamp in workflows list view

**Key Insight**: User Stories 1 and 2 are **independent** - they can be developed in parallel by different developers after Foundational phase is complete. They share the same backend (DynamoDB client, order tracking) but have separate frontend components and API endpoints.

### Within Each User Story

**User Story 1:**
1. Backend API endpoint (T014-T017) before Frontend service (T018-T020)
2. Frontend service (T018-T020) before Frontend UI (T021-T026)
3. Frontend UI (T021-T026) before Styling (T027-T029)
4. Models and API logic can be developed in parallel ([P] tasks)

**User Story 2:**
1. Backend models (T030-T032) and service (T033-T034) first
2. Frontend table updates (T035-T037) after backend ready
3. Models, helpers, and CSS can be developed in parallel ([P] tasks)

### Parallel Opportunities

**Phase 1 (Setup):** All 3 tasks can run in parallel if multiple people available

**Phase 2 (Foundational):**
- T004-T007 (all models) can run in parallel
- T008-T009 (DynamoDB methods) must be sequential or coordinated (same file)
- T010-T013 (WorkflowEngine updates) must be after T008-T009 complete

**Phase 3 (User Story 1):**
- Backend tasks T014-T015 (different methods in same file) can run together
- T016-T017 (API endpoint) after T014-T015
- Frontend interfaces T018-T019 can run in parallel
- Frontend UI T021-T026: T021-T022 first, then T023-T026 can be parallel
- Styling T027-T029 can all run in parallel

**Phase 4 (User Story 2):**
- Backend models T030-T032 can all run in parallel
- Frontend tasks T035-T037 can run in parallel (same file, different sections)

**Phase 5 (Polish):**
- Most tasks (T039-T052) can run in parallel as they affect different files/concerns

---

## Parallel Example: User Story 1

```bash
# After Foundational phase complete, User Story 1 can start:

# Sprint 1: Backend API (sequential for same file, but fast)
Task T014: "Implement get_workflow_order_history() in services/workflow_service.py"
Task T015: "Create conversion helper in services/workflow_service.py"
Task T016: "Add GET endpoint in api/routers/workflow.py"
Task T017: "Add error handling in api/routers/workflow.py"

# Sprint 2: Frontend in parallel (2 developers)
Developer A:
  Task T018: "Add OrderHistoryItem interface"
  Task T019: "Add OrderHistoryResponse interface"
  Task T020: "Implement getWorkflowOrderHistory()"

Developer B:
  Task T021: "Add order history state"
  Task T022: "Add useEffect to load orders"
  Task T023: "Add Order History section markup"

# Sprint 3: Frontend finalization (parallel)
Task T024: "Create order history table" (Developer A)
Task T025: "Add formatDate() helper" (Developer B)
Task T026: "Add empty state display" (Developer A)
Task T027: "Add CSS for .order-history-table" (Developer B)
Task T028: "Add CSS for .order-direction-badge" (Developer A)
Task T029: "Add CSS for .order-history-empty" (Developer B)
```

---

## Parallel Example: User Story 2

```bash
# Can start in parallel with User Story 1 (different files)

# Backend (sequential, but same developer as US1 backend)
Task T030-T032: "Extend WorkflowListItem model" (parallel - same file, different fields)
Task T033: "Implement _get_last_order_for_workflow()"
Task T034: "Update list_workflows() method"

# Frontend (can be different developer from US1 frontend)
Task T035-T037: "Add Last Order column and formatting" (parallel within WorkflowTable.tsx)
Task T038: "Add CSS styling"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Phase 1**: Setup (T001-T003) - Deploy DynamoDB table
2. **Phase 2**: Foundational (T004-T013) - Domain models + order tracking infrastructure
3. **Phase 3**: User Story 1 (T014-T029) - Full order history in detail modal
4. **STOP and VALIDATE**:
   - Manually trigger a workflow or insert test order data
   - Open workflow detail modal
   - Verify order history displays correctly
5. **Deploy/Demo MVP**: Users can now see workflow order history

**Why stop here?** User Story 1 alone delivers significant value - users can audit workflow trading activity for the past 7 days.

### Incremental Delivery (MVP + User Story 2)

1. Complete MVP (Phases 1-3)
2. **Phase 4**: User Story 2 (T030-T038) - Last order in list view
3. **VALIDATE**:
   - View workflows list page
   - Verify "Last Order" column shows timestamps
4. **Deploy**: Users now have both detail view (US1) and list view (US2) order visibility

### Full Feature (MVP + US2 + Polish)

1. Complete MVP + User Story 2 (Phases 1-4)
2. **Phase 5**: Polish (T039-T052) - Testing, error handling, documentation
3. **Final Validation**: Run quickstart.md end-to-end
4. **Production Deploy**: Complete feature ready for production

### Parallel Team Strategy

With 3 developers after Foundational phase (Phase 2) completes:

**Option A: User Story Focus**
- Developer 1: User Story 1 backend (T014-T017)
- Developer 2: User Story 1 frontend (T018-T029)
- Developer 3: User Story 2 (T030-T038)

**Option B: Layer Focus**
- Developer 1: All backend tasks (T014-T017, T030-T034)
- Developer 2: User Story 1 frontend (T018-T029)
- Developer 3: User Story 2 frontend (T035-T038)

**Recommendation**: Option A (User Story Focus) enables faster independent delivery of complete features.

---

## Task Count Summary

- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 10 tasks (CRITICAL - blocks all stories)
- **Phase 3 (User Story 1)**: 16 tasks (MVP target)
- **Phase 4 (User Story 2)**: 9 tasks
- **Phase 5 (Polish)**: 14 tasks

**Total**: 52 tasks

**Parallelizable**: 32 tasks marked [P] (61% can run in parallel with proper coordination)

**MVP Scope**: Phases 1-3 = 29 tasks (Setup + Foundational + US1)

---

## Notes

- **[P] tasks** = Different files or independent sections, no blocking dependencies
- **[Story] labels** = Map tasks to user stories for traceability and independent testing
- **No tests included** = Not requested in spec, can be added later if needed
- **Commit strategy**: Commit after each task or logical group (e.g., all models, complete endpoint)
- **Validation checkpoints**: Stop after each phase to test independently before proceeding
- **DynamoDB Local**: Use for development/testing per quickstart.md instructions
- **TTL testing**: TTL won't work in DynamoDB Local, test in AWS or manually verify ttl field values
- **Error handling**: Order tracking failures should NOT block workflow execution (graceful degradation)
- **Constitution compliance**: All tasks respect layered architecture (Service → Client → DynamoDB, no direct Table() access)
