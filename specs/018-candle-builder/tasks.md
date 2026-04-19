# Tasks: Unified Candle Builder

**Input**: Design documents from `/specs/018-candle-builder/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Test tasks included where existing tests must be updated (this is a refactoring of tested code).

**Organization**: Tasks grouped by user story priority. Since this is an incremental refactoring (not greenfield), setup/foundational phases handle model fixes and cleanup before story-level work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Model Changes)

**Purpose**: Fix model inaccuracies and add missing enum value. These are prerequisite for all subsequent work.

- [ ] T001 Add `M30 = "30m"` value to UnitTime enum in model/workflow.py
- [ ] T002 [P] Fix `EUMarket.close_hour` from 17 to 15 in model/__init__.py
- [ ] T003 [P] Fix `USMarket.close_hour` from 21 to 20 in model/__init__.py
- [ ] T004 Add `h4_blocks: List[int]` field to `Market` dataclass in model/__init__.py with default empty list
- [ ] T005 Set `h4_blocks=[3, 4, 2]` in `EUMarket.__init__` in model/__init__.py
- [ ] T006 [P] Set `h4_blocks=[4, 3]` in `USMarket.__init__` in model/__init__.py
- [ ] T007 Run existing tests to verify model changes don't break anything: `poetry run pytest tests/ -q`

**Checkpoint**: Model layer updated. All existing tests should pass (close_hour changes may cause test adjustments in Phase 2).

---

## Phase 2: Foundational (CFD Fallback Removal)

**Purpose**: Remove CFD fallback mechanism from candle builder. Simplifies the interface before merging methods.

**⚠️ CRITICAL**: Must complete before user story phases, as it changes the candle builder's public interface.

- [ ] T008 Remove CFD fallback logic (delta check + cfd data fetch) from `build_hour_candles` in services/candles_service.py (approximately lines 306-320)
- [ ] T009 Remove `cfd_code` parameter from `build_hour_candles` signature in services/candles_service.py
- [ ] T010 Remove `cfd_code` parameter from `build_weekly_candles` signature in services/candles_service.py
- [ ] T011 Remove `cfd_code` argument from `build_weekly_candles`'s internal call to `build_hour_candles` in services/candles_service.py
- [ ] T012 [P] Update caller in `_get_candles_from_indicator_ut` to remove `cfd_code=workflow.cfd` from `build_hour_candles` call in engines/workflow_engine.py (line ~232)
- [ ] T013 [P] Update caller in `_get_candles_from_indicator_ut` to remove `cfd_code=workflow.cfd` from `build_weekly_candles` call in engines/workflow_engine.py (line ~199)
- [ ] T014 [P] Update 3 callers in saxo_order/commands/snapshot.py to remove `cfd_code=index` from `build_hour_candles` calls (lines ~43, ~53, ~63)
- [ ] T015 Update test mocks and assertions in tests/services/test_candles_service.py to remove `cfd_code` parameter
- [ ] T016 [P] Update test mocks and assertions in tests/engines/test_workflow_engine.py to remove `cfd_code` parameter
- [ ] T017 Run full relevant test suite: `poetry run pytest tests/services/test_candles_service.py tests/engines/test_workflow_engine.py tests/utils/test_helper.py -q`

**Checkpoint**: CFD fallback removed. Candle builder only uses asset data. All tests pass.

---

## Phase 3: User Story 3 - Build H1 from 30m (Priority: P1) + User Story 6 - Unified US/EU (Priority: P1) + User Story 1 - Build Daily from 30m (Priority: P1)

**Goal**: Parameterize the H1 and Daily builders to use Market object instead of hardcoded open_hour checks. This implements Stories 1, 3, and 6 together because they share the same code paths.

**Independent Test**: Build H1 and Daily candles for both EU and US assets through the parameterized builders. Verify OHLC values match the current behavior exactly.

### Implementation

- [ ] T018 [US3] [US6] Refactor `_build_h1_from_30m` in services/candles_service.py to accept `Market` object (already does) and verify close_hour filtering works correctly with the fixed close_hour values (15 for EU, 20 for US)
- [ ] T019 [US1] [US6] Refactor `build_daily_candles_from_h1` in utils/helper.py: replace `if open_hour_utc0 == 7` / `elif open_hour_utc0 == 13` with a single code path that derives `ending_hour = close_hour - (1 if open_minutes == 30 else 0)` and `num_h1 = close_hour - open_hour + (1 if open_minutes == 0 else 0)` from Market parameters. Change signature from `(candles, open_hour_utc0)` to `(candles, market)`
- [ ] T020 [US1] [US6] Update callers of `build_daily_candles_from_h1` in services/candles_service.py to pass Market object instead of `open_hour_utc0` (in `get_candle_per_hour` and `build_hour_candles`)
- [ ] T021 [US1] Update tests for `build_daily_candles_from_h1` in tests/utils/test_helper.py to pass Market objects instead of open_hour integers. Verify expected results are identical.
- [ ] T022 Run daily builder tests: `poetry run pytest tests/utils/test_helper.py -k "daily" -q`

**Checkpoint**: H1 builder verified with corrected close_hours. Daily builder parameterized by Market. Both EU and US produce identical results to before.

---

## Phase 4: User Story 4 - Build H4 from H1 (Priority: P2)

**Goal**: Parameterize the H4 builder to use `Market.h4_blocks` instead of hardcoded open_hour identity checks.

**Independent Test**: Build H4 candles for EU (expect 3/4/2 grouping) and US (expect 4/3 grouping) using the parameterized builder. Verify results match current behavior.

### Implementation

- [ ] T023 [US4] Refactor `build_h4_candles_from_h1` in utils/helper.py: replace `if open_hour_utc0 == 7` / `elif open_hour_utc0 == 13` with a single loop that iterates over `Market.h4_blocks` to determine group sizes. Change signature from `(candles, open_hour_utc0)` to `(candles, market)`. Compute ending hours for each H4 block by walking backward from the session end using h4_blocks sizes and the Market's close_hour/open_minutes.
- [ ] T024 [US4] Update callers of `build_h4_candles_from_h1` in services/candles_service.py to pass Market object instead of `open_hour_utc0` (in `get_candle_per_hour` and `build_hour_candles`)
- [ ] T025 [US4] Update tests for `build_h4_candles_from_h1` in tests/utils/test_helper.py to pass Market objects instead of open_hour integers. Verify EU produces 3/4/2 groups and US produces 4/3 groups - identical to current behavior.
- [ ] T026 Run H4 builder tests: `poetry run pytest tests/utils/test_helper.py -k "h4" -q`

**Checkpoint**: H4 builder parameterized by Market.h4_blocks. Adding a new market only requires defining a new Market instance with its h4_blocks.

---

## Phase 5: User Story 2 - Rebuild current daily candle (Priority: P1) + User Story 5 - Weekly candles (Priority: P2)

**Goal**: Verify that current-day rebuild and weekly candle rebuild work correctly after the parameterization changes.

**Independent Test**: During a simulated trading session, verify the rebuilt current-day candle appears at index 0. Verify weekly candles include the rebuilt current week.

### Implementation

- [ ] T027 [US2] [US5] Verify `build_hour_candles` in services/candles_service.py correctly creates a Market object internally and passes it to the parameterized builders. Update the Market construction to use the new `h4_blocks` parameter (determine from open_hour or pass from caller).
- [ ] T028 [US5] Verify `build_weekly_candles` in services/candles_service.py works correctly after the `build_hour_candles` signature changes (cfd_code removed, Market passed through).
- [ ] T029 [US2] [US5] Run candle service tests: `poetry run pytest tests/services/test_candles_service.py -q`

**Checkpoint**: Current day and weekly rebuild verified with parameterized builders.

---

## Phase 6: User Story 8 - Single entry point (Priority: P2)

**Goal**: Merge `get_candle_per_hour` and `build_hour_candles` into a single `build_candles` method.

**Independent Test**: Call the unified method for H1, H4, and Daily. Verify taking `[0]` gives the same result as the old `get_candle_per_hour`.

### Implementation

- [ ] T030 [US8] Rename `build_hour_candles` to `build_candles` in services/candles_service.py. Update signature to accept `Market` object instead of individual `open_hour_utc0`, `close_hour_utc0`, `open_minutes` parameters. Add a `count` parameter for number of target-UT candles needed. Compute `nbr_30m` internally based on UT and count.
- [ ] T031 [US8] Remove `get_candle_per_hour` method from services/candles_service.py. Move its count-calculation logic (H1=4, H4=16, D=40 thirty-minute candles) into the `count`-based computation of `build_candles`.
- [ ] T032 [US8] Update `build_weekly_candles` in services/candles_service.py to call `build_candles` instead of `build_hour_candles`.
- [ ] T033 [P] [US8] Update `_get_candles_from_indicator_ut` in engines/workflow_engine.py to call `build_candles` with Market object and count parameter instead of `build_hour_candles`.
- [ ] T034 [P] [US8] Update `_run_workflow` in engines/workflow_engine.py to call `build_candles(..., count=1)[0]` instead of `get_candle_per_hour` (line ~262).
- [ ] T035 [P] [US8] Update `_get_trigger_candle` in engines/workflow_engine.py to call `build_candles(..., count=1)[0]` instead of `get_candle_per_hour` (line ~340).
- [ ] T036 [P] [US8] Update 3 callers in saxo_order/commands/snapshot.py to call `build_candles` with Market object.
- [ ] T037 [US8] Update tests in tests/services/test_candles_service.py for renamed method and new signature.
- [ ] T038 [US8] Update tests in tests/engines/test_workflow_engine.py for the method rename and signature changes.
- [ ] T039 Run full test suite: `poetry run pytest tests/services/test_candles_service.py tests/engines/test_workflow_engine.py -q`

**Checkpoint**: Single `build_candles` method replaces both `get_candle_per_hour` and `build_hour_candles`. All callers updated.

---

## Phase 7: User Story 7 - Remove CFD fallback (Priority: P2)

**Note**: Already completed in Phase 2 (Foundational). No additional tasks needed. This phase exists for traceability.

---

## Phase 8: User Story 9 - Remove legacy function (Priority: P3)

**Goal**: Remove `build_daily_candle_from_hours` and migrate its single production caller.

**Independent Test**: After removal, verify no code references the function and all tests pass.

### Implementation

- [ ] T040 [US9] Analyze the caller in saxo_order/commands/alerting.py (line ~663) to understand how it determines market context (EU vs US) and what data it passes. Plan the migration to use `build_candles` with appropriate Market.
- [ ] T041 [US9] Migrate `saxo_order/commands/alerting.py:663` from `build_daily_candle_from_hours(hour_candles, today.day)` to use the unified `build_candles` pipeline with the correct Market object.
- [ ] T042 [US9] Remove `build_daily_candle_from_hours` function from utils/helper.py (lines 8-48).
- [ ] T043 [US9] Remove `test_build_daily_candle_from_hours` test from tests/utils/test_helper.py.
- [ ] T044 [US9] Remove the import of `build_daily_candle_from_hours` from saxo_order/commands/alerting.py and tests/utils/test_helper.py.
- [ ] T045 Run alerting and helper tests: `poetry run pytest tests/saxo_order/commands/test_alerting.py tests/utils/test_helper.py -q`

**Checkpoint**: Legacy function fully removed. No dead code remains.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [ ] T046 Run full relevant test suite: `poetry run pytest tests/ -q` to verify no regressions across all modules
- [ ] T047 Run type checker: `poetry run mypy services/candles_service.py utils/helper.py model/workflow.py model/__init__.py`
- [ ] T048 Run formatter and linter: `poetry run black services/ utils/ model/ engines/ saxo_order/ tests/ && poetry run isort services/ utils/ model/ engines/ saxo_order/ tests/ && poetry run flake8 services/ utils/ model/ engines/ saxo_order/`
- [ ] T049 Verify no remaining references to old function names (`get_candle_per_hour`, `build_hour_candles`, `build_daily_candle_from_hours`) in production code (grep check)
- [ ] T050 Verify no remaining hardcoded `open_hour_utc0 == 7` or `open_hour_utc0 == 13` checks in utils/helper.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (CFD Removal)**: Depends on Phase 1 completion
- **Phase 3 (H1 + Daily parameterization)**: Depends on Phase 2 completion
- **Phase 4 (H4 parameterization)**: Depends on Phase 2 completion. Can run in parallel with Phase 3.
- **Phase 5 (Current day + Weekly verify)**: Depends on Phases 3 and 4
- **Phase 6 (Single entry point)**: Depends on Phase 5
- **Phase 7 (CFD removal - traceability)**: Already done in Phase 2
- **Phase 8 (Remove legacy)**: Depends on Phase 6
- **Phase 9 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (Daily from 30m)**: Phase 3 - depends on foundational phases only
- **US2 (Current day rebuild)**: Phase 5 - depends on US1 (daily builder must be parameterized first)
- **US3 (H1 from 30m)**: Phase 3 - depends on foundational phases only
- **US4 (H4 from H1)**: Phase 4 - depends on foundational phases only, parallel with US1/US3
- **US5 (Weekly)**: Phase 5 - depends on US1 and US2
- **US6 (Unified US/EU)**: Phases 3+4 - cross-cutting, validated by parameterization of all builders
- **US7 (Remove CFD)**: Phase 2 - foundational, no story dependencies
- **US8 (Single entry point)**: Phase 6 - depends on all builder parameterization (US1, US3, US4)
- **US9 (Remove legacy)**: Phase 8 - depends on US8 (needs unified entry point for migration)

### Execution Graph

```
Phase 1 (Model) → Phase 2 (CFD removal)
                       │
              ┌────────┴────────┐
              v                 v
     Phase 3 (H1+Daily)   Phase 4 (H4)
              │                 │
              └────────┬────────┘
                       v
              Phase 5 (Verify rebuild)
                       │
                       v
              Phase 6 (Merge methods)
                       │
                       v
              Phase 8 (Remove legacy)
                       │
                       v
              Phase 9 (Polish)
