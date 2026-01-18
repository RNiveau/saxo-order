# Implementation Plan: Alerts UI Page

**Branch**: `001-alerts-ui-page` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-alerts-ui-page/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a web UI page to display all active alerts (7-day retention) that are currently only sent to Slack. The alerts are already being generated daily by the existing alerting system and stored in DynamoDB with TTL-based automatic expiration. This feature exposes them through REST API endpoints and renders them in a React-based frontend page with filtering and sorting capabilities. Alerts can be sorted by MA50 slope (default) or by date, helping traders prioritize assets with strongest trends.

## Technical Context

**Backend:**
- **Language/Version**: Python 3.11
- **Primary Dependencies**: FastAPI, Pydantic, boto3 (DynamoDB client)
- **Storage**: DynamoDB table `alerts` with TTL enabled (7-day automatic expiration)
- **Testing**: pytest with unittest.mock for DynamoDB operations
- **Target Platform**: AWS Lambda (existing deployment) + Local uvicorn development

**Frontend:**
- **Language/Version**: TypeScript 5+, React 19+
- **Primary Dependencies**: React Router DOM v7+, Axios, Vite 7+
- **Testing**: None currently configured
- **Target Platform**: Web browser (served via Vite dev server on port 5173)

**Project Type**: Web application (backend FastAPI + frontend React)
**Performance Goals**:
- API response time <2 seconds for retrieving all alerts (up to 500 alerts)
- Page load time <2 seconds including API call
- Support pagination for 50+ alerts

**Constraints**:
- Must integrate with existing DynamoDB table structure (`asset_code` + `country_code` keys)
- Must respect existing `Alert` dataclass model (alert_type, date, data, asset_code, country_code)
- Must follow layered architecture (API Router → AlertingService → DynamoDBClient → DynamoDB)
- TTL-based expiration handled by DynamoDB (no application-level deletion logic)

**Scale/Scope**:
- ~50-100 assets monitored daily
- Up to 6 alert types per asset per day
- Maximum ~600 alerts stored at any time (50-100 assets × 6 alerts × 7 days retention)
- Single user (trader) access pattern

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Layered Architecture Discipline ✅

**Backend:**
- ✅ API Layer: New `api/routers/alerting.py` with FastAPI router - thin orchestration only
- ✅ Service Layer: New `api/services/alerting_service.py` with business logic (formatting, filtering)
- ✅ Client Layer: Existing `client/aws_client.py` DynamoDBClient - no changes needed
- ✅ Model Layer: Existing `model/__init__.py` Alert dataclass - no changes needed
- ✅ Dependency injection: AlertingService receives DynamoDBClient as constructor parameter

**Frontend:**
- ✅ Pages: New `frontend/src/pages/Alerts.tsx` with routing - no direct API calls
- ✅ Components: New `frontend/src/components/AlertCard.tsx` for alert display
- ✅ Services: Use existing `frontend/src/services/api.ts` - add alertService methods
- ✅ TypeScript interfaces match backend Pydantic models (AlertResponse, AlertItemResponse)

**Verdict**: ✅ PASS - All layers properly separated with correct dependency flow

### II. Clean Code First ✅

- ✅ Self-documenting: Use AlertType enum from `model/enum.py` (6 types: CONGESTION20, COMBO, etc.)
- ✅ No hardcoded strings: Alert types reference enum values
- ✅ No over-engineering: Simple GET endpoints, no caching/WebSocket complexity
- ✅ No unnecessary comments: Code structure follows existing patterns (watchlist module)

**Verdict**: ✅ PASS - Follows clean code standards with enum-driven design

### III. Configuration-Driven Design ✅

**Backend:**
- ✅ DynamoDB table name from `config.yml` (already configured: `alerts` table)
- ✅ AWS credentials from environment/secrets.yml (existing configuration)
- ✅ No hardcoded endpoints or magic numbers

**Frontend:**
- ✅ API URL from `import.meta.env.VITE_API_URL` (existing pattern)
- ✅ No hardcoded backend endpoints in components

**API:**
- ✅ CORS origins already configured in `api/main.py` (localhost:3000, localhost:5173)

**Verdict**: ✅ PASS - No new configuration needed, uses existing setup

### IV. Safe Deployment Practices ✅

- ✅ No infrastructure changes required (alerts table already exists)
- ✅ No Lambda function changes (alerting workflow unchanged)
- ✅ API changes deploy via `./deploy.sh` (standard process)
- ✅ Frontend builds via `npm run build` in frontend directory
- ✅ Conventional commits for all changes

**Verdict**: ✅ PASS - Uses existing deployment processes

