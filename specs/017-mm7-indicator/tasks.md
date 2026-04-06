# Tasks: MM7 Indicator & Workflow

**Input**: Design documents from `/specs/017-mm7-indicator/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ quickstart.md ✅

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Foundational (Blocking Prerequisite)

**Purpose**: The `IndicatorType.MA7` enum value must exist before any workflow class or engine dispatch can reference it. This single task unblocks all user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T001 Add `MA7 = "ma7"` to `IndicatorType` enum in `model/workflow.py` (after `MA50 = "ma50"`)

**Checkpoint**: `IndicatorType.MA7` resolves correctly — US1 and US2 implementation can now begin.

---

## Phase 2: User Story 1 — MM7 Workflow Engine Integration (Priority: P1) 🎯 MVP

**Goal**: A workflow configured with `ma7` as indicator type runs correctly — computes the 7-period moving average and evaluates price proximity conditions for both "above" and "below" directions.

**Independent Test**: Configure a workflow with `IndicatorType.MA7` in the test suite; verify the engine computes `mobile_average(candles, 7)` and that below/above conditions trigger correctly. Run `poetry run pytest tests/engines/test_workflow_engine.py -v`.

### Implementation for User Story 1

- [ ] T002 [P] [US1] Add `MA7Workflow` class in `engines/workflows.py` after `MA50Workflow` — `init_workflow` calls `mobile_average(candles, 7)`; `below_condition` and `above_condition` mirror `MA50Workflow` exactly
- [ ] T003 [P] [US1] Update `engines/workflow_engine.py` — add `MA7Workflow` to import from `engines.workflows`; add `case IndicatorType.MA7` in main dispatch (instantiate `MA7Workflow()`); add `case IndicatorType.MA7: nbr_weeks = 12` in weekly candle-count match; add `case IndicatorType.MA7: nbr_hour = 12 * multiplicator` in hourly candle-count match
- [ ] T004 [US1] Add MM7 parametrized test cases in `tests/engines/test_workflow_engine.py` mirroring `test_run_ma_50_workflow` — cover `WorkflowDirection.BELOW` and `WorkflowDirection.ABOVE` with mocked MA7 value (depends on T002, T003)

**Checkpoint**: US1 fully functional. `poetry run pytest tests/engines/test_workflow_engine.py -v` passes including new MM7 cases. All existing MA50 tests still pass.

---

## Phase 3: User Story 2 — Enum Recognition & Deserialization (Priority: P2)

**Goal**: `mm7` is accepted as a valid indicator name in workflow YAML configuration and deserializes correctly at engine startup.

**Independent Test**: Add a `name: ma7` entry in `workflows.yml` (or a test fixture YAML), start the workflow engine, and confirm no `"indicator ma7 isn't managed"` error is logged and the workflow initializes without exception.

### Implementation for User Story 2

- [ ] T005 [US2] Smoke-test YAML deserialization — add a dry-run MM7 workflow entry to `workflows.yml` (e.g., `name: buy mm7 h4 test`, `dry_run: true`) and verify the engine loads it without error using the quickstart.md YAML example as reference (depends on T001, T003)

**Checkpoint**: US2 complete. `IndicatorType.get_value("ma7")` resolves to `IndicatorType.MA7`; engine reads an `ma7` workflow from YAML without hitting the unhandled indicator fallthrough.

---

## Phase 4: User Story 3 — Indicator Types API Endpoint & Frontend Integration (Priority: P2)

**Goal**: The backend exposes `GET /api/workflow/indicator-types` returning all `IndicatorType` members with display labels. The frontend fetches from this endpoint instead of using a hardcoded list.

**Independent Test**: Call `GET /api/workflow/indicator-types` and verify the response includes all indicator types including `mm7`. Open the workflow creation modal and verify the dropdown populates correctly.

### Implementation for User Story 3

- [ ] T009 [US3] Add `INDICATOR_LABELS` mapping and `GET /api/workflow/indicator-types` endpoint in `api/routers/workflow.py` — returns `[{ "value": member.value, "label": label }]` for each `IndicatorType` member (depends on T001)
- [ ] T010 [P] [US3] Add `getIndicatorTypes()` method to `workflowService` in `frontend/src/services/api.ts` — calls `GET /api/workflow/indicator-types` and returns `{ value: string; label: string }[]`
- [ ] T011 [US3] Update `WorkflowCreateModal.tsx` — remove hardcoded `INDICATOR_OPTIONS`, fetch from `workflowService.getIndicatorTypes()` on mount, handle loading state (depends on T009, T010)

**Checkpoint**: US3 complete. Dropdown in modal is driven by the API; adding a new `IndicatorType` requires only a backend change.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and validation across all stories.

- [ ] T006 [P] Run `poetry run mypy engines/workflows.py engines/workflow_engine.py model/workflow.py api/routers/workflow.py` — fix any type errors
- [ ] T007 [P] Run `poetry run black . && poetry run isort . && poetry run flake8` — fix any formatting/linting issues
- [ ] T008 Run full test suite `poetry run pytest --cov` — confirm no regressions and coverage maintained

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 2)**: Depends on T001 — T002 and T003 can run in parallel with each other; T004 depends on T002 + T003
- **US2 (Phase 3)**: Depends on T001 + T003
- **US3 (Phase 4)**: T009 depends on T001; T010 is independent; T011 depends on T009 + T010
- **Polish (Phase 5)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Unblocked after T001
- **US2 (P2)**: Unblocked after T001 + T003 (engine dispatch must exist for YAML to route correctly)
- **US3 (P2)**: T009 unblocked after T001; T010 unblocked immediately; T011 unblocked after T009 + T010

### Parallel Opportunities

After T001 completes:
- T002 (`engines/workflows.py`) and T003 (`engines/workflow_engine.py`) touch different files → run in parallel
- T006 and T007 (Polish) → run in parallel

---

## Parallel Example: User Story 1

```bash
# After T001 completes, launch T002 and T003 together (different files):
Task T002: "Add MA7Workflow class in engines/workflows.py"
Task T003: "Update engines/workflow_engine.py — import + 3 dispatch cases"

# Then T004 once both complete:
Task T004: "Add MM7 test cases in tests/engines/test_workflow_engine.py"
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: T001 — add enum value
2. Complete Phase 2: T002 + T003 (parallel) → T004
3. **STOP and VALIDATE**: `poetry run pytest tests/engines/test_workflow_engine.py -v`
4. Ship: the core trigger behavior is live

### Full Delivery (US1 + US2 + US3 + Polish)

1. T001 → T002 ‖ T003 → T004 → T005
2. T001 → T009; T010 (parallel, independent) → T011
3. T006 ‖ T007 → T008

Total: 11 tasks.

---

## Notes

- [P] tasks = different files, no mutual dependencies — safe to run in parallel
- T002 and T003 are independent (different files) — ideal for parallel work
- No new files are created; all changes are additions to existing files
- Commit after T001 (enum), after T002+T003 (implementation), after T004 (tests)
- Verify `poetry run pytest` passes before each commit
