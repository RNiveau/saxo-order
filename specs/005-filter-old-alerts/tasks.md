# Tasks: Filter Old Alerts (5-Day Retention)

**Input**: Design documents from `/specs/005-filter-old-alerts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: No automated tests - manual testing only (no frontend test framework configured)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Frontend**: `frontend/src/`
- **Backend**: `api/` (no changes for this feature)
- This feature is frontend-only; no backend modifications required

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify development environment and dependencies

- [X] T001 Verify Node.js 18+ and npm/yarn installed
- [X] T002 Create feature branch `005-filter-old-alerts` from main
- [X] T003 Install frontend dependencies with `npm install` in frontend/
- [X] T004 Verify TypeScript 5+ and React 19+ versions in frontend/package.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared utility functions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create frontend/src/utils/alertFilters.ts with FIVE_DAYS_HOURS constant (120)
- [X] T006 Implement filterRecentAlerts() function in frontend/src/utils/alertFilters.ts
- [X] T007 Implement deduplicateAlertsByType() function in frontend/src/utils/alertFilters.ts
- [X] T008 Implement processAlerts() combined pipeline function in frontend/src/utils/alertFilters.ts
- [X] T009 Add invalid date handling with console.warn in filterRecentAlerts()
- [X] T010 Verify TypeScript compiles with `npm run type-check` in frontend/

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - See Only Recent Alerts (Priority: P1) 🎯 MVP

**Goal**: Filter alerts to show only those from the last 5 days (≤120 hours old)

**Independent Test**: Create alerts with timestamps spanning 1 to 8 days ago. Navigate to Alerts page and Asset Detail page. Verify only alerts from 1, 3, 5 days ago are displayed; 6 and 8 day old alerts are hidden.

### Implementation for User Story 1

- [X] T011 [P] [US1] Import processAlerts from '../utils/alertFilters' in frontend/src/pages/Alerts.tsx
- [X] T012 [P] [US1] Import processAlerts from '../utils/alertFilters' in frontend/src/pages/AssetDetail.tsx
- [X] T013 [US1] Apply processAlerts() to API response in Alerts.tsx (after alertService.getAll())
- [X] T014 [US1] Apply processAlerts() to API response in AssetDetail.tsx (after alertService.getAll())
- [X] T015 [US1] Update empty state message from "7 days" to "5 days" in frontend/src/pages/Alerts.tsx
- [X] T016 [US1] Verify TypeScript compiles with `npm run type-check` in frontend/
- [X] T017 [US1] Run `npm run lint` and fix any linting errors in frontend/
- [ ] T018 [US1] Manual test: Verify alerts >5 days old are filtered on Alerts page
- [ ] T019 [US1] Manual test: Verify alerts at exactly 120 hours are included (boundary test)
- [ ] T020 [US1] Manual test: Verify alerts >5 days old are filtered on Asset Detail page
- [ ] T021 [US1] Manual test: Verify empty state shows "5 days" message when no recent alerts

**Checkpoint**: At this point, User Story 1 should be fully functional - 5-day filtering works on both pages

---

## Phase 4: User Story 2 - Consistent Filtering Across Views (Priority: P2)

**Goal**: Ensure 5-day filter applies identically on Alerts page and Asset Detail page

**Independent Test**: Create test alerts at 4.5 days and 5.5 days old. Verify 4.5-day alert appears in BOTH pages, and 5.5-day alert appears in NEITHER page.

**Note**: This story builds on User Story 1 - no new implementation needed, only validation

### Validation for User Story 2

- [ ] T022 [US2] Manual test: Create alert at 4.5 days old, verify visible on Alerts page
- [ ] T023 [US2] Manual test: Verify same 4.5-day alert visible on Asset Detail page
- [ ] T024 [US2] Manual test: Create alert at 5.5 days old, verify NOT visible on Alerts page
- [ ] T025 [US2] Manual test: Verify same 5.5-day alert NOT visible on Asset Detail page
- [ ] T026 [US2] Manual test: Navigate between multiple Asset Detail pages, verify consistent 5-day filtering
- [ ] T027 [US2] Manual test: Verify both pages use same processAlerts() function (code review)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - filtering is consistent across all views

---

## Phase 5: User Story 3 - Deduplicate Alerts by Type (Priority: P2)

**Goal**: Keep only the most recent alert for each (asset, alert_type) combination

**Independent Test**: Create 3 COMBO alerts for "ITP:xpar" at 2h, 1d, 3d ago. View Alerts page and Asset Detail page. Verify only the 2h alert is displayed.

**Note**: Deduplication logic already implemented in Phase 2 (deduplicateAlertsByType function). This phase validates it works correctly.

### Validation for User Story 3

- [ ] T028 [US3] Manual test: Create 3 COMBO alerts for same asset at different times
- [ ] T029 [US3] Manual test: Verify only most recent COMBO alert is displayed on Alerts page
- [ ] T030 [US3] Manual test: Verify only most recent COMBO alert is displayed on Asset Detail page
- [ ] T031 [US3] Manual test: Create COMBO + CONGESTION20 for same asset
- [ ] T032 [US3] Manual test: Verify both alerts display (different types not deduplicated)
- [ ] T033 [US3] Manual test: Create COMBO alerts for different assets
- [ ] T034 [US3] Manual test: Verify each asset shows its own COMBO alert (per-asset deduplication)
- [ ] T035 [US3] Manual test: Test Binance asset (null country_code) deduplication works correctly
- [ ] T036 [US3] Manual test: Verify deduplication key format in browser console (debug mode)

**Checkpoint**: All user stories should now be independently functional - filtering + deduplication working

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, performance checks, and documentation

- [ ] T037 [P] Manual test: Create 500 test alerts, verify page remains responsive
- [ ] T038 [P] Manual test: Verify invalid date alerts are excluded without breaking page
- [ ] T039 [P] Manual test: Check browser console for warning messages on invalid dates
- [ ] T040 Run production build with `npm run build` in frontend/
- [ ] T041 Verify build succeeds with no TypeScript or Vite errors
- [ ] T042 Manual smoke test: View Alerts page in production build
- [ ] T043 Manual smoke test: View Asset Detail page in production build
- [ ] T044 [P] Run full quickstart.md testing checklist (all 10 test cases)
- [ ] T045 [P] Code review: Verify no hardcoded 120 hours (uses FIVE_DAYS_HOURS constant)
- [ ] T046 [P] Code review: Verify processAlerts() called in both Alerts.tsx and AssetDetail.tsx
- [ ] T047 Update CLAUDE.md if any new patterns or guidelines discovered
- [ ] T048 Verify conventional commit format for all commits on feature branch

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 can start immediately after Phase 2
  - User Story 2 validates User Story 1 (no new code)
  - User Story 3 validates deduplication (logic already in Phase 2)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Validates User Story 1 - Should run after US1 complete for best results
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independent validation of deduplication

### Within Each User Story

- User Story 1: Import utilities → Apply to pages → Update messages → Lint/type-check → Manual tests
- User Story 2: Manual validation only (no implementation)
- User Story 3: Manual validation only (deduplication already implemented in Phase 2)

### Parallel Opportunities

- Phase 1: All setup tasks (T001-T004) can run in parallel
- Phase 2: T005 first, then T006-T009 can run in parallel (all editing same file sequentially is better)
- User Story 1: T011 and T012 (imports) can run in parallel (different files)
- User Story 1: T018-T021 (manual tests) can run in parallel if multiple testers available
- User Story 2: T022-T027 (manual tests) can run in parallel if multiple testers available
- User Story 3: T028-T036 (manual tests) can run in parallel if multiple testers available
- Phase 6: T037-T039, T044-T046 (tests and code review) can run in parallel

---

## Parallel Example: User Story 1 Implementation

```bash
# Step 1: Run imports in parallel (different files):
Task T011: "Import processAlerts in frontend/src/pages/Alerts.tsx"
Task T012: "Import processAlerts in frontend/src/pages/AssetDetail.tsx"

