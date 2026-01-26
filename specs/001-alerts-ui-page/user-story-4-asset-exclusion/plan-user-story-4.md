# Implementation Plan: Asset Exclusion from Alerting (User Story 4)

**Branch**: `001-alerts-ui-page` | **Date**: 2026-01-26 | **Spec**: [spec.md](./spec.md)
**Parent Plan**: [plan.md](./plan.md) (User Stories 1-3)

## Summary

Add the ability to exclude specific assets from alert processing to reduce noise and improve batch run efficiency. Assets marked as excluded will be filtered out during watchlist construction in batch runs, and their alerts will be hidden from the alert view. Exclusion is managed through a boolean flag (`is_excluded`) in the existing `asset_details` DynamoDB table. A new UI section will allow traders to view excluded assets and manage exclusions directly from the frontend, with no CLI required.

## Technical Context

**Backend:**
- **Language/Version**: Python 3.11
- **Primary Dependencies**: FastAPI, Pydantic, boto3 (DynamoDB client)
- **Storage**: Existing DynamoDB table `asset_details` with new `is_excluded` boolean field
- **Testing**: pytest with unittest.mock for DynamoDB operations
- **Target Platform**: AWS Lambda (existing deployment) + Local uvicorn development

**Frontend:**
- **Language/Version**: TypeScript 5+, React 19+
- **Primary Dependencies**: React Router DOM v7+, Axios, Vite 7+
- **Testing**: None currently configured
- **Target Platform**: Web browser (served via Vite dev server on port 5173)

**Project Type**: Extension of existing alerts UI feature

**Performance Goals**:
- Batch run time reduction proportional to number of excluded assets
- No performance degradation for alert view filtering
- Asset exclusion updates take effect on next batch run (within 24 hours)

**Constraints**:
- Must use existing `asset_details` table (no new table)
- Must preserve existing asset_details fields (tradingview_url, updated_at)
- Must follow layered architecture (API Router → Service → DynamoDBClient → DynamoDB)
- No CLI commands required (UI-only management)
- Exclusion list read once at batch run start (no runtime updates)

**Scale/Scope**:
- ~50-100 assets monitored daily
- Expected exclusions: 5-20 assets (10-20% of watchlist)
- Single user access pattern
- Excluded assets remain in source data (Saxo API, followup-stocks.json)

## Constitution Check

*GATE: Must pass before implementation.*

### I. Layered Architecture Discipline ✅

**Backend:**
- ✅ API Layer: Modify `api/routers/asset_details.py` - add PUT endpoint for exclusion toggle
- ✅ Service Layer: Create `api/services/asset_details_service.py` - business logic for exclusion management
- ✅ Client Layer: Modify `client/aws_client.py` - add methods for exclusion queries and updates
- ✅ Model Layer: Update `api/models/asset_details.py` - add `is_excluded` field to AssetDetailResponse
- ✅ Batch Layer: Modify `saxo_order/commands/alerting.py` - filter excluded assets during watchlist build
- ✅ Dependency injection: Service receives DynamoDBClient as constructor parameter

**Frontend:**
- ✅ Pages: Create new `frontend/src/pages/AssetExclusions.tsx` for exclusion management
- ✅ Components: Create `frontend/src/components/ExclusionToggle.tsx` for inline toggle in alert cards
- ✅ Services: Extend `frontend/src/services/api.ts` - add assetDetailsService methods

**Verdict**: ✅ PASS - All layers properly separated with correct dependency flow

### II. Clean Code First ✅

- ✅ Self-documenting: Boolean field `is_excluded` is clear and explicit
- ✅ No hardcoded strings: Use existing enums and constants
- ✅ No over-engineering: Simple boolean flag, straightforward filtering logic
- ✅ No unnecessary comments: Code structure follows existing patterns

**Verdict**: ✅ PASS - Follows clean code standards

### III. Configuration-Driven Design ✅

**Backend:**
- ✅ DynamoDB table name from `config.yml` (existing: `asset_details` table)
- ✅ AWS credentials from environment/secrets.yml (existing configuration)
- ✅ No new hardcoded values

**Frontend:**
- ✅ API URL from `import.meta.env.VITE_API_URL` (existing pattern)

**Verdict**: ✅ PASS - No new configuration needed, uses existing setup

### IV. Safe Deployment Practices ✅

- ✅ No infrastructure changes required (asset_details table already exists)
- ✅ No Lambda function signature changes (alerting workflow enhanced, not modified)
- ✅ API changes deploy via `./deploy.sh` (standard process)
- ✅ Frontend builds via `npm run build` in frontend directory
- ✅ Conventional commits for all changes
- ✅ Backward compatible: New field defaults to false (not excluded)

