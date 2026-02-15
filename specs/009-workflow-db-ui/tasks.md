# Tasks: Workflow Management UI & Database Migration

**Input**: Design documents from `/specs/009-workflow-db-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are OPTIONAL - only included if explicitly requested. This feature spec does not request TDD, so test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Infrastructure)

**Purpose**: Create DynamoDB table and verify project dependencies

- [ ] T001 [P] Create workflows DynamoDB table definition in pulumi/dynamodb.py with partition key "id" (String) and PAY_PER_REQUEST billing
- [ ] T002 [P] Verify backend dependencies installed (FastAPI, boto3, Pydantic, PyYAML) via poetry install
- [ ] T003 [P] Verify frontend dependencies installed (React 19+, React Router DOM v7+, Axios) via npm install in frontend/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create WorkflowListItem Pydantic model in model/workflow_api.py with fields: id, name, index, cfd, enable, dry_run, is_us, end_date, primary_indicator, primary_unit_time, created_at, updated_at
- [ ] T005 [P] Create WorkflowDetail Pydantic model in model/workflow_api.py with all Workflow fields plus nested Condition, Indicator, Close, Trigger models
- [ ] T006 Add get_all_workflows() method to client/dynamodb_client.py that scans "workflows" table and returns List[Dict]
- [ ] T007 [P] Add get_workflow_by_id(workflow_id: str) method to client/dynamodb_client.py that returns single workflow Dict or None
- [ ] T008 [P] Add batch_put_workflows(workflows: List[Dict]) method to client/dynamodb_client.py using batch_writer for migration support
- [ ] T009 Create WorkflowService class in services/workflow_service.py with __init__(dynamodb_client: DynamoDBClient) accepting client via dependency injection

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 4 - Migrate Workflows from YAML to Database (Priority: P1) 🎯 MVP Foundation

**Goal**: Enable one-time migration from workflows.yml to DynamoDB with validation, UUID generation, and idempotency

**Independent Test**: Run migration script with sample workflows.yml, verify all workflows created in DynamoDB with correct field mappings and ISO 8601 date format

### Implementation for User Story 4

- [ ] T010 [US4] Create migration script at scripts/migrate_workflows.py that loads workflows.yml using PyYAML
- [ ] T011 [US4] Add validation function in scripts/migrate_workflows.py to check for duplicate workflow names and unsupported indicator types before migration
- [ ] T012 [US4] Add UUID generation for workflow IDs in scripts/migrate_workflows.py using uuid.uuid4()
- [ ] T013 [US4] Add date format conversion in scripts/migrate_workflows.py to transform end_date from YYYY/MM/DD to ISO 8601 format (YYYY-MM-DD)
- [ ] T014 [US4] Add default trigger application logic in scripts/migrate_workflows.py that applies defaults when trigger config missing (ut=h1, signal=breakout, location/order_direction based on close.direction, quantity=0.1)
- [ ] T015 [US4] Add created_at and updated_at timestamp generation in scripts/migrate_workflows.py using datetime.utcnow().isoformat()
- [ ] T016 [US4] Add progress logging in scripts/migrate_workflows.py showing workflows processed/created/failed counts
- [ ] T017 [US4] Integrate batch_put_workflows() call in scripts/migrate_workflows.py to insert validated workflows into DynamoDB
- [ ] T018 [US4] Add rollback capability in scripts/migrate_workflows.py tracking created IDs for deletion on failure
- [ ] T019 [US4] Update Lambda workflow loader in lambda/lambda_function.py to check for DynamoDB table existence before loading
- [ ] T020 [US4] Add DynamoDB workflow loading in lambda/lambda_function.py that queries enable=true workflows via dynamodb_client
- [ ] T021 [US4] Add YAML fallback logic in lambda/lambda_function.py that loads from S3/YAML if DynamoDB query fails or table missing
- [ ] T022 [US4] Add workflow source logging in lambda/lambda_function.py (database vs YAML) for debugging

**Checkpoint**: At this point, User Story 4 should be fully functional - migration script can populate DynamoDB and Lambda can load workflows from database

---

## Phase 4: User Story 5 - List Workflows via API (Priority: P2)

**Goal**: Provide REST API endpoint for listing all workflows with pagination, filtering, and sorting

**Independent Test**: Call GET /api/workflows with various query parameters, verify paginated response with correct filtering and sorting applied

### Implementation for User Story 5

- [ ] T023 [P] [US5] Add list_workflows() method to services/workflow_service.py that calls dynamodb_client.get_all_workflows()
- [ ] T024 [US5] Add filtering logic in services/workflow_service.py list_workflows() for enabled, index (case-insensitive partial match), indicator_type (searches conditions array), dry_run parameters
- [ ] T025 [US5] Add sorting logic in services/workflow_service.py list_workflows() for sort_by (name, index, end_date, created_at, updated_at) and sort_order (asc, desc)
- [ ] T026 [US5] Add pagination logic in services/workflow_service.py list_workflows() that slices results based on page and per_page parameters
- [ ] T027 [US5] Add transformation logic in services/workflow_service.py list_workflows() that converts Dict to WorkflowListItem Pydantic models extracting primary_indicator and primary_unit_time from first condition
- [ ] T028 [US5] Create WorkflowListResponse Pydantic model in model/workflow_api.py with fields: workflows (List[WorkflowListItem]), total, page, per_page, total_pages
- [ ] T029 [US5] Create workflows router in api/routers/workflows.py with FastAPI router setup
- [ ] T030 [US5] Add GET /api/workflows endpoint in api/routers/workflows.py accepting query params: page, per_page, enabled, index, indicator_type, dry_run, sort_by, sort_order
- [ ] T031 [US5] Wire WorkflowService in api/routers/workflows.py GET /api/workflows endpoint calling list_workflows() and returning WorkflowListResponse
- [ ] T032 [US5] Add error handling in api/routers/workflows.py GET /api/workflows endpoint returning HTTP 500 with error detail on DynamoDB query failures
- [ ] T033 [US5] Register workflows router in api/main.py including it in FastAPI app with /api prefix

**Checkpoint**: At this point, User Story 5 should be fully functional - API returns paginated, filtered, sorted workflow lists

---

## Phase 5: User Story 6 - Get Workflow Details via API (Priority: P2)

**Goal**: Provide REST API endpoint for retrieving single workflow complete configuration by ID

**Independent Test**: Call GET /api/workflows/{id} with valid and invalid IDs, verify complete workflow object returned with all nested fields or 404 error

### Implementation for User Story 6

- [ ] T034 [US6] Add get_workflow_detail(workflow_id: str) method to services/workflow_service.py that calls dynamodb_client.get_workflow_by_id()
- [ ] T035 [US6] Add transformation logic in services/workflow_service.py get_workflow_detail() that converts Dict to WorkflowDetail Pydantic model with nested structures
- [ ] T036 [US6] Add GET /api/workflows/{id} endpoint in api/routers/workflows.py accepting workflow_id path parameter
- [ ] T037 [US6] Wire WorkflowService in api/routers/workflows.py GET /api/workflows/{id} endpoint calling get_workflow_detail() and returning WorkflowDetail
- [ ] T038 [US6] Add 404 error handling in api/routers/workflows.py GET /api/workflows/{id} endpoint when workflow_id not found returning error detail "Workflow not found"
- [ ] T039 [US6] Add 500 error handling in api/routers/workflows.py GET /api/workflows/{id} endpoint on DynamoDB query failures

**Checkpoint**: At this point, User Story 6 should be fully functional - API returns complete workflow details or appropriate errors

---

## Phase 6: User Story 1 - View All Active Workflows (Priority: P1) 🎯 MVP UI

**Goal**: Create workflow management page displaying all workflows in table with status indicators, pagination, and navigation to detail view

**Independent Test**: Navigate to /workflows page, verify table displays all workflows with correct columns, status icons, dry run badges, and pagination controls

### Implementation for User Story 1

- [ ] T040 [P] [US1] Create Workflow TypeScript interface in frontend/src/services/api.ts matching WorkflowListItem Pydantic model
- [ ] T041 [P] [US1] Create WorkflowListResponse TypeScript interface in frontend/src/services/api.ts with workflows, total, page, per_page, total_pages fields
- [ ] T042 [P] [US1] Create WorkflowDetail TypeScript interface in frontend/src/services/api.ts matching backend WorkflowDetail Pydantic model with nested Condition, Indicator, Close, Trigger interfaces
- [ ] T043 [US1] Add listWorkflows() function to frontend/src/services/api.ts calling GET /api/workflows with query parameters returning Promise<WorkflowListResponse>
- [ ] T044 [P] [US1] Add getWorkflowDetail(id: string) function to frontend/src/services/api.ts calling GET /api/workflows/{id} returning Promise<WorkflowDetail>
- [ ] T045 [US1] Create Workflows.tsx page component in frontend/src/pages/ with useState for workflows, loading, error states
- [ ] T046 [US1] Add useEffect in frontend/src/pages/Workflows.tsx calling listWorkflows() on mount and storing results in state
- [ ] T047 [US1] Add Visibility API pattern in frontend/src/pages/Workflows.tsx for 60-second auto-refresh when tab visible (pause when hidden) following LongTermPositions.tsx pattern
- [ ] T048 [US1] Create WorkflowTable component in frontend/src/components/WorkflowTable.tsx accepting workflows prop
- [ ] T049 [US1] Add table HTML structure in frontend/src/components/WorkflowTable.tsx with columns: Name, Index, CFD, Status, Dry Run, Indicator, Unit Time, End Date
- [ ] T050 [US1] Add status icon rendering in frontend/src/components/WorkflowTable.tsx showing green ✓ for enabled, red ✗ for disabled
- [ ] T051 [US1] Add dry run badge rendering in frontend/src/components/WorkflowTable.tsx displaying "DRY RUN" label when workflow.dry_run is true
- [ ] T052 [US1] Add pagination controls in frontend/src/components/WorkflowTable.tsx with page number display and prev/next buttons
- [ ] T053 [US1] Add loading state UI in frontend/src/pages/Workflows.tsx showing spinner while fetching workflows
- [ ] T054 [US1] Add error state UI in frontend/src/pages/Workflows.tsx showing error message with retry button on API failures
- [ ] T055 [US1] Add empty state UI in frontend/src/pages/Workflows.tsx showing "No workflows found" when workflows array is empty
- [ ] T056 [US1] Add Workflows route in frontend/src/App.tsx mapping /workflows path to Workflows page component
- [ ] T057 [US1] Add Workflows navigation link in frontend/src/components/Navigation.tsx or main menu

**Checkpoint**: At this point, User Story 1 should be fully functional - traders can view all workflows in paginated table with status indicators

---

## Phase 7: User Story 2 - Filter and Sort Workflows (Priority: P1)

**Goal**: Add client-side filtering and sorting controls to workflow table for quick workflow location

**Independent Test**: Apply filters (enabled status, index, indicator, dry run) and sort (name, index, end date), verify table updates instantly showing only matching workflows in correct order

### Implementation for User Story 2

- [ ] T058 [US2] Add useState in frontend/src/pages/Workflows.tsx for filter state: filterEnabled, filterIndex, filterIndicator, filterDryRun
- [ ] T059 [US2] Add useState in frontend/src/pages/Workflows.tsx for sort state: sortBy, sortOrder
- [ ] T060 [US2] Add client-side filtering logic in frontend/src/pages/Workflows.tsx using useMemo that filters workflows array based on all filter criteria
- [ ] T061 [US2] Add client-side sorting logic in frontend/src/pages/Workflows.tsx using useMemo that sorts filtered workflows by sortBy field and sortOrder direction
- [ ] T062 [US2] Add useSearchParams from react-router-dom in frontend/src/pages/Workflows.tsx to read/write filter and sort state to URL query parameters
- [ ] T063 [US2] Add page reset logic in frontend/src/pages/Workflows.tsx that sets page to 1 when any filter changes
- [ ] T064 [US2] Create filter controls section in frontend/src/pages/Workflows.tsx with dropdowns/inputs for Status (All/Enabled/Disabled), Index (text input), Indicator (dropdown with ma50/combo/bbb/bbh/polarite/zone), Dry Run (All/Dry Run Only/Live Only)
- [ ] T065 [US2] Add column header click handlers in frontend/src/components/WorkflowTable.tsx for Name, Index, End Date columns toggling sort direction
- [ ] T066 [US2] Add sort indicator UI in frontend/src/components/WorkflowTable.tsx showing ↑ or ↓ arrow on sorted column header
- [ ] T067 [US2] Update pagination logic in frontend/src/components/WorkflowTable.tsx to paginate filtered and sorted results instead of raw workflows

**Checkpoint**: At this point, User Story 2 should be fully functional - traders can filter and sort workflows instantly with results reflected in URL for shareability

---

## Phase 8: User Story 3 - View Workflow Details (Priority: P1)

**Goal**: Display complete workflow configuration in detail modal when row clicked

**Independent Test**: Click any workflow row, verify detail modal opens showing all fields (conditions with indicator/close/element, trigger with all parameters, market settings)

### Implementation for User Story 3

- [ ] T068 [US3] Add useState in frontend/src/pages/Workflows.tsx for selectedWorkflowId and isDetailModalOpen state
- [ ] T069 [US3] Add row click handler in frontend/src/components/WorkflowTable.tsx calling onClick prop with workflow.id
- [ ] T070 [US3] Wire row click handler in frontend/src/pages/Workflows.tsx setting selectedWorkflowId and opening modal
- [ ] T071 [US3] Create WorkflowDetailModal component in frontend/src/components/WorkflowDetailModal.tsx accepting workflowId, isOpen, onClose props
- [ ] T072 [US3] Add useEffect in frontend/src/components/WorkflowDetailModal.tsx calling getWorkflowDetail(workflowId) when modal opens
- [ ] T073 [US3] Add modal structure in frontend/src/components/WorkflowDetailModal.tsx with sections: Basic Info, Conditions, Trigger, Market Settings
- [ ] T074 [US3] Add Basic Info section in frontend/src/components/WorkflowDetailModal.tsx displaying name, index, cfd, enable, dry_run, end_date fields
- [ ] T075 [US3] Add Conditions section in frontend/src/components/WorkflowDetailModal.tsx rendering each condition with Indicator (name, ut, value, zone_value), Close (direction, ut, spread), Element display
- [ ] T076 [US3] Add Trigger section in frontend/src/components/WorkflowDetailModal.tsx displaying ut, signal, location, order_direction, quantity fields
- [ ] T077 [US3] Add Market Settings section in frontend/src/components/WorkflowDetailModal.tsx showing "US Market" indicator when is_us is true
- [ ] T078 [US3] Add loading state in frontend/src/components/WorkflowDetailModal.tsx showing spinner while fetching workflow details
- [ ] T079 [US3] Add error handling in frontend/src/components/WorkflowDetailModal.tsx displaying error message if workflow fetch fails
- [ ] T080 [US3] Add close button in frontend/src/components/WorkflowDetailModal.tsx calling onClose prop
- [ ] T081 [US3] Wire WorkflowDetailModal in frontend/src/pages/Workflows.tsx passing selectedWorkflowId, isDetailModalOpen, and close handler

**Checkpoint**: At this point, User Story 3 should be fully functional - traders can click any workflow to see complete configuration details

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T082 [P] Add CSS styling for workflow table in frontend/src/pages/Workflows.css using shared.css patterns (.data-table class)
- [ ] T083 [P] Add CSS styling for WorkflowDetailModal in frontend/src/components/WorkflowDetailModal.css with modal overlay and content positioning
- [ ] T084 [P] Add format helpers in frontend/src/utils/workflowFormatters.ts for date formatting (end_date), indicator name display, and unit time labels
- [ ] T085 Update quickstart.md documentation with final deployment instructions and troubleshooting updates based on implementation learnings
- [ ] T086 Run manual smoke test following quickstart.md steps: migration, API endpoints, UI navigation, filtering, sorting, detail view
- [ ] T087 Verify Lambda integration by deploying updated lambda/lambda_function.py and checking CloudWatch logs for "Loaded N workflows from DynamoDB"
- [ ] T088 [P] Code cleanup: Remove debug logging, verify no hardcoded API URLs in frontend, ensure Black/isort formatting
- [ ] T089 Deploy infrastructure changes via pulumi up creating workflows DynamoDB table
- [ ] T090 Run migration script poetry run python scripts/migrate_workflows.py to populate DynamoDB with workflows.yml data

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 4 (Phase 3)**: Depends on Foundational phase - migration is foundation for all data access
- **User Story 5 (Phase 4)**: Depends on Foundational phase - independent of other stories
- **User Story 6 (Phase 5)**: Depends on Foundational phase - independent of other stories
- **User Story 1 (Phase 6)**: Depends on User Story 5 (API must exist for frontend to call)
- **User Story 2 (Phase 7)**: Depends on User Story 1 (extends table with filtering/sorting)
- **User Story 3 (Phase 8)**: Depends on User Story 1 and User Story 6 (needs table for row clicks and API for detail fetching)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 4 (P1)**: Foundation - MUST complete first (provides data for all other stories)
- **User Story 5 (P2)**: Can start after Foundational phase - independent of US4 but US1 depends on it
- **User Story 6 (P2)**: Can start after Foundational phase - independent of US4 but US3 depends on it
- **User Story 1 (P1)**: Depends on US5 (needs list API)
- **User Story 2 (P1)**: Depends on US1 (adds filtering/sorting to existing table)
- **User Story 3 (P1)**: Depends on US1 (row clicks) and US6 (detail API)

### Critical Path for MVP

1. Phase 1: Setup (T001-T003)
2. Phase 2: Foundational (T004-T009) ⚠️ BLOCKS all stories
3. Phase 3: User Story 4 (T010-T022) ⚠️ Data migration foundation
4. Phase 4: User Story 5 (T023-T033) ⚠️ API needed for frontend
5. Phase 6: User Story 1 (T040-T057) 🎯 **MVP COMPLETE HERE**
6. Phase 5: User Story 6 (T034-T039) - For detail view
7. Phase 8: User Story 3 (T068-T081) - Detail modal
8. Phase 7: User Story 2 (T058-T067) - Filtering/sorting enhancement

**Recommended MVP**: Complete through Phase 6 (User Story 1) for basic workflow viewing functionality.

### Within Each User Story

- Models before services
- Services before API endpoints
- API endpoints before frontend integration
- Core implementation before enhancements

### Parallel Opportunities

- **Setup (Phase 1)**: All 3 tasks (T001-T003) can run in parallel
- **Foundational (Phase 2)**: T004-T005 (models), T006-T008 (client methods), T009 (service) can overlap
- **User Story 4 (Phase 3)**: T010-T018 (migration script) can develop in parallel with T019-T022 (Lambda updates)
- **User Story 5 (Phase 4)**: T023-T027 (service logic) can develop in parallel with T028 (model) and T029 (router setup)
- **User Story 1 (Phase 6)**: T040-T044 (TypeScript interfaces and API calls) can develop in parallel with T048-T052 (WorkflowTable component)
- **Phase 9 (Polish)**: T082-T084 (styling and formatters) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch TypeScript interfaces and API service functions together:
Task: "Create Workflow TypeScript interface in frontend/src/services/api.ts"
Task: "Create WorkflowListResponse TypeScript interface in frontend/src/services/api.ts"
Task: "Create WorkflowDetail TypeScript interface in frontend/src/services/api.ts"

# While those are in progress, launch WorkflowTable component work:
Task: "Create WorkflowTable component in frontend/src/components/WorkflowTable.tsx"
Task: "Add table HTML structure in frontend/src/components/WorkflowTable.tsx"

# These can all develop independently before integration
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T009) ⚠️ BLOCKS all stories
3. Complete Phase 3: User Story 4 (T010-T022) ⚠️ Data foundation
4. Complete Phase 4: User Story 5 (T023-T033) ⚠️ List API
5. Complete Phase 6: User Story 1 (T040-T057) 🎯 **MVP COMPLETE**
6. **STOP and VALIDATE**: Test workflow page displays all workflows with pagination
7. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 4 → Run migration, verify data in DynamoDB
3. Add User Story 5 + 6 → Test APIs independently with curl
4. Add User Story 1 → Test workflow list page → **Deploy/Demo (MVP!)**
5. Add User Story 2 → Test filtering/sorting → Deploy/Demo
6. Add User Story 3 → Test detail view → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 4 (Migration)
   - Developer B: User Story 5 + 6 (APIs)
   - Developer C: Setup User Story 1 frontend structure (wait for US5 API)
3. After US5 complete:
   - Developer C: Complete User Story 1 (UI)
   - Developer A: User Story 2 (Filtering)
   - Developer B: User Story 3 (Detail view)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- User Story 4 (migration) is foundational - must complete before UI stories can show data
- User Story 5 (list API) is required dependency for User Story 1 (UI)
- User Story 6 (detail API) is required dependency for User Story 3 (detail view)
- Tests not included per spec - no TDD requirement stated
- Frontend has no test framework configured per plan.md

---

## Task Summary

**Total Tasks**: 90
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 6 tasks
- Phase 3 (US4 - Migration): 13 tasks
- Phase 4 (US5 - List API): 11 tasks
- Phase 5 (US6 - Detail API): 6 tasks
- Phase 6 (US1 - View Workflows): 18 tasks
- Phase 7 (US2 - Filter/Sort): 10 tasks
- Phase 8 (US3 - Detail View): 14 tasks
- Phase 9 (Polish): 9 tasks

**Parallel Opportunities**: 20+ tasks marked [P] for parallel execution

**MVP Scope**: Phases 1-6 (58 tasks) delivers basic workflow viewing with pagination

**Full Feature**: All 90 tasks delivers complete workflow management UI with filtering, sorting, and detail views
