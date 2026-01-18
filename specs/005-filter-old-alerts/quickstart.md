# Quickstart Guide: Filter Old Alerts (5-Day Retention)

**Feature**: 005-filter-old-alerts
**Date**: 2026-01-18
**Branch**: `005-filter-old-alerts`
**Status**: Implementation Ready

## Overview

This guide provides step-by-step instructions for implementing and testing the 5-day alert retention feature. All changes are frontend-only; no backend modifications required.

---

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Access to saxo-order repository
- Frontend development environment configured

---

## Development Setup

### 1. Create Feature Branch

```bash
cd /Users/kiva/codes/saxo-order
git checkout main
git pull origin main
git checkout -b 005-filter-old-alerts
```

### 2. Install Dependencies

```bash
cd frontend
npm install
```

### 3. Start Development Server

```bash
npm run dev
```

Frontend will be available at `http://localhost:5173` (default Vite port).

---

## Implementation Steps

### Step 1: Create Alert Filters Utility

**File**: `frontend/src/utils/alertFilters.ts`

Create new file with the following content:

```typescript
import { AlertItem } from '../services/api';

export const FIVE_DAYS_HOURS = 120;

export const filterRecentAlerts = (
  alerts: AlertItem[],
  maxAgeHours: number = FIVE_DAYS_HOURS
): AlertItem[] => {
  const now = new Date();
  return alerts.filter(alert => {
    if (!alert.date) return false;

    const alertDate = new Date(alert.date);
    if (isNaN(alertDate.getTime())) {
      console.warn(`Invalid date for alert ${alert.id}: ${alert.date}`);
      return false;
    }

    const ageHours = (now.getTime() - alertDate.getTime()) / (1000 * 60 * 60);
    return ageHours <= maxAgeHours;
  });
};

export const deduplicateAlertsByType = (alerts: AlertItem[]): AlertItem[] => {
  const keyMap = new Map<string, AlertItem>();

  for (const alert of alerts) {
    const key = `${alert.asset_code}:${alert.country_code || 'null'}:${alert.alert_type}`;
    const existing = keyMap.get(key);

    if (!existing || new Date(alert.date) > new Date(existing.date)) {
      keyMap.set(key, alert);
    }
  }

  return Array.from(keyMap.values());
};

export const processAlerts = (alerts: AlertItem[]): AlertItem[] => {
  const recent = filterRecentAlerts(alerts);
  const deduped = deduplicateAlertsByType(recent);
  return deduped.sort((a, b) =>
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};
```

### Step 2: Update Alerts Page

**File**: `frontend/src/pages/Alerts.tsx`

**Changes**:

1. Add import at top of file:
```typescript
import { processAlerts } from '../utils/alertFilters';
```

2. Modify the alert fetch logic (around line 50):
```typescript
const data = await alertService.getAll();
const processedAlerts = processAlerts(data.alerts);
setAlerts(processedAlerts);
```

3. Update empty state message (around line 161):
Change `"7 days"` to `"5 days"` in the empty state text.

### Step 3: Update Asset Detail Page

**File**: `frontend/src/pages/AssetDetail.tsx`

**Changes**:

1. Add import at top of file:
```typescript
import { processAlerts } from '../utils/alertFilters';
```

2. Modify the alert fetch logic (around lines 156-161):
```typescript
const response = await alertService.getAll({ asset_code, country_code });
const processedAlerts = processAlerts(response.alerts);
setAlertsData(processedAlerts);
```

---

## Manual Testing Checklist

Since the frontend has no automated test framework configured, use this manual testing checklist to validate the implementation.

### Test Environment Setup

**Create Test Alerts**: Use the backend API or database tools to create test alerts with specific timestamps:

```python
# Example: Create test alerts with different ages
test_alerts = [
    {"asset_code": "ITP", "country_code": "xpar", "alert_type": "COMBO", "date": "2026-01-17T10:00:00Z"},  # 1 day ago
    {"asset_code": "ITP", "country_code": "xpar", "alert_type": "COMBO", "date": "2026-01-15T10:00:00Z"},  # 3 days ago
    {"asset_code": "ITP", "country_code": "xpar", "alert_type": "COMBO", "date": "2026-01-13T10:00:00Z"},  # 5 days ago
    {"asset_code": "ITP", "country_code": "xpar", "alert_type": "COMBO", "date": "2026-01-12T10:00:00Z"},  # 6 days ago
    {"asset_code": "ITP", "country_code": "xpar", "alert_type": "COMBO", "date": "2026-01-10T10:00:00Z"},  # 8 days ago
]
```