### V. Domain Model Integrity ✅

- ✅ Alert model unchanged: Uses existing `Alert` dataclass from `model/__init__.py`
- ✅ Alert.id property preserved: Composite key `asset_code_country_code`
- ✅ Optional country_code respected: Handles None values correctly
- ✅ No raw DynamoDB responses exposed: Service layer transforms to Pydantic models

**Verdict**: ✅ PASS - Respects existing domain model conventions

---

**Overall Constitution Compliance**: ✅ **PASS** - All 5 principles satisfied with no violations

## Project Structure

### Documentation (this feature)

```text
.specify/specs/001-alerts-ui-page/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (skipped - no research needed)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── alerts-api.yaml  # OpenAPI specification
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
# Backend (API + Services)
api/
├── routers/
│   └── alerting.py           # NEW: AlertingRouter with GET endpoints
├── services/
│   └── alerting_service.py   # NEW: AlertingService (business logic)
├── models/
│   └── alerting.py           # NEW: Pydantic models (AlertResponse, AlertItemResponse)
└── main.py                   # MODIFIED: Register alerting router

# Client Layer (unchanged - existing DynamoDB client)
client/
└── aws_client.py             # EXISTING: DynamoDBClient.get_all_alerts()

# Model Layer (unchanged - existing Alert dataclass)
model/
├── __init__.py               # EXISTING: Alert dataclass
└── enum.py                   # EXISTING: AlertType enum

# Frontend
frontend/src/
├── pages/
│   └── Alerts.tsx            # NEW: Alerts page component
├── components/
│   └── AlertCard.tsx         # NEW: Individual alert display component
├── services/
│   └── api.ts                # MODIFIED: Add alertService methods
└── App.tsx                   # MODIFIED: Add /alerts route

# Tests
tests/api/services/
└── test_alerting_service.py  # NEW: AlertingService unit tests
tests/api/routers/
└── test_alerting.py          # NEW: AlertingRouter integration tests
```

**Structure Decision**: Web application structure. Backend uses existing DynamoDB client and Alert model, adds API layer (router + service + Pydantic models) to expose alerts. Frontend adds new page and component, extends existing API service. No changes to data storage or alert generation logic.

## Complexity Tracking

**No violations** - Constitution Check passed completely. No complexity justifications needed.

## Implementation Phases

### Phase 0: Research ✅ COMPLETED

**Status**: ✅ Skipped - No research needed

**Rationale**: Complete understanding of existing alert system achieved through codebase exploration:
- Alert generation system (`saxo_order/commands/alerting.py`)
- DynamoDB storage structure (`pulumi/dynamodb.py`)
- Alert domain model (`model/__init__.py`, `model/enum.py`)
- DynamoDB client (`client/aws_client.py`)

**Artifacts**:
- ❌ `research.md` - Not created (no unknowns to resolve)
- ✅ Codebase exploration completed via Task agent

---

### Phase 1: Design & Contracts ✅ COMPLETED

**Status**: ✅ All artifacts generated

**Artifacts Created**:
1. ✅ `data-model.md` - Complete data model documentation
   - Existing domain models (Alert, AlertType)
   - DynamoDB storage model (unchanged)
   - New API models (Pydantic)
   - New frontend models (TypeScript interfaces)
   - Data flow diagrams
   - Validation rules

2. ✅ `contracts/alerts-api.yaml` - OpenAPI 3.0 specification
   - Endpoint: `GET /api/alerts`
   - Query parameters: asset_code, alert_type, country_code
   - Response schemas: AlertsResponse, AlertItemResponse
   - Error responses: 400, 401, 503

3. ✅ `quickstart.md` - Developer guide
   - Backend development workflow
   - Frontend development workflow
   - Testing procedures
   - Troubleshooting guide
   - Deployment instructions

**API Contract Summary**:

| Endpoint | Method | Purpose | Query Params |
|----------|--------|---------|--------------|
| `/api/alerts` | GET | Get all alerts with optional filtering | asset_code, alert_type, country_code |

**Data Models**:

| Layer | Model | Purpose |
|-------|-------|---------|
| Domain | Alert (dataclass) | Existing - no changes |
| API | AlertItemResponse (Pydantic) | Single alert response |
| API | AlertsResponse (Pydantic) | Collection with filters |
| Frontend | AlertItem (TypeScript) | Component props interface |
| Frontend | AlertsResponse (TypeScript) | API response interface |

---

### Phase 2: Implementation Planning (Tasks Generation)

**Status**: ⏭️ Ready for `/speckit.tasks` command

