# Tasks: SLWIN Tag for Watchlist

**Input**: Design documents from `/specs/007-slwin-tag/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No test tasks included (no frontend testing framework configured, backend tests TBD)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `api/` directory (models, services, routers)
- **Frontend**: `frontend/src/` directory (components, pages, services)
- **Tests**: `tests/api/` directory for backend tests

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify development environment and existing infrastructure

- [ ] T001 Verify backend running on port 8000 with `poetry run python run_api.py`
- [ ] T002 Verify frontend running on port 5173 with `cd frontend && npm run dev`
- [ ] T003 [P] Verify existing watchlist endpoints respond correctly at `/api/watchlist`

**Checkpoint**: Development environment ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend enum that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add SLWIN value to WatchlistTag enum in `api/models/watchlist.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 & 3 Combined - Tag Toggle & Mutual Exclusivity (Priority: P1) 🎯 MVP

**Goal**: Enable users to add/remove SLWIN tag on assets with automatic enforcement of mutual exclusivity between SLWIN and short-term tags. This combines US1 (Add SLWIN Tag) and US3 (Mutual Exclusivity) as they share the same backend logic.

**Independent Test**:
1. Navigate to asset detail page and click SLWIN toggle button
2. Verify asset is tagged with SLWIN label in database
3. Verify clicking short-term toggle removes SLWIN tag
4. Verify clicking SLWIN toggle removes short-term tag

### Backend Implementation

- [ ] T005 [US1+US3] Add mutual exclusivity enforcement method `_enforce_tag_mutual_exclusivity()` in `api/services/watchlist_service.py`
- [ ] T006 [US1+US3] Update short-term toggle handler to remove SLWIN when short-term added in `api/services/watchlist_service.py` or router
- [ ] T007 [US1+US3] Update crypto filtering logic to include SLWIN exception in `api/services/watchlist_service.py` line ~208

### Frontend State Management

- [ ] T008 [P] [US1+US3] Add `isSLWIN` state variable in `frontend/src/pages/AssetDetail.tsx` line ~37
- [ ] T009 [P] [US1+US3] Initialize SLWIN state from API in `checkWatchlistStatus` function in `frontend/src/pages/AssetDetail.tsx` line ~134
- [ ] T010 [P] [US1+US3] Reset SLWIN state in `handleToggleWatchlist` function in `frontend/src/pages/AssetDetail.tsx` line ~346

### Frontend Toggle Button

- [ ] T011 [US1+US3] Implement `handleToggleSLWIN` toggle handler in `frontend/src/pages/AssetDetail.tsx` after line ~472
- [ ] T012 [US1+US3] Update `handleToggleShortTerm` to remove SLWIN when short-term added in `frontend/src/pages/AssetDetail.tsx` line ~386
- [ ] T013 [US1+US3] Add SLWIN toggle button to UI after short-term button in `frontend/src/pages/AssetDetail.tsx` line ~544

**Checkpoint**: At this point, SLWIN tag can be toggled on assets with full mutual exclusivity enforcement

---

## Phase 4: User Story 2 - View SLWIN Assets in Sidebar (Priority: P2)

**Goal**: Display SLWIN-tagged assets in sidebar between short-term and untagged assets with visual separators

**Independent Test**:
1. Tag multiple assets with SLWIN via asset detail page
2. Navigate to any page with sidebar
3. Verify SLWIN assets appear after short-term but before untagged
4. Verify dividers appear between sections

### Backend Sorting Logic

- [ ] T014 [US2] Update `sort_key` function to include SLWIN priority in `api/services/watchlist_service.py` line ~174

### Frontend Sidebar Display

- [ ] T015 [US2] Update sidebar sorting detection to identify SLWIN assets in `frontend/src/components/Sidebar.tsx` line ~184
- [ ] T016 [US2] Add divider logic for SLWIN section transitions in `frontend/src/components/Sidebar.tsx` line ~188

**Checkpoint**: SLWIN assets now appear in correct sidebar position with visual separators

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, testing, and documentation

- [ ] T017 [P] Format backend code with `poetry run black api/ && poetry run isort api/`
- [ ] T018 [P] Format frontend code with `cd frontend && npm run lint`
- [ ] T019 [P] Verify TypeScript compiles without errors with `cd frontend && npm run build`
- [ ] T020 Add unit test for SLWIN enum value in `tests/api/models/test_watchlist.py`
- [ ] T021 Add unit test for mutual exclusivity enforcement in `tests/api/services/test_watchlist_service.py`
- [ ] T022 Add unit test for sorting with SLWIN assets in `tests/api/services/test_watchlist_service.py`
- [ ] T023 [P] Run full backend test suite with `poetry run pytest tests/api/ -v`
- [ ] T024 [P] Perform manual integration testing per quickstart.md scenarios

**Checkpoint**: All quality gates passed, ready for deployment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Phase 3 (US1+US3): Can start immediately after Phase 2
  - Phase 4 (US2): Can start immediately after Phase 2 (independent of Phase 3)
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1+3 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1+US3 but benefits from having SLWIN-tagged assets to display

### Within Each User Story

**Phase 3 (US1+US3)**:
- Backend tasks (T005-T007) can run sequentially or T007 can run in parallel with T005-T006
- Frontend state management tasks (T008-T010) marked [P] can run in parallel
- Frontend toggle button tasks (T011-T013) must run sequentially (T011 first, then T012-T013 in any order)

**Phase 4 (US2)**:
- Backend sorting (T014) independent of frontend
- Frontend sidebar tasks (T015-T016) can run in parallel

### Parallel Opportunities

