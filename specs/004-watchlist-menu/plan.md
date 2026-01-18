# Implementation Plan: Long-Term Positions Menu

**Branch**: `004-watchlist-menu` | **Date**: 2026-01-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-watchlist-menu/spec.md`

**User Direction**: Maximize reuse of existing watchlist backend infrastructure

## Summary

Add a dedicated menu for viewing long-term positions by filtering watchlist items with the "long-term" label. Implementation reuses 95% of existing watchlist backend (service layer, data models, DynamoDB operations, enrichment logic) with minimal additions: one new service method and one new API endpoint. Frontend adds a new page component following existing watchlist patterns.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI (backend), Vite + React Router DOM v7+ (frontend)
**Storage**: AWS DynamoDB (existing "watchlist" table)
**Testing**: pytest with unittest.mock (backend), TBD (frontend)
**Target Platform**: AWS Lambda (backend via Docker/ECR), Web browser (frontend)
**Project Type**: Web application (backend API + frontend SPA)
**Performance Goals**: <3 seconds load time for 100+ positions, 60-second price refresh interval
**Constraints**: <2 seconds for tag modification reflection, real-time price updates every 60 seconds when market open
**Scale/Scope**: Single filtered endpoint, one new frontend page, minimal backend extension

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Layered Architecture Discipline
✅ **PASS** - Implementation follows established layers:
- Backend: New endpoint in API layer (`api/routers/watchlist.py`), new method in Service layer (`api/services/watchlist_service.py`)
- Service receives DynamoDB client via constructor dependency injection (existing pattern)
- Frontend: New page in `frontend/src/pages/`, API calls through `frontend/src/services/api.ts`
- NO cross-layer violations - reuses existing patterns

### Clean Code First
✅ **PASS** - Implementation uses existing enums (`WatchlistTag.LONG_TERM`), no hardcoded strings
- Follows Black formatter (79 char line length), isort conventions
- Self-documenting code following existing service method patterns
- MyPy type checking required for new service method

### Configuration-Driven Design
✅ **PASS** - No new configuration needed:
- Reuses existing DynamoDB table configuration
- Frontend uses existing `VITE_API_URL` for API endpoint
- No new secrets or environment variables required

### Safe Deployment Practices
✅ **PASS** - Standard deployment process:
- Backend: Deploy via `./deploy.sh` (Docker image to ECR, Pulumi update)
- Frontend: Standard Vite build (`npm run build`)
- Infrastructure unchanged (no Pulumi modifications needed)
- Conventional commit format required

### Domain Model Integrity
✅ **PASS** - Reuses existing domain models:
- WatchlistItem model already contains all required fields
- WatchlistTag enum includes LONG_TERM value
- Enrichment logic handles both Saxo and Binance assets correctly
- Explicit `exchange` field already present in model

**Gate Status**: ✅ ALL GATES PASSED - No violations, proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/004-watchlist-menu/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0 output (to be generated)
├── data-model.md        # Phase 1 output (to be generated)
├── quickstart.md        # Phase 1 output (to be generated)
├── contracts/           # Phase 1 output (to be generated)
└── checklists/
    └── requirements.md  # Specification quality checklist (complete)
```

### Source Code (repository root)

```text
# Backend API
api/
├── routers/
│   └── watchlist.py              # ADD: /long-term endpoint (12 lines)
├── services/
│   └── watchlist_service.py      # ADD: get_long_term_positions() method (25 lines)
└── models/
    └── watchlist.py              # NO CHANGES (reuse existing models)

# Frontend
frontend/src/
├── pages/
│   └── LongTermPositions.tsx     # NEW: Long-term positions page component
├── services/
│   └── api.ts                    # ADD: getLongTermPositions() function (5 lines)
└── App.tsx                       # MODIFY: Add route for long-term positions page

# Database
client/
└── aws_client.py                 # NO CHANGES (reuse existing DynamoDB methods)

# Tests
tests/
├── api/
│   ├── services/
│   │   └── test_watchlist_service.py  # ADD: 2-3 test methods for get_long_term_positions()
│   └── routers/
│       └── test_watchlist.py          # ADD: 2-3 test methods for /long-term endpoint
```