**What happens next**:
- Run `/speckit.tasks` to generate `tasks.md`
- Tasks will be dependency-ordered
- Each task includes acceptance criteria
- Implementation follows task order

**Expected Task Categories**:
1. Backend API Layer (3-4 tasks)
   - Create Pydantic models
   - Create AlertingService
   - Create AlertingRouter
   - Register router in main.py

2. Backend Testing (2-3 tasks)
   - Write service unit tests
   - Write router integration tests

3. Frontend (3-4 tasks)
   - Extend API service
   - Create AlertCard component
   - Create Alerts page
   - Add route to App.tsx

4. Integration & Polish (1-2 tasks)
   - End-to-end testing
   - Add navigation link
   - Style components

**Total Estimated Tasks**: 9-13 tasks

---

## Architecture Decisions

### Decision 1: No Real-Time Updates

**Context**: Spec originally included P2 user story for real-time updates (auto-refresh every 60 seconds)

**Decision**: User removed P2 story - manual page refresh only

**Rationale**:
- Simpler implementation (no polling, no WebSocket)
- Alerts generated daily at 6:15 PM - low update frequency
- Manual refresh acceptable for single-user application
- Can add later if needed without architectural changes

**Trade-offs**:
- ✅ Simpler: No polling logic, no state management for background updates
- ✅ Faster: One less requirement to implement
- ❌ User Experience: Must manually refresh to see new alerts

### Decision 2: Client-Side Filtering

**Context**: Filtering alerts by asset_code and alert_type

**Decision**: Hybrid approach - backend supports query params but frontend does client-side filtering after initial load

**Rationale**:
- Small data volume (~100-150 alerts max)
- Single user application
- Reduces API calls (fetch once, filter locally)
- Backend query params support future pagination or server-side filtering

**Trade-offs**:
- ✅ Performance: Instant filtering (no network latency)
- ✅ Simplicity: No complex backend query logic
- ✅ Flexibility: Easy to add more filter types without backend changes
- ⚠️ Scalability: Won't work if alert volume grows to thousands (not expected)

### Decision 3: DynamoDB Scan (No Secondary Index)

**Context**: Retrieving all alerts requires full table scan

**Decision**: Use full table scan with `get_all_alerts()` - no DynamoDB secondary index

**Rationale**:
- Small table size (~100-150 items total)
- Single user, low query frequency
- TTL handles expiration automatically
- Scan operation fast enough (<500ms for 150 items)
- No need for complex query patterns

**Trade-offs**:
- ✅ Simple: No index management, no additional AWS costs
- ✅ Fast enough: Acceptable performance for current scale
- ❌ Scalability: Would need GSI if table grows to 10K+ items (not expected)
- ✅ Cost: Scan uses fewer read capacity units than multiple queries

### Decision 4: Alert Data Payload as Generic Dict

**Context**: Alert.data structure varies by alert_type (6 different schemas)

**Decision**: Keep `data: Dict[str, Any]` generic - no type-specific models

**Rationale**:
- Alert types have different data structures
- Frontend displays raw JSON (dev/debug use case)
- Creating 6 separate Pydantic models adds complexity
- Data structure defined by alert generation system (stable)

**Trade-offs**:
- ✅ Simple: Single AlertItemResponse model for all types
- ✅ Flexible: Easy to add new alert types without API changes
- ❌ Type Safety: Frontend doesn't have typed access to data fields
- ⚠️ Validation: No runtime validation of data payload structure

### Decision 5: No Pagination (Initial Version)

**Context**: Spec requires pagination for 50+ alerts

**Decision**: Implement pagination in Phase 2 (implementation) rather than design phase

**Rationale**:
- Pagination logic is implementation detail (not architectural)
- Client-side pagination sufficient for current scale
- API already returns all data needed
- Can add without contract changes

**Implementation Note**:
- Display 50 alerts per page (client-side pagination)
- "Next/Previous" buttons in frontend
- No backend API changes required

### Decision 6: MA50 Slope Sorting (Default Sort Order)

**Context**: User Story 3 requires sorting alerts by MA50 slope to prioritize strongest trends

**Decision**: Calculate and store ma50_slope for ALL alert types during alert generation, make MA50 slope the default sort order (descending)

**Rationale**:
- MA50 slope indicates trend strength - helps traders prioritize assets with strongest momentum
- Slope calculation already exists in `indicator_service.py` (slope_percentage function)
- Calculating at generation time avoids on-demand computation overhead
- All alert types benefit from trend context (not just COMBO alerts)
- Sort by actual slope value (not absolute value) - positive slopes prioritized over negative