**Verdict**: ✅ PASS - Uses existing deployment processes, fully backward compatible

### V. Domain Model Integrity ✅

- ✅ AssetDetail model enhanced: Adds optional `is_excluded` boolean field
- ✅ Alert model unchanged: No modifications to existing Alert dataclass
- ✅ Existing asset_details fields preserved: tradingview_url, updated_at remain unchanged
- ✅ Default value: `is_excluded=false` for existing records (backward compatible)

**Verdict**: ✅ PASS - Respects existing domain model conventions

---

**Overall Constitution Compliance**: ✅ **PASS** - All 5 principles satisfied with no violations

## Project Structure

### Documentation (this feature)

```text
specs/001-alerts-ui-page/
├── spec.md                     # Feature specification (updated with User Story 4)
├── plan.md                     # Original plan (User Stories 1-3)
├── plan-user-story-4.md        # This file (User Story 4 implementation plan)
├── tasks-user-story-4.md       # To be generated (implementation tasks)
└── contracts/
    └── asset-exclusion-api.yaml  # OpenAPI spec for exclusion endpoints
```

### Source Code Changes

```text
# Backend - API Layer
api/routers/
└── asset_details.py            # MODIFIED: Add PUT /api/asset-details/{asset_id}/exclusion

api/services/
└── asset_details_service.py    # NEW: AssetDetailsService with exclusion logic

api/models/
└── asset_details.py            # MODIFIED: Add is_excluded field to AssetDetailResponse

# Backend - Client Layer
client/
└── aws_client.py               # MODIFIED: Add get_excluded_assets(), update_asset_exclusion()

# Backend - Batch Processing
saxo_order/commands/
└── alerting.py                 # MODIFIED: Filter excluded assets in run_alerting()

# Frontend - UI
frontend/src/pages/
├── Alerts.tsx                  # MODIFIED: Add exclusion indicator/toggle to alert cards
└── AssetExclusions.tsx         # NEW: Dedicated page for exclusion management

frontend/src/components/
└── ExclusionToggle.tsx         # NEW: Toggle component for exclusion state

frontend/src/services/
└── api.ts                      # MODIFIED: Add assetDetailsService methods

# Tests
tests/api/services/
└── test_asset_details_service.py  # NEW: Service unit tests

tests/api/routers/
└── test_asset_details.py       # MODIFIED: Add exclusion endpoint tests

tests/commands/
└── test_alerting.py            # MODIFIED: Test exclusion filtering in batch run
```

## Complexity Tracking

**No violations** - Constitution Check passed completely. No complexity justifications needed.

## Implementation Phases

### Phase 1: Backend Data Layer

**Objective**: Add exclusion field to asset_details table and extend DynamoDB client

**Tasks**:
1. Extend DynamoDB Client:
   - Add `get_excluded_assets() -> List[str]` method to fetch all assets where `is_excluded=true`
   - Add `update_asset_exclusion(asset_id: str, is_excluded: bool) -> bool` method
   - Add `get_all_asset_details() -> List[Dict]` method for exclusion list page
   - Handle missing `is_excluded` field (defaults to false for existing records)

2. Update API Models:
   - Add `is_excluded: Optional[bool] = Field(default=False)` to `AssetDetailResponse`
   - Create `AssetExclusionUpdateRequest` Pydantic model with `is_excluded: bool` field

3. Write Unit Tests:
   - Test `get_excluded_assets()` with mixed excluded/not-excluded assets
   - Test `update_asset_exclusion()` for both true and false values
   - Test handling of missing `is_excluded` field (backward compatibility)
   - Test `get_all_asset_details()` pagination and filtering

**Acceptance Criteria**:
- ✅ DynamoDB client can query excluded assets
- ✅ DynamoDB client can update exclusion status
- ✅ Existing records without `is_excluded` field default to false
- ✅ All unit tests pass with 100% coverage

---

### Phase 2: Backend API Layer

**Objective**: Expose exclusion management via REST API

**Tasks**:
1. Create Asset Details Service:
   - Create `api/services/asset_details_service.py`
   - Implement `get_asset_details(asset_id: str) -> AssetDetailResponse`
   - Implement `update_exclusion(asset_id: str, is_excluded: bool) -> AssetDetailResponse`
   - Implement `get_all_excluded_assets() -> List[AssetDetailResponse]`
   - Implement `get_all_assets_with_details() -> List[AssetDetailResponse]`

