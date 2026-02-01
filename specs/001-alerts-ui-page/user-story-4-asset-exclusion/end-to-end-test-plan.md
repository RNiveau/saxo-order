# End-to-End Test Plan: Asset Exclusion Feature

**Feature**: User Story 4 - Asset Exclusion
**Date**: 2026-01-26
**Status**: Testing

## Test Environment

- **Backend**: Python 3.11, FastAPI
- **Frontend**: TypeScript 5+, React 19, Vite
- **Database**: DynamoDB (`asset_details` table)
- **Prerequisites**:
  - Backend server running on `http://localhost:8000`
  - Frontend dev server running on `http://localhost:5173`
  - AWS credentials configured for DynamoDB access

## Test Scenarios

### 1. Backend API Testing

#### 1.1 Get All Assets with Details
```bash
# Test: Retrieve all assets with exclusion status
curl -X GET "http://localhost:8000/api/asset-details" | jq

# Expected: 200 OK with list of assets
# Verify: Response includes is_excluded field for all assets
# Verify: Count fields (count, excluded_count, active_count) are present
```

#### 1.2 Get Single Asset Details
```bash
# Test: Retrieve specific asset details
curl -X GET "http://localhost:8000/api/asset-details/SAN" | jq

# Expected: 200 OK with asset details
# Verify: is_excluded field is present
# Verify: tradingview_url and updated_at fields are included
```

#### 1.3 Exclude an Asset
```bash
# Test: Exclude asset SAN from alerting
curl -X PUT "http://localhost:8000/api/asset-details/SAN/exclusion" \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": true}' | jq

# Expected: 200 OK with updated asset details
# Verify: is_excluded is true
# Verify: updated_at timestamp is recent
```

#### 1.4 Un-exclude an Asset
```bash
# Test: Un-exclude asset SAN
curl -X PUT "http://localhost:8000/api/asset-details/SAN/exclusion" \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": false}' | jq

# Expected: 200 OK with updated asset details
# Verify: is_excluded is false
# Verify: updated_at timestamp is updated
```

#### 1.5 Get Excluded Assets Only
```bash
# Test: Retrieve only excluded assets
curl -X GET "http://localhost:8000/api/asset-details/excluded/list" | jq

# Expected: 200 OK with list of excluded assets only
# Verify: All assets in list have is_excluded = true
# Verify: excluded_count equals count
# Verify: active_count is 0
```

#### 1.6 Error Handling - Invalid Asset
```bash
# Test: Try to update non-existent asset
curl -X PUT "http://localhost:8000/api/asset-details/INVALID/exclusion" \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": true}' | jq

# Expected: 404 Not Found
# Verify: Error message is descriptive
```

#### 1.7 Error Handling - Invalid Request Body
```bash
# Test: Send invalid request body
curl -X PUT "http://localhost:8000/api/asset-details/SAN/exclusion" \
  -H "Content-Type: application/json" \
  -d '{"invalid_field": true}' | jq

# Expected: 400 Bad Request or 422 Unprocessable Entity
# Verify: Error message indicates missing required field
```

### 2. Frontend UI Testing

#### 2.1 Asset Exclusions Page Access
**Steps**:
1. Navigate to `http://localhost:5173`
2. Click on "Asset Exclusions" in the sidebar (🚫 icon)
3. Verify URL changes to `/exclusions`
4. Verify page loads successfully

**Expected Results**:
- Page displays with two sections: "Excluded Assets" and "Active Assets"
- Search bar is visible at the top
- Asset counts are displayed in section headers

#### 2.2 View All Assets
**Steps**:
1. On Asset Exclusions page, observe both sections
2. Note the count of excluded vs active assets

**Expected Results**:
- All assets from DynamoDB are displayed
- Assets are correctly categorized (excluded vs active)
- Each asset shows: Asset ID, TradingView URL (if available), Last Updated timestamp

#### 2.3 Search Functionality
**Steps**:
1. Type "SAN" in the search bar
2. Observe filtered results
3. Clear search and verify all assets reappear

**Expected Results**:
- Only assets matching "SAN" are displayed
- Search is case-insensitive
- Both excluded and active sections update
- Clearing search shows all assets again

#### 2.4 Exclude an Asset
**Steps**:
1. Find an active asset (e.g., "ITP")
2. Click the "Exclude" button
3. Confirm the action in the confirmation dialog
4. Observe the result

**Expected Results**:
- Confirmation dialog appears asking "Are you sure you want to exclude ITP?"
- After confirmation, asset moves from Active to Excluded section
- Button changes to "Un-exclude"
- Section counts update immediately
- No page reload required

#### 2.5 Un-exclude an Asset
**Steps**:
1. Find an excluded asset (e.g., "SAN")
2. Click the "Un-exclude" button
3. Confirm the action in the confirmation dialog
4. Observe the result