**Implementation**:
- Backend: Add ma50_slope calculation to all alert detection functions in `saxo_order/commands/alerting.py`
- Backend: Store ma50_slope in alert.data dict for all alert types
- Frontend: Default sort by ma50_slope descending (highest slope first)
- Frontend: Provide sort dropdown with "MA50 Slope" (default) and "Recent" options
- Handle null/missing slopes as 0 for sorting

**Trade-offs**:
- ✅ Better UX: Traders see most urgent assets first by default
- ✅ Performance: Pre-calculated slopes avoid runtime computation
- ✅ Consistency: All alerts have trend context
- ⚠️ Storage: Adds ~8 bytes per alert (float64) - negligible impact
- ⚠️ Computation: Adds ~5ms per alert generation (acceptable)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| DynamoDB TTL delay (48h max) | Medium | Low | Accept - edge case, non-critical |
| Alert data structure changes | Low | Medium | Monitor alert generation code for changes |
| AWS service outage | Low | High | Add retry logic, display user-friendly error |
| Frontend-backend type mismatch | Medium | Medium | Add integration tests, validate responses |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| No alerts in DynamoDB (empty table) | Medium | Low | Display helpful "waiting for alerts" message |
| Alerting Lambda fails | Low | Medium | Existing Slack monitoring alerts to failures |
| CORS misconfiguration | Medium | Low | Test locally before deploying |

---

## Performance Targets

**Backend API** (`GET /api/alerts`):
- ✅ Target: <2 seconds for 500 alerts
- ✅ Expected: ~500ms for 150 alerts (typical case)
- ✅ DynamoDB scan: 1MB per page, auto-pagination

**Frontend Page Load**:
- ✅ Target: <2 seconds total (including API call)
- ✅ Expected: ~800ms (500ms API + 300ms render)
- ✅ Filtering: Instant (<50ms client-side)

**Data Volume**:
- ✅ Current: ~50-100 assets × 1-2 alerts avg = 100-150 alerts
- ✅ Maximum: 100 assets × 6 alert types = 600 alerts (worst case)
- ✅ Retention: 7 days automatic expiration

**API Response Size**:
- ✅ Single alert: ~200-500 bytes (varies by data payload)
- ✅ Typical response: ~30-50 KB (150 alerts)
- ✅ Maximum response: ~200-300 KB (600 alerts worst case)

---

## Testing Strategy

### Backend Testing

**Unit Tests** (`tests/api/services/test_alerting_service.py`):
- AlertingService.get_all_alerts() with no filters
- AlertingService.get_all_alerts() with asset_code filter
- AlertingService.get_all_alerts() with alert_type filter
- AlertingService.get_all_alerts() with country_code filter
- AlertingService._to_response() transformation logic
- AlertingService._calculate_filters() with various alert combinations
- Edge case: Empty alert list
- Edge case: Alerts with missing country_code (crypto assets)

**Coverage Target**: 100% for AlertingService (8 tests)

**Integration Tests** (`tests/api/routers/test_alerting.py`):
- GET /api/alerts returns 200 with valid schema
- GET /api/alerts?asset_code=ITP filters correctly
- GET /api/alerts?alert_type=combo filters correctly
- GET /api/alerts with invalid alert_type returns 400
- GET /api/alerts with DynamoDB unavailable returns 503
- Response matches OpenAPI schema

**Coverage Target**: All endpoints and error cases (6 tests)

### Frontend Testing

**Status**: No testing framework configured (TBD)

**Manual Testing Checklist**:
- [ ] Page loads without errors
- [ ] Alerts display correctly (asset, type, timestamp, data)
- [ ] Filter by asset code works
- [ ] Filter by alert type works
- [ ] Filter counts update correctly
- [ ] "Clear filters" button works
- [ ] Empty state displays when no alerts
- [ ] Error state displays on API failure
- [ ] Loading state displays during fetch
- [ ] Timestamps display in local timezone
- [ ] Alert cards are styled correctly
- [ ] Mobile responsive layout works

### End-to-End Testing

**Smoke Test**:
1. Start backend: `poetry run python run_api.py`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to: http://localhost:5173/alerts
4. Verify: Alerts load and display correctly
5. Test: Apply filter, verify results update
6. Test: Clear filter, verify all alerts return

**Pre-Deployment Checklist**:
- [ ] All backend tests pass: `poetry run pytest`
- [ ] Backend API accessible: `curl http://localhost:8000/api/alerts`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Frontend displays alerts in production build
- [ ] CORS configured for production frontend URL
- [ ] DynamoDB table has test data

---

## Deployment Plan

### Prerequisites

