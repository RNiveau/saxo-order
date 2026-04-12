# Tasks: Inclined Line Indicator (ROB/SOH)

**Input**: Design documents from `/specs/512-inclined-line-indicator/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Merge Existing Work)

**Purpose**: Integrate partial implementation from `inclined-indicator` branch into the working branch

- [ ] T001 Cherry-pick or merge the diff from `inclined-indicator` branch (commits e1288c5, e10190d) into the current branch, bringing in Point, IndicatorInclined, IndicatorType.INCLINED, workflow loader parsing, workflow engine dispatch, InclinedWorkflow skeleton, find_linear_function, and apply_linear_function
- [ ] T002 Verify merged code compiles and existing tests pass with `poetry run pytest`

**Checkpoint**: All existing partial implementation is on the working branch. Existing tests still pass.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model and math layer must be solid before workflow logic can be built

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Add validation in model/workflow.py IndicatorInclined constructor: raise SaxoException if x1.x == x2.x (same date prevents line definition)
- [ ] T004 [P] Add unit tests for find_linear_function() and apply_linear_function() in tests/services/test_indicator_service.py — test with known point pairs (ascending line, descending line, horizontal edge case)

**Checkpoint**: Foundation ready — model validates inputs, math utilities are tested.

---

## Phase 3: User Story 1 + 2 — Core Workflow Logic (Priority: P1) 🎯 MVP

**Goal**: The workflow engine can load an inclined indicator from YAML, compute the projected line value at the current date using business days, and evaluate above/below conditions against the current candle price with spread tolerance.

**Independent Test**: Define a workflow in workflows.yml with an inclined indicator, run the workflow engine, and verify it projects the line correctly and triggers when candle price is within spread of the projected value.

### Implementation

- [ ] T005 Implement InclinedWorkflow.init_workflow() in engines/workflows.py — cast indicator to IndicatorInclined, call number_of_day_between_dates() for x1→x2 distance (business days) and x1→current_date distance, then call apply_linear_function() to compute projected line value, store as self.indicator_value (single float)
- [ ] T006 Implement InclinedWorkflow.below_condition() in engines/workflows.py — mirror PolariteWorkflow pattern: check if candle close/high or element is within [indicator_value - spread, indicator_value]
- [ ] T007 Implement InclinedWorkflow.above_condition() in engines/workflows.py — mirror PolariteWorkflow pattern: check if candle close/low or element is within [indicator_value, indicator_value + spread]
- [ ] T008 Add unit tests for InclinedWorkflow in tests/engines/test_workflows.py — test init_workflow with mocked saxo_client.is_day_open(), test below_condition and above_condition with known candle values and spread, test edge case where indicator returns None (insufficient data)
- [ ] T009 Verify the nbr_hour multiplicator refactor in engines/workflow_engine.py _get_candles_from_indicator_ut() is correct (the inclined-indicator branch moved `nbr_hour *= multiplicator` after the match statement)
- [ ] T010 Add a sample inclined workflow to workflows.yml for manual testing (can be disabled with enable: false)

**Checkpoint**: Core inclined indicator works end-to-end via YAML workflow definition. A trader can configure two reference points and the engine evaluates price against the projected line.

---

## Phase 4: User Story 3 — API & Frontend Integration (Priority: P2)

**Goal**: A trader can create, view, and edit inclined line workflows from the web UI, with the indicator type dropdown including "inclined" and dynamic form fields for the two reference points.

**Independent Test**: Open the workflow creation form, select "inclined", fill in two reference points, save, and verify the workflow appears in the list with correct configuration.

### Backend API

- [ ] T011 [P] [US3] Add PointInput Pydantic model and extend WorkflowIndicatorInput with optional x1/x2 fields in model/workflow_api.py
- [ ] T012 [P] [US3] Add optional x1_date, x1_price, x2_date, x2_price fields to IndicatorDetail in model/workflow_api.py
- [ ] T013 [US3] Add INCLINED to the indicator_type_labels dict with label "Inclined (ROB/SOH)" in api/routers/workflow.py
- [ ] T014 [US3] Add inclined-specific validation in services/workflow_service.py create_workflow() and update_workflow() — require x1 and x2 when indicator name is "inclined", validate x1.date != x2.date, validate dates are ISO format
- [ ] T015 [US3] Update workflow serialization/deserialization in services/workflow_service.py to persist and load x1/x2 fields from DynamoDB workflow items
- [ ] T016 [US3] Update _build_workflow_detail() in api/routers/workflow.py (or services/workflow_service.py) to populate x1_date, x1_price, x2_date, x2_price in IndicatorDetail response for inclined indicators

### Frontend

- [ ] T017 [US3] Add conditional reference point inputs in frontend/src/components/WorkflowCreateModal.tsx — when indicator name is "inclined", show date and price inputs for Point 1 and Point 2, hide value/zone_value fields
- [ ] T018 [US3] Update form state and payload construction in frontend/src/components/WorkflowCreateModal.tsx — add x1Date, x1Price, x2Date, x2Price state variables, include x1/x2 in submitted payload when indicator is "inclined"
- [ ] T019 [US3] Update edit mode population in frontend/src/components/WorkflowCreateModal.tsx — when loading an existing inclined workflow for editing, populate the x1/x2 form fields from the workflow detail response

**Checkpoint**: Inclined workflows can be created and managed from the UI. The indicator types dropdown includes "Inclined (ROB/SOH)".

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup and verification across all stories

- [ ] T020 [P] Remove the commented-out experimental code in saxo_order/commands/internal.py technical() that was added during prototyping on the inclined-indicator branch
- [ ] T021 [P] Run full test suite with `poetry run pytest --cov` and verify no regressions
- [ ] T022 [P] Run code quality checks: `poetry run black .`, `poetry run isort .`, `poetry run mypy .`, `poetry run flake8`
- [ ] T023 [P] Run frontend build: `cd frontend && npm run build && npm run lint`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion
- **US1+US2 Core (Phase 3)**: Depends on Phase 2 — this is the MVP
- **US3 API & Frontend (Phase 4)**: Depends on Phase 3 (needs model and engine working)
- **Polish (Phase 5)**: Depends on all previous phases

### User Story Dependencies

- **US1 + US2 (P1)**: Combined because US2 (configuration) is a prerequisite for US1 (monitoring). After Phase 2 they can start.
- **US3 (P2)**: Depends on US1+US2 being complete (needs working model classes and engine logic). Backend API tasks (T011-T016) can run in parallel. Frontend tasks (T017-T019) depend on API tasks.

### Within Each Phase

- Tasks marked [P] within the same phase can run in parallel
- Unmarked tasks run sequentially in listed order

### Parallel Opportunities

- T003 and T004 can run in parallel (different files)
- T011 and T012 can run in parallel (same file but independent sections)
- T020, T021, T022, T023 can all run in parallel

---

## Parallel Example: Phase 4 Backend

```
# These can run in parallel (independent additions to model file):
Task T011: Add PointInput + extend WorkflowIndicatorInput in model/workflow_api.py
Task T012: Add x1/x2 fields to IndicatorDetail in model/workflow_api.py

# Then sequentially (depends on models):
Task T013: Add INCLINED to indicator_type_labels
Task T014: Add validation in workflow_service.py
Task T015: Update serialization in workflow_service.py
Task T016: Update detail builder for response
```

---

## Implementation Strategy

### MVP First (Phase 1 → 2 → 3)

1. Merge existing branch code → verify tests pass
2. Add model validation + math utility tests
3. Implement InclinedWorkflow logic (init_workflow + conditions)
4. **STOP and VALIDATE**: Test with a sample workflow in workflows.yml
5. This delivers the core value: inclined line monitoring via workflow engine

### Incremental Delivery

1. Phase 1-3 → MVP: YAML-based inclined workflows work end-to-end
2. Phase 4 → Full feature: UI creation and management
3. Phase 5 → Production-ready: cleanup, coverage, quality gates

---

## Notes

- The `inclined-indicator` branch has ~70% of the model/loader/engine scaffolding done — Phase 1 merges this
- The core new work is in T005-T007 (InclinedWorkflow logic) — this is where the feature's value lives
- PolariteWorkflow in engines/workflows.py is the reference pattern for condition evaluation
- The `saxo_client` dependency in InclinedWorkflow constructor (for business day calculation) is already wired in the branch code
