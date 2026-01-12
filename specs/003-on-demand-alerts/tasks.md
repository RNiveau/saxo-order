# Tasks: On-Demand Alerts Execution

**Feature**: 003-on-demand-alerts
**Input**: Design documents from `specs/003-on-demand-alerts/`
**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ data-model.md, ✅ contracts/run-alerts.yaml, ✅ quickstart.md

**Tests**: No test tasks included - feature spec does not require tests (no testing framework currently configured for frontend, backend tests optional)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

This is a **full-stack feature**:
- **Backend**: `api/`, `saxo_order/`, `services/`, `client/` (Python + FastAPI)
- **Frontend**: `frontend/src/` (React + TypeScript + Vite)
- **No tests**: No testing framework configured for frontend, backend tests optional

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal project initialization

**Status**: ✅ Complete - all infrastructure already exists

- Backend API structure exists ✅
- Frontend AssetDetail page exists ✅
- DynamoDB `alerts` table exists ✅
- Detection algorithms exist in `services/` ✅
- `alertService` in `frontend/src/services/api.ts` exists ✅

**No setup tasks needed** - all infrastructure is in place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend refactoring that MUST be complete before user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Extract Reusable Detection Logic

- [X] T001 Extract detection orchestration function from `saxo_order/commands/alerting.py` - create `run_detection_for_asset(asset_code, country_code, exchange, candles_service, indicator_service, congestion_service, dynamodb_client)` function that runs all 6 detection algorithms and stores results
- [X] T002 Refactor `run_alerting()` in `saxo_order/commands/alerting.py` to call extracted `run_detection_for_asset()` function (reduce duplication, maintain existing CLI behavior)

**Checkpoint**: ✅ Foundation ready - detection logic is reusable from both CLI and API

---

## Phase 3: User Story 1 - Run Alerts on Demand (Priority: P1) 🎯 MVP

**Goal**: Enable traders to manually trigger alert detection for the current asset with immediate feedback

**Independent Test**: Navigate to asset detail page (e.g., `/asset/ITP:xpar`), click "Run Alerts" button, verify system executes detection and displays new alerts or "No new alerts" message with 5-minute cooldown

**Acceptance Criteria**:
1. "Run Alerts" button appears on asset detail page
2. Button triggers API call to backend detection endpoint
3. Backend executes detection for current asset only (filtered by asset_code + country_code)
4. New alerts display immediately after execution with "NEW" badge
5. 5-minute cooldown enforced (backend validates, frontend displays timer)
6. Success/error messages display for 3 seconds

### Backend: API Models

- [X] T003 [P] [US1] Add `RunAlertsRequest` Pydantic model in `api/models/alerting.py` with fields: asset_code (str), country_code (Optional[str]), exchange (str)
- [X] T004 [P] [US1] Add `RunAlertsResponse` Pydantic model in `api/models/alerting.py` with fields: status (str), alerts_detected (int), alerts (List[AlertItemResponse]), execution_time_ms (int), message (str), next_allowed_at (datetime)

### Backend: Service Layer (Cooldown + Detection)

- [X] T005 [US1] Add `_get_last_run_at()` method in `api/services/alerting_service.py` - query DynamoDB alerts table for `last_run_at` field (returns Optional[datetime])
- [X] T006 [US1] Add `_is_cooldown_active()` method in `api/services/alerting_service.py` - check if last_run_at is within 5 minutes of now (returns bool + next_allowed_at datetime)
- [X] T007 [US1] Add `_update_last_run_at()` method in `api/services/alerting_service.py` - update DynamoDB alerts table with current timestamp in `last_run_at` field
- [X] T008 [US1] Add `run_on_demand_detection()` method in `api/services/alerting_service.py` - orchestrate cooldown check, call extracted `run_detection_for_asset()`, update last_run_at, return RunAlertsResponse

### Backend: API Endpoint

- [X] T009 [US1] Add `POST /api/alerts/run` endpoint in `api/routers/alerting.py` - accept RunAlertsRequest, call `alerting_service.run_on_demand_detection()`, return RunAlertsResponse (200 success, 429 cooldown, 500 error)

### Backend: DynamoDB Schema Extension

