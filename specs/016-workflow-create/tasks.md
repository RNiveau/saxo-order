# Tasks: Create Workflow

**Input**: Design documents from `/specs/016-workflow-create/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: No test tasks — not requested in spec; no frontend testing framework configured.

**Scope**: 4 backend files modified, 2 new frontend files, 2 existing frontend files modified.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[US1]**: Create workflow from Workflows page (P1)
- **[US2]**: Create workflow from Asset Detail page (P2)

---

## Phase 1: Setup

> No new packages, directories, or infrastructure required. Proceed directly to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend Pydantic request models and DynamoDB client method that both user stories depend on.

**⚠️ CRITICAL**: Phase 3 and 4 cannot begin until T001–T004 are complete.

- [x] T001 [P] Add five Pydantic input models to `model/workflow_api.py` after the existing `AllWorkflowOrderItem` class: `WorkflowIndicatorInput` (fields: `name: str`, `ut: str`, `value: Optional[float] = None`, `zone_value: Optional[float] = None`), `WorkflowCloseInput` (fields: `direction: str`, `ut: str`, `spread: float = Field(..., gt=0)`), `WorkflowConditionInput` (fields: `indicator: WorkflowIndicatorInput`, `close: WorkflowCloseInput`, `element: Optional[str] = None`), `WorkflowTriggerInput` (fields: `ut: str`, `location: str`, `order_direction: str`, `quantity: float = Field(..., gt=0)`), `WorkflowCreateRequest` (fields: `name: str = Field(..., min_length=1)`, `index: str = Field(..., min_length=1)`, `cfd: str = Field(..., min_length=1)`, `enable: bool = True`, `dry_run: bool = True`, `is_us: bool = False`, `end_date: Optional[str] = None`, `conditions: List[WorkflowConditionInput] = Field(..., min_length=1)`, `trigger: WorkflowTriggerInput`)
- [x] T002 [P] Add `put_workflow(self, workflow: Dict[str, Any]) -> None` method to `client/aws_client.py` after `batch_put_workflows`: call `self.dynamodb.Table("workflows").put_item(Item=workflow)`, check HTTP status ≥ 400 and log error + raise `RuntimeError("Failed to persist workflow")` if so
- [x] T003 Add `create_workflow(self, data: WorkflowCreateRequest) -> WorkflowDetail` method to `services/workflow_service.py`; import `WorkflowCreateRequest` from `model.workflow_api`; implementation: (1) validate `end_date` is a future date using `datetime.fromisoformat` if provided and raise `ValueError` with a descriptive message if past; (2) validate indicator-specific fields: `value` required when `data.conditions[0].indicator.name` is `"polarite"` or `"zone"`, `zone_value` required when name is `"zone"`; (3) build `workflow_dict` with `id=str(uuid.uuid4())`, `name=data.name.strip()`, `index=data.index`, `cfd=data.cfd`, `enable=data.enable`, `dry_run=data.dry_run`, `is_us=data.is_us`, `end_date=data.end_date`, `conditions=[{"indicator": {"name": c.indicator.name, "ut": c.indicator.ut, "value": c.indicator.value, "zone_value": c.indicator.zone_value}, "close": {"direction": c.close.direction, "ut": c.close.ut, "spread": c.close.spread}, "element": c.element} for c in data.conditions]`, `trigger={"ut": data.trigger.ut, "signal": "breakout", "location": data.trigger.location, "order_direction": data.trigger.order_direction, "quantity": data.trigger.quantity}`, `created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")`, `updated_at=created_at`; (4) call `self.dynamodb_client.put_workflow(workflow_dict)`; (5) return `WorkflowDetail` built from the saved dict using the same mapping as `get_workflow_by_id` (depends on T001, T002)
- [x] T004 [P] Add five TypeScript interfaces to `frontend/src/services/api.ts` after the existing `AllWorkflowOrdersResponse` interface: `WorkflowIndicatorInput`, `WorkflowCloseInput`, `WorkflowConditionInput`, `WorkflowTriggerInput`, `WorkflowCreateRequest` — field types as defined in `specs/016-workflow-create/data-model.md`; then add `createWorkflow: async (data: WorkflowCreateRequest): Promise<WorkflowDetail>` method to the `workflowService` object: `POST /api/workflow/workflows` with JSON body, return `response.data`