### Test Case 1: 5-Day Age Filter

**Objective**: Verify only alerts ≤5 days old are displayed.

**Steps**:
1. Navigate to Alerts page (`/alerts`)
2. Observe the list of displayed alerts
3. Check the timestamps of visible alerts

**Expected Result**:
- Alerts from 1, 3, and 5 days ago are visible
- Alerts from 6 and 8 days ago are NOT visible
- Empty state shows "No alerts from the last 5 days" if all alerts are >5 days old

**Pass/Fail**: [ ]

---

### Test Case 2: Boundary Condition (Exactly 5 Days)

**Objective**: Verify alert at exactly 120 hours is included.

**Steps**:
1. Create an alert with timestamp exactly 5 days (120 hours) ago
2. Navigate to Alerts page
3. Verify the alert is visible

**Expected Result**:
- Alert at exactly 120 hours is displayed (inclusive boundary)

**Pass/Fail**: [ ]

---

### Test Case 3: Deduplication by Alert Type

**Objective**: Verify only the most recent alert per (asset, type) is shown.

**Steps**:
1. Create 3 COMBO alerts for "ITP:xpar" at 2 hours, 1 day, and 3 days ago
2. Navigate to Alerts page
3. Check how many COMBO alerts for "ITP:xpar" are displayed

**Expected Result**:
- Only 1 COMBO alert for "ITP:xpar" is visible (the one from 2 hours ago)
- Older COMBO alerts for the same asset are hidden

**Pass/Fail**: [ ]

---

### Test Case 4: Different Alert Types Not Deduplicated

**Objective**: Verify alerts of different types for same asset are NOT deduplicated.

**Steps**:
1. Create COMBO alert for "ITP:xpar" at 1 day ago
2. Create CONGESTION20 alert for "ITP:xpar" at 2 days ago
3. Navigate to Alerts page
4. Check if both alerts are visible

**Expected Result**:
- Both COMBO and CONGESTION20 alerts are displayed
- Different types are treated as distinct signals

**Pass/Fail**: [ ]

---

### Test Case 5: Per-Asset Deduplication

**Objective**: Verify deduplication is per-asset, not global.

**Steps**:
1. Create COMBO alert for "ITP:xpar" at 1 day ago
2. Create COMBO alert for "BTCUSDT" at 2 days ago
3. Navigate to Alerts page
4. Verify both COMBO alerts are visible

**Expected Result**:
- Both alerts are displayed (different assets)
- Deduplication doesn't remove COMBO alerts across different assets

**Pass/Fail**: [ ]

---

### Test Case 6: Asset Detail Page Consistency

**Objective**: Verify filtering and deduplication work the same on Asset Detail page.

**Steps**:
1. Create 3 COMBO alerts for "ITP:xpar" at 2h, 1d, 5d ago
2. Create 1 COMBO alert for "ITP:xpar" at 6 days ago
3. Navigate to Asset Detail page for "ITP:xpar"
4. Check which alerts are displayed

**Expected Result**:
- Only the most recent COMBO alert (2h ago) is visible
- 6-day-old alert is NOT visible
- Same filtering behavior as Alerts page

**Pass/Fail**: [ ]

---

### Test Case 7: Binance Assets (Null Country Code)

**Objective**: Verify filtering works for Binance assets without country_code.

**Steps**:
1. Create 2 COMBO alerts for "BTCUSDT" (country_code = null) at 1d and 3d ago
2. Navigate to Alerts page
3. Verify only the most recent COMBO alert is displayed

**Expected Result**:
- Only 1 COMBO alert for "BTCUSDT" is visible (1 day ago)
- Deduplication key handles null country_code correctly

**Pass/Fail**: [ ]

---

### Test Case 8: Empty State Messages