- [X] T010 [P] [US1] Update DynamoDB `store_alerts()` in `client/aws_client.py` to preserve `last_run_at` field when storing alerts (don't overwrite existing value unless explicitly provided)

### Frontend: API Service Extension

- [X] T011 [P] [US1] Add `RunAlertsResponse` TypeScript interface in `frontend/src/services/api.ts` with fields matching backend model
- [X] T012 [US1] Add `run()` method to `alertService` in `frontend/src/services/api.ts` - POST to `/api/alerts/run` with asset_code, country_code, exchange, 60-second timeout

### Frontend: Component State

- [X] T013 [US1] Add on-demand alerts state variables in `frontend/src/pages/AssetDetail.tsx` - useState for runAlertsLoading (boolean), runAlertsError (string|null), runAlertsSuccess (string|null), nextAllowedAt (Date|null), newAlertIds (Set<string>)

### Frontend: Execution Logic

- [X] T014 [US1] Create `handleRunAlerts()` function in `frontend/src/pages/AssetDetail.tsx` - parse symbol to extract asset_code/country_code/exchange, call alertService.run(), handle response (update state, refresh alerts, track new IDs for badges)
- [X] T015 [US1] Add cooldown timer logic in `frontend/src/pages/AssetDetail.tsx` - useEffect with setInterval to update countdown display every second, clear when nextAllowedAt expires
- [X] T016 [US1] Add auto-clear success/error messages in `frontend/src/pages/AssetDetail.tsx` - setTimeout to clear runAlertsSuccess and runAlertsError after 3 seconds

### Frontend: UI Implementation

- [X] T017 [US1] Add "Run Alerts" button JSX in `frontend/src/pages/AssetDetail.tsx` in alerts section - button with onClick={handleRunAlerts}, disabled during loading or cooldown, text changes to "Running..." with spinner when loading
- [X] T018 [US1] Add cooldown timer display in `frontend/src/pages/AssetDetail.tsx` - show "Next run in MM:SS" when nextAllowedAt is set, hide when cooldown expires
- [X] T019 [US1] Add success/error message display in `frontend/src/pages/AssetDetail.tsx` - render runAlertsSuccess or runAlertsError above button, auto-fade after 3 seconds
- [X] T020 [US1] Add "NEW" badge rendering in alerts map in `frontend/src/pages/AssetDetail.tsx` - check if alert.id is in newAlertIds Set, display badge with 60-second auto-removal (setTimeout)
- [X] T021 [US1] Add auto-refresh alerts section after successful execution in `frontend/src/pages/AssetDetail.tsx` - call existing fetchAlerts(symbol) in handleRunAlerts success path

### Frontend: Styling

- [X] T022 [P] [US1] Add `.run-alerts-btn` styles in `frontend/src/pages/AssetDetail.css` - button styling matching existing page buttons (add-to-watchlist-btn pattern)
- [X] T023 [P] [US1] Add `.run-alerts-btn:disabled` styles in `frontend/src/pages/AssetDetail.css` - opacity, cursor not-allowed
- [X] T024 [P] [US1] Add `.alert-status-message` styles in `frontend/src/pages/AssetDetail.css` - success (green) and error (red) message styling with fade animation
- [X] T025 [P] [US1] Add `.cooldown-timer` styles in `frontend/src/pages/AssetDetail.css` - countdown display styling
- [X] T026 [P] [US1] Add `.alert-badge-new` styles in `frontend/src/pages/AssetDetail.css` - "NEW" badge styling (bright color, small size, positioned on alert card)

**Story 1 Complete**: ✅ User can manually trigger alert detection and see results immediately with cooldown enforcement

---

## Phase 4: User Story 2 - Understand Execution Status (Priority: P2)

**Goal**: Provide clear visual feedback during execution (loading, success, error states)

**Independent Test**: Click "Run Alerts" button and verify: (1) button disabled with "Running..." text and spinner, (2) success message "Alerts analysis completed" displays for 3 seconds after success, (3) error message displays with helpful description on failure, (4) countdown timer shows remaining cooldown time

**Acceptance Criteria**:
1. Button shows loading spinner during execution
2. Button text changes to "Running..." when disabled
3. Success message displays for exactly 3 seconds
4. Error messages are specific and actionable
5. Countdown timer updates every second during cooldown

### Loading State Enhancements

- [ ] T027 [US2] Add loading spinner component in `frontend/src/pages/AssetDetail.tsx` - render spinning icon when runAlertsLoading is true (reuse existing spinner pattern from indicators section)
- [ ] T028 [US2] Add extended loading message in `frontend/src/pages/AssetDetail.tsx` - after 30 seconds of loading, change message to "Alert detection is taking longer than usual..."

### Error Handling Enhancements

- [ ] T029 [US2] Add specific error message mapping in `handleRunAlerts()` in `frontend/src/pages/AssetDetail.tsx` - map HTTP status codes to user-friendly messages (429 → cooldown, 500 → service unavailable, 504 → timeout, network error → connection failed)
- [ ] T030 [US2] Add timeout handling in `frontend/src/pages/AssetDetail.tsx` - catch Axios timeout error (60s), set runAlertsError to "Alert detection timed out. Please try again."

### Success Message Enhancements

- [ ] T031 [US2] Add success message text generation in `handleRunAlerts()` in `frontend/src/pages/AssetDetail.tsx` - format message based on alerts_detected count ("Detected 2 new alerts" vs "No new alerts detected")

### Styling Enhancements

- [ ] T032 [P] [US2] Add loading spinner animation styles in `frontend/src/pages/AssetDetail.css` - keyframe rotation animation for spinner icon
- [ ] T033 [P] [US2] Add `.alert-status-message.success` specific styles in `frontend/src/pages/AssetDetail.css` - green background, checkmark icon
- [ ] T034 [P] [US2] Add `.alert-status-message.error` specific styles in `frontend/src/pages/AssetDetail.css` - red background, error icon
- [ ] T035 [P] [US2] Add fade-out animation for status messages in `frontend/src/pages/AssetDetail.css` - CSS transition for opacity 0 → 1 → 0 over 3 seconds

**Story 2 Complete**: ✅ User receives clear feedback at every stage of execution (loading, success, error)

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final touches, testing, and deployment preparation

### Code Quality

- [ ] T036 Run backend type checking with `cd . && mypy api/ saxo_order/` - verify no type errors in modified files
- [ ] T037 [P] Run backend linting with `cd . && flake8 api/ saxo_order/` - verify no linting errors (existing errors unrelated to our changes)
- [ ] T038 [P] Run frontend TypeScript check with `cd frontend && npm run build` - verify no compilation errors
- [ ] T039 [P] Run frontend linting with `cd frontend && npm run lint` - verify no linting errors (existing errors unrelated to our changes)

### Manual Testing

- [ ] T040 Test successful execution - navigate to asset with 0 alerts, run detection, verify new alerts appear with "NEW" badge
- [ ] T041 [P] Test no alerts found - run detection on asset with no signals, verify "No new alerts detected" message
- [ ] T042 [P] Test cooldown enforcement - run alerts twice within 5 minutes, verify 429 error and countdown timer
- [ ] T043 [P] Test cooldown expiration - wait 5 minutes after execution, verify button re-enables and countdown disappears
- [ ] T044 [P] Test different alert types - verify COMBO, CONGESTION, candle pattern alerts all detect and display correctly
- [ ] T045 [P] Test asset without country_code - run detection on Binance asset (e.g., BTCUSDT), verify country_code handled as null
- [ ] T046 [P] Test API error handling - simulate 500 error (disable backend), verify error message displays
- [ ] T047 [P] Test network failure - simulate network disconnect mid-execution, verify error message
- [ ] T048 [P] Test timeout scenario - use asset with slow detection (>60s if possible), verify timeout error and no cooldown penalty
- [ ] T049 [P] Test "NEW" badge expiration - wait 60 seconds after detection, verify badges disappear automatically

### Backend Testing (Optional)

- [ ] T050 [P] Write unit test for `run_on_demand_detection()` in `tests/api/services/test_alerting_service.py` - mock DynamoDB and detection functions, verify cooldown logic and response structure
- [ ] T051 [P] Write unit test for cooldown validation in `tests/api/services/test_alerting_service.py` - test edge cases (exactly 5 minutes, just under 5 minutes, just over 5 minutes)

### Documentation & Deployment

- [ ] T052 Verify quickstart guide accuracy - compare `specs/003-on-demand-alerts/quickstart.md` with actual implementation, update if needed
- [ ] T053 Verify API contract accuracy - compare `specs/003-on-demand-alerts/contracts/run-alerts.yaml` with actual endpoint behavior, update if needed
- [ ] T054 Pre-deployment checklist - verify backend builds successfully (`./deploy.sh` dry run), frontend builds successfully, no console errors (requires user validation)

**Polish Complete**: ✅ Feature ready for deployment

---

## Dependencies

### Story Completion Order

```
Phase 1 (Setup)           ✅ Complete (no tasks)
  ↓
Phase 2 (Foundation)      T001 → T002 (sequential, CLI refactoring)
  ↓
Phase 3 (User Story 1)
  Backend Models:         T003, T004 (parallel)
  ├──────────────────────→ Backend Service: T005 → T006 → T007 → T008 (sequential)
  ├──────────────────────→ Backend API: T009 (depends on T003, T004, T008)
  ├──────────────────────→ Backend DB: T010 (parallel with T003-T009)
  ├──────────────────────→ Frontend API: T011 → T012 (sequential)
  ├──────────────────────→ Frontend State: T013 (parallel with T011-T012)
  ├──────────────────────→ Frontend Logic: T014 → T015 → T016 (sequential, depends on T012, T013)
  ├──────────────────────→ Frontend UI: T017 → T018 → T019 → T020 → T021 (sequential, depends on T014-T016)
  └──────────────────────→ Frontend Styles: T022, T023, T024, T025, T026 (parallel, after UI tasks)
  ↓
Phase 4 (User Story 2)
  Loading Enhancements:   T027 → T028 (sequential)
  ├──────────────────────→ Error Handling: T029 → T030 (sequential, parallel with T027-T028)
  ├──────────────────────→ Success Messages: T031 (parallel with T027-T030)
  └──────────────────────→ Styles: T032, T033, T034, T035 (parallel, after logic tasks)
  ↓
Phase 5 (Polish)          T036, T037, T038, T039 (quality checks, parallel)
  └──────────────────────→ T040-T049 (manual tests, parallel)
  └──────────────────────→ T050-T051 (optional backend tests, parallel)
  └──────────────────────→ T052-T054 (documentation, sequential)
```

### Critical Path

1. **Foundation** (blocking): T001-T002 extract reusable detection logic
2. **User Story 1** (MVP): T003-T026 deliver minimum viable product (on-demand execution with cooldown)
3. **User Story 2** (enhancement): T027-T035 add enhanced feedback and error handling
4. **Polish** (optional): T036-T054 ensure quality and readiness

### Parallel Opportunities

**Within Phase 2 (Foundation)**:
- T001-T002 sequential (refactoring same file)
- Total: 1 track

**Within Phase 3 (User Story 1)**:
- Backend Models (T003, T004) parallel
- Backend Service (T005-T008) sequential
- Backend API (T009) depends on models + service
- Backend DB (T010) parallel with all backend tasks
- Frontend API (T011-T012) sequential
- Frontend State (T013) parallel with API
- Frontend Logic (T014-T016) sequential, depends on API + State
- Frontend UI (T017-T021) sequential, depends on Logic
- Frontend Styles (T022-T026) parallel, after UI
- Total: Up to 6 parallel tracks (backend models, backend service, backend DB, frontend API/state, frontend logic, frontend styles)

**Within Phase 4 (User Story 2)**:
- Loading (T027-T028) sequential
- Error Handling (T029-T030) sequential, parallel with Loading
- Success Messages (T031) parallel with Loading + Error
- Styles (T032-T035) parallel, after logic
- Total: 3-4 parallel tracks

**Within Phase 5 (Polish)**:
- Quality checks (T036-T039) all parallel
- Manual tests (T040-T049) all parallel
- Backend tests (T050-T051) parallel
- Documentation (T052-T054) sequential
- Total: Up to 13 parallel tasks (4 quality + 10 manual tests + 2 backend tests)

---

## Implementation Strategy

### MVP Scope (User Story 1)

**Minimum Viable Product** consists of:
- Phase 2 (Foundation): T001-T002
- Phase 3 (User Story 1): T003-T026

This delivers:
✅ On-demand alert detection triggered by button click
✅ Backend API with cooldown enforcement
✅ Frontend UI with loading states and results display
✅ "NEW" badges on newly detected alerts
✅ 5-minute cooldown with timer

**Estimated Tasks**: 28 tasks (Foundation + US1)

### Incremental Delivery

After MVP (US1), deliver each story independently:

**Phase 4 (US2)**: Enhanced execution status feedback
- Independent from US1 (extends existing UI states)
- Can be tested independently
- **Estimated**: 9 tasks

**Phase 5 (Polish)**: Quality and testing
- Final validation before deployment
- **Estimated**: 19 tasks (4 quality + 10 manual + 2 optional tests + 3 docs)

### Recommended Execution Order

1. **Phase 2**: Foundation (extract reusable detection logic)
2. **Phase 3**: User Story 1 (MVP - on-demand execution)
3. **Phase 4**: User Story 2 (enhanced feedback)
4. **Phase 5**: Polish and deploy

---

## Task Summary

**Total Tasks**: 54 tasks

**By Phase**:
- Phase 1 (Setup): 0 tasks (infrastructure exists)
- Phase 2 (Foundation): 2 tasks
- Phase 3 (User Story 1): 24 tasks
- Phase 4 (User Story 2): 9 tasks
- Phase 5 (Polish): 19 tasks

**By Story**:
- User Story 1: 24 tasks (MVP)
- User Story 2: 9 tasks (enhanced feedback)
- Foundation: 2 tasks
- Polish: 19 tasks

**Parallel Opportunities**:
- Foundation: 1 track (sequential refactoring)
- User Story 1: Up to 6 parallel tracks
- User Story 2: 3-4 parallel tracks
- Polish: Up to 13 parallel tasks

**Format Validation**: ✅ All 54 tasks follow checklist format with IDs, story labels, and file paths

---

## Next Steps

Run `/speckit.implement` to execute tasks automatically, or execute tasks manually in the order specified by the dependency graph.

**Recommended**: Start with MVP scope (T001-T026) to deliver value quickly, then add enhancements incrementally.