2. Extend Asset Details Router:
   - Refactor existing GET endpoint to use service layer (currently calls DynamoDB client directly)
   - Add `PUT /api/asset-details/{asset_id}/exclusion` endpoint
   - Add `GET /api/asset-details/excluded` endpoint (list all excluded assets)
   - Add `GET /api/asset-details` endpoint (list all assets with details)
   - Return updated `AssetDetailResponse` with `is_excluded` field

3. Create OpenAPI Contract:
   - Document all exclusion endpoints in `contracts/asset-exclusion-api.yaml`
   - Include request/response schemas
   - Document error responses (400, 404, 500)

4. Write Integration Tests:
   - Test PUT endpoint updates exclusion status correctly
   - Test GET excluded endpoint returns only excluded assets
   - Test GET all assets includes exclusion status
   - Test 404 when asset doesn't exist
   - Test validation errors for invalid request bodies

**Acceptance Criteria**:
- ✅ PUT endpoint successfully toggles exclusion status
- ✅ GET excluded endpoint returns correct list
- ✅ GET all assets includes is_excluded field
- ✅ All integration tests pass
- ✅ OpenAPI spec complete and accurate

---

### Phase 3: Backend Batch Processing

**Objective**: Filter excluded assets during alerting batch runs

**Tasks**:
1. Modify `run_alerting()` function in `saxo_order/commands/alerting.py`:
   - After building initial watchlist (French stocks + followup stocks)
   - Before the detection loop, fetch excluded assets: `excluded_assets = dynamodb_client.get_excluded_assets()`
   - Filter watchlist: `watchlist = [s for s in stocks if s.code not in excluded_assets]`
   - Log filtered count: `logger.info(f"Filtered out {filtered_count} excluded assets")`
   - Ensure manual single-asset alerting (`--code` flag) also respects exclusions

2. Add Debug Logging:
   - Log excluded asset list at start of batch run
   - Log each excluded asset that gets filtered out
   - Log total assets processed before/after exclusion filtering

3. Write Integration Tests:
   - Test batch run with no excluded assets (baseline behavior)
   - Test batch run with some excluded assets (verify filtering works)
   - Test batch run with all assets excluded (should complete quickly with no alerts)
   - Test manual alerting with `--code` for excluded asset (should skip processing)
   - Test that excluded assets don't generate alerts

**Acceptance Criteria**:
- ✅ Excluded assets never processed during batch runs
- ✅ Batch run time reduced proportionally to excluded asset count
- ✅ Logs clearly indicate filtering occurred
- ✅ Manual alerting respects exclusions
- ✅ All integration tests pass

---

### Phase 4: Backend Alert Retrieval Filtering

**Objective**: Hide alerts for excluded assets from API responses

**Tasks**:
1. Modify `AlertingService.get_all_alerts()` in `api/services/alerting_service.py`:
   - After retrieving alerts from DynamoDB
   - Before applying existing filters (asset_code, alert_type)
   - Fetch excluded assets: `excluded_assets = self.dynamodb_client.get_excluded_assets()`
   - Filter alerts: `alerts = [a for a in alerts if a.asset_code not in excluded_assets]`
   - Apply to both filtered and unfiltered result sets

2. Update Available Filters:
   - Ensure `available_asset_codes` in response excludes excluded assets
   - Excluded assets should not appear in filter dropdowns

3. Write Unit Tests:
   - Test alert retrieval with no excluded assets (baseline)
   - Test alert retrieval with some excluded assets (verify filtering)
   - Test alert retrieval with all alerts from excluded assets (return empty)
   - Test that available filters don't include excluded assets

**Acceptance Criteria**:
- ✅ Excluded asset alerts never returned by API
- ✅ Excluded assets don't appear in filter dropdowns
- ✅ Filtering preserves all other alert data
- ✅ All unit tests pass

---

### Phase 5: Frontend - Exclusion Management Page

**Objective**: Create dedicated page for viewing and managing exclusions

**Tasks**:
1. Create AssetExclusions Page:
   - Create `frontend/src/pages/AssetExclusions.tsx`
   - Fetch all assets with details from `GET /api/asset-details`
   - Display two sections: "Excluded Assets" and "Active Assets"
   - Each asset shows: asset_id, tradingview_url link, exclusion toggle
   - Implement toggle button that calls `PUT /api/asset-details/{asset_id}/exclusion`
   - Show loading states during API calls
   - Show success/error messages after toggle operations
   - Add search/filter box to quickly find assets

2. Add Navigation:
   - Add route to `frontend/src/App.tsx`: `/exclusions`
   - Add navigation link in sidebar/header: "Asset Exclusions" or "Manage Exclusions"

