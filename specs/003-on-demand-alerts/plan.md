# Implementation Plan: On-Demand Alerts Execution

**Branch**: `003-on-demand-alerts` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-on-demand-alerts/spec.md`

## Summary

Add on-demand alert detection capability to the asset detail page, allowing traders to manually trigger alert analysis for the current asset. This extends the existing scheduled alert detection system (Lambda-based batch processing) with an interactive, per-asset execution model. Users click a "Run Alerts" button, the backend executes detection algorithms (combo, congestion, candle patterns), stores results in DynamoDB, and the frontend refreshes to display new alerts with visual "NEW" badges.

## Technical Context

**Backend:**
- **Language/Version**: Python 3.11+
- **Primary Dependencies**: FastAPI, boto3 (DynamoDB), existing detection services
- **Existing Architecture**:
  - Alert detection in `saxo_order/commands/alerting.py` (batch orchestration)
  - Detection algorithms in `services/indicator_service.py`, `services/congestion_indicator.py`
  - Storage via `client/aws_client.py:DynamoDBClient`
  - API endpoints in `api/routers/alerting.py` (currently read-only GET)
- **New Endpoint**: `POST /api/alerts/run` - triggers on-demand detection for single asset
- **Testing**: Existing pytest framework in `tests/`
- **Deployment**: AWS Lambda (Docker-based), deployed via `./deploy.sh`

**Frontend:**
- **Language/Version**: TypeScript 5+, React 19+
- **Primary Dependencies**: React Router DOM v7+, Axios, Vite 7+
- **Existing Page**: `frontend/src/pages/AssetDetail.tsx` (already has alerts display section from feature 002)
- **API Integration**: Use existing `alertService` in `frontend/src/services/api.ts` (add new `run()` method)
- **Testing**: None currently configured
- **Target Platform**: Web browser (served via Vite dev server on port 5173)

**Data Storage:**
- **DynamoDB Table**: `alerts` (partition key: asset_code, sort key: country_code)
- **TTL**: 7-day automatic expiration
- **Deduplication**: Existing logic in `DynamoDBClient.store_alerts()` (filters same-type, same-day alerts)

**Project Type**: Full-stack feature (backend API + frontend UI)

**Performance Goals**:
- Alert detection completes in <10 seconds for 95% of requests (per success criteria)
- Backend enforces 5-minute cooldown per asset to prevent system overload
- Frontend timeout: 60 seconds maximum wait

**Constraints**:
- Must reuse existing detection logic from `saxo_order/commands/alerting.py` (no algorithm duplication)
- Must maintain layered architecture (API → Service → Client layers)
- Must handle both Saxo (with/without country_code) and Binance assets
- Must preserve existing scheduled alert detection (no interference)
- Backend must enforce cooldown (frontend timer is UI-only, not security boundary)

**Scale/Scope**:
- Expected: 1-5 on-demand executions per user per day
- Maximum: 12 executions per hour per asset (5-minute cooldown)
- Alert detection processes 250 daily candles + 10 hourly candles
- Supports 6 alert types: COMBO, CONGESTION20, CONGESTION100, DOUBLE_TOP, DOUBLE_INSIDE_BAR, CONTAINING_CANDLE

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Layered Architecture Discipline ✅

**Backend:**
- ✅ API Layer: `api/routers/alerting.py` - add POST endpoint, thin orchestration
- ✅ Service Layer: `api/services/alerting_service.py` - add `run_on_demand_detection()` business logic
- ✅ Client Layer: Reuse `client/aws_client.py:DynamoDBClient`, `client/saxo_client.py:SaxoClient`
- ✅ Model Layer: Reuse existing `Alert` dataclass, `AlertType` enum
- ✅ Shared Logic: Extract detection orchestration from `saxo_order/commands/alerting.py` into service layer

**Frontend:**
- ✅ Pages: Modify `frontend/src/pages/AssetDetail.tsx` - add button, loading state, cooldown timer
- ✅ Components: Reuse existing `AlertCard.tsx` (no changes needed)
- ✅ Services: Extend `frontend/src/services/api.ts` - add `alertService.run()` method
- ✅ No direct API calls in components: All API interaction through service layer

**Verdict**: ✅ PASS - Respects layered architecture, no violations

### II. Clean Code First ✅

- ✅ Self-documenting: Reuse existing detection functions with clear names (`combo()`, `double_top()`, etc.)
- ✅ No hardcoded strings: Use existing `AlertType` enum for alert types
- ✅ No over-engineering: Simple orchestration wrapper around existing detection logic
- ✅ No unnecessary comments: Existing patterns are clear

**Verdict**: ✅ PASS - Follows clean code patterns

### III. Configuration-Driven Design ✅

**Backend:**
- ✅ API URL from environment: `VITE_API_URL` (existing pattern)
- ✅ DynamoDB table name: From AWS config (existing pattern)
- ✅ Cooldown period: 5 minutes (spec requirement, can be made configurable in future)
- ✅ Timeout: 60 seconds (spec requirement)

**Frontend:**
- ✅ API endpoint: Uses `import.meta.env.VITE_API_URL` (existing pattern)
- ✅ No hardcoded backend URLs

**Verdict**: ✅ PASS - Uses existing configuration patterns

### IV. Safe Deployment Practices ✅

- ✅ Conventional commits for all changes
- ✅ Backend deploys via `./deploy.sh` (Docker-based Lambda)
- ✅ Infrastructure as code: No manual AWS console changes
- ✅ Frontend builds via `npm run build`

**Verdict**: ✅ PASS - Standard deployment process

### V. Domain Model Integrity ✅

- ✅ Alert model unchanged: Uses existing `Alert` dataclass with `exchange` field
- ✅ Asset identifier parsing: Correctly handles "CODE:COUNTRY" and "SYMBOL" formats (existing `_parse_asset_code()`)
- ✅ No assumptions about country_code: Properly handles null/empty values
- ✅ Exchange field: Alert model already includes explicit `exchange` field (per constitution v1.2.0)
- ✅ Candle ordering: Follows existing convention (index 0 = newest)
- ✅ Saxo API constraints: Reuses existing horizon reconstruction logic

**Verdict**: ✅ PASS - Respects domain model integrity

---

**Overall Constitution Compliance**: ✅ **PASS** - All 5 principles satisfied with no violations

## Project Structure

### Documentation (this feature)

```text
specs/003-on-demand-alerts/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── data-model.md        # Data model documentation (Phase 1)
├── quickstart.md        # User guide (Phase 1)
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Task list (Phase 2 - to be generated)
```

### Source Code (repository root)

```text
# Backend (API + Service Layer)
api/
├── routers/
│   └── alerting.py              # MODIFIED: Add POST /api/alerts/run endpoint
├── services/
│   └── alerting_service.py      # MODIFIED: Add run_on_demand_detection() method
└── models/
    └── alerting.py              # MODIFIED: Add RunAlertsRequest, RunAlertsResponse models

