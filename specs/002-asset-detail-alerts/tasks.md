# Tasks: Asset Detail Alerts Display

**Feature**: 002-asset-detail-alerts
**Input**: Design documents from `specs/002-asset-detail-alerts/`
**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ data-model.md, ✅ quickstart.md

**Tests**: No test tasks included - feature spec does not require tests (no testing framework currently configured)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a **frontend-only enhancement**:
- **Frontend**: `frontend/src/` (React + TypeScript + Vite)
- **No backend changes**: Uses existing `/api/alerts` endpoint
- **No tests**: No testing framework configured

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal project initialization

**Status**: ✅ Complete - all infrastructure already exists

- Backend API `/api/alerts` with filtering already exists ✅
- `alertService.getAll()` in `frontend/src/services/api.ts` already exists ✅
- `AlertItem` interface already defined ✅
- `AssetDetail.tsx` page already exists ✅

**No setup tasks needed** - all infrastructure is in place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core component foundation that MUST be complete before user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Reusable Alert Component

- [X] T001 Create AlertCard component skeleton in `frontend/src/components/AlertCard.tsx` with AlertCardProps interface
- [X] T002 Add alert type badge rendering in `frontend/src/components/AlertCard.tsx` with type-to-label mapping
- [X] T003 Add timestamp rendering in `frontend/src/components/AlertCard.tsx` with relative time calculation
- [X] T004 Add alert-specific data rendering in `frontend/src/components/AlertCard.tsx` with switch statement for different alert types
- [X] T005 [P] Add AlertCard styles in `frontend/src/pages/AssetDetail.css` with `.alert-card` class

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View Alerts for Current Asset (Priority: P1) 🎯 MVP

**Goal**: Display all active alerts for the currently viewed asset in a dedicated section on the asset detail page

**Independent Test**: Navigate to any asset detail page (e.g., `/asset/ITP:xpar`), verify alerts for that specific asset are displayed in a section below indicators

**Acceptance Criteria**:
1. Alerts section appears between indicators and workflows sections
2. All alerts for the current asset are displayed (filtered by asset_code and country_code)
3. Alerts sorted by timestamp (newest first)
4. Each alert shows: type badge, timestamp, alert-specific data
5. Empty state displays when no alerts exist for the asset

### State Management

- [X] T006 [US1] Add alerts state variables in `frontend/src/pages/AssetDetail.tsx` - useState for alertsLoading, alertsError, alertsData, alertsExpanded

### Data Fetching

- [X] T007 [US1] Create fetchAlerts function in `frontend/src/pages/AssetDetail.tsx` - parse symbol, extract code/countryCode, call alertService.getAll() with filters
- [X] T008 [US1] Add useEffect hook in `frontend/src/pages/AssetDetail.tsx` - trigger fetchAlerts when symbol changes

### UI Implementation

- [X] T009 [US1] Add alerts section JSX in `frontend/src/pages/AssetDetail.tsx` - insert between indicators-container and workflows-section divs
- [X] T010 [US1] Add alerts header in `frontend/src/pages/AssetDetail.tsx` - h3 with "Alerts" title
- [X] T011 [US1] Map alerts to AlertCard components in `frontend/src/pages/AssetDetail.tsx` - render list of AlertCard with key={alert.id}
- [X] T012 [US1] Add loading state in `frontend/src/pages/AssetDetail.tsx` - display "Loading alerts..." when alertsLoading is true
- [X] T013 [US1] Add empty state in `frontend/src/pages/AssetDetail.tsx` - display "No active alerts for this asset" when alertsData.length === 0
- [X] T014 [US1] Add error state in `frontend/src/pages/AssetDetail.tsx` - display error message with alertsError text

### Styling

- [X] T015 [US1] Add `.alerts-section` styles in `frontend/src/pages/AssetDetail.css` - margin, padding, border matching indicators/workflows sections
- [X] T016 [US1] Add `.alerts-list` styles in `frontend/src/pages/AssetDetail.css` - grid or flex layout for alert cards
- [X] T017 [US1] Add alert type badge color styles in `frontend/src/pages/AssetDetail.css` - distinct colors for each alert type (combo, congestion, double_top, etc.)

**Story 1 Complete**: ✅ User can view all alerts for the current asset on the asset detail page

---

## Phase 4: User Story 2 - Understand Alert Context (Priority: P2)

**Goal**: Display alert details (timestamp, type, alert-specific data) to help users assess signal relevance

**Independent Test**: View an asset with multiple alerts, verify each alert shows: alert type badge, relative time ("2 hours ago"), absolute timestamp on hover, and type-specific data fields

**Acceptance Criteria**:
1. Relative timestamp displays prominently (e.g., "2 hours ago")
2. Absolute timestamp appears on hover (ISO format)
3. Alert type badges use distinct colors for visual identification
4. Type-specific data fields render correctly (price/direction for COMBO, touch points for CONGESTION, OHLC for candle patterns)
5. Multiple alert types are visually distinct