# Step 2: Apply processing logic sequentially (wait for imports):
Task T013: "Apply processAlerts() in Alerts.tsx"
Task T014: "Apply processAlerts() in AssetDetail.tsx"

# Step 3: Run all manual tests in parallel (if multiple testers):
Task T018: "Manual test: Verify alerts >5 days old filtered on Alerts page"
Task T019: "Manual test: Verify 120-hour boundary condition"
Task T020: "Manual test: Verify alerts >5 days old filtered on Asset Detail page"
Task T021: "Manual test: Verify empty state shows 5 days"
```

---

## Parallel Example: User Story 3 Validation

```bash
# All deduplication tests can run in parallel:
Task T028: "Create 3 COMBO alerts for same asset"
Task T031: "Create COMBO + CONGESTION20 for same asset"
Task T033: "Create COMBO alerts for different assets"
Task T035: "Test Binance asset deduplication"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010) - CRITICAL
3. Complete Phase 3: User Story 1 (T011-T021)
4. **STOP and VALIDATE**: Test 5-day filtering on both pages independently
5. Deploy/demo if ready

**Estimated effort**: ~2-3 hours for MVP (Phase 1 + Phase 2 + Phase 3)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (~30 min)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! ~1.5 hours)
3. Add User Story 2 → Validate consistency → Deploy/Demo (~30 min validation)
4. Add User Story 3 → Validate deduplication → Deploy/Demo (~1 hour validation)
5. Polish phase → Final validation and performance checks (~1 hour)

