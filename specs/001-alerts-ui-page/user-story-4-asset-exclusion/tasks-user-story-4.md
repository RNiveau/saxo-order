# Implementation Tasks: Asset Exclusion (User Story 4)

**Feature**: 001-alerts-ui-page | **User Story**: 4 - Exclude Assets from Alerting
**Plan**: [plan-user-story-4.md](./plan-user-story-4.md) | **Spec**: [spec.md](./spec.md)

## Task Execution Order

Tasks are numbered in dependency order. Complete each task fully before moving to the next. Each task includes:
- **Files**: Specific files to create or modify
- **Acceptance Criteria**: How to verify the task is complete
- **Dependencies**: Which tasks must be completed first

---

## Phase 1: Backend Data Layer

### Task 1: Add exclusion methods to DynamoDB client

**Files**:
- `client/aws_client.py`

**Description**:
Add three new methods to `DynamoDBClient` class for managing asset exclusions:

1. `get_excluded_assets() -> List[str]`:
   - Scan `asset_details` table for items where `is_excluded=true`
   - Return list of asset_id strings
   - Handle missing `is_excluded` field (treat as false)
   - Return empty list if no excluded assets

2. `update_asset_exclusion(asset_id: str, is_excluded: bool) -> bool`:
   - Update `asset_details` table item with `is_excluded` field
   - Set `updated_at` to current ISO timestamp
   - Create item if asset_id doesn't exist
   - Return True on success, False on failure

3. `get_all_asset_details() -> List[Dict[str, Any]]`:
   - Scan entire `asset_details` table
   - Return all items with all fields (asset_id, tradingview_url, updated_at, is_excluded)
   - Handle pagination automatically
   - Default `is_excluded` to false if field missing

**Implementation Notes**:
- Use `scan()` operation for `get_excluded_assets()` with FilterExpression
- Use `update_item()` for `update_asset_exclusion()` with UpdateExpression
- Use `scan()` with pagination for `get_all_asset_details()`
- Handle DynamoDB exceptions gracefully with logging

**Acceptance Criteria**:
- [ ] `get_excluded_assets()` returns empty list when no assets excluded
- [ ] `get_excluded_assets()` returns correct list of excluded asset IDs
- [ ] `get_excluded_assets()` handles missing `is_excluded` field (treats as false)
- [ ] `update_asset_exclusion()` successfully creates/updates item in DynamoDB
- [ ] `update_asset_exclusion()` sets `updated_at` timestamp correctly
- [ ] `get_all_asset_details()` returns all assets with correct fields
- [ ] `get_all_asset_details()` handles pagination automatically
- [ ] All methods log errors appropriately

**Dependencies**: None

---

### Task 2: Create Pydantic models for asset exclusion

**Files**:
- `api/models/asset_details.py` (modify existing)

**Description**:
Extend existing `AssetDetailResponse` model and create new request model:

1. Modify `AssetDetailResponse`:
   - Add `is_excluded: Optional[bool] = Field(default=False, description="True if asset is excluded from alerting")`
   - Keep existing fields: asset_id, tradingview_url, updated_at

2. Create `AssetExclusionUpdateRequest`:
   ```python
   class AssetExclusionUpdateRequest(BaseModel):
       is_excluded: bool = Field(description="Exclusion status")
   ```

3. Create `AssetListResponse`:
   ```python
   class AssetListResponse(BaseModel):
       assets: List[AssetDetailResponse]
       count: int
       excluded_count: Optional[int] = None
       active_count: Optional[int] = None
   ```

**Acceptance Criteria**:
- [ ] `AssetDetailResponse` includes `is_excluded` field with correct type and default
- [ ] `AssetExclusionUpdateRequest` validates boolean values correctly
- [ ] `AssetListResponse` includes all required fields
- [ ] Models serialize/deserialize correctly
- [ ] Field descriptions are accurate

**Dependencies**: None

---

### Task 3: Write unit tests for DynamoDB exclusion methods