3. Style Components:
   - Follow existing design system patterns
   - Use consistent button/toggle styles
   - Responsive layout for mobile/tablet/desktop
   - Clear visual distinction between excluded and active assets

**Acceptance Criteria**:
- ✅ Page displays all assets with current exclusion status
- ✅ Toggle button updates exclusion status via API
- ✅ UI updates immediately after successful toggle
- ✅ Loading and error states handled gracefully
- ✅ Page is accessible from main navigation
- ✅ Responsive design works on all screen sizes

---

### Phase 6: Frontend - Alert View Integration

**Objective**: Integrate exclusion management into existing Alerts page

**Tasks**:
1. Add Exclusion Indicator to AlertCard:
   - Modify `frontend/src/components/AlertCard.tsx`
   - Add small badge/icon showing "(Excluded)" if asset is currently excluded
   - Make exclusion status visible but not prominent (informational only)
   - Note: This is informational - excluded alerts shouldn't appear in view anyway

2. Add Inline Exclusion Toggle (Optional Enhancement):
   - Add toggle button/icon to alert card actions
   - Clicking toggle opens confirmation dialog
   - On confirm, calls `PUT /api/asset-details/{asset_id}/exclusion`
   - Show toast notification on success
   - Alert remains visible until page refresh (backend will filter on next load)

3. Update Alerts Page:
   - Modify `frontend/src/pages/Alerts.tsx`
   - Add info message explaining exclusion feature
   - Add link to exclusion management page

**Acceptance Criteria**:
- ✅ Alert cards show exclusion status (if needed for debugging)
- ✅ Inline toggle works correctly (if implemented)
- ✅ UI provides clear feedback on toggle actions
- ✅ Users can navigate to exclusion management page from alerts page

---

### Phase 7: Testing & Documentation

**Objective**: Comprehensive testing and documentation updates

**Tasks**:
1. End-to-End Testing:
   - Start backend and frontend locally
   - Exclude an asset via UI
   - Verify alert view no longer shows alerts for that asset
   - Run manual alerting for excluded asset: `poetry run k-order alerting --code=SAN --country-code=xpar`
   - Verify no alerts generated
   - Un-exclude the asset
   - Run alerting again and verify alerts are generated
   - Verify batch run logs show exclusion filtering

2. Update Documentation:
   - Update `specs/001-alerts-ui-page/quickstart.md` with exclusion management instructions
   - Add "Asset Exclusion" section to feature documentation
   - Document API endpoints in OpenAPI spec
   - Update README if needed

3. Manual Testing Checklist:
   - [ ] Excluding asset via UI updates DynamoDB
   - [ ] Excluded assets don't appear in batch run processing
   - [ ] Excluded asset alerts don't appear in alert view
   - [ ] Filter dropdowns don't include excluded assets
   - [ ] Un-excluding asset restores normal behavior
   - [ ] Manual alerting respects exclusions
   - [ ] Exclusion management page displays correctly
   - [ ] Inline toggle works from alert cards (if implemented)
   - [ ] Loading states display correctly
   - [ ] Error handling works for API failures
   - [ ] Mobile responsive layout works

4. Performance Testing:
   - Measure batch run time with 0 exclusions (baseline)
   - Measure batch run time with 10 exclusions (~10% reduction)
   - Measure batch run time with 20 exclusions (~20% reduction)
   - Verify API response time not degraded by exclusion filtering

**Acceptance Criteria**:
- ✅ All end-to-end scenarios pass
- ✅ Documentation complete and accurate
- ✅ Manual testing checklist 100% complete
- ✅ Performance targets met

---

## Architecture Decisions

### Decision 1: Single Boolean Field vs. Separate Table

**Context**: Store exclusion data in existing `asset_details` table vs. new `exclusions` table

**Decision**: Use single `is_excluded` boolean field in existing `asset_details` table

**Rationale**:
- User specifically requested using asset_details table with new column
- Simplifies data model (one less table to manage)
- Asset exclusion is logically an asset property (belongs with asset details)
- Eliminates join operations (better performance)
- Easier to query for both excluded and non-excluded assets
- No additional AWS costs for new table

**Trade-offs**:
- ✅ Simple: One table, one field, straightforward queries
- ✅ Performance: No joins, direct key lookup
- ✅ Cost: No additional DynamoDB table charges
- ⚠️ Extensibility: Future exclusion metadata (reason, date) would add more fields vs. separate record

### Decision 2: UI-Only Management (No CLI)

**Context**: How should users manage asset exclusions?

**Decision**: Provide only web UI for exclusion management (no CLI commands)