Total estimated effort: ~4-5 hours for complete feature

### Sequential Strategy (Single Developer)

Recommended order for solo implementation:

1. Phase 1: Setup (15 min)
2. Phase 2: Foundational - Create all utility functions (1 hour)
3. Phase 3: User Story 1 - Apply to pages + basic tests (1.5 hours)
4. Phase 4: User Story 2 - Validation tests only (30 min)
5. Phase 5: User Story 3 - Deduplication tests only (1 hour)
6. Phase 6: Polish - Final checks and build (1 hour)

### Parallel Team Strategy

With 2 developers (after Phase 2 complete):

- **Developer A**: User Story 1 implementation (Phase 3)
- **Developer B**: Prepare test data for User Stories 2 and 3

Then:
- **Developer A**: User Story 2 validation (Phase 4)
- **Developer B**: User Story 3 validation (Phase 5)

Both work on Phase 6 (Polish) together.

**Time savings**: ~1-2 hours with parallel execution

---

## Notes

- **[P] tasks**: Different files or independent operations, can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **No automated tests**: Project has no frontend test framework configured; all testing is manual
- **Manual test strategy**: Follow quickstart.md test checklist (10 test cases)
- **Performance target**: <50ms for filtering + deduplication of 500 alerts
- **Browser testing**: Test on Chrome, Firefox, Safari (per plan.md)
- **Deployment**: Standard Vite build process (`npm run build`)
- **Rollback safety**: Frontend-only changes, easy to revert if needed
- **Code quality**: Run lint + type-check before committing each phase
- **Commit convention**: Use `feat:` prefix for feature additions, `fix:` for bug fixes

---

## Success Criteria

### User Story 1 Complete When:
- ✅ Alerts page shows only alerts ≤120 hours old
- ✅ Asset Detail page shows only alerts ≤120 hours old
- ✅ Alerts at exactly 120 hours are included (boundary condition)
- ✅ Alerts >120 hours are excluded
- ✅ Empty state message says "5 days" not "7 days"
- ✅ TypeScript compiles with no errors
- ✅ Linting passes with no errors

### User Story 2 Complete When:
- ✅ Same alert appears (or doesn't appear) consistently on both pages
- ✅ No discrepancies between Alerts page and Asset Detail page filtering
- ✅ Multiple Asset Detail pages all filter at exactly 5 days

### User Story 3 Complete When:
- ✅ Only most recent alert per (asset, type) is displayed
- ✅ Different alert types for same asset are NOT deduplicated
- ✅ Deduplication is per-asset, not global
- ✅ Binance assets (null country_code) deduplicate correctly

### Feature Complete When:
- ✅ All 3 user stories validated
- ✅ Production build succeeds
- ✅ All 10 quickstart.md test cases pass
- ✅ Performance <50ms for 500 alerts
- ✅ Invalid dates handled gracefully with console warnings
- ✅ Ready for deployment

---

## Task Count Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 6 tasks
- **Phase 3 (User Story 1)**: 11 tasks
- **Phase 4 (User Story 2)**: 6 tasks
- **Phase 5 (User Story 3)**: 9 tasks
- **Phase 6 (Polish)**: 12 tasks

**Total**: 48 tasks

**Parallelizable tasks**: 15 tasks marked [P]
**MVP tasks (Phase 1-3 only)**: 21 tasks

---

## Next Actions

1. Start with Phase 1 (Setup) - verify environment
2. Complete Phase 2 (Foundational) - create utility functions
3. Implement Phase 3 (User Story 1) for MVP
4. Validate Phases 4-5 (User Stories 2-3)
5. Polish and deploy (Phase 6)

**Ready to begin implementation!**
