# Research Findings: Filter Old Alerts (5-Day Retention)

**Feature**: 005-filter-old-alerts
**Date**: 2026-01-18
**Phase**: Phase 0 - Research
**Status**: Complete

## Overview

This document consolidates research findings from exploring the current alert implementation in the frontend codebase. The goal is to understand how alerts are currently fetched, displayed, and filtered to inform the design of client-side 5-day filtering and deduplication logic.

## Research Questions Addressed

1. How do Alerts.tsx and AssetDetail.tsx manage alert state after API fetch?
2. What is the exact structure of AlertItem interface and what fields are available?
3. What existing filtering patterns exist that we can extend?
4. Where should shared utility functions live in the frontend codebase?

---

## Finding 1: Alert State Management

### Alerts Page (`frontend/src/pages/Alerts.tsx`)

**Lines 50-77**: Alert fetch and state management

```typescript
// Fetches all alerts from API on component mount
const data = await alertService.getAll();
setAlerts(data.alerts);  // Store in state: alerts: AlertItem[]
setAvailableFilters(data.available_filters);
```

**Current Filtering Approach**:
- Client-side filtering already exists for `asset_code` and `alert_type`
- Uses composite key for React rendering: `${asset_code}_${alert_type}_${date}`
- Filtering happens in state after fetch, not during API call

**Key Insight**: The page already has a pattern for client-side filtering that we can extend with age-based filtering and deduplication.

### Asset Detail Page (`frontend/src/pages/AssetDetail.tsx`)

**Lines 156-169**: Asset-specific alert fetch

```typescript
// Fetches alerts filtered by asset_code and country_code via query params
const response = await alertService.getAll({ asset_code, country_code });
setAlertsData(response.alerts);  // Store in state: alertsData: AlertItem[]
```

**Lines 667-674**: Alert rendering
- Shows first 3 alerts by default
- Expandable to show all alerts
- Supports on-demand alert detection with "NEW" badges

**Key Insight**: Asset Detail page fetches pre-filtered data from API but stores all results in state. We can apply the same processAlerts() utility function here.

---

## Finding 2: AlertItem Interface Structure

**Source**: `frontend/src/services/api.ts`

```typescript
export interface AlertItem {
  id: string;                    // Unique identifier
  alert_type: string;            // Type: COMBO, CONGESTION20, etc.
  asset_code: string;            // Asset symbol (e.g., "ITP", "BTCUSDT")
  asset_description: string;     // Human-readable asset name
  exchange: string;              // "saxo" or "binance"
  country_code: string | null;   // Exchange code (e.g., "xpar") or null
  date: string;                  // ISO 8601 timestamp (UTC)
  data: Record<string, any>;     // Type-specific alert data
  age_hours: number;             // Pre-calculated age in hours
}
```

**Key Fields for Our Implementation**:
- `date`: ISO 8601 timestamp - use for age calculation
- `alert_type`: Category - use for deduplication key
- `asset_code`: Asset identifier - use for deduplication key
- `country_code`: Exchange identifier - use for deduplication key (handle null)
- `age_hours`: Pre-calculated - can use for display but recalculate for filtering

**Key Insight**: The `date` field is already in ISO format, making JavaScript Date parsing straightforward. We have all fields needed for both filtering and deduplication.

---

## Finding 3: Current Filtering Patterns

### Alerts Page Filtering (Lines 69-77)

```typescript
// Client-side filter application
const filtered = alerts.filter(alert => {
  if (selectedAsset && alert.asset_code !== selectedAsset) return false;
  if (selectedType && alert.alert_type !== selectedType) return false;
  return true;
});
```

**Pattern Identified**:
- Filter chain with early returns
- Filters applied to in-memory array after fetch
- Multiple filter conditions can be combined

**Extension Strategy**: Add age-based filter and deduplication to this existing pattern.

### React Rendering Key Pattern

Current composite key: `${asset_code}_${alert_type}_${date}`

**Key Insight**: This key already combines asset, type, and date - similar to our deduplication needs. However, it's used for rendering uniqueness, not deduplication logic.

---

## Finding 4: Utility Function Location

**Existing Utility Files**:
- `frontend/src/utils/marketHours.ts` - Market hours calculations
- `frontend/src/utils/tradingview.ts` - TradingView URL generation

**Pattern Observed**:
- Pure functions organized by domain (market hours, external integrations)
- Exported functions with clear, descriptive names
- No dependencies on React state or components

**Decision**: Create `frontend/src/utils/alertFilters.ts` following this pattern.

**Proposed Structure**:
```typescript
// Constants
export const FIVE_DAYS_HOURS = 120;

// Filtering functions
export const filterRecentAlerts = (alerts: AlertItem[], maxAgeHours: number): AlertItem[];
export const deduplicateAlertsByType = (alerts: AlertItem[]): AlertItem[];
export const processAlerts = (alerts: AlertItem[]): AlertItem[];
```