**Rationale**:
- User explicitly stated "I don't need the CLI to manage the exclusion list"
- Web UI provides better user experience for browsing and toggling exclusions
- Visual interface easier for managing multiple assets
- Consistent with existing UI-first approach in the project
- CLI would duplicate functionality without added value

**Trade-offs**:
- ✅ Better UX: Visual interface with instant feedback
- ✅ Simpler: One less interface to implement and maintain
- ✅ Consistency: Aligns with UI-first design philosophy
- ❌ Automation: Cannot script bulk exclusions (acceptable for single-user app)
- ⚠️ Deployment: Requires frontend deployment for exclusion changes (acceptable)

### Decision 3: Read Exclusions Once Per Batch Run

**Context**: When should exclusion list be loaded during batch processing?

**Decision**: Load exclusion list once at start of batch run, use in-memory for duration

**Rationale**:
- Batch runs are short-lived (~5-20 minutes)
- Exclusion changes are infrequent (manual user action)
- Reading once reduces DynamoDB read costs
- Simplifies implementation (no cache invalidation logic)
- Acceptable latency: exclusion changes take effect on next batch run (max 24 hours)

**Trade-offs**:
- ✅ Simple: No caching logic, no staleness concerns
- ✅ Performance: One DynamoDB query vs. N queries (one per asset)
- ✅ Cost: Minimal read capacity units consumed
- ⚠️ Latency: Exclusion changes not immediate (max 24 hour delay) - acceptable

### Decision 4: Filter Alerts in API vs. Database

**Context**: Where should excluded asset alerts be filtered?

**Decision**: Filter alerts in application layer (AlertingService) after DynamoDB retrieval

**Rationale**:
- DynamoDB `alerts` table uses asset_code as partition key (no global filtering)
- Adding filter condition would require scanning entire table anyway
- Application-layer filtering is straightforward and performant for current scale
- No need for complex DynamoDB query expressions
- Maintains separation of concerns (exclusion logic in service layer)

**Trade-offs**:
- ✅ Simple: Clear filtering logic in service layer
- ✅ Flexible: Easy to add additional filtering criteria
- ⚠️ Network: Transfers excluded alerts over network before filtering (minimal impact)
- ⚠️ Scalability: Would need optimization if alert volume grows to 10K+ (not expected)

### Decision 5: Inline Toggle vs. Dedicated Page Only

**Context**: Should exclusion toggles appear directly in alert cards?

**Decision**: Provide both - dedicated exclusion management page (primary) and optional inline toggle in alert cards (convenience)

**Rationale**:
- Dedicated page provides comprehensive view of all exclusions
- Inline toggle offers quick access without navigation
- Inline toggle is optional enhancement (can be added in Phase 6)
- Users can choose workflow based on preference
- Inline toggle useful when reviewing alerts and deciding to exclude asset

**Trade-offs**:
- ✅ Flexibility: Multiple workflows supported
- ✅ UX: Quick actions available in context
- ⚠️ Complexity: Two UI surfaces to maintain (minimal)
- ⚠️ Consistency: Need to ensure both surfaces stay in sync (handled by API)

### Decision 6: Default Exclusion Status for Existing Records

**Context**: How to handle existing asset_details records without `is_excluded` field?

**Decision**: Default to `is_excluded=false` for missing fields (not excluded)

**Rationale**:
- Backward compatible with existing data
- Preserves current behavior (all assets active by default)
- Users explicitly opt-in to exclusion (safer default)
- No migration script needed (handled dynamically)
- Aligns with Python/TypeScript conventions (None/undefined treated as false)

**Trade-offs**:
- ✅ Backward Compatible: Existing assets remain active
- ✅ Safe: No risk of accidentally excluding assets
- ✅ Simple: No data migration required
- ✅ Explicit: Users must intentionally exclude assets

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| DynamoDB field missing for old records | High | Low | Default to false in application layer |
| Exclusion not applied in batch run | Low | Medium | Add comprehensive logging and integration tests |
| Race condition (exclude during batch run) | Low | Low | Accept - exclusion takes effect on next run |
| Frontend-backend type mismatch | Medium | Low | Add integration tests, validate responses |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| User accidentally excludes wrong asset | Medium | Low | Add confirmation dialog before exclusion |
| All assets excluded by mistake | Low | Medium | Show warning if >50% assets excluded |
| Exclusion not visible to user | Low | Medium | Clear UI indication in both alert view and management page |

---

## Performance Targets

