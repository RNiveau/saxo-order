# Tasks: Long-Term Positions Menu

**Input**: Design documents from `/specs/004-watchlist-menu/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Backend unit tests are included following project standards. Frontend tests are TBD (no testing framework configured).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

This is a **web application** with:
- Backend API: `api/`, `client/`, `tests/api/`
- Frontend SPA: `frontend/src/`, `frontend/tests/` (TBD)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment verification and dependency check

- [ ] T001 Verify Python 3.11+ installed and poetry configured
- [ ] T002 Verify Node.js 18+ and npm dependencies in frontend/
- [ ] T003 [P] Run `poetry install` to ensure backend dependencies available
- [ ] T004 [P] Run `npm install` in frontend/ to ensure frontend dependencies available
- [ ] T005 Verify AWS credentials configured for DynamoDB access (existing table: `watchlist`)
- [ ] T006 Start backend API server (`poetry run python run_api.py`) and verify http://localhost:8000 accessible
- [ ] T007 Start frontend dev server (`npm run dev` in frontend/) and verify http://localhost:5173 accessible

**Checkpoint**: Development environment ready, both servers running

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Note**: This project has MINIMAL foundational work because it maximizes reuse of existing watchlist infrastructure (95% code reuse).

- [ ] T008 Verify existing WatchlistTag enum includes LONG_TERM value in api/models/watchlist.py
- [ ] T009 Verify existing WatchlistItem model includes all required fields in api/models/watchlist.py
- [ ] T010 Verify existing WatchlistResponse model works for long-term endpoint in api/models/watchlist.py
- [ ] T011 Verify existing DynamoDB client `get_watchlist()` method accessible in client/aws_client.py
- [ ] T012 Verify existing `_enrich_and_sort_watchlist()` method reusable in api/services/watchlist_service.py

**Checkpoint**: Foundation verified - all existing infrastructure ready for reuse

---

## Phase 3: User Story 1 - View Long-Term Holdings (Priority: P1) 🎯 MVP

**Goal**: Enable users to view a filtered list of long-term positions with real-time prices

**Independent Test**: Tag 3 assets with "long-term" label in DynamoDB, access /api/watchlist/long-term endpoint or frontend page, verify exactly 3 assets display with current prices and variation percentages

### Backend Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Create test method `test_get_long_term_positions_filters_correctly` in tests/api/services/test_watchlist_service.py
- [ ] T014 [P] [US1] Create test method `test_get_long_term_positions_empty_when_no_items` in tests/api/services/test_watchlist_service.py
- [ ] T015 [P] [US1] Create test method `test_get_long_term_positions_enriches_prices` in tests/api/services/test_watchlist_service.py
- [ ] T016 [P] [US1] Create test method `test_get_long_term_endpoint_returns_200` in tests/api/routers/test_watchlist.py
- [ ] T017 [P] [US1] Create test method `test_get_long_term_endpoint_empty_response` in tests/api/routers/test_watchlist.py

**Test Checkpoint**: All tests written and FAILING (red status)

### Backend Implementation for User Story 1

- [ ] T018 [US1] Implement `get_long_term_positions()` method in api/services/watchlist_service.py following existing `get_watchlist()` pattern (lines 183-215)
- [ ] T019 [US1] Add `GET /long-term` endpoint in api/routers/watchlist.py following existing endpoint pattern (after line 105)
- [ ] T020 [US1] Run backend tests for User Story 1 and verify all 5 tests pass (`poetry run pytest tests/api/services/test_watchlist_service.py tests/api/routers/test_watchlist.py -v`)

**Backend Checkpoint**: Backend endpoint functional, all tests passing (green status)

### Frontend Implementation for User Story 1

- [ ] T021 [P] [US1] Add `getLongTermPositions()` method to watchlistService in frontend/src/services/api.ts
- [ ] T022 [P] [US1] Create LongTermPositions.tsx component in frontend/src/pages/ copying structure from Watchlist.tsx
- [ ] T023 [P] [US1] Create LongTermPositions.css in frontend/src/pages/ with stale-indicator and badge-crypto styles
- [ ] T024 [US1] Add route for `/long-term` in frontend/src/App.tsx inside <Routes> component
- [ ] T025 [US1] Implement state management (useState for items, loading, error) in LongTermPositions.tsx
- [ ] T026 [US1] Implement loadData() function calling api.getLongTermPositions() in LongTermPositions.tsx
- [ ] T027 [US1] Implement auto-refresh with visibility detection (copy pattern from Watchlist.tsx lines 45-80) in LongTermPositions.tsx
- [ ] T028 [US1] Implement stale price detection function (15-minute threshold) in LongTermPositions.tsx
- [ ] T029 [US1] Implement table rendering with asset rows in LongTermPositions.tsx
- [ ] T030 [US1] Add stale data warning indicator (⚠️ icon) next to prices when price data > 15 minutes old in LongTermPositions.tsx
- [ ] T031 [US1] Add crypto badge (₿ Crypto) for assets with 'crypto' label in LongTermPositions.tsx
- [ ] T032 [US1] Add empty state message when no long-term positions found in LongTermPositions.tsx
- [ ] T033 [US1] Add click handler to navigate to asset detail page in LongTermPositions.tsx

**Frontend Checkpoint**: Frontend page renders, displays data, auto-refreshes

### User Story 1 Validation

- [ ] T034 [US1] Manual test: Tag 2 assets with "long-term" in DynamoDB, verify they appear in frontend
- [ ] T035 [US1] Manual test: Verify empty state displays when no long-term assets exist
- [ ] T036 [US1] Manual test: Verify stale data warning appears for assets with old prices
- [ ] T037 [US1] Manual test: Verify crypto badge appears for crypto assets
- [ ] T038 [US1] Manual test: Verify auto-refresh works after 60 seconds (check network tab)
- [ ] T039 [US1] Manual test: Verify clicking asset row navigates to asset detail page

**Checkpoint**: User Story 1 is fully functional and independently testable ✅

---

## Phase 4: User Story 2 - Remove or Reclassify Positions (Priority: P2)

**Goal**: Enable users to manage long-term position tags and delete assets directly from the long-term menu

**Independent Test**: Access long-term menu with existing long-term positions, remove "long-term" tag from one asset, verify it disappears from menu but remains in All Watchlist view

**Note**: This story reuses existing endpoints (`PATCH /api/watchlist/{asset_id}/labels`, `DELETE /api/watchlist/{asset_id}`) - NO new backend code required.

### Backend Tests for User Story 2

**Note**: Existing tests for update_labels and delete endpoints already exist. Verify coverage:

- [ ] T040 [US2] Verify existing test coverage for `PATCH /api/watchlist/{asset_id}/labels` endpoint in tests/api/routers/test_watchlist.py
- [ ] T041 [US2] Verify existing test coverage for `DELETE /api/watchlist/{asset_id}` endpoint in tests/api/routers/test_watchlist.py

### Frontend Implementation for User Story 2

- [ ] T042 [P] [US2] Add "Remove from Long-Term" button to each asset row in LongTermPositions.tsx
- [ ] T043 [P] [US2] Add "Delete Asset" button to each asset row in LongTermPositions.tsx
- [ ] T044 [US2] Implement `handleRemoveLongTermTag()` function calling watchlistService.updateLabels() in LongTermPositions.tsx
- [ ] T045 [US2] Implement `handleDeleteAsset()` function calling watchlistService.deleteFromWatchlist() in LongTermPositions.tsx
- [ ] T046 [US2] Add confirmation dialog for delete action (use browser confirm() or create modal) in LongTermPositions.tsx
- [ ] T047 [US2] Add loading state during tag removal/deletion operations in LongTermPositions.tsx
- [ ] T048 [US2] Add success/error toast notifications after operations complete in LongTermPositions.tsx
- [ ] T049 [US2] Automatically refresh list after tag removal or deletion in LongTermPositions.tsx
- [ ] T050 [US2] Add CSS styles for action buttons (.remove-btn, .delete-btn) in LongTermPositions.css

### User Story 2 Validation

- [ ] T051 [US2] Manual test: Remove "long-term" tag from asset, verify it disappears from long-term menu
- [ ] T052 [US2] Manual test: Verify removed asset still appears in All Watchlist view
- [ ] T053 [US2] Manual test: Remove "long-term" tag from asset with multiple tags (e.g., "homepage"), verify other tags preserved
- [ ] T054 [US2] Manual test: Delete asset, verify it disappears from all watchlist views
- [ ] T055 [US2] Manual test: Verify confirmation dialog appears before deletion
- [ ] T056 [US2] Manual test: Verify success message appears after operations

**Checkpoint**: User Story 2 is fully functional and independently testable ✅

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, documentation, and deployment preparation

- [ ] T057 [P] Run `poetry run black .` to format backend code
- [ ] T058 [P] Run `poetry run isort .` to sort backend imports
- [ ] T059 [P] Run `poetry run mypy .` to verify type checking passes
- [ ] T060 [P] Run `poetry run flake8` to verify linting passes
- [ ] T061 [P] Run `npm run lint` in frontend/ to verify frontend linting passes
- [ ] T062 [P] Run `npm run build` in frontend/ to verify TypeScript compiles
- [ ] T063 Run full backend test suite (`poetry run pytest --cov`) and verify coverage maintained
- [ ] T064 Review quickstart.md and verify all setup instructions accurate
- [ ] T065 Add navigation menu item linking to `/long-term` page in frontend (if Sidebar component exists)
- [ ] T066 Update CLAUDE.md with any new patterns or conventions discovered during implementation
- [ ] T067 Create git commit with conventional commit format: `feat: add long-term positions menu`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - NO dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) AND User Story 1 completion (reuses frontend component)
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Fully independent
- **User Story 2 (P2)**: Can start after User Story 1 (Phase 3) - Adds functionality to existing component

### Within Each User Story

**User Story 1**:
1. Tests FIRST (T013-T017) - all in parallel [P]
2. Backend implementation (T018-T020) - sequential
3. Frontend components (T021-T023) - all in parallel [P]
4. Frontend integration (T024-T033) - sequential with dependencies
5. Validation (T034-T039) - can run in parallel with multiple testers

**User Story 2**:
1. Test verification (T040-T041) - parallel [P]
2. Frontend UI elements (T042-T043) - parallel [P]
3. Frontend functionality (T044-T050) - sequential
4. Validation (T051-T056) - parallel with multiple testers

### Parallel Opportunities

- **Setup (Phase 1)**: T003 and T004 can run in parallel
- **Foundational (Phase 2)**: T008-T012 are all verification tasks, can run in parallel
- **User Story 1 Tests**: T013-T017 can all run in parallel (different test files/methods)
- **User Story 1 Frontend**: T021-T023 can run in parallel (different files)
- **User Story 2 Tests**: T040-T041 can run in parallel
- **User Story 2 UI**: T042-T043 can run in parallel
- **Polish**: T057-T062 can all run in parallel (different tools)

---

## Parallel Example: User Story 1 Backend Tests

```bash
# Launch all backend tests for User Story 1 together:
Task: "Create test_get_long_term_positions_filters_correctly in tests/api/services/test_watchlist_service.py"
Task: "Create test_get_long_term_positions_empty_when_no_items in tests/api/services/test_watchlist_service.py"
Task: "Create test_get_long_term_positions_enriches_prices in tests/api/services/test_watchlist_service.py"
Task: "Create test_get_long_term_endpoint_returns_200 in tests/api/routers/test_watchlist.py"
Task: "Create test_get_long_term_endpoint_empty_response in tests/api/routers/test_watchlist.py"
```

## Parallel Example: User Story 1 Frontend Components

```bash
# Launch frontend foundation tasks together:
Task: "Add getLongTermPositions() to api.ts"
Task: "Create LongTermPositions.tsx component"
Task: "Create LongTermPositions.css styles"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007) → Environment ready
2. Complete Phase 2: Foundational (T008-T012) → Verify existing infrastructure
3. Complete Phase 3: User Story 1 (T013-T039) → MVP functional
4. **STOP and VALIDATE**: Test User Story 1 independently
5. **DECISION POINT**: Deploy MVP or continue to User Story 2?