---

## Finding 5: Date Calculation Approach

**JavaScript Date Handling**:
- ISO 8601 strings parse directly: `new Date(alert.date)`
- Calculate age: `(now.getTime() - alertDate.getTime()) / (1000 * 60 * 60)`
- Comparison: `ageHours <= 120`

**Example Implementation**:
```typescript
const calculateAgeHours = (isoDateString: string): number => {
  const alertDate = new Date(isoDateString);
  const now = new Date();
  const diffMs = now.getTime() - alertDate.getTime();
  return diffMs / (1000 * 60 * 60);
};
```

**Edge Cases Identified**:
- Invalid date strings: `new Date('invalid')` returns `Invalid Date`
- Use `isNaN(alertDate.getTime())` to detect invalid dates
- Filter out invalid dates to prevent NaN comparisons

---

## Finding 6: Deduplication Key Design

**Requirement**: Keep only the most recent alert for each (asset, alert_type) combination.

**Deduplication Key Format**:
```typescript
const key = `${alert.asset_code}:${alert.country_code || 'null'}:${alert.alert_type}`;
```

**Rationale**:
- `asset_code`: Ensures per-asset deduplication
- `country_code || 'null'`: Handles Binance assets (country_code = null or empty)
- `alert_type`: Allows multiple alert types per asset

**Examples**:
- `"ITP:xpar:COMBO"` - Saxo stock with COMBO alert
- `"BTCUSDT:null:COMBO"` - Binance crypto with COMBO alert
- `"ITP:xpar:CONGESTION20"` - Same Saxo stock, different alert type (not deduplicated)

**Key Insight**: Using `country_code || 'null'` ensures consistent key generation for both Saxo and Binance assets.

---

## Finding 7: Processing Pipeline Order

**Correct Order**:
1. **Filter by age first** (remove alerts >120 hours)
2. **Deduplicate remaining alerts** (keep most recent per key)
3. **Sort by timestamp descending** (newest first)

**Rationale**:
- Filtering first reduces dataset size for deduplication (performance optimization)
- Deduplication before sorting ensures we sort the final set
- Sorting last prepares data for display

**Performance Consideration**:
- Filtering 500 alerts: O(n) - fast
- Deduplication with Map: O(n) - fast
- Sorting: O(n log n) - acceptable for <1000 items
- **Total**: <50ms for 500 alerts (meets NFR-001)

---

## Design Decisions

Based on research findings, the following design decisions were made:

### Decision 1: Shared Utility Functions
**Location**: `frontend/src/utils/alertFilters.ts`
**Rationale**: Follows existing pattern in frontend/src/utils/; enables code reuse across Alerts.tsx and AssetDetail.tsx

### Decision 2: Age Calculation Method
**Approach**: Calculate age in hours using JavaScript Date objects
**Rationale**: ISO 8601 timestamps from API parse directly; no timezone conversion needed (server uses UTC)

### Decision 3: Deduplication Key Format
**Format**: `${asset_code}:${country_code || 'null'}:${alert_type}`
**Rationale**: Handles both Saxo (with country_code) and Binance (null country_code) consistently; allows multiple alert types per asset

### Decision 4: Processing Pipeline
**Order**: Filter → Deduplicate → Sort
**Rationale**: Filtering first optimizes performance; sorting last prepares for display

### Decision 5: Invalid Date Handling
**Approach**: Filter out alerts with invalid date fields
**Rationale**: Prevents NaN comparisons; log warnings for debugging (per FR-022)

---

## Implementation Recommendations

1. **Create Utility Module First**: Implement `alertFilters.ts` with full test coverage before modifying pages
2. **Reuse Across Pages**: Both Alerts.tsx and AssetDetail.tsx should import and use the same `processAlerts()` function
3. **Performance Monitoring**: Add console.time/timeEnd during development to validate <50ms performance
4. **Error Handling**: Log warnings for invalid dates but don't break page rendering
5. **Testing Strategy**: Manual testing with alerts at 1, 3, 5, 6, 8 days old; multiple alerts of same type per asset

---

## Open Questions

**None remaining** - all research questions have been addressed with sufficient detail for Phase 1 design.

---

## Next Steps

Proceed to **Phase 1: Design & Contracts** to create:
1. `data-model.md` - Document AlertItem structure, deduplication key, filtering criteria
2. `quickstart.md` - Development setup and manual testing checklist
3. `contracts/` - API contracts (none needed, but document existing GET /api/alerts endpoint)
4. Update agent context with `.specify/scripts/bash/update-agent-context.sh claude`