**Expected Results**:
- Confirmation dialog appears asking "Are you sure you want to un-exclude SAN?"
- After confirmation, asset moves from Excluded to Active section
- Button changes to "Exclude"
- Section counts update immediately
- No page reload required

#### 2.6 Error Handling - Network Failure
**Steps**:
1. Stop the backend server
2. Try to exclude an asset
3. Observe error handling

**Expected Results**:
- Error message is displayed to user
- UI remains responsive
- Asset state doesn't change

#### 2.7 Alerts Page Info Banner
**Steps**:
1. Navigate to Alerts page (`/`)
2. Observe the info banner above filter controls
3. Click "Manage exclusions" link

**Expected Results**:
- Info banner is visible with text: "Alerts from excluded assets are automatically hidden"
- Link navigates to `/exclusions` page
- Banner has distinct visual styling (blue background)

#### 2.8 Sidebar Navigation
**Steps**:
1. Navigate between pages using sidebar
2. Verify "Asset Exclusions" link is present
3. Verify active state highlighting works

**Expected Results**:
- "Asset Exclusions" link is visible in sidebar with 🚫 icon
- Active page is highlighted in sidebar
- All navigation links work correctly

### 3. Integration Testing

#### 3.1 Complete Exclusion Workflow
**Steps**:
1. **Baseline**: Note current alert count on Alerts page
2. **Exclude**: Exclude asset "SAN" from Asset Exclusions page
3. **Verify Alerts**: Go to Alerts page, verify SAN alerts are hidden
4. **Batch Run**: Trigger batch alerting (if possible in test environment)
5. **Verify Filtering**: Confirm SAN is skipped during detection
6. **Un-exclude**: Un-exclude "SAN"
7. **Verify Restoration**: Check that SAN alerts reappear (if any exist)

**Expected Results**:
- SAN alerts are immediately hidden after exclusion
- Batch alerting skips SAN (check logs)
- Un-excluding restores visibility of existing SAN alerts
- Filter dropdowns on Alerts page don't show excluded assets

#### 3.2 Multiple Asset Exclusion
**Steps**:
1. Exclude multiple assets (e.g., SAN, BNP, ITP)
2. Navigate to Alerts page
3. Verify all excluded asset alerts are hidden
4. Check filter dropdowns
5. Un-exclude one asset
6. Verify its alerts reappear

**Expected Results**:
- All excluded asset alerts are hidden
- Filter dropdowns don't include excluded assets
- Partial un-exclusion works correctly
- Counts update accurately

#### 3.3 Backward Compatibility
**Steps**:
1. Check assets that don't have `is_excluded` field in DynamoDB
2. Verify they appear as "Active" by default
3. Toggle exclusion on such an asset
4. Verify `is_excluded` field is added to DynamoDB

**Expected Results**:
- Missing `is_excluded` defaults to false (active)
- No errors when toggling exclusion on legacy assets
- Database is updated correctly

#### 3.4 Concurrent User Actions
**Steps**:
1. Open Asset Exclusions page in two browser tabs
2. In Tab 1, exclude asset "SAN"
3. In Tab 2, refresh the page
4. Verify Tab 2 shows updated state

**Expected Results**:
- Tab 2 reflects the exclusion after refresh
- No data inconsistencies
- Both tabs can make updates independently

### 4. Performance Testing

#### 4.1 Asset List Load Time
**Steps**:
1. Open browser DevTools Network tab
2. Navigate to Asset Exclusions page
3. Measure time to load asset list

**Expected Results**:
- Initial load completes in < 2 seconds
- No unnecessary API calls
- Data is cached appropriately

#### 4.2 Exclusion Toggle Responsiveness
**Steps**:
1. Time the exclusion toggle operation
2. Measure from button click to UI update

**Expected Results**:
- Toggle operation completes in < 500ms
- UI feedback is immediate (optimistic update if possible)
- No UI blocking during operation

#### 4.3 Batch Alerting Performance
**Steps**:
1. Measure batch alerting runtime with 0 exclusions
2. Exclude 50% of assets
3. Measure batch alerting runtime again
4. Compare runtimes

**Expected Results**:
- Runtime reduction is proportional to excluded asset count
- Filtering overhead is negligible (< 100ms)
- Logs show correct filtered counts

#### 4.4 Search Performance
**Steps**:
1. Load Asset Exclusions page with 100+ assets
2. Type quickly in search bar
3. Observe responsiveness

**Expected Results**:
- Search results update smoothly
- No lag or freezing
- Debouncing works correctly (if implemented)

### 5. Data Integrity Testing

#### 5.1 DynamoDB Verification
**Steps**:
1. Use AWS CLI or Console to inspect `asset_details` table
2. Verify `is_excluded` field is set correctly
3. Check `updated_at` timestamp updates