**Batch Run Processing**:
- ✅ Target: Proportional time reduction (10 excluded assets = ~10% faster)
- ✅ Expected: 5-20% reduction for typical usage (5-20 excluded assets)
- ✅ Overhead: <500ms for loading exclusion list at batch start

**API Performance** (`GET /api/alerts`):
- ✅ Target: No degradation from exclusion filtering
- ✅ Expected: <50ms overhead for filtering 100-150 alerts
- ✅ Acceptable: Up to 200ms for worst case (600 alerts, 20 exclusions)

**UI Performance**:
- ✅ Exclusion toggle response: <1 second (API call + UI update)
- ✅ Exclusion management page load: <2 seconds (fetch all assets)
- ✅ Asset search/filter: <100ms (client-side filtering)

**Data Volume**:
- ✅ Typical: 5-20 excluded assets (10-20% of watchlist)
- ✅ Maximum: 50 excluded assets (50% of watchlist)
- ✅ Edge case: All assets excluded (handled gracefully with warning)

---

## Testing Strategy

### Backend Testing

**Unit Tests** (`tests/api/services/test_asset_details_service.py`):
- AssetDetailsService.get_asset_details() with is_excluded field
- AssetDetailsService.update_exclusion() toggle true/false
- AssetDetailsService.get_all_excluded_assets() filtering
- Edge case: Asset without is_excluded field (defaults to false)
- Edge case: Update exclusion for non-existent asset

**Coverage Target**: 100% for AssetDetailsService (5 tests)

**Unit Tests** (`tests/client/test_aws_client.py`):
- DynamoDBClient.get_excluded_assets() with mixed data
- DynamoDBClient.update_asset_exclusion() success/failure
- DynamoDBClient.get_all_asset_details() pagination
- Edge case: Missing is_excluded field handling

**Coverage Target**: 100% for exclusion methods (4 tests)

**Integration Tests** (`tests/api/routers/test_asset_details.py`):
- PUT /api/asset-details/{asset_id}/exclusion returns 200
- PUT endpoint updates is_excluded correctly
- GET /api/asset-details/excluded returns only excluded assets
- GET /api/asset-details includes is_excluded in response
- PUT with invalid asset_id returns 404
- PUT with invalid request body returns 400

**Coverage Target**: All endpoints and error cases (6 tests)

**Integration Tests** (`tests/commands/test_alerting.py`):
- Batch run with no excluded assets (baseline)
- Batch run with excluded assets (verify filtering)
- Batch run with all assets excluded (quick completion)
- Manual alerting with excluded asset (verify skip)
- Verify excluded assets don't generate alerts
- Verify log messages indicate filtering

**Coverage Target**: Exclusion logic in batch processing (6 tests)

### Frontend Testing

**Status**: No testing framework configured

**Manual Testing Checklist**:
- [ ] Exclusion management page loads successfully
- [ ] Page displays all assets with correct exclusion status
- [ ] Toggle button updates exclusion status
- [ ] UI reflects changes immediately
- [ ] Loading states display during API calls
- [ ] Error messages display on API failures
- [ ] Search/filter box works correctly
- [ ] Alert cards show exclusion indicator (if implemented)
- [ ] Inline toggle works from alert cards (if implemented)
- [ ] Navigation link accessible from main menu
- [ ] Responsive layout works on mobile/tablet/desktop
- [ ] Confirmation dialogs appear before exclusion
- [ ] Success toast notifications display

### End-to-End Testing

**Smoke Test**:
1. Start backend: `poetry run python run_api.py`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to: http://localhost:5173/exclusions
4. Toggle exclusion for an asset (e.g., "SAN")
5. Verify: Asset appears in "Excluded Assets" section
6. Navigate to: http://localhost:5173/alerts
7. Verify: No alerts for excluded asset appear
8. Run manual alerting: `poetry run k-order alerting --code=SAN --country-code=xpar`
9. Verify: Logs show asset was skipped due to exclusion
10. Toggle exclusion off for the asset
11. Run alerting again: `poetry run k-order alerting --code=SAN --country-code=xpar`
12. Verify: Alerts are generated

**Pre-Deployment Checklist**:
- [ ] All backend tests pass: `poetry run pytest`
- [ ] Backend API endpoints accessible: `curl http://localhost:8000/api/asset-details/excluded`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Frontend displays exclusion management page
- [ ] CORS configured for production frontend URL
- [ ] DynamoDB table has test data with is_excluded field

---

## Deployment Plan

### Prerequisites

- ✅ DynamoDB table `asset_details` exists (no changes needed)
- ✅ Backend API server deployed
- ✅ Frontend deployment configured
- ✅ AWS credentials configured