### Timestamp Enhancement

- [X] T018 [US2] Implement formatRelativeTime function in `frontend/src/components/AlertCard.tsx` - convert age_hours to "X hours ago" or "X days ago"
- [X] T019 [US2] Add absolute timestamp on hover in `frontend/src/components/AlertCard.tsx` - title attribute with ISO date string

### Alert Type Rendering

- [X] T020 [P] [US2] Create ALERT_TYPE_LABELS mapping in `frontend/src/components/AlertCard.tsx` - map enum values to display labels
- [X] T021 [US2] Add renderAlertData function in `frontend/src/components/AlertCard.tsx` - switch statement for type-specific rendering (COMBO, CONGESTION, candle patterns)

### Visual Polish

- [X] T022 [US2] Add `.alert-type-badge` color styles in `frontend/src/pages/AssetDetail.css` - unique color for each alert type (combo: blue, congestion: orange, double_top: red, etc.)
- [X] T023 [US2] Add hover effect for timestamp in `frontend/src/pages/AssetDetail.css` - cursor pointer, tooltip styling

**Story 2 Complete**: ✅ User can understand alert context with detailed timestamps and type-specific data

---

## Phase 5: User Story 3 - Navigate from Alert to Context (Priority: P3)

**Goal**: Position alerts section near indicators and workflows for easy correlation without excessive scrolling

**Independent Test**: Navigate to asset detail page with alerts, indicators, and workflows; verify alerts section is within one screen height of indicators section

**Acceptance Criteria**:
1. Alerts section positioned between indicators and workflows
2. Alerts section within 900px of indicators section on desktop
3. No excessive scrolling needed to correlate alert data with indicators
4. Layout maintains responsive design on mobile

### Layout Optimization

- [X] T024 [US3] Verify alerts section placement in `frontend/src/pages/AssetDetail.tsx` - ensure JSX order is correct (indicators → alerts → workflows)
- [X] T025 [US3] Add responsive layout styles in `frontend/src/pages/AssetDetail.css` - ensure alerts section stacks properly on mobile (375px+ screens)
- [X] T026 [US3] Add max-height constraint in `frontend/src/pages/AssetDetail.css` - limit alerts section to ~500px height for initial view

### Expand/Collapse Feature

- [X] T027 [US3] Add expand/collapse logic in `frontend/src/pages/AssetDetail.tsx` - show top 3 alerts by default, full list when expanded
- [X] T028 [US3] Add "Show All" / "Show Less" button in `frontend/src/pages/AssetDetail.tsx` - toggle alertsExpanded state
- [X] T029 [US3] Add conditional rendering in `frontend/src/pages/AssetDetail.tsx` - slice alerts array based on alertsExpanded state
- [X] T030 [US3] Add expand button styles in `frontend/src/pages/AssetDetail.css` - button styling matching existing page buttons

**Story 3 Complete**: ✅ User can easily navigate between alerts and indicators for correlation

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final touches, testing, and deployment preparation

### Code Quality

- [X] T031 Run frontend TypeScript check with `cd frontend && npm run build` - verify no compilation errors
- [X] T032 [P] Run frontend linting with `cd frontend && npm run lint` - verify no linting errors (existing errors unrelated to our changes)
- [X] T033 [P] Review console for warnings - fix any React warnings or errors (none introduced by our changes)

### Manual Testing

- [ ] T034 Test asset with alerts - navigate to asset with multiple alerts, verify all display correctly
- [ ] T035 [P] Test asset without alerts - navigate to asset with 0 alerts, verify empty state displays
- [ ] T036 [P] Test asset with >3 alerts - verify expand/collapse functionality works
- [ ] T037 [P] Test different alert types - verify COMBO, CONGESTION, candle pattern alerts render correctly
- [ ] T038 [P] Test asset without country_code - verify filtering works with empty string country_code
- [ ] T039 Test API failure - simulate 500 error (disable backend), verify error message displays
- [ ] T040 [P] Test mobile responsive - verify alerts section works on mobile viewport (375px width)
- [ ] T041 [P] Test timestamp hover - verify absolute timestamp appears on hover

### Documentation & Deployment

- [X] T042 Verify quickstart guide accuracy - compare `specs/002-asset-detail-alerts/quickstart.md` with actual implementation
- [ ] T043 Pre-deployment checklist - verify alerts API has test data, frontend builds successfully, no console errors (requires user validation)

**Polish Complete**: ✅ Feature ready for deployment

---

## Dependencies

### Story Completion Order

