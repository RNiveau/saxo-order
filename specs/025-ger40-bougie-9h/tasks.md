---
description: "Task list for GER40 Bougie de 9h double take-profit backtest"
---

# Tasks: Hardcoded "GER40 Bougie de 9h" Backtest (double take-profit)

**Input**: Design documents from `/specs/025-ger40-bougie-9h/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/backtest-api.md, quickstart.md

**Tests**: INCLUDED — the repo's constitution (Testing Standards) and the existing `tests/api/services/test_backtest_service.py` / `tests/api/routers/test_backtest.py` establish a test-first convention for the backtest engine; SC-G02/SC-G03 require verified outcomes.

**Organization**: Tasks are grouped by user story. This feature extends the existing spec-021 backtest modules — most work is backend engine, and the GER40 definition auto-appears in the frontend menu once registered.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 (setup/foundational/polish carry no story label)

## Path Conventions

Existing flat layout (plan.md Structure Decision): backend packages `model/`, `services/`, `api/` at repo root; `frontend/src/`; tests in `tests/` mirroring source.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a known-good baseline before touching shared engine code.

- [ ] T001 Confirm the existing backtest suite is green before changes: run `poetry run pytest tests/api/services/test_backtest_service.py tests/api/routers/test_backtest.py -q` and record the pass count (regression baseline for B9H/B9HTC unchanged behavior, SC-G05).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Register the GER40 definition, its per-definition default thresholds, and the double-TP properties so every user story can reach it. No engine behavior yet.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Add `G9H = "Bougie de 9h GER40"` to the `Strategy` enum in `model/enum.py` (Constitution II — no hardcoded strategy string; data-model.md §New enum member).
- [ ] T003 [P] Extend `BacktestDefinition` in `model/backtest.py` with the fields `default_parameters: BacktestParameters = field(default_factory=BacktestParameters)`, `double_take_profit: bool = False`, `first_target_fraction: Optional[float] = None`, `stop_from_reference_level: bool = False` (all defaulting to current CAC40 behavior; data-model.md §Extended entity). Leave `BacktestParameters` shape/defaults unchanged.
- [ ] T004 Register the `G9H` `BacktestDefinition` in `BACKTEST_DEFINITIONS` in `api/services/backtest_service.py` — `instrument="GER40.I"`, `name=Strategy.G9H.value`, `display_name="GER40 Bougie de 9h"`, `default_parameters=BacktestParameters(stop_loss_points=150, take_profit_offset_points=10, break_even_trigger_points=50, max_entry_distance_points=40)`, `double_take_profit=True`, `first_target_fraction=0.5`, `stop_from_reference_level=True` (data-model.md exact snippet). Depends on T002, T003.
- [ ] T005 Add a `resolve_parameters(definition, overrides) -> BacktestParameters` helper in `api/services/backtest_service.py` that fills each omitted override from `definition.default_parameters` (research §5 / contracts §Threshold parameters). Depends on T003.
- [ ] T006 Rework `_params` in `api/routers/backtest.py` to return the four thresholds as optional overrides, and resolve them against the looked-up definition's defaults inside each endpoint (after `_resolve_definition`, before `evaluate_day`/`run_range`), keeping the `Query(gt=0)` positivity validation and 422 behavior (contracts §Threshold parameters; unknown definition still 400). Depends on T004, T005.
- [ ] T007 Extend `BacktestDefinitionResponse` and `backtest_definition_to_response` in `api/models/backtest.py` with `double_take_profit: bool` and `default_parameters` (a four-float model echoing the definition's defaults); leave `TradeResponse`/`DayDetailResponse`/`BacktestRunResponse` unchanged (FR-G10; contracts §definitions). Depends on T003.
- [ ] T008 [P] Extend the `BacktestDefinition` TS interface in `frontend/src/services/api.ts` with `double_take_profit: boolean` and `default_parameters: Required<BacktestParameters>` (contracts §Frontend service mapping). Depends on T007.
- [ ] T009 In `frontend/src/pages/Backtest.tsx`, seed the threshold inputs from `selectedDefinition.default_parameters` instead of the hardcoded `PARAM_FIELDS` defaults, re-seeding when the selected definition changes (so GER40 shows 150/10/50/40 and CAC40 still shows 50/10/20/20). Depends on T008.

**Checkpoint**: `GET /api/backtest/definitions` lists `G9H` with GER40 defaults; the menu shows "GER40 Bougie de 9h"; a run against `G9H` currently executes as if single-lot (no double-TP yet). B9H/B9HTC unchanged.

---

## Phase 3: User Story 1 - Single-day double-TP backtest (Priority: P1) 🎯 MVP

**Goal**: A `G9H` single day produces correct two-lot / double-take-profit positions — TP1 at the H1 midpoint, runner to TP2 or break-even, both lots on a reference-level stop (x2 loss), take-first-then-break-even — surfaced as one aggregated `Trade`.

**Independent Test**: Run `/api/backtest/day?definition=G9H&date=…` against hand-built candle days and verify entry, per-lot exits, net points, and exit reason match manual calc for every SC-G02 outcome type.

### Tests for User Story 1 (write first, expect FAIL)

- [ ] T010 [P] [US1] Add double-TP engine tests to `tests/api/services/test_backtest_service.py` covering: both-lots stop-out before TP1 (`points = 2·(stop−entry)`, `stop_loss`, stop = H1 low − 150); TP1 fills then runner hits TP2 (`points = (TP1−entry)+(TP2−entry)`, `take_profit`); TP1 then runner returns to break-even (net-positive, `break_even`); +50 break-even armed before TP1 then flat stop-out (net ≈ 0); end-of-day with both lots open and with runner only; the short mirror off the H1 high (TP2 = H1 low + 10, stop = H1 high + 150); no-trade; no-data. Assert on outcomes, not mocks (CLAUDE.md). Uses the existing hand-built 5-minute candle pattern.
- [ ] T011 [P] [US1] Add a `/api/backtest/day` test for `G9H` to `tests/api/routers/test_backtest.py` asserting a traded day returns each position as one aggregated `TradeResponse` (shared `entry_price`, runner's `exit_price`/`exit_reason`, net `points`), response shape unchanged from B9H.

### Implementation for User Story 1

- [ ] T012 [US1] Extend `_OpenPosition` in `api/services/backtest_service.py` with `double`, `first_target_level`, `first_target_taken`, `banked_points`, `initial_stop_price`; update the `stop_level` property to branch: `be_armed` → entry, else `stop_from_reference_level` → `initial_stop_price`, else `entry ± stop_loss_points` (unchanged CAC40 path). (data-model.md §Engine state). Depends on T004.
- [ ] T013 [US1] Add the double-TP exit handling in `_resolve_exit` (or a `_resolve_exit_double` branch selected when `position.double`) in `api/services/backtest_service.py`: while both lots open — stop beats TP1 on a same-candle collision (both lots close, `points = 2·(stop−entry)`); TP1 hit → bank `TP1−entry`, set `first_target_taken`, arm runner break-even (FR-G04), handle same-candle TP1+TP2; +50 trigger arms shared stop (FR-G06). Runner only — break-even stop at entry, TP2, gap-fill (FR-010). Depends on T012.
- [ ] T014 [US1] Add a `_close_double_trade` helper in `api/services/backtest_service.py` that builds the aggregated `Trade` with explicit net `points` (`banked_points` + runner leg, or `2·` leg for both-lots exits), the runner's `exit_price`/`exit_time`/`exit_reason`, raising an explicit exception (no `assert`, Constitution II.5) on any invariant violation. Depends on T012.
- [ ] T015 [US1] Wire double-TP into `_evaluate_trades`/`evaluate_day` in `api/services/backtest_service.py`: compute `first_target_level = (h1_high + h1_low)/2` and the reference-based `initial_stop_price` per direction, construct `_OpenPosition` with the definition's double-TP props, and route open positions through the double-TP exit path and end-of-day close. Entry detection/validity (`_DirectionSearch`, validity judged against TP2) unchanged. Depends on T012, T013, T014.

**Checkpoint**: T010/T011 pass; a `G9H` single day returns correct aggregated two-lot positions. MVP deliverable — CAC40 still green (rerun T001 suite).

---

## Phase 4: User Story 2 - Range summary with per-position classification (Priority: P2)

**Goal**: A `G9H` range run counts each two-lot position once and classifies it by net-points sign (a TP1-then-break-even winner counts as a win, not BE).

**Independent Test**: Run `/api/backtest/run?definition=G9H&…` over a mixed range and verify days/trades/wins/losses/BE/avg-win/avg-loss/final match a manual computation from per-day net points; a TP1-then-BE position lands in wins.

### Tests for User Story 2 (write first, expect FAIL)

- [ ] T016 [P] [US2] Add summary-classification tests to `tests/api/services/test_backtest_service.py`: for `G9H`, a net-positive TP1-then-break-even position counts as winning (not BE); a genuinely-flat position (both lots at break-even, no TP) counts as BE; `average_win`/`average_loss` use net points. Assert B9H classification is unchanged (regression).

### Implementation for User Story 2

- [ ] T017 [US2] In `_build_summary` in `api/services/backtest_service.py`, branch on `definition.double_take_profit`: classify by net-points sign (net > 0 win, net < 0 loss, net == 0 BE) for double-TP definitions; keep the existing mechanism-based (`exit_reason == BREAK_EVEN`) classification for B9H/B9HTC (FR-G08 / research §6). Depends on US1 (T015).
- [ ] T018 [US2] Add a `/api/backtest/run` and `/api/backtest/run/csv` test for `G9H` to `tests/api/routers/test_backtest.py` asserting one row/trade per position (net points) and that the CSV parameters block echoes the resolved GER40 defaults (150/10/50/40). Depends on T017.

**Checkpoint**: `G9H` range summary and CSV correct; B9H summary/CSV unchanged.

---

## Phase 5: User Story 3 - Inspect a day's levels, candles and trades (Priority: P3)

**Goal**: The day detail view and its CSV show the H1 levels, 5-minute candles, and each aggregated `G9H` position's entry/exit — reusing the existing detail component and export (no response-shape change, FR-G10).

**Independent Test**: Open the day detail for a `G9H` day with a position and confirm H1 levels, candles, and the position's entry/exit render consistently with the summary; export the day CSV.

### Tests for User Story 3 (write first, expect FAIL)

- [ ] T019 [P] [US3] Add a `/api/backtest/day/csv` test for `G9H` to `tests/api/routers/test_backtest.py` asserting the three-block CSV (H1 levels, candles, trades) renders the aggregated position row with net points and the resolved-parameters block.

### Implementation for User Story 3

- [ ] T020 [US3] Verify `frontend/src/components/BacktestDayDetail.tsx` renders a `G9H` day (H1 levels, candle series, entry/exit markers) using the unchanged `DayDetailResponse`; make only the minimal adjustment needed if a two-lot position's single aggregated trade surfaces any label gap (e.g. it may read "long"/"short" as today). No new response field is introduced.

**Checkpoint**: All three stories independently functional for GER40; CAC40 unaffected.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T021 Run `poetry run black . && poetry run isort . && poetry run flake8 && poetry run mypy .` and fix any violations in the changed backend files (Constitution Quality Gates; 79-char lines).
- [ ] T022 Run `cd frontend && npm run lint && npm run build` and fix any TypeScript/ESLint issues in `api.ts` / `Backtest.tsx` (Constitution Frontend Quality Gates).
- [ ] T023 Run the full backend suite `poetry run pytest -q` and confirm B9H/B9HTC results are byte-for-byte unchanged vs the T001 baseline (SC-G05 regression guard).
- [ ] T024 Execute `specs/025-ger40-bougie-9h/quickstart.md` end-to-end (definitions list, single-day, range, CSV, threshold override) and confirm SC-G01…SC-G05.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup — BLOCKS all user stories (registers the definition, defaults, response fields, frontend plumbing).
- **User Stories (Phase 3–5)**: all depend on Foundational. US2 depends on US1's engine (aggregated trades exist before they can be classified). US3 depends only on Foundational for the response but is naturally validated after US1 produces trades.
- **Polish (Phase 6)**: after the desired stories.

### User Story Dependencies

- **US1 (P1)**: after Foundational. The MVP — delivers the double-TP engine.
- **US2 (P2)**: after US1 (classifies the positions US1 produces).
- **US3 (P3)**: after Foundational; independent of US1/US2 in code (reuses existing detail/CSV), verified after US1.

### Within Each User Story

- Tests written first and expected to FAIL, then implementation (constitution test-first convention).
- Model/state (`_OpenPosition`) before exit logic before wiring.

### Parallel Opportunities

- T002 and T003 (different model files) run in parallel.
- T008 is parallel-safe once T007 lands (different file).
- T010 and T011 (service vs router test files) run in parallel; T016 and T019 likewise.
- US3 (T019/T020) can be built in parallel with US2 by a second contributor once US1 lands.

---

## Parallel Example: Foundational + User Story 1

```bash
# Foundational model changes in parallel:
Task: "Add Strategy.G9H to model/enum.py"                # T002
Task: "Extend BacktestDefinition fields in model/backtest.py"  # T003