```

### Parallel Opportunities

- **Phase 3 and Phase 4** can run in parallel (different functions in utils/helper.py)
- Within Phase 2: T012, T013, T014 can run in parallel (different files)
- Within Phase 6: T033, T034, T035, T036 can run in parallel (different files)
- Within Phase 8: T042, T043, T044 can run in parallel after T041

---

## Parallel Example: Phase 2

```bash
# After T008-T011 (candles_service.py changes), launch callers in parallel:
Task T012: "Update workflow_engine.py build_hour_candles call"
Task T013: "Update workflow_engine.py build_weekly_candles call"
Task T014: "Update snapshot.py build_hour_candles calls"
```

## Parallel Example: Phase 6

```bash
# After T030-T032 (candles_service.py changes), launch callers in parallel:
Task T033: "Update workflow_engine _get_candles_from_indicator_ut"
Task T034: "Update workflow_engine _run_workflow"
Task T035: "Update workflow_engine _get_trigger_candle"
Task T036: "Update snapshot.py callers"
```

---

## Implementation Strategy

### MVP First (Phases 1-3)

1. Complete Phase 1: Model fixes (M30 enum, close_hours, h4_blocks)
2. Complete Phase 2: Remove CFD fallback
3. Complete Phase 3: Parameterize H1 + Daily builders
4. **STOP and VALIDATE**: All existing tests pass, daily candles build correctly for both EU/US

### Incremental Delivery

1. Phases 1-2 → Foundation ready (model correct, CFD gone)
2. Phase 3 → Daily builder parameterized → Validate EU/US
3. Phase 4 → H4 builder parameterized → Validate EU/US
4. Phase 5 → Rebuild logic verified
5. Phase 6 → Single entry point → All callers migrated
6. Phase 8 → Legacy removed → Clean codebase
7. Phase 9 → Final validation

---

## Notes

- This is a refactoring of working code. Every phase must preserve exact behavioral parity with current implementation.
- The key risk is Phase 3/4 (builder parameterization). Always compare rebuilt candle OHLC values against current behavior before and after.
- Phases 3 and 4 can run in parallel since they modify different functions in utils/helper.py.
- Commit after each phase completion, not after individual tasks.
