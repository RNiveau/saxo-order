# Implementation Plan: SLWIN Tag for Watchlist

**Branch**: `007-slwin-tag` | **Date**: 2026-02-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-slwin-tag/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a new SLWIN (Stop Loss Win) tag to the watchlist system that is mutually exclusive with the short-term tag. SLWIN-tagged assets appear in the sidebar between short-term and untagged assets, with backend enforcement of all mutual exclusivity rules using last-write-wins concurrency strategy. The feature includes a toggle button on the asset detail page and overrides crypto exclusion rules for SLWIN-tagged assets.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ (frontend)
**Primary Dependencies**: FastAPI (backend API), React 19+ (frontend), Vite 7+ (frontend build), DynamoDB (storage)
**Storage**: AWS DynamoDB (watchlist table with labels attribute)
**Testing**: pytest (backend), no frontend testing framework currently
**Target Platform**: AWS Lambda (backend), Web browsers (frontend)
**Project Type**: Web application (React frontend + FastAPI backend)
**Performance Goals**: <2 seconds for tag toggle operations, instant sidebar updates
**Constraints**: Backend enforces all business rules, last-write-wins for concurrent updates
**Scale/Scope**: Single new tag, ~5 files modified (backend models, service, API router, frontend components)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Layered Architecture Discipline ✅

- **Backend layers respected**:
  - Models (`api/models/watchlist.py`): Add SLWIN to WatchlistTag enum
  - Service (`api/services/watchlist_service.py`): Enforce mutual exclusivity, update sorting logic
  - API Router (`api/routers/watchlist.py`): Expose tag update endpoints (already exist)
  - No violations: Service uses client methods, no direct DynamoDB access

- **Frontend layers respected**:
  - Components (`frontend/src/components/Sidebar.tsx`): Display SLWIN section with divider
  - Pages (`frontend/src/pages/AssetDetail.tsx`): Add SLWIN toggle button
  - Services (`frontend/src/services/api.ts`): Use existing watchlist service methods
  - No violations: All API calls through service layer

### Clean Code First ✅

- Uses existing `WatchlistTag` enum (add SLWIN value)
- No hardcoded strings for tag values
- Self-documenting: SLWIN constant clearly identifies "Stop Loss Win" in comments
- Minimal code changes: extends existing patterns

### Configuration-Driven Design ✅

- No new configuration required
- Uses existing DynamoDB watchlist table structure
- Frontend uses existing `VITE_API_URL` configuration
- No API endpoints or credentials to configure

### Safe Deployment Practices ✅

- No infrastructure changes required (DynamoDB table already supports arbitrary labels)
- Standard deployment via `./deploy.sh` after code changes
- Conventional commit format: `feat: add SLWIN tag to watchlist`

### Domain Model Integrity ✅

- Assets already include explicit `exchange` field (Saxo/Binance)
- SLWIN tag stored as string in `labels` array (existing DynamoDB structure)
- Backend enforces mutual exclusivity (no frontend validation)
- Sorting logic update maintains existing Candle ordering conventions (not applicable to this feature)

**Constitution Check Result**: ✅ PASS - All principles satisfied, no violations to justify

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Backend (Python)
api/
├── models/
│   └── watchlist.py                # Add SLWIN to WatchlistTag enum
├── services/
│   └── watchlist_service.py        # Update sorting logic, enforce mutual exclusivity
└── routers/
    └── watchlist.py                # Existing endpoints used (no changes)

# Frontend (React + TypeScript)
frontend/src/
├── components/
│   └── Sidebar.tsx                 # Update sorting, add SLWIN divider
├── pages/
│   └── AssetDetail.tsx             # Add SLWIN toggle button
└── services/
    └── api.ts                      # Use existing watchlist service methods

# Tests
tests/api/
├── models/
│   └── test_watchlist.py           # Verify SLWIN enum value
├── services/
│   └── test_watchlist_service.py   # Test mutual exclusivity, sorting
└── routers/
    └── test_watchlist.py           # Test API enforcement
```

**Structure Decision**: Web application structure with Python backend and React frontend. This is an extension to the existing watchlist feature, so we modify existing files rather than creating new modules. Backend follows service layer pattern with DynamoDB storage. Frontend follows component-based architecture with centralized API service layer.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - Constitution check passed without issues.

## Phase 0: Research (Complete)

**Output**: `research.md`

**Key Decisions**:
1. Backend tag enforcement using service layer filtering
2. Last-write-wins concurrency strategy (DynamoDB native)
3. Extended sort_key function with 3-priority tuple sorting
4. SLWIN overrides crypto exclusion (like short-term does)
5. Reuse existing tag button styles with new `.slwin-btn` class
6. Add divider between SLWIN and untagged sections

**Status**: ✅ All unknowns resolved, ready for Phase 1

## Phase 1: Design & Contracts (Complete)

**Outputs**:
- `data-model.md` - Entity changes, business rules, state transitions
- `contracts/watchlist-slwin.yaml` - API contract documentation
- `quickstart.md` - Implementation guide with code examples
- `CLAUDE.md` - Updated with feature technologies

**Key Artifacts**:
1. **Data Model**: WatchlistTag enum extended, sorting algorithm defined, mutual exclusivity rules documented
2. **API Contract**: OpenAPI spec with examples, business rules documented as x-extensions
3. **Quickstart Guide**: 7-phase implementation checklist with code snippets, testing scenarios, troubleshooting

**Agent Context Updated**: ✅ CLAUDE.md updated with Python 3.11, TypeScript 5+, FastAPI, React 19+, Vite 7+, DynamoDB

**Status**: ✅ All design artifacts complete, ready for Phase 2 (tasks)

## Final Constitution Check (Post-Design)

**Re-evaluation after design phase**:

### Layered Architecture Discipline ✅
- Backend: Service layer handles business logic (mutual exclusivity, sorting)
- Backend: No client internals accessed (uses DynamoDB client methods)
- Frontend: All API calls through `watchlistService` in `services/api.ts`
- Frontend: Components receive data via props, emit events via callbacks

### Clean Code First ✅
- Uses WatchlistTag enum (no hardcoded "slwin" strings)
- Self-documenting: clear variable names (`isSLWIN`, `handleToggleSLWIN`)
- No unnecessary comments in implementation plan

### Configuration-Driven Design ✅
- No new configuration required
- Uses existing DynamoDB table structure
- Frontend uses existing `VITE_API_URL`

### Safe Deployment Practices ✅
- Standard deployment via `./deploy.sh`
- Conventional commit format specified in quickstart
- No manual AWS console changes

### Domain Model Integrity ✅
- Backend enforces business rules (mutual exclusivity)
- Explicit `exchange` field used (not inferred from country_code)
- Tag values match enum definitions

**Final Result**: ✅ PASS - No violations introduced during design

## Implementation Readiness

**Ready for `/speckit.tasks`**: ✅ Yes

**Artifacts Complete**:
- [x] plan.md (this file)
- [x] research.md
- [x] data-model.md
- [x] contracts/watchlist-slwin.yaml
- [x] quickstart.md
- [x] CLAUDE.md updated

**Next Command**: `/speckit.tasks` to generate task breakdown