- **Setup (Phase 1)**: T001, T002, T003 can run in parallel (different commands)
- **Foundational (Phase 2)**: Single task, no parallelization
- **Phase 3 Frontend State**: T008, T009, T010 can run in parallel (different parts of same file)
- **Phase 4 Frontend**: T015, T016 can run together (same file, nearby lines)
- **Phase 5 Quality**: T017, T018, T019, T023, T024 can run in parallel (different tools/commands)

---

## Parallel Example: User Story 1+3 (Phase 3)

```bash
# Frontend state management (all in parallel):
Task T008: "Add isSLWIN state variable in frontend/src/pages/AssetDetail.tsx line ~37"
Task T009: "Initialize SLWIN state from API in checkWatchlistStatus function in frontend/src/pages/AssetDetail.tsx line ~134"
Task T010: "Reset SLWIN state in handleToggleWatchlist function in frontend/src/pages/AssetDetail.tsx line ~346"
```

## Parallel Example: User Story 2 (Phase 4)

```bash
# Frontend sidebar updates (both in parallel):
Task T015: "Update sidebar sorting detection to identify SLWIN assets in frontend/src/components/Sidebar.tsx line ~184"
Task T016: "Add divider logic for SLWIN section transitions in frontend/src/components/Sidebar.tsx line ~188"
```

---

## Implementation Strategy

### MVP First (User Stories 1+3 Only)

1. Complete Phase 1: Setup (verify environment)
2. Complete Phase 2: Foundational (add enum - CRITICAL)
3. Complete Phase 3: User Stories 1+3 (toggle button + mutual exclusivity)
4. **STOP and VALIDATE**: Test independently:
   - Click SLWIN button, verify tag added
   - Click short-term button, verify SLWIN removed
   - Click SLWIN button when short-term present, verify short-term removed
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Enum ready
2. Add User Stories 1+3 → Test toggle and mutual exclusivity → Deploy/Demo (MVP!)
3. Add User Story 2 → Test sidebar display → Deploy/Demo
4. Complete Polish → Final quality checks → Production deployment

### Parallel Team Strategy

With 2 developers:

1. **Together**: Complete Setup (Phase 1) + Foundational (Phase 2)
2. **Once Foundational done**:
   - **Developer A**: Phase 3 (US1+US3) - Backend + Frontend toggle
   - **Developer B**: Phase 4 (US2) - Backend sorting + Frontend sidebar
3. **Together**: Phase 5 (Polish) - Code quality and testing

---

## Task Execution Guide

### Backend Tasks (Python)

```bash
# T004: Add enum value
# Open api/models/watchlist.py
# Add: SLWIN = "slwin"  # Stop Loss Win - mutually exclusive with SHORT_TERM

# T005: Add mutual exclusivity method
# Open api/services/watchlist_service.py
# Add method after other helper methods

# T006-T007: Update service logic
# Open api/services/watchlist_service.py
# Locate and update specific functions

# Format and lint
poetry run black api/ && poetry run isort api/
poetry run mypy api/
poetry run flake8 api/
```

### Frontend Tasks (TypeScript/React)

```bash
# T008-T010: Add state management
# Open frontend/src/pages/AssetDetail.tsx
# Add state variable, initialization, and reset logic

# T011-T013: Add toggle button
# Open frontend/src/pages/AssetDetail.tsx
# Add handler function and button JSX

# T014-T016: Update sidebar
# Open frontend/src/components/Sidebar.tsx
# Update sorting detection and divider logic

# Format and validate
cd frontend
npm run lint
npm run build
```

### Testing Tasks

```bash
# T020-T022: Add unit tests
# Open tests/api/models/test_watchlist.py
# Open tests/api/services/test_watchlist_service.py
# Add test functions

# T023: Run test suite
poetry run pytest tests/api/ -v

# T024: Manual integration testing
# Follow scenarios in quickstart.md
```

---

## Success Criteria

- ✅ SLWIN enum value added to backend model
- ✅ Mutual exclusivity enforced (SLWIN ↔ Short-Term)
- ✅ SLWIN toggle button works on asset detail page
- ✅ SLWIN assets appear in correct sidebar position
- ✅ Dividers display between tag sections
- ✅ Crypto assets with SLWIN tag appear in sidebar
- ✅ Backend tests pass
- ✅ Frontend builds without TypeScript errors
- ✅ Code formatted and linted
- ✅ All manual test scenarios pass

---

## Estimated Time Breakdown

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1: Setup | T001-T003 | 5 min |
| Phase 2: Foundational | T004 | 5 min |
| Phase 3: US1+US3 (MVP) | T005-T013 | 75 min |
| Phase 4: US2 | T014-T016 | 30 min |
| Phase 5: Polish | T017-T024 | 45 min |
| **Total** | **24 tasks** | **~2.5 hours** |

---

## Notes

- [P] tasks = different files or independent changes, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US3 combined in Phase 3 because they share backend mutual exclusivity logic
- Each user story phase should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Manual testing scenarios documented in quickstart.md

---

## Next Steps After Task Completion

1. ✅ Commit changes with conventional commit format
2. ✅ Create pull request with feature summary
3. ✅ Request code review
4. ✅ Deploy to production via `./deploy.sh`
5. Monitor user feedback and usage patterns

## Related Documentation

- Feature Spec: `specs/007-slwin-tag/spec.md`
- Implementation Plan: `specs/007-slwin-tag/plan.md`
- Research: `specs/007-slwin-tag/research.md`
- Data Model: `specs/007-slwin-tag/data-model.md`
- API Contract: `specs/007-slwin-tag/contracts/watchlist-slwin.yaml`
- Quickstart Guide: `specs/007-slwin-tag/quickstart.md`