- ✅ DynamoDB table `alerts` exists (no changes needed)
- ✅ Alerting Lambda running (no changes needed)
- ✅ AWS credentials configured
- ✅ Backend API server deployed

### Backend Deployment Steps

```bash
# 1. Run tests
poetry run pytest

# 2. Build and deploy
./deploy.sh

# 3. Verify deployment
curl https://your-api-url.com/api/alerts

# 4. Check CloudWatch logs
aws logs tail /aws/lambda/api_lambda --follow
```

### Frontend Deployment Steps

```bash
# 1. Update environment
echo "VITE_API_URL=https://your-api-url.com" > frontend/.env.production

# 2. Build
cd frontend
npm run build

# 3. Deploy dist/ folder
# (Deploy to Vercel, Netlify, S3, or your hosting provider)

# 4. Verify
curl https://your-frontend-url.com/alerts
```

### Rollback Plan

**Backend**: Redeploy previous Docker image from ECR
**Frontend**: Revert to previous dist/ build on hosting provider
**Risk**: Low - feature is additive (no breaking changes to existing code)

---

## Success Metrics

**Feature Adoption**:
- ✅ User visits /alerts page at least once per week
- ✅ User uses filters to find specific alerts
- ✅ Reduces need to check Slack for alert history

**Technical Performance**:
- ✅ API response time <2 seconds (99th percentile)
- ✅ Page load time <2 seconds (99th percentile)
- ✅ Zero API errors under normal load
- ✅ 100% test coverage for AlertingService

**User Satisfaction**:
- ✅ All alerts from Slack visible in UI (100% match)
- ✅ Timestamp accuracy within 1 minute
- ✅ Filters work without false positives/negatives
- ✅ No complaints about missing alerts or slow performance

---

## Future Enhancements (Out of Scope)

These features are explicitly out of scope for the initial implementation but may be considered later:

1. **Real-Time Updates**: Auto-refresh every 60 seconds (removed from spec)
2. **Push Notifications**: Browser notifications for new alerts
3. **Alert Acknowledgement**: Mark alerts as "seen" or "acted upon"
4. **Alert Details Modal**: Detailed view with formatted data (vs raw JSON)
5. **Historical Trends**: Charts showing alert frequency over time
6. **Export to CSV**: Download alerts for external analysis
7. **Alert Configuration**: UI for managing watchlist and alert thresholds
8. **Multi-User Support**: User-specific alert preferences
9. **Server-Side Pagination**: Backend pagination for 1000+ alerts
10. **Advanced Filtering**: Date range, multiple asset selection, regex search

---

## Appendices

### A. Alert Type Reference

Complete list of alert types with descriptions:

| Alert Type | Description | Data Fields |
|------------|-------------|-------------|
| `congestion20` | Congestion pattern in last 20 candles | `touch_points`, `candles` |
| `congestion100` | Congestion pattern in last 100 candles | `touch_points`, `candles` |
| `combo` | Combo indicator signal | `price`, `direction`, `strength`, `has_been_triggered`, `details` |
| `double_top` | Double top reversal pattern | `close`, `open`, `higher`, `lower` |
| `double_inside_bar` | Double inside bar pattern | `close`, `open`, `higher`, `lower` |
| `containing_candle` | Containing candle pattern | `close`, `open`, `higher`, `lower` |

### B. Existing API Patterns

Reference existing modules for consistency:

| Module | Pattern | Example |
|--------|---------|---------|
| Watchlist | GET /api/watchlist | List all items |
| Report | POST /api/report | Create report |
| Homepage | GET /api/homepage | Get homepage items |
| Fund | GET /api/fund/accounts | List accounts |

**Key Patterns to Follow**:
- Router prefix: `/api/{module}`
- Service layer: `api/services/{module}_service.py`
- Pydantic models: `api/models/{module}.py`
- Dependency injection: `Depends(get_{module}_service)`
- Response models: `{Module}Response` + `{Module}ItemResponse`

### C. Related Code Locations

Reference for implementation:

| Component | Location | Purpose |
|-----------|----------|---------|
| Alert generation | `saxo_order/commands/alerting.py` | Creates alerts |
| DynamoDB client | `client/aws_client.py` | Storage operations |
| Alert model | `model/__init__.py` | Domain model |
| AlertType enum | `model/enum.py` | Type enumeration |
| DynamoDB table | `pulumi/dynamodb.py` | Infrastructure |
| Lambda handler | `lambda_function.py` | AWS Lambda entry |

---

**Plan Status**: ✅ **READY FOR IMPLEMENTATION**

**Next Step**: Run `/speckit.tasks` to generate implementation task list