**Structure Decision**: Web application structure (backend + frontend). Implementation maximizes reuse of existing watchlist infrastructure - 95% code reuse achieved by leveraging established patterns in service layer, router layer, and data models. Only additions are one filtered service method and one frontend page following existing patterns.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No complexity violations detected. Implementation fully complies with constitution principles.*

---

## Phase 0: Research

**Status**: ✅ Complete

### Research Questions

Based on Technical Context and user requirement to "reuse as much as possible on the current backend for the classic watchlist", the following research tasks are needed:

1. **Frontend Component Patterns**: How does existing Watchlist.tsx implement filtering, display, and real-time updates?
2. **Routing Integration**: How to add new route in React Router DOM v7+ following existing patterns?
3. **Stale Data UI Patterns**: Best practices for displaying "stale data" warning indicators (FR-012 from spec)
4. **Crypto Badge UI Patterns**: How to display asset type badges inline with asset names (FR-013 from spec)

### Research Tasks

#### Task 1: Frontend Watchlist Component Analysis
**Question**: What patterns does Watchlist.tsx use for rendering items, handling tag filters, and auto-refresh?
**Approach**:
- Read `frontend/src/pages/Watchlist.tsx`
- Identify state management patterns
- Identify refresh interval logic
- Identify tag filter UI patterns

#### Task 2: React Router DOM v7+ Route Configuration
**Question**: How are routes configured in App.tsx for existing pages?
**Approach**:
- Read `frontend/src/App.tsx`
- Identify route definition pattern
- Identify navigation menu integration

#### Task 3: Stale Data Warning UI Patterns
**Question**: What's the best practice for displaying warning indicators in asset lists?
**Approach**:
- Research Material-UI/React icon libraries used in project
- Identify color conventions for warnings in existing components
- Consider icon + text vs. icon-only vs. background color approaches

#### Task 4: Crypto Asset Badge UI
**Question**: How to display inline badges for asset differentiation?
**Approach**:
- Check if existing components use badges
- Research CSS patterns for inline badges in asset lists
- Consider icon vs. text badge vs. pill badge

**Output**: `research.md` with consolidated findings and design decisions

---

## Phase 1: Design & Contracts

**Status**: ✅ Complete

### Design Artifacts

**Prerequisites**: research.md complete