# Backend (Shared Detection Logic)
saxo_order/commands/
└── alerting.py                  # MODIFIED: Extract detection orchestration into reusable function

# Frontend (UI + API Client)
frontend/src/
├── pages/
│   ├── AssetDetail.tsx          # MODIFIED: Add "Run Alerts" button, loading/cooldown state
│   └── AssetDetail.css          # MODIFIED: Add button and status message styles
└── services/
    └── api.ts                   # MODIFIED: Add alertService.run() method

# No changes to existing files:
# - client/aws_client.py (DynamoDB client already has store_alerts())
# - client/saxo_client.py (already has get_historical_data())
# - services/indicator_service.py (detection algorithms unchanged)
# - services/congestion_indicator.py (detection algorithms unchanged)
# - model/__init__.py (Alert dataclass unchanged)
```

**Structure Decision**: Full-stack enhancement. Backend adds new API endpoint that orchestrates existing detection logic. Frontend adds interactive button with loading states. All storage reuses existing DynamoDB patterns with deduplication.

## Complexity Tracking

**No violations** - Constitution Check passed completely. No complexity justifications needed.

**Simplifications Made**:
- Leveraged existing detection algorithms (no code duplication)
- Reused DynamoDB storage patterns with existing deduplication logic
- Extended existing API service patterns (FastAPI dependency injection)
- Used existing asset symbol parsing logic (`_parse_asset_code()`)
- Followed existing AssetDetail.tsx patterns (button placement, loading states)

## Implementation Phases

### Phase 0: Research ✅ COMPLETED

**Status**: ✅ Skipped - No research needed

**Rationale**: Complete understanding achieved through codebase exploration:
- Alert detection architecture fully documented
- Existing detection algorithms located in `services/` directory
- DynamoDB storage patterns understood (`client/aws_client.py`)
- Frontend integration patterns clear from feature 002-asset-detail-alerts
- No unknowns require external research

**Artifacts**:
- ❌ `research.md` - Not created (no unknowns to resolve)
- ✅ Codebase exploration completed via Explore agent

---

### Phase 1: Design & Contracts ⏸️ NOT STARTED

**Status**: ⏸️ Next Phase

**Objectives**:
1. Document on-demand execution data model (request/response structures) ✅
2. Create API contract for POST /api/alerts/run endpoint ✅
3. Create quickstart guide for using on-demand alerts ✅

**Artifacts to Create**:
1. ✅ `data-model.md` - On-demand execution request/response models
2. ✅ `contracts/run-alerts.yaml` - OpenAPI spec for POST endpoint
3. ✅ `quickstart.md` - User guide for on-demand execution

---

### Phase 2: Implementation Planning

**Status**: ⏸️ Not Started

**Objectives**:
1. Create detailed task list in `tasks.md`
2. Break down backend API, service, and CLI refactoring steps
3. Break down frontend button, loading states, and cooldown timer steps
4. Define testing approach (manual testing checklist, pytest for backend)

**Next Command**: `/speckit.tasks` to generate implementation task list

---

## Architecture Decisions

### AD-001: Cooldown Enforcement (Backend vs Frontend)

**Decision**: Backend enforces cooldown via DynamoDB, frontend displays timer for UX

**Rationale**:
- Backend validation prevents abuse (frontend timer can be bypassed via browser devtools)
- Store last execution timestamp in DynamoDB `alerts` table (add `last_run_at` field)
- Frontend fetches `next_allowed_at` from API response to display countdown
- If user attempts execution during cooldown, backend returns 429 Too Many Requests

**Alternatives Considered**:
- Frontend-only enforcement: Rejected - not a security boundary, can be bypassed
- In-memory cooldown tracking: Rejected - loses state on Lambda cold starts
- Redis cache: Rejected - adds infrastructure complexity, DynamoDB sufficient

### AD-002: Detection Logic Reuse Strategy

**Decision**: Extract detection orchestration from `saxo_order/commands/alerting.py` into service layer

**Rationale**:
- Current batch logic in CLI command (not reusable from API endpoint)
- Service layer function `run_detection_for_asset()` can be called from both CLI and API
- No algorithm duplication (DRY principle)
- Maintains layered architecture (API → Service → Client)

**Alternatives Considered**:
- Duplicate detection logic in API service: Rejected - violates DRY, maintenance nightmare
- Call CLI command from API: Rejected - wrong layer dependency, CLI is presentation layer
- Create separate detection service class: Rejected - over-engineering for single-asset use case

### AD-003: API Endpoint Design

**Decision**: `POST /api/alerts/run` with request body containing asset details

**Rationale**:
- POST semantically correct (creates/triggers resource, not idempotent)
- Request body allows explicit asset_code, country_code, exchange parameters
- Response includes execution status, new alerts count, next_allowed_at timestamp
- Consistent with RESTful patterns

**Request Example**:
```json
POST /api/alerts/run
{
  "asset_code": "ITP",
  "country_code": "xpar",
  "exchange": "saxo"
}
```

**Response Example**:
```json
{
  "status": "success",
  "alerts_detected": 2,
  "alerts": [...],
  "execution_time_ms": 3452,
  "message": "Detected 2 new alerts",
  "next_allowed_at": "2026-01-12T15:35:00Z"
}
```

**Alternatives Considered**:
- GET endpoint: Rejected - GET should not trigger side effects (alert detection/storage)
- WebSocket: Rejected - over-engineering, HTTP long polling sufficient for 10s timeout
- Query parameters instead of body: Rejected - POST body more semantic for action triggers

### AD-004: Loading State UI Pattern

**Decision**: Disabled button with spinner + loading message, auto-refresh alerts section

**Rationale**:
- Spec requirement (FR-005, FR-006): Loading indicator and button state change
- Matches existing patterns in AssetDetail.tsx (indicators, workflows loading states)
- Cooldown timer prevents confusion ("why is button disabled?")
- Auto-refresh avoids manual page reload

**Alternatives Considered**:
- Modal overlay: Rejected - blocks entire page, overkill for 10s operation
- Toast notification only: Rejected - doesn't communicate ongoing process clearly
- Separate loading section: Rejected - clutters UI, button state change sufficient

### AD-005: "NEW" Badge Display Strategy

**Decision**: Frontend tracks newly detected alert IDs in component state for 60 seconds

**Rationale**:
- Spec requirement (FR-013): Highlight new alerts visually
- Backend doesn't need to track "new" state (frontend-only concern)
- Use `setTimeout()` to remove badge after 60 seconds
- Store new alert IDs in `useState<Set<string>>()` for quick lookup

**Alternatives Considered**:
- Backend timestamp: Rejected - adds complexity, frontend can handle with component state
- Permanent badge: Rejected - contradicts spec (60-second duration)
- CSS animation: Rejected - needs JS timer anyway to remove badge, state cleaner

## File Changes Summary

### New Files (2 docs)

1. **`specs/003-on-demand-alerts/data-model.md`** (~150 lines)
   - Purpose: Document on-demand execution data structures
   - Content: Request/response models, cooldown tracking, state transitions

2. **`specs/003-on-demand-alerts/contracts/run-alerts.yaml`** (~80 lines)
   - Purpose: OpenAPI specification for POST /api/alerts/run
   - Content: Request schema, response schemas (success/error), status codes

3. **`specs/003-on-demand-alerts/quickstart.md`** (~60 lines)
   - Purpose: User guide for on-demand alerts
   - Content: How to trigger, what to expect, cooldown behavior, troubleshooting

### Modified Files (Backend: 3)

1. **`api/routers/alerting.py`** (+~40 lines)
   - Add: `POST /api/alerts/run` endpoint
   - Add: Cooldown validation (check `last_run_at`, return 429 if too soon)
   - Add: Dependency injection for `AlertingService`

2. **`api/services/alerting_service.py`** (+~120 lines)
   - Add: `run_on_demand_detection(asset_code, country_code, exchange)` method
   - Add: Cooldown check logic (query DynamoDB for `last_run_at`)
   - Add: Detection orchestration (calls extracted service function)
   - Add: Response construction (status, alerts_detected, next_allowed_at)

3. **`saxo_order/commands/alerting.py`** (refactor, ~50 lines changed)
   - Extract: `run_detection_for_asset(asset_code, country_code, exchange, candles_service, indicator_service, congestion_service, dynamodb_client)` function
   - Modify: `run_alerting()` to call extracted function (reduce duplication)
   - No new functionality, just refactoring for reusability

4. **`api/models/alerting.py`** (+~30 lines)
   - Add: `RunAlertsRequest` Pydantic model
   - Add: `RunAlertsResponse` Pydantic model

### Modified Files (Frontend: 3)

1. **`frontend/src/pages/AssetDetail.tsx`** (+~150 lines)
   - Add: `runAlertsLoading` state (boolean)
   - Add: `runAlertsError` state (string | null)
   - Add: `runAlertsSuccess` state (string | null, auto-clears after 3s)
   - Add: `nextAllowedAt` state (Date | null, for cooldown timer)
   - Add: `newAlertIds` state (Set<string>, tracks newly detected alerts)
   - Add: `handleRunAlerts()` function (calls API, handles response)
   - Add: Cooldown timer countdown display
   - Add: "Run Alerts" button JSX in alerts section
   - Add: Success/error message display (3-second toast)

2. **`frontend/src/pages/AssetDetail.css`** (+~60 lines)
   - Add: `.run-alerts-btn` styles (matches existing button patterns)
   - Add: `.run-alerts-btn:disabled` styles
   - Add: `.alert-status-message` styles (success/error messages)
   - Add: `.cooldown-timer` styles
   - Add: `.alert-badge-new` styles (for "NEW" badge on alerts)

3. **`frontend/src/services/api.ts`** (+~20 lines)
   - Add: `run(asset_code, country_code, exchange)` method to `alertService`
   - Returns: `Promise<RunAlertsResponse>`

### Unchanged Files (Existing Infrastructure)

- ✅ `client/aws_client.py` - `DynamoDBClient.store_alerts()` already handles deduplication
- ✅ `client/saxo_client.py` - `get_historical_data()` already fetches candles
- ✅ `services/indicator_service.py` - Detection algorithms reused as-is
- ✅ `services/congestion_indicator.py` - Congestion detection reused as-is
- ✅ `model/__init__.py` - `Alert` dataclass unchanged
- ✅ `frontend/src/components/AlertCard.tsx` - Reused without changes

**Total LOC Impact**: ~470 lines added (370 backend+frontend code, 100 docs), 50 lines refactored

## Next Steps

1. ✅ Complete Phase 1: Generate `data-model.md`, `contracts/run-alerts.yaml`, `quickstart.md`
2. ⏭️ Run `/speckit.tasks` to generate detailed task list in `tasks.md`
3. ⏭️ Run `/speckit.implement` to execute tasks from task list
4. ⏭️ Manual testing against spec success criteria
5. ⏭️ Create commit following conventional commit format

**Ready for**: Phase 1 design artifacts generation
