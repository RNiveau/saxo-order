# Tasks: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

**Input**: Design documents from `/specs/021-backtest-menu-hardcoded/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/backtest-api.md, quickstart.md

**Tests**: Included. The spec's Success Criteria (SC-002: "match manual calculation exactly for every trade on every day"; SC-003: aggregate figures "match a manual computation") are effectively testable assertions, and the project constitution requires backend test coverage (mocked external calls, mirrored `tests/` structure) as a Pre-Merge Gate.

**Organization**: Tasks are grouped by user story (US1/US2/US3, matching spec.md's priorities) to enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and repo-relative

## Path Conventions

This is the existing saxo-order layout (not the generic template split): backend packages `api/`, `services/`, `model/`, `client/`, `utils/` at repo root; `frontend/src/`; tests under `tests/` mirroring source structure.

---

## Phase 1: Setup (Shared Scaffolding)

**Purpose**: Create the empty files/wiring every later task attaches to. No business logic yet.

- [ ] T001 Create `api/routers/backtest.py` with an empty `APIRouter(prefix="/api/backtest", tags=["backtest"])` and register it via `app.include_router(backtest.router)` in `api/main.py` (alongside the other routers)
- [ ] T002 [P] Create `model/backtest.py` (empty module, ready for dataclasses — no external dependencies, per Constitution's Model Layer rule)
- [ ] T003 [P] Create `api/models/backtest.py` (empty module for Pydantic response models) and `api/services/backtest_service.py` with a `BacktestService` class whose constructor takes a `CandlesService` (dependency injection, matching `ReportService`'s pattern)
- [ ] T004 [P] Add a "Backtest" sidebar entry (`NavLink to="/backtest"`, icon + label) in `frontend/src/components/Sidebar.tsx`, add `<Route path="/backtest" element={<Backtest />} />` in `frontend/src/App.tsx`, and create a placeholder `frontend/src/pages/Backtest.tsx` that renders a heading only

**Checkpoint**: Menu entry visible, router mounted, empty modules ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared domain types, candle-fetching capability, and timezone math that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Add `ExitReason` enum (`STOP_LOSS`, `BREAK_EVEN`, `TAKE_PROFIT`, `END_OF_DAY`) extending `EnumWithGetValue` in `model/enum.py`
- [ ] T006 [P] Add `DayStatus` enum (`NO_DATA`, `NO_TRADE`, `TRADED`) extending `EnumWithGetValue` in `model/enum.py`
- [ ] T007 [P] Add `M5 = "5m"` member to the existing `UnitTime` enum in `model/workflow.py`
- [ ] T008 Define `BacktestDefinition`, `Trade`, `DayResult`, `DayResultSummary`, `BacktestSummary`, `BacktestRunResult` dataclasses in `model/backtest.py` per data-model.md (depends on T005, T006, T007)
- [ ] T009 [P] Add Paris-local time helpers as module-level functions in `api/services/backtest_service.py`: `paris_reference_window_utc(trading_date: date) -> tuple[datetime, datetime]` (9:00–10:00 Paris local, DST-aware, returned as UTC bounds), `paris_session_end_utc(trading_date: date) -> datetime` (end of FRA40.I regular session), and `is_future_paris_date(d: date) -> bool`, all built on `zoneinfo.ZoneInfo("Europe/Paris")` (research.md §1). Kept local to this module rather than `utils/helper.py` since `BacktestService` is currently their only consumer (Constitution II — no speculative shared abstractions until a second consumer exists)
- [ ] T010 Implement `CandlesService.get_candles_in_window(code: str, horizon: int, start_utc: datetime, end_utc: datetime) -> List[Candle]` in `services/candles_service.py`: calls `SaxoClient.get_historical_data` at the given horizon, maps via `map_data_to_candles`, and filters to candles whose `date` falls in `[start_utc, end_utc)` (depends on T007)
- [ ] T011 [P] Add `get_backtest_service(candles_service: CandlesService = Depends(get_candles_service)) -> BacktestService` factory in `api/dependencies.py`, reusing the existing `get_candles_service()` factory already used by `api/routers/homepage.py`, `indexes.py`, `indicator.py`, and `watchlist.py`, rather than re-deriving `CandlesService` construction
- [ ] T012 [P] Implement `GET /api/backtest/definitions` in `api/routers/backtest.py`, returning the single hardcoded `BacktestDefinition` (`code="B9H"`, `display_name="CAC40 Bougie de 9h"`, `instrument="FRA40.I"`, name sourced from `Strategy.B9H.value` — research.md §4) via a Pydantic `BacktestDefinitionResponse` in `api/models/backtest.py` (depends on T008)

**Checkpoint**: Foundation ready — enums, dataclasses, candle fetching, timezone math, and the static definitions endpoint all exist. User story implementation can now begin.

---

## Phase 3: User Story 1 - Run the "CAC40 Bougie de 9h" backtest for a single day (Priority: P1) 🎯 MVP

**Goal**: A trader picks the hardcoded backtest and one past day, and sees the exact trade-by-trade outcome (entry price/time, exit price/time, exit reason, points) or a clear no-trade/no-data result.

**Independent Test**: Call `GET /api/backtest/day?definition=B9H&date=<known day>` and verify entry price, exit price, exit reason, and points match a manual read of the FRA40.I chart for that day (SC-001, SC-002).

### Tests for User Story 1

- [ ] T013 [P] [US1] Unit tests for `BacktestService.evaluate_day` in `tests/api/services/test_backtest_service.py`, covering: no-data day (missing H1 candle), no-trade day (no breakout or no confirmed reversal), stop-loss exit, break-even exit (armed at +20pts then breached), take-profit exit, end-of-day exit, a gap-through-level exit, a multi-trade day (re-entry after a closed trade), a same-candle case where the candle that would trigger a stop-loss/take-profit exit also reaches the +20pt break-even-arm threshold (must resolve as the pre-candle-level exit — arming only takes effect on the next candle, per spec.md Edge Cases), and a same-candle round-trip case where a candle's high reaches the break-even-arm threshold and its low would also breach the entry price within that same candle (must NOT produce a break-even exit that same candle) — mock `CandlesService.get_candles_in_window`
- [ ] T014 [P] [US1] Router tests for `GET /api/backtest/day` in `tests/api/routers/test_backtest.py`: 200 with a traded day, 200 with `status=no_data`, 400 for a future `date`, 400 for an unknown `definition`
- [ ] T015 [P] [US1] Unit tests for `CandlesService.get_candles_in_window` in `tests/services/test_candles_service.py`: horizon=60 window returns the correct single H1 candle, horizon=5 window returns only candles inside `[start_utc, end_utc)`, empty result when Saxo returns nothing for the window

### Implementation for User Story 1

- [ ] T016 [US1] Implement `BacktestService.evaluate_day(definition: BacktestDefinition, trading_date: date) -> DayResult` in `api/services/backtest_service.py`: fetch the 9:00–10:00 Paris-local H1 reference candle via `get_candles_in_window` (horizon=60) and `paris_reference_window_utc` (FR-003); return `NO_DATA` status if unavailable (FR-004); fetch 5-minute candles from 10:00 to `paris_session_end_utc` (horizon=5) (FR-005); detect the breakout-reversal signal and enter a long trade at the confirming candle's close (FR-006, FR-007); evaluate exits per candle in order — stop-loss (starting at entry-50), break-even arming at entry+20 effective next candle (FR-008a), take-profit at H1-high-10, end-of-day (FR-008); resolve same-candle stop-vs-take-profit conflicts as a stop exit (FR-009); apply gap-fill pricing (FR-010); after a trade closes, resume evaluating for a new signal for the rest of the day (FR-011) (depends on T008, T009, T010)
- [ ] T017 [US1] Implement `GET /api/backtest/day` in `api/routers/backtest.py`: validate `date` is not in the future and `definition` is known (400 otherwise, per contracts/backtest-api.md), call `BacktestService.evaluate_day`, return `DayDetailResponse` built from `DayResult` via `api/models/backtest.py` (depends on T016)
- [ ] T018 [P] [US1] Implement `backtestService.getDefinitions` and `backtestService.getDayDetail` plus matching TypeScript interfaces (`BacktestDefinition`, `Trade`, `DayDetailResponse`) in `frontend/src/services/api.ts`
- [ ] T019 [US1] Implement single-day mode in `frontend/src/pages/Backtest.tsx`: definition picker populated from `getDefinitions`, a date picker, a run action, and a result view showing no-data / no-trade messaging or the trade list (entry price/time, exit price/time, exit reason, points) (depends on T018)
- [ ] T020 [P] [US1] Style the single-day result view in `frontend/src/pages/Backtest.css`

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Run the backtest over a UI-provided time range and see aggregate results (Priority: P2)

**Goal**: A trader enters a start/end date and gets one summary: number of days, number of trades, number of winning/losing/BE positions, average win, average loss, and final result.

**Independent Test**: Call `GET /api/backtest/run` over a known multi-week range and verify the 8 summary figures match a manual computation from the individual per-day results (SC-003).

### Tests for User Story 2

- [ ] T021 [P] [US2] Unit tests for `BacktestService.run_range` in `tests/api/services/test_backtest_service.py`: win/loss/BE counts, average win/loss correctly excluding BE trades, `final_result` as the net sum, `number_of_days` excluding no-data days, no-data days excluded from the returned `days` list, and an empty/no-trade range returning all-zero figures with `average_win`/`average_loss` as `None`
- [ ] T022 [P] [US2] Router tests for `GET /api/backtest/run` in `tests/api/routers/test_backtest.py`: 200 with a populated summary, 400 when `end_date < start_date`, 400 when either date is in the future, 400 for an unknown `definition`

### Implementation for User Story 2

- [ ] T023 [US2] Implement `BacktestService.run_range(definition: BacktestDefinition, start_date: date, end_date: date) -> BacktestRunResult` in `api/services/backtest_service.py`: validate the range (FR-016, using `is_future_paris_date`), iterate each day calling `evaluate_day` (reuses US1's T016), build the `DayResultSummary` list (excluding `NO_DATA` days) and the `BacktestSummary` aggregate per FR-013 (depends on T016)
- [ ] T024 [US2] Implement `GET /api/backtest/run` in `api/routers/backtest.py`, returning `BacktestRunResponse` built from `BacktestRunResult` (depends on T023)
- [ ] T025 [P] [US2] Implement `backtestService.runRange` plus TypeScript interfaces (`BacktestSummary`, `DayResultSummary`, `BacktestRunResponse`) in `frontend/src/services/api.ts`
- [ ] T026 [US2] Implement range mode in `frontend/src/pages/Backtest.tsx`: start/end date pickers, inline validation error display for invalid ranges (FR-016), the 8-figure summary display, and a compact per-day results table (depends on T025)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Inspect the reference levels and candles behind a day's result (Priority: P3)

**Goal**: From a range result, a trader opens a specific day and sees the H1 high/low, the 5-minute candle sequence, and the entry/exit points marked against it.

**Independent Test**: From a range run, open the detail view for a day that had a trade and confirm the displayed H1 high/low, candle sequence, and entry/exit markers match that day's summary figures (SC-004).

### Implementation for User Story 3

- [ ] T027 [P] [US3] Build a reusable day-detail display (component or section within `frontend/src/pages/Backtest.tsx`) that renders H1 high/low, the 5-minute candle sequence, and entry/exit markers for one day's trades, reusing the `DayDetailResponse` shape already returned by US1's `getDayDetail` (no new backend work — data-model.md's `DayResult` already carries everything needed)
- [ ] T028 [US3] Wire each row of US2's per-day results table to open the day-detail display for that date via `backtestService.getDayDetail` (depends on T026, T027)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates required by the project constitution before this feature is considered done.

- [ ] T029 [P] Run `poetry run mypy .` and `poetry run flake8` and fix any violations in the new/changed backend files
- [ ] T030 [P] Run `poetry run black .` and `poetry run isort .` on the new/changed backend files
- [ ] T031 [P] Run `npm run build` and `npm run lint` in `frontend/` and fix any violations
- [ ] T032 Execute the manual walkthrough in `specs/021-backtest-menu-hardcoded/quickstart.md` end-to-end (backend curl checks + frontend flow), **including its SC-002 section**: run the backtest against at least 6 real historical FRA40.I trading days spanning every outcome type (no data, no trade, stop-loss exit, break-even exit, take-profit exit, end-of-day exit), manually verifying entry price, exit price, exit reason, and points against the actual chart for each, and confirm every step passes
- [ ] T033 [P] Run `poetry run pytest --cov` for the full suite and confirm coverage is maintained or improved (Constitution Pre-Merge Gate)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational; reuses `evaluate_day` from US1 (T016) — cannot start implementation until T016 exists, though its tests (T021, T022) can be drafted in parallel
- **User Story 3 (Phase 5)**: Depends on Foundational; reuses the `/day` endpoint (T017) and the range table (T026) — start after both US1 and US2 are functional
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests are written alongside/before their story's implementation tasks
- Dataclasses/enums (Foundational) before services; services before routers; routers before frontend wiring
- Story complete and independently verifiable before moving to the next priority

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel (T001 first, since T003's router import needs T001's file to exist — in practice T001–T004 touch disjoint files and can run together, but do T001 first if in doubt)
- Foundational: T006, T007 in parallel with each other; T009 in parallel with T005–T008; T011, T012 in parallel once T008 lands
- US1: T013, T014, T015 in parallel (different test files); T018, T020 in parallel with backend tasks once their inputs exist
- US2: T021, T022 in parallel; T025 in parallel with T023/T024
- US3: T027 in parallel with finishing touches on US1/US2
- Polish: T029, T030, T031, T033 in parallel

---

## Parallel Example: User Story 1

```bash
# Tests together:
Task: "Unit tests for BacktestService.evaluate_day in tests/api/services/test_backtest_service.py"
Task: "Router tests for GET /api/backtest/day in tests/api/routers/test_backtest.py"
Task: "Unit tests for CandlesService.get_candles_in_window in tests/services/test_candles_service.py"

# Frontend service + styling together, once T016/T017 exist:
Task: "Implement backtestService.getDefinitions/getDayDetail in frontend/src/services/api.ts"
Task: "Style the single-day result view in frontend/src/pages/Backtest.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (critical — blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run T013–T015 tests, then the single-day steps of quickstart.md, against a real known FRA40.I day
5. Demo the single-day flow

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate independently → MVP demo
3. User Story 2 → validate independently → range summary demo
4. User Story 3 → validate independently → full drill-down demo
5. Polish → constitution gates green

---

## Notes

- [P] tasks touch different files with no unmet dependencies
- [US1]/[US2]/[US3] labels map every story-phase task back to spec.md's priorities for traceability
- FR-002's "no generic engine" constraint keeps the strategy *logic*, instrument, and 9–10 window fixed in code; the four numeric thresholds became per-run parameters (`BacktestParameters`, FR-025, added 2026-07-21), defaulting to 50/10/20/20 — see plan.md's Complexity Tracking (resolved) and the "Parametrized thresholds" requirements
- Commit after each task or logical group; stop at any checkpoint to validate a story independently before continuing