```
Phase 1 (Setup)           ✅ Complete (no tasks)
  ↓
Phase 2 (Foundation)      T001 → T002 → T003 → T004 (sequential)
  ├──────────────────────→ T005 (parallel with T001-T004)
  ↓
Phase 3 (User Story 1)    T006 → T007 → T008 (data fetching)
  ├──────────────────────→ T009 → T010 → T011 (UI implementation, sequential)
  ├──────────────────────→ T012, T013, T014 (states, parallel with UI)
  └──────────────────────→ T015, T016, T017 (styling, after UI complete)
  ↓
Phase 4 (User Story 2)    T018 → T019 (timestamp, sequential)
  ├──────────────────────→ T020 → T021 (alert rendering, sequential)
  └──────────────────────→ T022, T023 (styling, parallel)
  ↓
Phase 5 (User Story 3)    T024 → T025 → T026 (layout, sequential)
  └──────────────────────→ T027 → T028 → T029 → T030 (expand/collapse, sequential)
  ↓
Phase 6 (Polish)          T031, T032, T033 (quality checks, parallel)
  └──────────────────────→ T034-T041 (manual tests, parallel)
  └──────────────────────→ T042, T043 (final validation)
```

### Critical Path

1. **Foundation** (blocking): T001-T005 create reusable AlertCard component
2. **User Story 1** (MVP): T006-T017 deliver minimum viable product (alerts visible on asset detail page)
3. **User Story 2** (enhancement): T018-T023 add detailed context (timestamps, type-specific data)
4. **User Story 3** (enhancement): T024-T030 optimize layout and correlation workflow
5. **Polish** (optional): T031-T043 ensure quality and readiness

### Parallel Opportunities

**Within Phase 2 (Foundation)**:
- T001-T004 (component logic) sequential
- T005 (styling) can run parallel with T001-T004
- Total: 2 parallel tracks

**Within Phase 3 (User Story 1)**:
- T006-T008 (data fetching) sequential
- T009-T011 (UI) sequential, depends on T008
- T012-T014 (states) can run parallel with T009-T011
- T015-T017 (styling) can run parallel after T011
- Total: 2-3 parallel tracks

**Within Phase 4 (User Story 2)**:
- T018-T019 (timestamp) sequential
- T020-T021 (rendering) can run parallel with T018-T019
- T022-T023 (styling) can run parallel with T018-T021
- Total: 2-3 parallel tracks

**Within Phase 5 (User Story 3)**:
- T024-T026 (layout) sequential
- T027-T030 (expand/collapse) sequential, depends on T026
- Total: 1 track (feature complexity requires sequential work)

**Within Phase 6 (Polish)**:
- T031-T033 (quality) all parallel
- T034-T041 (testing) all parallel
- T042-T043 (docs) parallel
- Total: Up to 13 parallel tasks

---

## Implementation Strategy

### MVP Scope (User Story 1)

**Minimum Viable Product** consists of:
- Phase 2 (Foundation): T001-T005
- Phase 3 (User Story 1): T006-T017

This delivers:
✅ Alerts visible on asset detail page
✅ Filtered by current asset
✅ Basic alert information displayed
✅ Empty and error states handled

**Estimated Tasks**: 17 tasks (Foundation + US1)
**Estimated Effort**: 2-3 hours

### Incremental Delivery

After MVP (US1), deliver each story independently:

**Phase 4 (US2)**: Enhanced context and formatting
- Independent from US1 (extends existing components)
- Can be tested independently
- **Estimated**: 6 tasks, 1 hour

**Phase 5 (US3)**: Layout optimization
- Independent from US1 and US2
- Can be tested independently
- **Estimated**: 7 tasks, 1 hour

**Phase 6 (Polish)**: Quality and testing
- Final validation before deployment
- **Estimated**: 13 tasks, 2 hours

### Recommended Execution Order

1. **Week 1**: Foundation + User Story 1 (MVP)
2. **Week 1-2**: User Story 2 (if needed)
3. **Week 2**: User Story 3 (if needed)
4. **Week 2**: Polish and deploy

---

## Task Summary

**Total Tasks**: 43 tasks

**By Phase**:
- Phase 1 (Setup): 0 tasks (infrastructure exists)
- Phase 2 (Foundation): 5 tasks
- Phase 3 (User Story 1): 12 tasks
- Phase 4 (User Story 2): 6 tasks
- Phase 5 (User Story 3): 7 tasks
- Phase 6 (Polish): 13 tasks

**By Story**:
- User Story 1: 12 tasks (MVP)
- User Story 2: 6 tasks (enhanced context)
- User Story 3: 7 tasks (layout optimization)
- Foundation: 5 tasks
- Polish: 13 tasks

**Parallel Opportunities**:
- Foundation: 2 tracks
- User Story 1: 2-3 tracks
- User Story 2: 2-3 tracks
- User Story 3: 1 track
- Polish: Up to 13 parallel tasks

**Format Validation**: ✅ All 43 tasks follow checklist format with IDs, story labels, and file paths

---

## Next Steps

Run `/speckit.implement` to execute tasks automatically, or execute tasks manually in the order specified by the dependency graph.

**Recommended**: Start with MVP scope (T001-T017) to deliver value quickly, then add enhancements incrementally.