**Checkpoint**: `WorkflowCreateRequest` importable in Python and TypeScript; `create_workflow()` callable with a valid payload; foundation ready for UI work.

---

## Phase 3: User Story 1 — Create Workflow from Workflows Page (Priority: P1) 🎯 MVP

**Goal**: A "New Workflow" button on the Workflows page opens a creation modal. The modal supports all 6 indicator types with dynamic field rendering, auto-suggests a workflow name, validates on submit, shows an error banner on API failure, and refreshes the list on success.

**Independent Test**: Navigate to `/workflows`, click "New Workflow", fill in the form for any indicator type, save, verify the workflow appears in the list. See `quickstart.md` scenarios 1–3, 5–8.

### Implementation

- [x] T005 [US1] Add `POST /api/workflow/workflows` endpoint to `api/routers/workflow.py`: import `WorkflowCreateRequest` from `model.workflow_api`; add `@router.post("/workflows", response_model=WorkflowDetail, status_code=201)` handler `async def create_workflow(data: WorkflowCreateRequest, workflow_service: WorkflowService = Depends(get_workflow_service))`; wrap in try/except: catch `ValueError` → raise `HTTPException(status_code=422, detail=str(e))`; catch generic `Exception` → log + raise `HTTPException(status_code=500, detail="Failed to create workflow")`; on success return `workflow_service.create_workflow(data)` (depends on T001, T003)
- [x] T006 [P] [US1] Create `frontend/src/components/WorkflowCreateModal.tsx`: implement a controlled-form modal with props `{ onClose: () => void; onSuccess: (workflow: WorkflowDetail) => void; prefill?: { index: string; cfd: string } }`; use `.modal-backdrop` / `.modal-content` / `.modal-header` / `.modal-close-button` CSS classes (same as WorkflowDetailModal); form state: `name`, `index`, `cfd`, `enable` (default true), `dry_run` (default true), `is_us` (default false), `end_date`, `indicatorName` (default `"bbb"`), `indicatorUt` (default `"h1"`), `indicatorValue`, `indicatorZoneValue`, `closeDirection` (default `"above"`), `closeUt` (default `"h1"`), `spread`, `element`, `triggerUt` (default `"h1"`), `triggerLocation` (default `"higher"`), `orderDirection` (default `"buy"`), `quantity`; name auto-suggestion: maintain `nameDirty: boolean` state (false initially); derive suggested name as `"{orderDirection.toUpperCase()} {indicatorName.toUpperCase()} {indicatorUt.toUpperCase()} {cfd}"` and update `name` whenever `nameDirty === false` and any of those fields changes; set `nameDirty = true` when user manually edits the name field; conditional rendering: show `indicatorValue` input only when `indicatorName === "polarite" || indicatorName === "zone"`; show `indicatorZoneValue` input only when `indicatorName === "zone"`; validation on submit: all required fields non-empty, `end_date` is future if provided, `spread > 0`, `quantity > 0`, `indicatorValue` non-empty for POL/ZONE, `indicatorZoneValue` non-empty for ZONE; on validation failure: set per-field error state and display inline error messages; on submit: set `saving` state, call `workflowService.createWorkflow(payload)`, on success call `onSuccess(result)` then `onClose()`, on failure set `saveError` string and display error banner above the Save button without closing; on Cancel/backdrop click: call `onClose()` (depends on T004)
- [x] T007 [P] [US1] Create `frontend/src/components/WorkflowCreateModal.css`: style the form using the existing `.modal-backdrop`, `.modal-content`, `.modal-header`, `.modal-close-button` classes already defined in `WorkflowDetailModal.css`; add new classes: `.create-workflow-form` (flex-column layout, gap 1rem, padding 1.5rem), `.form-row` (label + input stacked), `.form-row label` (0.875rem, uppercase, color #8b949e), `.form-row input`, `.form-row select` (same style as `.filter-select` in WorkflowOrders.css: dark background #0d1117, border #30363d, color #e6edf3, border-radius 6px, padding 0.5rem 0.75rem), `.form-toggles` (flex row, gap 1.5rem for boolean toggles), `.form-section-title` (color #8b949e, font-size 0.8rem, uppercase, letter-spacing 0.5px, margin-bottom 0.5rem, border-bottom 1px solid #30363d), `.form-error` (color #f85149, font-size 0.875rem, margin-top 0.25rem for inline field errors), `.save-error-banner` (background rgba(248,81,73,0.15), border 1px solid rgba(248,81,73,0.3), border-radius 6px, padding 0.75rem 1rem, color #f85149, margin-bottom 1rem), `.form-actions` (flex row, justify-content flex-end, gap 0.75rem, padding-top 1rem, border-top 1px solid #30363d), `.btn-save` (background #1f6feb, color white, border 1px solid #58a6ff, border-radius 6px, padding 0.75rem 1.5rem), `.btn-cancel` (background transparent, color #8b949e, border 1px solid #30363d, border-radius 6px, padding 0.75rem 1.5rem)
- [x] T008 [US1] Add `showCreateModal` state (boolean, default false) and `createWorkflow` handler to `frontend/src/pages/Workflows.tsx`: import `WorkflowCreateModal` from `../components/WorkflowCreateModal`; add a "New Workflow" button to the `.workflows-header` div (styled as a primary action button); on click set `showCreateModal = true`; render `{showCreateModal && <WorkflowCreateModal onClose={() => setShowCreateModal(false)} onSuccess={(newWorkflow) => { setWorkflows(prev => [newWorkflow as unknown as WorkflowListItem, ...prev]); setShowCreateModal(false); }} />}` at the bottom of the return (after `WorkflowDetailModal`); note: `WorkflowDetail` returned from the API may not have all `WorkflowListItem` fields (last_order_timestamp etc.) — call `loadWorkflows()` instead of prepending if casting is complex (depends on T006)

**Checkpoint**: `curl -X POST http://localhost:8000/api/workflow/workflows` with a valid payload returns 201 with WorkflowDetail JSON; clicking "New Workflow" on `/workflows` opens the modal; filling and saving creates the workflow and shows it in the list; Cancel closes without saving.

---

## Phase 4: User Story 2 — Create Workflow from Asset Detail Page (Priority: P2)

**Goal**: A "Create Workflow" button on the Asset Detail page opens the same `WorkflowCreateModal` with `index` and `cfd` pre-filled from the asset being viewed.

**Independent Test**: Navigate to an asset detail page, click "Create Workflow", verify index and CFD are pre-filled, complete remaining fields, save, verify the workflow appears on the Workflows page. See `quickstart.md` scenario 4.

### Implementation

- [x] T009 [US2] Add "Create Workflow" button and modal state to `frontend/src/pages/AssetDetail.tsx`: import `WorkflowCreateModal` from `../components/WorkflowCreateModal`; add `showCreateWorkflow` state (boolean, default false); extract `code` from the URL params (the asset code, e.g. `"GER40.I"` — already parsed in the component); add a "Create Workflow" button in the asset detail header area; on click set `showCreateWorkflow = true`; render `{showCreateWorkflow && <WorkflowCreateModal onClose={() => setShowCreateWorkflow(false)} onSuccess={() => setShowCreateWorkflow(false)} prefill={{ index: code, cfd: code }} />}` at the bottom of the return; ensure the `prefill` prop pre-fills both index and CFD fields in the modal with the asset's code (both editable) (depends on T006)

**Checkpoint**: Navigate to `/asset/GER40.I:xpar`, click "Create Workflow", verify the modal opens with index = `"GER40.I"` and CFD = `"GER40.I"` pre-filled; complete the form and save; verify the new workflow appears on the Workflows page.

---

## Phase 5: User Story 3 — Edit Workflow (Priority: P2)

**Goal**: An "Edit" button in the workflow detail modal opens `WorkflowCreateModal` in edit mode, pre-filled with the workflow's current values. On save, `PUT /api/workflow/workflows/{id}` updates the record and the detail view reflects the changes immediately.

**Independent Test**: Open a workflow detail modal, click "Edit", change the spread, save, verify the updated spread appears in the detail view.

### Implementation

- [x] T013 [P] Add `update_workflow(self, workflow_id: str, workflow: Dict[str, Any]) -> None` method to `client/aws_client.py` after `put_workflow`: call `self.dynamodb.Table("workflows").put_item(Item=workflow)` (full replacement); check HTTP status ≥ 400 and log error + raise `RuntimeError("Failed to update workflow")` if so
- [x] T014 Add `update_workflow(self, workflow_id: str, data: WorkflowCreateRequest) -> WorkflowDetail` method to `services/workflow_service.py`: (1) fetch existing workflow via `self.dynamodb_client.get_workflow_by_id(workflow_id)`; raise `ValueError("Workflow not found")` if None; (2) apply same end_date and indicator-specific validations as `create_workflow`; (3) build updated `workflow_dict` reusing existing `id` and `created_at`, setting `updated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")`; (4) call `self.dynamodb_client.update_workflow(workflow_id, converted_dict)`; (5) return `self._convert_to_detail(workflow_dict)` (depends on T013)
- [x] T015 [P] Add `PUT /api/workflow/workflows/{id}` endpoint to `api/routers/workflow.py`: `@router.put("/workflows/{workflow_id}", response_model=WorkflowDetail, status_code=200)`; handler `async def update_workflow(workflow_id: str = Path(...), data: WorkflowCreateRequest, workflow_service: WorkflowService = Depends(get_workflow_service))`; catch `ValueError` → 422; catch generic `Exception` → 500 "Failed to update workflow" (depends on T014)
- [x] T016 [P] Add `updateWorkflow: async (id: string, data: WorkflowCreateRequest): Promise<WorkflowDetail>` method to `workflowService` in `frontend/src/services/api.ts`: `PUT /api/workflow/workflows/{id}` with JSON body, return `response.data`
- [x] T017 Add `workflow?: WorkflowDetail` prop to `WorkflowCreateModal` in `frontend/src/components/WorkflowCreateModal.tsx`: when `workflow` is provided, pre-fill all form state from it on mount; change modal title to "Edit Workflow"; on submit call `workflowService.updateWorkflow(workflow.id, payload)` instead of `createWorkflow`; all existing validation and error-banner behaviour unchanged (depends on T016)
- [x] T018 Add "Edit" button to `WorkflowDetailModal` in `frontend/src/components/WorkflowDetailModal.tsx`: add `showEdit` state (boolean, default false); add an "Edit" button in `.modal-header`; when clicked set `showEdit = true`; render `{showEdit && <WorkflowCreateModal workflow={workflow} onClose={() => setShowEdit(false)} onSuccess={(updated) => { setWorkflow(updated); setShowEdit(false); }} />}` — import `WorkflowCreateModal`; `updated` replaces the current `workflow` state so detail view reflects changes immediately (depends on T017)

**Checkpoint**: Open a workflow detail modal, click "Edit", verify all fields pre-filled, change spread, save → detail view shows new spread; `curl -X PUT http://localhost:8000/api/workflow/workflows/{id}` with valid payload returns 200 with updated `WorkflowDetail`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T010 [P] Run `poetry run mypy model/workflow_api.py client/aws_client.py services/workflow_service.py api/routers/workflow.py` and `poetry run flake8 model/workflow_api.py client/aws_client.py services/workflow_service.py api/routers/workflow.py` from repo root; fix any type or lint errors in the modified backend files
- [x] T011 [P] Run `npm run build` and `npm run lint` in `frontend/`; fix any TypeScript or ESLint errors introduced in `WorkflowCreateModal.tsx`, `api.ts`, `Workflows.tsx`, `AssetDetail.tsx`
- [x] T012 Run all acceptance scenarios from `specs/016-workflow-create/quickstart.md` (scenarios 1–9) manually
- [x] T019 [P] Run backend mypy + flake8 on updated files after Phase 5
- [x] T020 [P] Run `npm run build` + lint on updated frontend files after Phase 5

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No dependencies — start immediately; T001 and T002 and T004 are parallel
- **Phase 3 (US1)**: T005 depends on T001 + T003; T006 depends on T004; T007 parallel with T006; T008 depends on T006
- **Phase 4 (US2)**: Depends on T006 (WorkflowCreateModal must exist)
- **Phase 5 (US3 — Edit)**: T013 parallel; T014 depends on T013; T015 depends on T014; T016 parallel; T017 depends on T016; T018 depends on T017
- **Phase 6 (Polish)**: Depends on all Phase 5 tasks complete

### Execution Graph

```
T001 [P] ──> T003 ──> T005
T002 [P] ──> T003
T004 [P] ──> T006 ──> T008
             T007 [P] (alongside T006)
T006 ──────> T009 [P]

T010 [P] ┐
T011 [P] ├── (after all implementation tasks)
T012     ┘
```

### Parallel Opportunities

```bash
# Phase 2 — launch together:
Task: "5 Pydantic input models in model/workflow_api.py"      # T001
Task: "put_workflow() in client/aws_client.py"               # T002
Task: "TS interfaces + createWorkflow() in api.ts"           # T004

# Phase 3 — backend vs frontend in parallel (after T001+T002+T003):
Task: "POST /api/workflow/workflows in api/routers/workflow.py"  # T005
Task: "WorkflowCreateModal.tsx"                               # T006 (after T004)
Task: "WorkflowCreateModal.css"                               # T007 [P with T006]

# Phase 5 — lint/build in parallel:
Task: "Backend mypy + flake8"                                 # T010 [P]
Task: "Frontend build + lint"                                 # T011 [P]
```

---

## Implementation Strategy

### MVP (User Story 1 only — Phase 2 + Phase 3)

1. Complete Phase 2 (T001 → T002 → T003, T004 in parallel) — foundational models + API
2. Complete Phase 3 (T005 backend; T006 → T008 frontend)
3. Complete Phase 5 lint/build (T010, T011)
4. **STOP and VALIDATE**: Confirm modal opens, form works for all 6 indicator types, workflow appears in list
5. Proceed to Phase 4 (US2) once US1 is stable

### Incremental Delivery

1. Phase 2 complete → backend models and client method ready; API endpoint live
2. US1 complete → creation modal functional on Workflows page → deploy/demo
3. US2 complete → creation from Asset Detail page → deploy/demo

### Commit strategy

```
feat: add workflow creation modal with indicator-aware form
```

---

## Notes

- `[P]` = different files, no shared in-progress dependency
- `[US1]` / `[US2]` map every task to its user story for traceability
- No test tasks — not requested; no frontend testing framework
- The `WorkflowDetail` return type from `create_workflow()` reuses the existing model — no new response model needed
- `signal` is always `"breakout"` — injected by the service layer, never exposed in the form
- `WorkflowCreateModal` accepts a `prefill` prop — this is the only coupling point between US1 and US2; no other changes needed in the modal for US2