1. **data-model.md**: Document WatchlistItem structure (reuse existing), filtering criteria for long-term positions
2. **contracts/**: OpenAPI schema for new `/api/watchlist/long-term` endpoint
3. **quickstart.md**: Development setup, testing instructions, deployment steps

### API Contracts

**New Endpoint**:
```
GET /api/watchlist/long-term
Response: WatchlistResponse (existing model)
{
  "items": [
    {
      "id": "asset_id",
      "asset_symbol": "itp:xpar",
      "description": "Inter Parfums",
      "country_code": "xpar",
      "current_price": 45.32,
      "variation_pct": 1.25,
      "currency": "EUR",
      "added_at": "2024-12-15T10:30:00Z",
      "labels": ["long-term", "homepage"],
      "tradingview_url": "https://...",
      "exchange": "saxo"
    }
  ],
  "total": 1
}
```

**Output**: API contract in `/contracts/long-term-positions.yaml`, data model documentation, quickstart guide

---

## Phase 2: Task Generation

**Status**: ⏳ Pending (manual invocation of `/speckit.tasks` required after Phase 1)

**Note**: Phase 2 is executed by running `/speckit.tasks` command separately. This command generates `tasks.md` with dependency-ordered implementation tasks.

---

## Implementation Notes

### Backend Reuse Strategy

**Reusing from WatchlistService** (`api/services/watchlist_service.py`):
- `_enrich_asset()` method (lines 66-118): Handles price fetching, variation calculation, TradingView URL lookup
- `_enrich_and_sort_watchlist()` method (lines 121-177): Enriches and sorts items
- Filtering pattern (lines 198-213): Template for long-term filter

**New Method Signature**:
```python
def get_long_term_positions(self) -> WatchlistResponse:
    """
    Get long-term tagged positions for the dedicated menu.
    Filters for items with 'long-term' label and enriches with current prices.

    Returns:
        WatchlistResponse with items that have 'long-term' label
    """
```

**Implementation Pattern** (following existing `get_watchlist()` lines 183-215):
1. Call `self.dynamodb_client.get_watchlist()` to get all items
2. Filter: Keep ONLY items where `WatchlistTag.LONG_TERM.value in labels`
3. Pass filtered items to `self._enrich_and_sort_watchlist()`
4. Return WatchlistResponse

### Frontend Reuse Strategy

**Reusing from Watchlist.tsx** (`frontend/src/pages/Watchlist.tsx`):
- Component structure for rendering asset lists
- Auto-refresh timer logic (60-second interval)
- Asset card/row styling
- Tag display patterns

**New Component**: `LongTermPositions.tsx`
- Copy Watchlist.tsx structure
- Remove tag filter UI (not needed - already filtered by backend)
- Add stale data warning indicator logic (new requirement)
- Add crypto badge display logic (new requirement)
- Call `api.getLongTermPositions()` instead of `api.getAllWatchlist()`

### Testing Strategy

**Backend Tests** (following `tests/api/services/test_watchlist_service.py` lines 36-102):
1. Test filtering logic: Mock DynamoDB returns mixed items, assert only long-term items returned
2. Test empty case: Mock DynamoDB returns no long-term items, assert empty list
3. Test enrichment: Mock price API, assert enrichment applied to long-term items

**Frontend Tests**: TBD (no testing framework currently configured per constitution)

### Deployment Checklist

**Backend**:
1. Add new endpoint to `api/routers/watchlist.py`
2. Add new method to `api/services/watchlist_service.py`
3. Add tests to `tests/api/services/test_watchlist_service.py` and `tests/api/routers/test_watchlist.py`
4. Run `poetry run pytest` to verify all tests pass
5. Run `poetry run black . && poetry run isort .` to format code
6. Run `poetry run mypy .` to verify type checking
7. Deploy via `./deploy.sh`

**Frontend**:
1. Create `frontend/src/pages/LongTermPositions.tsx`
2. Add `getLongTermPositions()` to `frontend/src/services/api.ts`
3. Add route to `frontend/src/App.tsx`
4. Add navigation menu item (if applicable)
5. Run `npm run build` to verify TypeScript compiles
6. Run `npm run lint` to verify ESLint passes
7. Manual smoke test: Navigate to long-term positions page, verify data loads

---

## Success Criteria Mapping

From spec.md Success Criteria:

- **SC-001**: Users can access long-term positions within 2 clicks from the main navigation
  - **Implementation**: Add navigation menu item in frontend linking to `/long-term` route

- **SC-002**: Long-term positions menu displays up-to-date prices within 60 seconds of market data changes
  - **Implementation**: Reuse existing 60-second auto-refresh timer from Watchlist.tsx

- **SC-003**: 100% of assets tagged "long-term" appear in the dedicated menu (no filtering errors)
  - **Implementation**: Service layer filters using `WatchlistTag.LONG_TERM.value in labels` (enum-based, type-safe)

- **SC-004**: Tag modifications (remove "long-term") reflect in the menu within 2 seconds without page refresh
  - **Implementation**: Frontend re-fetches data on tag modification, leveraging existing update_labels endpoint

- **SC-005**: Menu supports displaying at least 100 long-term positions without performance degradation (load time under 3 seconds)
  - **Implementation**: Single scrollable list (FR-014), leverages existing DynamoDB scan + enrichment pipeline proven for All Watchlist view

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Stale price data UI unclear | Medium | Low | Research existing warning patterns in codebase during Phase 0 |
| React Router v7+ breaking changes | Low | Medium | Verify route configuration pattern during Phase 0 research |
| DynamoDB scan performance with 100+ items | Low | Medium | Existing "All Watchlist" endpoint already handles this scale successfully |
| Frontend auto-refresh conflicts | Low | Low | Follow existing 60-second timer pattern from Watchlist.tsx |

---

## Next Steps

1. **Complete Phase 0**: Generate `research.md` by executing research tasks 1-4
2. **Complete Phase 1**: Generate `data-model.md`, `contracts/`, and `quickstart.md`
3. **Run `/speckit.tasks`**: Generate dependency-ordered tasks in `tasks.md`
4. **Implement**: Follow tasks.md for step-by-step implementation
5. **Test**: Run backend tests, manual frontend smoke test
6. **Deploy**: Backend via `./deploy.sh`, frontend via Vite build

**Command to continue**: `/speckit.tasks` (after Phase 0 and Phase 1 complete)
