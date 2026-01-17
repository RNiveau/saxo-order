# Tasks: Alerts UI Page

**Feature**: 001-alerts-ui-page
**Input**: Design documents from `.specify/specs/001-alerts-ui-page/`
**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ data-model.md, ✅ contracts/, ✅ quickstart.md

**Tests**: No test tasks included - feature spec does not require tests (existing test coverage patterns apply)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

This is a **web application** with backend and frontend:
- **Backend**: `api/` (FastAPI + Pydantic)
- **Frontend**: `frontend/src/` (React + TypeScript + Vite)
- **Tests**: `tests/api/` (pytest)
- **Models**: `model/` (existing, no changes)
- **Clients**: `client/` (existing, no changes)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal project initialization - most infrastructure already exists

**Status**: ✅ Most setup complete (DynamoDB table, Alert model, DynamoDBClient, frontend shell all exist)

**No setup tasks needed** - all infrastructure is already in place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core API infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Backend API Foundation

- [X] T001 Create Pydantic models in `api/models/alerting.py` (AlertItemResponse, AlertsResponse)
- [X] T002 Create AlertingService skeleton in `api/services/alerting_service.py` with DynamoDBClient injection
- [X] T003 Create AlertingRouter in `api/routers/alerting.py` with GET /api/alerts endpoint
- [X] T004 Register AlertingRouter in `api/main.py` with `/api/alerts` prefix

### Frontend API Service Foundation

- [X] T005 [P] Add TypeScript interfaces in `frontend/src/services/api.ts` (AlertItem, AlertsResponse)
- [X] T006 [P] Add alertService object in `frontend/src/services/api.ts` with getAll() method

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View All Active Alerts (Priority: P1) 🎯 MVP

**Goal**: Display all active alerts from the last 7 days in a dedicated page with basic information (asset, type, timestamp, data)

**Independent Test**: Navigate to http://localhost:5173/alerts and verify all alerts from the last 7 days are displayed, sorted newest first

**Acceptance Criteria**:
1. ✅ All alerts display in a list
2. ✅ Sorted by timestamp (newest first)
3. ✅ Each alert shows: asset code, alert type, timestamp, alert data
4. ✅ Alerts older than 7 days not displayed (TTL handles this)
5. ✅ Empty state displays when no alerts exist

### Backend Implementation

- [X] T007 [US1] Implement AlertingService.get_all_alerts() in `api/services/alerting_service.py` - fetch from DynamoDB, sort, transform to responses
- [X] T008 [US1] Implement AlertingService._to_response() in `api/services/alerting_service.py` - transform Alert to AlertItemResponse with age calculation
- [X] T009 [US1] Implement GET /api/alerts handler in `api/routers/alerting.py` - call service.get_all_alerts() and return AlertsResponse

### Frontend Implementation

- [X] T010 [P] [US1] Create AlertCard component in `frontend/src/components/AlertCard.tsx` - display single alert with asset, type, timestamp, data
- [X] T011 [US1] Create Alerts page in `frontend/src/pages/Alerts.tsx` - fetch alerts, handle loading/error, display alert list
- [X] T012 [US1] Add /alerts route in `frontend/src/App.tsx` - register Alerts page component

### Integration & Polish

- [X] T013 [US1] Add navigation link to Alerts page in `frontend/src/App.tsx` or sidebar component
- [X] T014 [US1] Style Alerts page and AlertCard component - create CSS for layout and alert cards
- [X] T015 [US1] Add empty state handling - display "No active alerts" message when alerts array is empty
- [X] T016 [US1] Add error state handling - display error message with retry button on API failure

**Story 1 Complete**: ✅ User can view all active alerts in a dedicated page

---

## Phase 4: User Story 2 - Filter and Search Alerts (Priority: P2)

**Goal**: Enable filtering alerts by asset code and alert type to focus on specific trading opportunities

**Independent Test**: Apply a filter for a specific asset (e.g., "ITP"), verify only alerts for that asset are displayed

**Acceptance Criteria**:
1. ✅ Filter dropdown for asset code displays all available assets
2. ✅ Filter dropdown for alert type displays all available types
3. ✅ Applying filter updates alert list to show only matching items
4. ✅ Clearing filter shows all alerts again
5. ✅ Filter counts display number of available options