### Backend Deployment Steps

```bash
# 1. Run tests
poetry run pytest

# 2. Build and deploy
./deploy.sh

# 3. Verify deployment - test exclusion endpoint
curl -X PUT https://your-api-url.com/api/asset-details/test-asset/exclusion \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": true}'

# 4. Verify get excluded endpoint
curl https://your-api-url.com/api/asset-details/excluded

# 5. Check CloudWatch logs
aws logs tail /aws/lambda/api_lambda --follow
```

### Frontend Deployment Steps

```bash
# 1. Update environment
echo "VITE_API_URL=https://your-api-url.com" > frontend/.env.production

# 2. Build
cd frontend
npm run build

# 3. Deploy dist/ folder to hosting provider

# 4. Verify exclusion management page
curl https://your-frontend-url.com/exclusions
```

### Post-Deployment Verification

```bash
# 1. Verify exclusion toggle works via UI
# (Manual: Navigate to exclusion page, toggle an asset)

# 2. Verify batch run respects exclusions
poetry run k-order alerting

# 3. Check logs for exclusion filtering
aws logs tail /aws/lambda/alerting_lambda --follow

# 4. Verify excluded asset alerts don't appear in UI
# (Manual: Navigate to alerts page, verify excluded asset not shown)
```

### Rollback Plan

**Backend**: Redeploy previous Docker image from ECR
**Frontend**: Revert to previous dist/ build on hosting provider
**Database**: No schema changes - old code will ignore is_excluded field
**Risk**: Low - feature is additive, backward compatible

---

## Success Metrics

**Feature Adoption**:
- ✅ User excludes at least 5-10 assets within first week
- ✅ Batch run time reduces proportionally to exclusions
- ✅ User references exclusion management page when reviewing alerts

**Technical Performance**:
- ✅ Batch run time reduction: 10 excluded assets = ~10% faster
- ✅ API response time: No degradation for alert retrieval
- ✅ Exclusion toggle response: <1 second (API call + UI update)
- ✅ Zero errors in CloudWatch logs for exclusion operations

**User Satisfaction**:
- ✅ Excluded assets never appear in alert view (100% filtering accuracy)
- ✅ Excluded assets never processed in batch runs (verified in logs)
- ✅ Toggle state updates immediately in UI (no refresh needed)
- ✅ No complaints about excluded assets generating alerts

---

## API Contract

### Endpoint: PUT /api/asset-details/{asset_id}/exclusion

**Purpose**: Update exclusion status for an asset

**Request**:
```json
{
  "is_excluded": true
}
```

**Response** (200 OK):
```json
{
  "asset_id": "SAN",
  "tradingview_url": "https://www.tradingview.com/chart/?symbol=XPAR:SAN",
  "updated_at": "2026-01-26T10:30:00Z",
  "is_excluded": true
}
```

**Error Responses**:
- 400 Bad Request: Invalid request body
- 404 Not Found: Asset does not exist
- 500 Internal Server Error: DynamoDB operation failed

---

### Endpoint: GET /api/asset-details/excluded

**Purpose**: Get all excluded assets

**Response** (200 OK):
```json
{
  "assets": [
    {
      "asset_id": "SAN",
      "tradingview_url": "https://www.tradingview.com/chart/?symbol=XPAR:SAN",
      "updated_at": "2026-01-26T10:30:00Z",
      "is_excluded": true
    },
    {
      "asset_id": "BNP",
      "tradingview_url": null,
      "updated_at": "2026-01-25T14:20:00Z",
      "is_excluded": true
    }
  ],
  "count": 2
}
```

**Error Responses**:
- 500 Internal Server Error: DynamoDB operation failed

---

### Endpoint: GET /api/asset-details

**Purpose**: Get all assets with details (including exclusion status)

**Response** (200 OK):
```json
{
  "assets": [
    {
      "asset_id": "SAN",
      "tradingview_url": "https://www.tradingview.com/chart/?symbol=XPAR:SAN",
      "updated_at": "2026-01-26T10:30:00Z",
      "is_excluded": true
    },
    {
      "asset_id": "ITP",
      "tradingview_url": null,
      "updated_at": "2026-01-24T09:15:00Z",
      "is_excluded": false
    }
  ],
  "count": 2,
  "excluded_count": 1,
  "active_count": 1
}
```

**Error Responses**:
- 500 Internal Server Error: DynamoDB operation failed

---

## Future Enhancements (Out of Scope)

These features are explicitly out of scope for this implementation but may be considered later:

1. **Exclusion Reason**: Add optional text field explaining why asset was excluded
2. **Exclusion History**: Track when assets were excluded/un-excluded and by whom
3. **Bulk Exclusion**: Select multiple assets and exclude/un-exclude at once
4. **Smart Suggestions**: Recommend assets to exclude based on low signal quality or false positives
5. **Temporary Exclusion**: Exclude for N days then automatically re-enable
6. **Exclusion Categories**: Group excluded assets by reason (e.g., "low volume", "false signals")
7. **Export/Import Exclusions**: Download exclusion list as CSV for backup or sharing
8. **Exclusion Sync**: Sync exclusions across multiple users (if multi-user support added)
9. **Conditional Exclusion**: Exclude only for specific alert types (e.g., exclude SAN from COMBO alerts but not DOUBLE_TOP)
10. **Alert Type Exclusion**: Globally disable specific alert types rather than specific assets

---

## Appendices

### A. Database Schema Changes

**Table**: `asset_details`

**New Field**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `is_excluded` | Boolean | No | false | True if asset should be excluded from alerting |

**Existing Fields** (unchanged):
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `asset_id` | String | Yes | Primary key - unique asset identifier |
| `tradingview_url` | String | No | Custom TradingView URL for asset |
| `updated_at` | String | No | ISO timestamp of last update |

**Backward Compatibility**:
- Existing records without `is_excluded` field are treated as `is_excluded=false`
- No data migration required
- Old code versions can safely ignore new field

---

### B. Logging Strategy

**Batch Run Logs** (in `saxo_order/commands/alerting.py`):
```python
logger.info(f"Total assets in watchlist: {len(all_stocks)}")
excluded = dynamodb_client.get_excluded_assets()
logger.info(f"Excluded assets: {excluded}")
filtered_stocks = [s for s in all_stocks if s.code not in excluded]
logger.info(f"Assets after exclusion filtering: {len(filtered_stocks)}")
logger.info(f"Filtered out {len(all_stocks) - len(filtered_stocks)} excluded assets")
```

**API Logs** (in `api/services/asset_details_service.py`):
```python
logger.info(f"Updating exclusion for asset {asset_id}: is_excluded={is_excluded}")
logger.info(f"Retrieved {len(excluded_assets)} excluded assets")
logger.info(f"Filtered {filtered_count} alerts from excluded assets")
```

**Log Levels**:
- INFO: Normal operations (exclusion updates, filtering counts)
- WARNING: Suspicious operations (>50% assets excluded)
- ERROR: DynamoDB failures, API errors

---

### C. Related Code Locations

Reference for implementation:

| Component | Location | Purpose |
|-----------|----------|---------|
| Alert generation | `saxo_order/commands/alerting.py` | Modify to filter excluded assets |
| DynamoDB client | `client/aws_client.py` | Add exclusion methods |
| Asset details API | `api/routers/asset_details.py` | Add exclusion endpoints |
| Asset details model | `api/models/asset_details.py` | Add is_excluded field |
| Alerting service | `api/services/alerting_service.py` | Filter excluded alerts |
| Existing asset details route | `api/routers/asset_details.py:12-39` | Refactor to use service layer |

---

### D. UI Wireframes

**Exclusion Management Page Layout**:
```
┌─────────────────────────────────────────────────────┐
│ Asset Exclusion Management                          │
├─────────────────────────────────────────────────────┤
│ Search: [____________]                        [Filter▼] │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Excluded Assets (10)                                │
│ ┌───────────────────────────────────────────────┐   │
│ │ SAN  [TradingView↗]          [Un-exclude]    │   │
│ │ BNP  [TradingView↗]          [Un-exclude]    │   │
│ │ ...                                           │   │
│ └───────────────────────────────────────────────┘   │
│                                                     │
│ Active Assets (45)                                  │
│ ┌───────────────────────────────────────────────┐   │
│ │ ITP  [TradingView↗]          [Exclude]        │   │
│ │ CS   [TradingView↗]          [Exclude]        │   │
│ │ ...                                           │   │
│ └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Alert Card with Inline Toggle** (Optional):
```
┌───────────────────────────────────────────────────┐
│ Asset: ITP                        [TradingView↗]  │
│ Type: COMBO | MA50 Slope: +15.2% ⬆               │
│ Condition: Buy signal detected                    │
│ Timestamp: 2 hours ago                            │
│                                                   │
│ [View Details]  [Exclude Asset]  [...]           │
└───────────────────────────────────────────────────┘
```

---

**Plan Status**: ✅ **READY FOR TASK GENERATION**

**Next Step**: Generate `tasks-user-story-4.md` with dependency-ordered implementation tasks