# User Story 1 tests in parallel (write first, expect FAIL):
Task: "Double-TP engine tests in tests/api/services/test_backtest_service.py"  # T010
Task: "G9H /day aggregated-trade test in tests/api/routers/test_backtest.py"    # T011
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup (T001 baseline).
2. Phase 2 Foundational (T002–T009) — definition + defaults + plumbing.
3. Phase 3 US1 (T010–T015) — the double-TP engine.
4. **STOP and VALIDATE**: single-day `G9H` outcomes match manual calc (SC-G02); B9H still green.

### Incremental Delivery

1. Foundational → GER40 menu entry live (single-lot placeholder).
2. + US1 → correct two-lot double-TP single-day results (MVP).
3. + US2 → range summary with net-sign classification.
4. + US3 → day detail/CSV inspection.
5. Polish → lint/type/build/regression/quickstart.

---

## Notes

- [P] = different files, no incomplete-task dependency.
- Every user-story task carries its `[US#]` label; setup/foundational/polish do not.
- No `assert` in production code — raise explicit exceptions (Constitution II.5 / v1.3.0).
- B9H/B9HTC must stay byte-for-byte unchanged — all new behavior is gated behind `double_take_profit` / `stop_from_reference_level` per-definition flags.
- Commit after each task or logical group; conventional commit prefixes (`feat:`/`test:`/`docs:`).