### Backend Implementation

- [X] T017 [US2] Implement AlertingService._calculate_filters() in `api/services/alerting_service.py` - extract unique asset_codes, alert_types, country_codes from alerts
- [X] T018 [US2] Update AlertingService.get_all_alerts() in `api/services/alerting_service.py` - add asset_code, alert_type, country_code filter parameters
- [X] T019 [US2] Update GET /api/alerts handler in `api/routers/alerting.py` - add Query parameters for asset_code, alert_type, country_code

### Frontend Implementation

- [X] T020 [P] [US2] Add filter state in `frontend/src/pages/Alerts.tsx` - useState for selected filters (asset_code, alert_type) - client-side filtering implemented
- [X] T021 [US2] Add filter UI in `frontend/src/pages/Alerts.tsx` - dropdown selects for asset and alert type with user-friendly labels
- [X] T022 [US2] Update filtering in `frontend/src/pages/Alerts.tsx` - client-side filter using Array.filter() on alerts array
- [X] T023 [US2] Add "Clear Filters" button in `frontend/src/pages/Alerts.tsx` - reset filters to show all alerts

### Integration & Polish

- [X] T024 [US2] Display filter counts in `frontend/src/pages/Alerts.tsx` - show number of available options for each filter
- [X] T025 [US2] Add filter UI styling - create CSS for filter controls and layout

**Story 2 Complete**: ✅ User can filter alerts by asset and type

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final touches, testing, and deployment preparation

### Code Quality

- [ ] T026 Run backend tests with `poetry run pytest` - verify all tests pass
- [ ] T027 Run backend linting with `poetry run black .` and `poetry run isort .` - format code
- [ ] T028 Run backend type checking with `poetry run mypy .` - verify no type errors
- [ ] T029 [P] Run frontend build with `cd frontend && npm run build` - verify TypeScript compiles

### Documentation & Deployment

- [ ] T030 [P] Update API documentation - verify Swagger UI at http://localhost:8000/docs shows new endpoints
- [ ] T031 [P] Verify CORS configuration in `api/main.py` - ensure frontend origin (localhost:5173) is allowed
- [ ] T032 Manual smoke test - start backend and frontend, navigate to /alerts, verify alerts display and filtering works
- [ ] T033 Pre-deployment checklist - verify DynamoDB has test data, backend accessible, frontend builds successfully

**Polish Complete**: ✅ Feature ready for deployment

---

## Dependencies

### Story Completion Order

```
Phase 1 (Setup)           ✅ Complete (no tasks)
  ↓
Phase 2 (Foundation)      T001 → T002 → T003 → T004 (sequential)
  ├──────────────────────→ T005, T006 (parallel with T001-T004)
  ↓
Phase 3 (User Story 1)    T007 → T008 → T009 (backend sequential)
  ├──────────────────────→ T010, T011, T012 (frontend parallel with backend)
  ├──────────────────────→ T013, T014 (integration, depends on T009 + T012)
  └──────────────────────→ T015, T016 (polish, depends on T011)
  ↓
Phase 4 (User Story 2)    T017 → T018 → T019 (backend sequential, extends US1)
  ├──────────────────────→ T020, T021, T022, T023 (frontend parallel with backend)
  └──────────────────────→ T024, T025 (polish, depends on T022 + T023)
  ↓
Phase 5 (Polish)          T026, T027, T028, T029 (all parallel)
  └──────────────────────→ T030, T031 (parallel)
  └──────────────────────→ T032, T033 (final validation)
```

### Critical Path

1. **Foundation** (blocking): T001-T004 MUST complete before any user story work
2. **User Story 1** (MVP): T007-T016 deliver minimum viable product
3. **User Story 2** (enhancement): T017-T025 add filtering (depends on US1 complete)
4. **Polish** (optional): T026-T033 ensure quality and readiness

### Parallel Opportunities

**Within Phase 2 (Foundation)**:
- T001-T004 (backend) can run parallel with T005-T006 (frontend interfaces)
- Total: 2 parallel tracks