**MVP Deliverable**: Users can view filtered long-term positions with real-time prices, stale data warnings, and crypto badges.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Deploy/Demo (MVP!)**
3. Add User Story 2 → Test independently → **Deploy/Demo (Enhanced)**
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

**Not applicable**: This is a small feature (67 tasks total). Single developer can complete in 1-2 days.

If multiple developers available:
1. Team completes Setup + Foundational together (30 minutes)
2. Developer A: User Story 1 Backend (T013-T020) - 2-3 hours
3. Developer B: User Story 1 Frontend (T021-T033) - 4-5 hours (can start after T020)
4. Developer C: User Story 2 (T040-T056) - 2-3 hours (starts after T033)

---

## Task Summary

- **Total Tasks**: 67
- **Setup & Foundational**: 12 tasks (T001-T012)
- **User Story 1**: 27 tasks (T013-T039)
  - Backend tests: 5 tasks
  - Backend implementation: 3 tasks
  - Frontend: 13 tasks
  - Validation: 6 tasks
- **User Story 2**: 17 tasks (T040-T056)
  - Test verification: 2 tasks
  - Frontend: 9 tasks
  - Validation: 6 tasks
- **Polish**: 11 tasks (T057-T067)

### Parallelization Opportunities

- **24 tasks marked [P]** can run in parallel within their phase
- **Backend tests** (5 tasks) can all run together
- **Frontend foundation** (3 tasks) can all run together
- **Code quality checks** (6 tasks) can all run together