**Objective**: Verify empty state correctly mentions "5 days" (not "7 days").

**Steps**:
1. Delete all alerts or wait until all alerts are >5 days old
2. Navigate to Alerts page
3. Read the empty state message

**Expected Result**:
- Message says "No active alerts from the last 5 days" (or similar)
- Does NOT say "7 days"

**Pass/Fail**: [ ]

---

### Test Case 9: Invalid Date Handling

**Objective**: Verify alerts with invalid dates are excluded without breaking the page.

**Steps**:
1. Create an alert with malformed date field (e.g., `date: "invalid"`)
2. Navigate to Alerts page
3. Verify page renders without errors

**Expected Result**:
- Page loads successfully
- Invalid alert is NOT displayed
- Console shows warning: "Invalid date for alert {id}: invalid"

**Pass/Fail**: [ ]

---

### Test Case 10: Performance with Many Alerts

**Objective**: Verify filtering + deduplication completes in <50ms for 500 alerts.

**Steps**:
1. Create 500 test alerts with varying ages and types
2. Open browser DevTools → Performance tab
3. Navigate to Alerts page
4. Measure time for alert processing

**Expected Result**:
- Processing time <50ms (check console.time if instrumented)
- Page remains responsive

**Pass/Fail**: [ ]

---

## Code Quality Checks

### Linting

```bash
cd frontend
npm run lint
```

**Expected**: No linting errors related to new/modified files.

### Type Checking

```bash
cd frontend
npm run type-check  # or tsc --noEmit
```

**Expected**: No TypeScript errors.

### Formatting

```bash
cd frontend
npm run format  # or prettier --write src/
```

**Expected**: Code is formatted according to project style guide.

---

## Build Verification

### Development Build

```bash
cd frontend
npm run dev
```

**Expected**: Application starts without errors.

### Production Build

```bash
cd frontend
npm run build
```

**Expected**: Build completes successfully with no errors.

---

## Deployment Checklist

Before deploying to production:

- [ ] All manual test cases pass
- [ ] Linting passes with no errors
- [ ] TypeScript type checking passes
- [ ] Production build succeeds
- [ ] Empty state messages updated to "5 days"
- [ ] Console warnings logged for invalid dates (check browser console during testing)
- [ ] Performance acceptable (<50ms for 500 alerts)

---

## Troubleshooting

### Issue: Alerts not filtering by 5 days

**Possible Causes**:
- processAlerts() not called after API fetch
- Date calculation incorrect (check timezone handling)

**Debug Steps**:
1. Add console.log in filterRecentAlerts() to log age calculations
2. Verify alert.date is ISO 8601 format
3. Check browser time is correct

---

### Issue: Deduplication not working

**Possible Causes**:
- Deduplication key format incorrect
- country_code not handled for null values

**Debug Steps**:
1. Add console.log in deduplicateAlertsByType() to log keys
2. Verify key format: `"asset:country:type"`
3. Check country_code || 'null' logic

---

### Issue: TypeScript errors

**Possible Causes**:
- AlertItem import path incorrect
- Missing type annotations

**Debug Steps**:
1. Verify import: `import { AlertItem } from '../services/api';`
2. Check function signatures match data-model.md
3. Run `npm run type-check` for detailed errors

---

## Next Steps

After implementation and testing:

1. Run `/speckit.tasks` to generate tasks.md for implementation tracking
2. Create pull request with conventional commit format:
   ```
   feat: filter alerts to 5-day retention with deduplication

   - Add client-side filtering for alerts older than 5 days
   - Implement deduplication to keep most recent alert per (asset, type)
   - Update empty state messages from 7 days to 5 days
   - Apply consistent filtering across Alerts page and Asset Detail page

   Closes #<issue-number>
   ```
3. Deploy frontend via standard process (Vite build + deployment)

---

## Reference Documentation

- **Specification**: `specs/005-filter-old-alerts/spec.md`
- **Implementation Plan**: `specs/005-filter-old-alerts/plan.md`
- **Data Model**: `specs/005-filter-old-alerts/data-model.md`
- **Research Findings**: `specs/005-filter-old-alerts/research.md`