**Files**:
- `tests/client/test_aws_client.py` (create if doesn't exist, or modify existing)

**Description**:
Write comprehensive unit tests for the three new DynamoDB client methods:

Test cases for `get_excluded_assets()`:
- Returns empty list when no assets exist
- Returns empty list when no assets are excluded
- Returns correct list when some assets are excluded
- Handles assets with missing `is_excluded` field (treats as false)
- Returns only asset IDs, not full objects

Test cases for `update_asset_exclusion()`:
- Successfully updates existing asset to excluded
- Successfully updates existing asset to not excluded
- Creates new asset if doesn't exist
- Sets `updated_at` timestamp
- Returns True on success
- Returns False on DynamoDB error

Test cases for `get_all_asset_details()`:
- Returns empty list when table is empty
- Returns all assets with all fields
- Handles missing `is_excluded` field (defaults to false)
- Handles pagination correctly

**Implementation Notes**:
- Use `unittest.mock` to mock boto3 DynamoDB operations
- Mock `boto3.resource('dynamodb')` and table operations
- Create realistic mock responses matching DynamoDB structure

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Tests use proper mocking (no real DynamoDB calls)
- [ ] Tests cover happy path and error cases
- [ ] Tests verify correct data transformations
- [ ] Coverage: 100% of new methods

**Dependencies**: Task 1

---

## Phase 2: Backend API Layer

### Task 4: Create Asset Details Service

**Files**:
- `api/services/asset_details_service.py` (create new)

**Description**:
Create new service class `AssetDetailsService` with business logic for asset exclusion management:

```python
class AssetDetailsService:
    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb_client = dynamodb_client
        self.logger = Logger.get_logger("asset_details_service")

    def get_asset_details(self, asset_id: str) -> AssetDetailResponse:
        """Get details for a single asset"""
        # Get from DynamoDB, handle missing is_excluded field

    def update_exclusion(self, asset_id: str, is_excluded: bool) -> AssetDetailResponse:
        """Update exclusion status for an asset"""
        # Update in DynamoDB, return updated details

    def get_all_excluded_assets(self) -> List[AssetDetailResponse]:
        """Get all excluded assets"""
        # Filter for is_excluded=true

    def get_all_assets_with_details(self) -> AssetListResponse:
        """Get all assets with details and counts"""
        # Return all assets plus excluded/active counts
```

**Implementation Notes**:
- Accept DynamoDBClient via constructor (dependency injection)
- Default `is_excluded` to false for missing fields
- Log all operations at INFO level
- Handle DynamoDB errors and convert to service exceptions
- Calculate excluded_count and active_count in `get_all_assets_with_details()`

**Acceptance Criteria**:
- [ ] Service properly injected with DynamoDBClient
- [ ] `get_asset_details()` returns correct AssetDetailResponse
- [ ] `get_asset_details()` defaults is_excluded to false when missing
- [ ] `update_exclusion()` calls DynamoDB client correctly
- [ ] `update_exclusion()` returns updated asset details
- [ ] `get_all_excluded_assets()` returns only excluded assets
- [ ] `get_all_assets_with_details()` returns correct counts
- [ ] All methods log appropriately

**Dependencies**: Task 1, Task 2

---

### Task 5: Add exclusion endpoints to Asset Details Router

**Files**:
- `api/routers/asset_details.py` (modify existing)
- `api/dependencies.py` (may need to add service dependency)

**Description**:
Add three new endpoints to the existing asset details router:

1. **Refactor existing GET endpoint** to use service layer:
   ```python
   @router.get("/{asset_id}", response_model=AssetDetailResponse)
   async def get_asset_details(
       asset_id: str,
       service: AssetDetailsService = Depends(get_asset_details_service),
   ):
       return service.get_asset_details(asset_id)
   ```

2. **Add PUT exclusion toggle endpoint**:
   ```python
   @router.put("/{asset_id}/exclusion", response_model=AssetDetailResponse)
   async def update_asset_exclusion(
       asset_id: str,
       request: AssetExclusionUpdateRequest,
       service: AssetDetailsService = Depends(get_asset_details_service),
   ):
       return service.update_exclusion(asset_id, request.is_excluded)
   ```

3. **Add GET excluded list endpoint**:
   ```python
   @router.get("/", response_model=AssetListResponse)
   async def list_all_assets(
       service: AssetDetailsService = Depends(get_asset_details_service),
   ):
       return service.get_all_assets_with_details()
   ```

4. **Add GET excluded-only endpoint**:
   ```python
   @router.get("/excluded/list", response_model=AssetListResponse)
   async def list_excluded_assets(
       service: AssetDetailsService = Depends(get_asset_details_service),
   ):
       excluded = service.get_all_excluded_assets()
       return AssetListResponse(
           assets=excluded,
           count=len(excluded),
           excluded_count=len(excluded),
           active_count=0
       )
   ```

**Implementation Notes**:
- Add `get_asset_details_service()` dependency function in `api/dependencies.py`
- Use proper HTTP status codes (200 for success, 404 for not found, 400 for validation)
- Add proper error handling with HTTPException
- Note: The GET "/" endpoint must be defined AFTER GET "/{asset_id}" due to FastAPI routing precedence

**Acceptance Criteria**:
- [ ] Existing GET endpoint refactored to use service layer
- [ ] PUT exclusion endpoint accepts AssetExclusionUpdateRequest
- [ ] PUT endpoint returns updated AssetDetailResponse
- [ ] GET all assets endpoint returns AssetListResponse with counts
- [ ] GET excluded endpoint returns only excluded assets
- [ ] Error responses return appropriate HTTP status codes
- [ ] All endpoints properly injected with service dependency

**Dependencies**: Task 4

---

### Task 6: Write integration tests for exclusion endpoints

**Files**:
- `tests/api/routers/test_asset_details.py` (create new or modify existing)

**Description**:
Write integration tests for all asset details endpoints with focus on exclusion:

Test cases for `PUT /api/asset-details/{asset_id}/exclusion`:
- Returns 200 with correct response when updating to excluded
- Returns 200 with correct response when updating to not excluded
- Updates DynamoDB correctly
- Returns 400 for invalid request body (missing is_excluded field)
- Returns 400 for invalid is_excluded value (not boolean)

Test cases for `GET /api/asset-details`:
- Returns all assets with is_excluded field
- Returns correct excluded_count and active_count
- Handles empty table correctly
- Defaults is_excluded to false for missing field

Test cases for `GET /api/asset-details/excluded/list`:
- Returns only excluded assets
- Returns empty list when no exclusions
- Returns correct count

Test cases for `GET /api/asset-details/{asset_id}`:
- Returns asset with is_excluded field
- Defaults is_excluded to false when missing

**Implementation Notes**:
- Use FastAPI TestClient for integration tests
- Mock DynamoDBClient at the service layer
- Create realistic test data with mixed excluded/active assets
- Test request/response schemas match OpenAPI spec

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Tests use proper mocking (no real DynamoDB calls)
- [ ] Tests verify HTTP status codes
- [ ] Tests verify response schemas
- [ ] Tests cover validation errors
- [ ] Coverage: 100% of router endpoints

**Dependencies**: Task 5

---

## Phase 3: Backend Batch Processing

### Task 7: Filter excluded assets in batch alerting

**Files**:
- `saxo_order/commands/alerting.py` (modify existing)

**Description**:
Modify the `run_alerting()` function to filter out excluded assets before processing:

1. **After building the watchlist** (after combining French stocks + followup stocks):
   ```python
   # Get excluded assets from DynamoDB
   dynamodb_client = DynamoDBClient()
   excluded_asset_ids = dynamodb_client.get_excluded_assets()

   logger.info(f"Total assets in watchlist: {len(stocks)}")
   logger.info(f"Excluded assets: {excluded_asset_ids}")

   # Filter out excluded assets
   original_count = len(stocks)
   stocks = [s for s in stocks if s.code not in excluded_asset_ids]
   filtered_count = original_count - len(stocks)

   logger.info(f"Assets after exclusion filtering: {len(stocks)}")
   logger.info(f"Filtered out {filtered_count} excluded assets")
   ```

2. **Add early exit** if all assets excluded:
   ```python
   if len(stocks) == 0:
       logger.warning("All assets are excluded. No alerts will be generated.")
       post_message_to_slack("No alerts for today (all assets excluded).")
       return []
   ```

3. **Handle manual alerting** (when `--code` flag is used):
   ```python
   # Check if manually specified asset is excluded
   if code and code in excluded_asset_ids:
       logger.warning(f"Asset {code} is excluded from alerting. Skipping.")
       return []
   ```

**Implementation Notes**:
- Import DynamoDBClient at top of file if not already imported
- Add exclusion filtering logic right after watchlist construction
- Preserve existing logging patterns and conventions
- Ensure manual alerting respects exclusions
- Don't modify alert detection algorithms

**Acceptance Criteria**:
- [ ] Excluded assets filtered from watchlist before detection loop
- [ ] Logs show total assets, excluded count, and filtered count
- [ ] Logs show list of excluded asset IDs
- [ ] Early exit when all assets excluded
- [ ] Manual alerting (--code flag) respects exclusions
- [ ] No alerts generated for excluded assets
- [ ] Non-excluded assets processed normally

**Dependencies**: Task 1

---

### Task 8: Write integration tests for batch exclusion filtering

**Files**:
- `tests/commands/test_alerting.py` (create new or modify existing)

**Description**:
Write integration tests for exclusion filtering in batch alerting:

Test cases:
1. **Baseline**: Batch run with no excluded assets
   - All assets processed normally
   - All expected alerts generated

2. **Partial exclusion**: Batch run with some assets excluded
   - Excluded assets skipped
   - Non-excluded assets processed
   - Correct alerts generated only for non-excluded assets
   - Logs show filtered count

3. **All excluded**: Batch run with all assets excluded
   - No assets processed
   - No alerts generated
   - Early exit with appropriate message
   - Slack message: "No alerts for today (all assets excluded)"

4. **Manual alerting excluded asset**: Run with `--code=SAN` where SAN is excluded
   - Asset skipped
   - No alerts generated
   - Warning logged

5. **Manual alerting non-excluded asset**: Run with `--code=ITP` where ITP is not excluded
   - Asset processed normally
   - Alerts generated if conditions met

**Implementation Notes**:
- Mock DynamoDBClient.get_excluded_assets() to return test exclusion list
- Mock Saxo API calls to return test price data
- Mock Slack client to prevent actual messages
- Verify log messages contain expected text
- Use realistic test data (French stocks + followup stocks)

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Tests verify excluded assets never processed
- [ ] Tests verify non-excluded assets processed normally
- [ ] Tests verify correct log messages
- [ ] Tests verify alert generation matches expectations
- [ ] Coverage: Exclusion filtering logic in batch processing

**Dependencies**: Task 7

---

## Phase 4: Backend Alert Retrieval Filtering

### Task 9: Filter excluded asset alerts in AlertingService

**Files**:
- `api/services/alerting_service.py` (modify existing)

**Description**:
Modify `AlertingService.get_all_alerts()` to filter out alerts from excluded assets:

1. **Add exclusion filtering** after retrieving alerts from DynamoDB:
   ```python
   def get_all_alerts(
       self,
       asset_code: Optional[str] = None,
       alert_type: Optional[str] = None,
       country_code: Optional[str] = None,
   ) -> AlertsResponse:
       # Existing code: fetch alerts from DynamoDB
       alerts = self.dynamodb_client.get_all_alerts()

       # NEW: Filter out alerts from excluded assets
       excluded_asset_ids = self.dynamodb_client.get_excluded_assets()
       original_count = len(alerts)
       alerts = [a for a in alerts if a.asset_code not in excluded_asset_ids]
       filtered_count = original_count - len(alerts)

       if filtered_count > 0:
           self.logger.info(f"Filtered {filtered_count} alerts from excluded assets")

       # Continue with existing filtering logic (asset_code, alert_type, etc.)
       ...
   ```

2. **Update available filters** to exclude excluded assets:
   ```python
   def _calculate_filters(self, alerts: List[Alert]) -> Dict:
       # Existing filter calculation
       available_asset_codes = list(set([a.asset_code for a in alerts]))

       # NEW: Remove excluded assets from available filters
       excluded_asset_ids = self.dynamodb_client.get_excluded_assets()
       available_asset_codes = [
           code for code in available_asset_codes
           if code not in excluded_asset_ids
       ]

       # Continue with rest of filter calculation
       ...
   ```

**Implementation Notes**:
- Call `get_excluded_assets()` once per request (could be cached if needed)
- Apply exclusion filter BEFORE applying user-specified filters
- Don't modify alert objects themselves
- Preserve existing sorting and pagination logic
- Log filtered count for debugging

**Acceptance Criteria**:
- [ ] Alerts from excluded assets never returned by API
- [ ] Exclusion filtering applied before user filters
- [ ] Available filter options don't include excluded assets
- [ ] Non-excluded alerts returned normally
- [ ] Sorting and pagination work correctly
- [ ] Logs show filtered count when > 0

**Dependencies**: Task 1

---

### Task 10: Write unit tests for alert exclusion filtering

**Files**:
- `tests/api/services/test_alerting_service.py` (modify existing)

**Description**:
Add unit tests for exclusion filtering in AlertingService:

Test cases:
1. **No excluded assets**: Get all alerts with no exclusions
   - All alerts returned
   - No filtering applied

2. **Some excluded assets**: Get all alerts with some assets excluded
   - Excluded asset alerts filtered out
   - Non-excluded alerts returned
   - Correct count

3. **All alerts from excluded assets**: Get all alerts when all are excluded
   - Empty result set
   - No alerts returned

4. **Filter options exclude excluded assets**: Get available filters
   - Excluded asset codes not in available_asset_codes
   - Only non-excluded assets appear in filters

5. **User filter + exclusion filter**: Apply both user filter and exclusion
   - Both filters applied correctly
   - Correct alerts returned

**Implementation Notes**:
- Mock DynamoDBClient.get_excluded_assets() to return test exclusion list
- Mock DynamoDBClient.get_all_alerts() to return test alerts
- Create test data with mix of excluded and non-excluded assets
- Verify correct filtering logic

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Tests verify correct filtering behavior
- [ ] Tests verify filter options exclude excluded assets
- [ ] Tests verify interaction between user filters and exclusion
- [ ] Coverage: 100% of exclusion filtering logic

**Dependencies**: Task 9

---

## Phase 5: Frontend - Exclusion Management Page

### Task 11: Create AssetExclusions page component

**Files**:
- `frontend/src/pages/AssetExclusions.tsx` (create new)

**Description**:
Create dedicated page for viewing and managing asset exclusions:

**Features**:
1. **Data Fetching**:
   - Fetch all assets on mount: `GET /api/asset-details`
   - Show loading state while fetching
   - Handle errors with error message

2. **Two Sections**:
   - "Excluded Assets" section (is_excluded=true)
   - "Active Assets" section (is_excluded=false)
   - Show count for each section

3. **Asset Display**:
   - Asset ID (clickable if TradingView URL exists)
   - TradingView link icon (if URL exists)
   - Toggle button: "Un-exclude" for excluded, "Exclude" for active
   - Last updated timestamp

4. **Search/Filter**:
   - Search box to filter by asset ID
   - Real-time filtering as user types

5. **Toggle Functionality**:
   - Click toggle button → show confirmation dialog
   - On confirm → call `PUT /api/asset-details/{asset_id}/exclusion`
   - Show loading state on button during API call
   - Update UI immediately on success
   - Show error toast on failure
   - Move asset between sections after successful toggle

6. **Empty States**:
   - "No excluded assets" when exclusion list is empty
   - "No active assets" when all assets excluded (rare)

**Implementation Notes**:
- Use React hooks (useState, useEffect) for state management
- Use axios for API calls
- Follow existing page structure patterns (e.g., Alerts.tsx)
- Use existing component library for buttons, dialogs, inputs
- Implement confirmation dialog before exclusion changes
- Show toast notifications for success/error

**Acceptance Criteria**:
- [ ] Page fetches and displays all assets on mount
- [ ] Assets grouped into excluded and active sections
- [ ] Each section shows correct count
- [ ] Search/filter box filters assets in real-time
- [ ] Toggle button shows confirmation dialog
- [ ] API call updates exclusion status correctly
- [ ] UI updates immediately after successful toggle
- [ ] Loading states display during API calls
- [ ] Error states handled gracefully
- [ ] Empty states display correctly
- [ ] TradingView links work correctly

**Dependencies**: Task 5

---

### Task 12: Add AssetExclusions page to routing

**Files**:
- `frontend/src/App.tsx` (modify existing)

**Description**:
Add route for AssetExclusions page to the application:

1. **Import component**:
   ```typescript
   import AssetExclusions from './pages/AssetExclusions';
   ```

2. **Add route** (using React Router DOM v7+):
   ```typescript
   <Route path="/exclusions" element={<AssetExclusions />} />
   ```

3. **Add navigation link** in sidebar/header:
   ```typescript
   <Link to="/exclusions">Asset Exclusions</Link>
   ```
   or
   ```typescript
   <Link to="/exclusions">Manage Exclusions</Link>
   ```

**Implementation Notes**:
- Follow existing routing patterns
- Add navigation link in appropriate location (likely near "Alerts" link)
- Use consistent styling for navigation link
- Ensure route is accessible from all pages

**Acceptance Criteria**:
- [ ] Route registered correctly in App.tsx
- [ ] Navigation to /exclusions renders AssetExclusions page
- [ ] Navigation link visible in sidebar/header
- [ ] Link styling consistent with other navigation links
- [ ] Deep linking works: Direct navigation to /exclusions URL

**Dependencies**: Task 11

---

### Task 13: Extend frontend API service for exclusions

**Files**:
- `frontend/src/services/api.ts` (modify existing)

**Description**:
Add API methods for asset exclusion management:

```typescript
// Get all assets with details
export const assetDetailsService = {
  // Get all assets
  getAllAssets: async (): Promise<AssetListResponse> => {
    const response = await axios.get(`${API_URL}/api/asset-details`);
    return response.data;
  },

  // Get only excluded assets
  getExcludedAssets: async (): Promise<AssetListResponse> => {
    const response = await axios.get(`${API_URL}/api/asset-details/excluded/list`);
    return response.data;
  },

  // Update exclusion status
  updateExclusion: async (
    assetId: string,
    isExcluded: boolean
  ): Promise<AssetDetailResponse> => {
    const response = await axios.put(
      `${API_URL}/api/asset-details/${assetId}/exclusion`,
      { is_excluded: isExcluded }
    );
    return response.data;
  },

  // Get single asset details
  getAssetDetails: async (assetId: string): Promise<AssetDetailResponse> => {
    const response = await axios.get(`${API_URL}/api/asset-details/${assetId}`);
    return response.data;
  },
};
```

**TypeScript Interfaces**:
```typescript
interface AssetDetailResponse {
  asset_id: string;
  tradingview_url?: string;
  updated_at?: string;
  is_excluded?: boolean;
}

interface AssetListResponse {
  assets: AssetDetailResponse[];
  count: number;
  excluded_count?: number;
  active_count?: number;
}
```

**Implementation Notes**:
- Use existing axios instance with API_URL from env
- Follow existing API service patterns
- Add proper TypeScript types
- Handle errors appropriately (axios will throw on non-2xx)

**Acceptance Criteria**:
- [ ] All methods defined with correct signatures
- [ ] Methods call correct API endpoints
- [ ] TypeScript interfaces match backend Pydantic models
- [ ] Methods use existing axios configuration
- [ ] Error handling follows existing patterns

**Dependencies**: Task 5

---

## Phase 6: Frontend - Alert View Integration

### Task 14: Add exclusion indicator to AlertCard (optional)

**Files**:
- `frontend/src/components/AlertCard.tsx` (modify existing)

**Description**:
Add visual indicator when viewing details about an asset's exclusion status:

**Note**: This is informational only - excluded asset alerts shouldn't appear in the view due to backend filtering. This is useful for debugging or edge cases where exclusion just changed.

1. **Add small badge/chip** to alert card:
   ```typescript
   {alert.is_excluded && (
     <span className="badge badge-warning">
       Excluded
     </span>
   )}
   ```

2. **Styling**:
   - Small, subtle badge (not prominent)
   - Warning color (yellow/orange)
   - Position: Near asset name or in metadata section

**Implementation Notes**:
- Only show badge if `is_excluded=true` (shouldn't happen in normal operation)
- Use existing badge/chip component from design system
- Keep it subtle - this is debug info, not primary feature

**Acceptance Criteria**:
- [ ] Badge displays when is_excluded=true
- [ ] Badge hidden when is_excluded=false
- [ ] Badge styling follows design system
- [ ] Badge doesn't disrupt card layout

**Dependencies**: Task 9 (backend filtering must be in place first)

---

### Task 15: Add inline exclusion toggle to AlertCard (optional enhancement)

**Files**:
- `frontend/src/components/AlertCard.tsx` (modify existing)
- `frontend/src/components/ExclusionToggle.tsx` (create new)

**Description**:
Add quick-action toggle button to exclude/un-exclude asset directly from alert card:

1. **Create ExclusionToggle component**:
   ```typescript
   interface ExclusionToggleProps {
     assetId: string;
     isExcluded: boolean;
     onToggle: (assetId: string, newStatus: boolean) => void;
   }

   export function ExclusionToggle({ assetId, isExcluded, onToggle }: ExclusionToggleProps) {
     const [loading, setLoading] = useState(false);

     const handleToggle = async () => {
       const confirmed = window.confirm(
         `Are you sure you want to ${isExcluded ? 'un-exclude' : 'exclude'} ${assetId}?`
       );
       if (!confirmed) return;

       setLoading(true);
       try {
         await assetDetailsService.updateExclusion(assetId, !isExcluded);
         onToggle(assetId, !isExcluded);
         // Show success toast
       } catch (error) {
         // Show error toast
       } finally {
         setLoading(false);
       }
     };

     return (
       <button onClick={handleToggle} disabled={loading}>
         {loading ? 'Loading...' : (isExcluded ? 'Un-exclude' : 'Exclude')}
       </button>
     );
   }
   ```

2. **Integrate into AlertCard**:
   - Add ExclusionToggle to card actions section
   - Pass asset_id and is_excluded props
   - Handle onToggle callback to update local state

3. **User Flow**:
   - User clicks "Exclude" button
   - Confirmation dialog appears
   - On confirm, API call made
   - Loading state shown on button
   - Success: Toast notification, alert remains visible (filtered on next page load)
   - Error: Toast notification, no change

**Implementation Notes**:
- This is a convenience feature (optional enhancement)
- Main exclusion management still via /exclusions page
- Alert remains visible until page refresh (backend will filter on next load)
- Use existing toast notification system
- Follow existing button/action patterns

**Acceptance Criteria**:
- [ ] ExclusionToggle component renders correctly
- [ ] Confirmation dialog appears before API call
- [ ] Loading state displays during API call
- [ ] Success toast shows after successful toggle
- [ ] Error toast shows on failure
- [ ] Button disabled during loading
- [ ] onToggle callback updates parent state

**Dependencies**: Task 13, Task 14

---

### Task 16: Add exclusion info and navigation to Alerts page

**Files**:
- `frontend/src/pages/Alerts.tsx` (modify existing)

**Description**:
Add informational section and navigation link for exclusion management:

1. **Add info banner** at top of page:
   ```typescript
   <div className="info-banner">
     <p>
       Alerts from excluded assets are automatically hidden.
       <Link to="/exclusions">Manage exclusions</Link>
     </p>
   </div>
   ```

2. **Styling**:
   - Subtle background color (info blue or light gray)
   - Small icon (info icon)
   - Clear, concise text
   - Prominent link to /exclusions page

**Implementation Notes**:
- Banner should be dismissible (optional)
- Only show if user hasn't seen it before (localStorage flag)
- Keep it minimal and non-intrusive

**Acceptance Criteria**:
- [ ] Info banner displays on Alerts page
- [ ] Banner explains exclusion feature
- [ ] Link to /exclusions page works correctly
- [ ] Banner styling follows design system
- [ ] Banner dismissible (if implemented)

**Dependencies**: Task 12

---

## Phase 7: Testing & Documentation

### Task 17: End-to-end testing

**Files**:
- Manual testing (no code changes)

**Description**:
Perform comprehensive end-to-end testing of the entire exclusion feature:

**Test Scenarios**:

1. **Exclude asset via UI**:
   - Navigate to /exclusions page
   - Find an active asset (e.g., "SAN")
   - Click "Exclude" button
   - Confirm in dialog
   - Verify: Asset moves to excluded section
   - Verify: DynamoDB updated (check AWS console or CLI)

2. **Verify batch run respects exclusion**:
   - Wait for next scheduled batch run OR trigger manually
   - Check CloudWatch logs
   - Verify: Excluded asset skipped in logs
   - Verify: Excluded asset count logged
   - Verify: No alerts generated for excluded asset

3. **Verify alert view filters excluded alerts**:
   - Navigate to /alerts page
   - Verify: No alerts for excluded asset displayed
   - Verify: Excluded asset not in filter dropdown

4. **Un-exclude asset**:
   - Navigate to /exclusions page
   - Find excluded asset
   - Click "Un-exclude" button
   - Confirm in dialog
   - Verify: Asset moves to active section
   - Verify: DynamoDB updated

5. **Verify manual alerting respects exclusion**:
   - Exclude asset "SAN"
   - Run: `poetry run k-order alerting --code=SAN --country-code=xpar`
   - Verify: Logs show asset skipped
   - Verify: No alerts generated

6. **Performance test**:
   - Exclude 10 assets
   - Note baseline batch run time
   - Verify: Batch run time reduced by ~10%
   - Check logs for filtering count

7. **Edge cases**:
   - Exclude all assets → verify early exit with appropriate message
   - Exclude asset mid-batch run → verify takes effect on next run
   - Exclude non-existent asset → verify handled gracefully

**Acceptance Criteria**:
- [ ] All test scenarios pass successfully
- [ ] Exclusion status persists in DynamoDB
- [ ] Batch runs respect exclusions
- [ ] Alert view filters excluded assets
- [ ] Manual alerting respects exclusions
- [ ] UI updates immediately after toggle
- [ ] Performance improvement observed
- [ ] Edge cases handled gracefully

**Dependencies**: All previous tasks

---

### Task 18: Update documentation

**Files**:
- `specs/001-alerts-ui-page/quickstart.md` (modify existing)
- `README.md` (modify if needed)

**Description**:
Update project documentation to include exclusion feature:

1. **Update quickstart.md**:
   - Add "Asset Exclusion" section after "Alert View" section
   - Document how to access exclusion management page
   - Document exclusion toggle functionality
   - Document how exclusions affect batch runs
   - Document API endpoints for exclusion

   ```markdown
   ## Asset Exclusion

   ### Overview
   Assets can be excluded from alert processing to reduce noise and improve batch run efficiency.

   ### Accessing Exclusion Management
   1. Navigate to `/exclusions` or click "Manage Exclusions" in the sidebar
   2. View excluded and active assets in separate sections
   3. Use search box to quickly find assets

   ### Excluding/Un-excluding Assets
   1. Find asset in the appropriate section
   2. Click "Exclude" or "Un-exclude" button
   3. Confirm in dialog
   4. Changes take effect on next batch run (within 24 hours)

   ### Effects of Exclusion
   - Excluded assets skipped during batch alerting runs
   - No alerts generated for excluded assets
   - Existing alerts for excluded assets hidden from alert view
   - Batch run time reduced proportionally to number of exclusions

   ### API Endpoints
   - `GET /api/asset-details` - Get all assets with exclusion status
   - `PUT /api/asset-details/{asset_id}/exclusion` - Toggle exclusion
   - `GET /api/asset-details/excluded/list` - Get only excluded assets
   ```

2. **Update README.md** (if it contains feature list):
   - Add bullet point for asset exclusion feature
   - Link to quickstart for details

**Acceptance Criteria**:
- [ ] quickstart.md updated with exclusion section
- [ ] Documentation clear and comprehensive
- [ ] Examples provided for common operations
- [ ] API endpoints documented
- [ ] README.md updated (if applicable)

**Dependencies**: Task 17

---

### Task 19: Create OpenAPI specification for exclusion endpoints

**Files**:
- `specs/001-alerts-ui-page/contracts/asset-exclusion-api.yaml` (create new)

**Description**:
Document exclusion API endpoints in OpenAPI 3.0 format:

```yaml
openapi: 3.0.0
info:
  title: Asset Exclusion API
  version: 1.0.0
  description: API endpoints for managing asset exclusions in alerting system

servers:
  - url: http://localhost:8000
    description: Local development
  - url: https://your-api-url.com
    description: Production

paths:
  /api/asset-details:
    get:
      summary: Get all assets with details
      description: Returns all assets including exclusion status and counts
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetListResponse'
        '500':
          description: Internal server error

  /api/asset-details/{asset_id}:
    get:
      summary: Get single asset details
      parameters:
        - name: asset_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetDetailResponse'
        '404':
          description: Asset not found
        '500':
          description: Internal server error

  /api/asset-details/{asset_id}/exclusion:
    put:
      summary: Update asset exclusion status
      parameters:
        - name: asset_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AssetExclusionUpdateRequest'
      responses:
        '200':
          description: Successful update
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetDetailResponse'
        '400':
          description: Invalid request body
        '500':
          description: Internal server error

  /api/asset-details/excluded/list:
    get:
      summary: Get only excluded assets
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetListResponse'
        '500':
          description: Internal server error

components:
  schemas:
    AssetDetailResponse:
      type: object
      properties:
        asset_id:
          type: string
          example: "SAN"
        tradingview_url:
          type: string
          nullable: true
          example: "https://www.tradingview.com/chart/?symbol=XPAR:SAN"
        updated_at:
          type: string
          format: date-time
          nullable: true
          example: "2026-01-26T10:30:00Z"
        is_excluded:
          type: boolean
          default: false
          example: true

    AssetListResponse:
      type: object
      properties:
        assets:
          type: array
          items:
            $ref: '#/components/schemas/AssetDetailResponse'
        count:
          type: integer
          example: 50
        excluded_count:
          type: integer
          nullable: true
          example: 10
        active_count:
          type: integer
          nullable: true
          example: 40

    AssetExclusionUpdateRequest:
      type: object
      required:
        - is_excluded
      properties:
        is_excluded:
          type: boolean
          example: true
```

**Acceptance Criteria**:
- [ ] OpenAPI spec created with all endpoints documented
- [ ] Request/response schemas defined
- [ ] Examples provided for all schemas
- [ ] Error responses documented
- [ ] Spec validates correctly (use OpenAPI validator)

**Dependencies**: Task 5

---

### Task 20: Performance validation

**Files**:
- Manual testing (document results)

**Description**:
Measure and validate performance improvements from asset exclusion:

**Measurements**:

1. **Baseline batch run** (0 exclusions):
   - Run: `poetry run k-order alerting`
   - Record: Start time, end time, total duration
   - Record: Number of assets processed
   - Record: Number of alerts generated

2. **Batch run with 5 exclusions**:
   - Exclude 5 assets (~10% of typical watchlist)
   - Run: `poetry run k-order alerting`
   - Record: Start time, end time, total duration
   - Record: Number of assets processed
   - Record: Number of alerts generated
   - Calculate: Time reduction percentage

3. **Batch run with 10 exclusions**:
   - Exclude 10 assets (~20% of typical watchlist)
   - Run: `poetry run k-order alerting`
   - Record: Same metrics as above

4. **API performance** (GET /api/alerts):
   - Measure baseline response time (no exclusions)
   - Measure response time with 10 exclusions
   - Verify: No significant degradation (<50ms difference)

5. **UI performance**:
   - Measure exclusion toggle response time (button click to UI update)
   - Target: <1 second
   - Measure exclusion management page load time
   - Target: <2 seconds

**Expected Results**:
- Batch run time reduction: ~2% per excluded asset (10 exclusions = ~20% faster)
- API response time: No significant degradation
- UI toggle response: <1 second
- UI page load: <2 seconds

**Documentation**:
Create `specs/001-alerts-ui-page/performance-results.md` with results:
```markdown
# Performance Validation Results

## Batch Run Performance

| Exclusions | Assets Processed | Duration | Reduction |
|------------|------------------|----------|-----------|
| 0          | 50               | 300s     | Baseline  |
| 5          | 45               | 270s     | 10%       |
| 10         | 40               | 240s     | 20%       |

## API Performance

| Metric | Value |
|--------|-------|
| Baseline response time | 450ms |
| With 10 exclusions | 480ms |
| Difference | 30ms (acceptable) |

## UI Performance

| Operation | Time |
|-----------|------|
| Exclusion toggle | 850ms |
| Page load | 1.2s |

## Conclusions
- Performance targets met ✓
- Proportional time reduction achieved ✓
- No significant API degradation ✓
```

**Acceptance Criteria**:
- [ ] Baseline measurements recorded
- [ ] Exclusion measurements recorded
- [ ] Performance improvement validated (proportional reduction)
- [ ] API performance validated (no significant degradation)
- [ ] UI performance validated (meets targets)
- [ ] Results documented in performance-results.md

**Dependencies**: Task 17

---

## Summary

**Total Tasks**: 20
**Estimated Effort**: 15-20 hours
**Phases**: 7

**Phase Breakdown**:
- Phase 1 (Data Layer): Tasks 1-3 (3-4 hours)
- Phase 2 (API Layer): Tasks 4-6 (3-4 hours)
- Phase 3 (Batch Processing): Tasks 7-8 (2-3 hours)
- Phase 4 (Alert Filtering): Tasks 9-10 (2 hours)
- Phase 5 (Frontend Page): Tasks 11-13 (3-4 hours)
- Phase 6 (Frontend Integration): Tasks 14-16 (1-2 hours)
- Phase 7 (Testing & Docs): Tasks 17-20 (2-3 hours)

**Critical Path**:
Task 1 → Task 4 → Task 5 → Task 7 → Task 9 → Task 11 → Task 12 → Task 17

**Parallel Work Opportunities**:
- Tasks 2 and 3 can be done in parallel with Task 1
- Tasks 6 and 7 can be done in parallel after Task 5
- Tasks 9-10 can be done in parallel with Tasks 7-8
- Tasks 11-13 can all start after Task 5 completes

**Testing Coverage**:
- Unit tests: Tasks 3, 10
- Integration tests: Tasks 6, 8
- End-to-end tests: Task 17
- Performance tests: Task 20

**Optional Enhancements**:
- Task 14 (exclusion indicator badge) - informational only
- Task 15 (inline toggle) - convenience feature

---

## Implementation Notes

### Commit Strategy

Follow conventional commit format for each task:

- Task 1-3: `feat(backend): add asset exclusion data layer`
- Task 4-6: `feat(api): add asset exclusion endpoints`
- Task 7-8: `feat(alerting): filter excluded assets in batch runs`
- Task 9-10: `feat(api): filter excluded alerts from responses`
- Task 11-13: `feat(frontend): add asset exclusion management page`
- Task 14-16: `feat(frontend): integrate exclusion in alert view`
- Task 17-20: `test: validate exclusion feature end-to-end`

### Testing Strategy

- Write tests alongside implementation (not after)
- Aim for 100% coverage of new code
- Use mocks liberally (no real AWS calls in tests)
- Test edge cases and error conditions

### Deployment Strategy

- Deploy backend first (Tasks 1-10)
- Verify backend works via API testing
- Deploy frontend (Tasks 11-16)
- Verify end-to-end functionality
- Monitor logs and metrics

### Rollback Plan

If issues arise:
1. Frontend rollback: Revert frontend deployment (feature is UI-only)
2. Backend rollback: Revert API deployment (new endpoints won't be called)
3. Database rollback: Not needed (new field defaults to false)

---

**Status**: ✅ **READY FOR IMPLEMENTATION**

**Next Step**: Begin with Task 1 - Add exclusion methods to DynamoDB client