**Within Phase 3 (User Story 1)**:
- T007-T009 (backend) can run parallel with T010-T012 (frontend)
- T015-T016 (error handling) can run parallel with T014 (styling)
- Total: 2-3 parallel tracks

**Within Phase 4 (User Story 2)**:
- T017-T019 (backend) can run parallel with T020-T023 (frontend)
- T024-T025 (polish) can run parallel
- Total: 2 parallel tracks

**Within Phase 5 (Polish)**:
- T026-T029 (all code quality checks) can run parallel
- T030-T031 (documentation/config) can run parallel
- Total: 6 parallel tasks possible

---

## Implementation Strategy

### MVP First Approach

**Minimum Viable Product** = User Story 1 only
- Tasks: T001-T016 (16 tasks)
- Delivers: View all active alerts in a dedicated page
- Independent test: Navigate to /alerts, see all alerts displayed
- Time estimate: Can be completed in single implementation session

**Post-MVP Enhancement** = User Story 2
- Tasks: T017-T025 (9 tasks)
- Delivers: Filtering by asset and alert type
- Independent test: Apply filter, verify only matching alerts show
- Time estimate: Can be completed in separate session

**Polish** = Phase 5
- Tasks: T026-T033 (8 tasks)
- Delivers: Code quality, testing, deployment readiness
- Time estimate: 1-2 hours for verification

### Incremental Delivery

1. **Deliver MVP** (T001-T016):
   - Deploy to production after T016
   - User can immediately view all alerts
   - Gather feedback on UI/UX

2. **Add Filtering** (T017-T025):
   - Deploy after T025
   - Backward compatible (filter params optional)
   - Enhanced user experience

3. **Polish & Deploy** (T026-T033):
   - Run quality checks
   - Verify production readiness
   - Final deployment

---

## Task Summary

| Phase | Tasks | Parallelizable | User Story | Status |
|-------|-------|----------------|------------|--------|
| Setup | 0 | 0 | N/A | ✅ Complete |
| Foundation | 6 (T001-T006) | 2 (T005, T006) | N/A | ⏭️ Ready |
| User Story 1 | 10 (T007-T016) | 4 (T010, T013, T014, T015) | P1 | 🎯 MVP |
| User Story 2 | 9 (T017-T025) | 2 (T020, T024) | P2 | ⏭️ Post-MVP |
| Polish | 8 (T026-T033) | 6 (T026-T031) | N/A | ⏭️ Final |
| **Total** | **33 tasks** | **14 parallel** | 2 stories | Ready |

---

## Validation Checklist

**Format Compliance**: ✅ All 33 tasks follow checklist format
- ✅ All tasks have checkbox `- [ ]`
- ✅ All tasks have sequential ID (T001-T033)
- ✅ All tasks have [P] marker where applicable (14 tasks)
- ✅ All tasks have [Story] label for user story phases (19 tasks)
- ✅ All tasks have clear description with file path

**Coverage Completeness**: ✅ All requirements mapped to tasks
- ✅ User Story 1 (P1): 10 tasks covering all acceptance criteria
- ✅ User Story 2 (P2): 9 tasks covering all acceptance criteria
- ✅ Backend API: Pydantic models, service, router (T001-T009, T017-T019)
- ✅ Frontend: Components, page, routing (T010-T012, T020-T023)
- ✅ Integration: Navigation, styling, error handling (T013-T016, T024-T025)
- ✅ Quality: Testing, linting, deployment (T026-T033)

**Independent Testing**: ✅ Each user story can be tested independently
- ✅ US1 Independent Test: Navigate to /alerts, verify alerts display
- ✅ US2 Independent Test: Apply filter, verify only matching alerts show

**MVP Scope**: ✅ Clearly defined (User Story 1 only = T001-T016)

---

## Next Steps

1. **Start Implementation**: Begin with Phase 2 (Foundation) tasks T001-T006
2. **MVP Delivery**: Complete Phase 3 (User Story 1) tasks T007-T016
3. **Enhancement**: Add Phase 4 (User Story 2) tasks T017-T025
4. **Polish**: Run Phase 5 (Polish) tasks T026-T033
5. **Deploy**: Use `./deploy.sh` for backend, build frontend for hosting

**Ready to implement**: ✅ All tasks defined, dependencies mapped, parallel opportunities identified