**Commands**:
```bash
# Check asset exclusion status in DynamoDB
aws dynamodb get-item \
  --table-name asset_details \
  --key '{"asset_id": {"S": "SAN"}}'

# Scan for all excluded assets
aws dynamodb scan \
  --table-name asset_details \
  --filter-expression "is_excluded = :true_val" \
  --expression-attribute-values '{":true_val": {"BOOL": true}}'
```

**Expected Results**:
- `is_excluded` field exists with correct boolean value
- `updated_at` is an ISO 8601 timestamp
- No orphaned or corrupted data

#### 5.2 Alert Filtering Integrity
**Steps**:
1. Query alerts API directly
2. Verify excluded assets are not in results
3. Check available filters don't include excluded assets

**Commands**:
```bash
# Get all alerts
curl -X GET "http://localhost:8000/api/alerts/all" | jq

# Check available filters
curl -X GET "http://localhost:8000/api/alerts/all" | jq '.available_filters'
```

**Expected Results**:
- No alerts from excluded assets in response
- `available_filters.asset_codes` doesn't include excluded assets
- Alert counts are accurate

### 6. Edge Cases

#### 6.1 All Assets Excluded
**Steps**:
1. Exclude all assets
2. Navigate to Alerts page
3. Trigger batch alerting (if possible)

**Expected Results**:
- Alerts page shows "No active alerts" message
- Batch alerting skips all assets
- Slack notification sent: "No alerts for today (all assets excluded)"
- No errors or crashes

#### 6.2 Rapid Toggle
**Steps**:
1. Rapidly click Exclude/Un-exclude on same asset
2. Observe behavior

**Expected Results**:
- UI handles rapid clicks gracefully
- Final state matches last successful API call
- No race conditions or data corruption

#### 6.3 Empty Database
**Steps**:
1. Test with empty `asset_details` table
2. Navigate to Asset Exclusions page

**Expected Results**:
- Page shows "No assets found" or similar message
- No JavaScript errors
- UI remains functional

#### 6.4 Asset Without TradingView URL
**Steps**:
1. Find an asset without custom TradingView URL
2. Verify it displays correctly
3. Toggle exclusion

**Expected Results**:
- Asset displays "N/A" or empty for TradingView URL
- Exclusion toggle works normally
- No errors

## Test Results

### Backend API Tests
| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 1.1 | Get all assets | ⏳ Pending | |
| 1.2 | Get single asset | ⏳ Pending | |
| 1.3 | Exclude asset | ⏳ Pending | |
| 1.4 | Un-exclude asset | ⏳ Pending | |
| 1.5 | Get excluded only | ⏳ Pending | |
| 1.6 | Invalid asset error | ⏳ Pending | |
| 1.7 | Invalid body error | ⏳ Pending | |

### Frontend UI Tests
| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 2.1 | Page access | ⏳ Pending | |
| 2.2 | View all assets | ⏳ Pending | |
| 2.3 | Search functionality | ⏳ Pending | |
| 2.4 | Exclude asset | ⏳ Pending | |
| 2.5 | Un-exclude asset | ⏳ Pending | |
| 2.6 | Error handling | ⏳ Pending | |
| 2.7 | Alerts info banner | ⏳ Pending | |
| 2.8 | Sidebar navigation | ⏳ Pending | |

### Integration Tests
| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 3.1 | Complete workflow | ⏳ Pending | |
| 3.2 | Multiple exclusions | ⏳ Pending | |
| 3.3 | Backward compatibility | ⏳ Pending | |
| 3.4 | Concurrent actions | ⏳ Pending | |

### Performance Tests
| Test ID | Description | Status | Target | Actual | Notes |
|---------|-------------|--------|--------|--------|-------|
| 4.1 | List load time | ⏳ Pending | < 2s | | |
| 4.2 | Toggle response | ⏳ Pending | < 500ms | | |
| 4.3 | Batch performance | ⏳ Pending | Proportional | | |
| 4.4 | Search performance | ⏳ Pending | Smooth | | |

### Data Integrity Tests
| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 5.1 | DynamoDB verification | ⏳ Pending | |
| 5.2 | Alert filtering | ⏳ Pending | |

### Edge Case Tests
| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 6.1 | All assets excluded | ⏳ Pending | |
| 6.2 | Rapid toggle | ⏳ Pending | |
| 6.3 | Empty database | ⏳ Pending | |
| 6.4 | Missing TradingView URL | ⏳ Pending | |

## Sign-off

- [ ] All backend API tests passing
- [ ] All frontend UI tests passing
- [ ] All integration tests passing
- [ ] Performance targets met
- [ ] Data integrity verified
- [ ] Edge cases handled correctly
- [ ] Ready for production deployment

**Tester**: ________________
**Date**: ________________
**Comments**: ________________