### Independent Test Criteria

**User Story 1**:
- Tag 3 assets with "long-term" → Access menu → Verify 3 assets display with prices
- Remove "long-term" tag from all assets → Verify empty state displays
- Wait 60 seconds → Verify auto-refresh occurs

**User Story 2**:
- Remove "long-term" tag from asset → Verify disappears from long-term menu but remains in All Watchlist
- Delete asset → Verify disappears from all views
- Remove tag from asset with multiple labels → Verify other labels preserved

### Suggested MVP Scope

**Recommended**: User Story 1 only (T001-T039)
- **Effort**: 1-2 developer days
- **Value**: Core functionality - users can view long-term positions
- **Risk**: Low - 95% code reuse, proven patterns
- **Testing**: 5 backend unit tests + 6 manual frontend tests

**Optional Enhancement**: Add User Story 2 (T040-T056)
- **Effort**: Additional 0.5-1 day
- **Value**: Convenience - inline tag management
- **Risk**: Very low - reuses existing endpoints

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [US1]/[US2] labels map task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (T013-T017 should be red initially)
- Commit after each logical group of tasks (e.g., after T020, after T033, after T056)
- Stop at any checkpoint to validate story independently
- **95% code reuse achieved** - minimal new code, maximum leverage of existing infrastructure
- No database schema changes required - uses existing `watchlist` DynamoDB table
- No model changes required - uses existing `WatchlistItem` and `WatchlistResponse`

---

## Deployment Checklist

After completing desired user stories and Polish phase:

- [ ] All tests passing (`poetry run pytest`)
- [ ] Code formatted and linted (Black, isort, mypy, flake8)
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Manual testing complete for all implemented user stories
- [ ] Git commit created with conventional format
- [ ] Backend deployed via `./deploy.sh`
- [ ] Frontend deployed (method TBD based on hosting)
- [ ] Verify production endpoint accessible
- [ ] Monitor logs for errors in first 24 hours
