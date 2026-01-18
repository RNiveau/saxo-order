# Data Model: Filter Old Alerts (5-Day Retention)

**Feature**: 005-filter-old-alerts
**Date**: 2026-01-18
**Phase**: Phase 1 - Design & Contracts
**Status**: Complete

## Overview

This document defines the data structures, filtering criteria, and deduplication logic for the 5-day alert retention feature. All operations are client-side only; no backend data model changes are required.

---

## Core Data Structure

### AlertItem Interface

**Source**: `frontend/src/services/api.ts` (existing, no changes)

```typescript
export interface AlertItem {
  id: string;
  alert_type: string;
  asset_code: string;
  asset_description: string;
  exchange: string;
  country_code: string | null;
  date: string;
  data: Record<string, any>;
  age_hours: number;
}
```

### Field Descriptions

| Field | Type | Purpose | Example Values |
|-------|------|---------|----------------|
| `id` | string | Unique alert identifier | "alert_123456" |
| `alert_type` | string | Alert category | "COMBO", "CONGESTION20", "DOUBLE_TOP" |
| `asset_code` | string | Asset symbol | "ITP", "BTCUSDT", "AAPL" |
| `asset_description` | string | Human-readable name | "Interparfums", "Bitcoin/USDT" |
| `exchange` | string | Source exchange | "saxo", "binance" |
| `country_code` | string \| null | Exchange market code | "xpar", "xnas", null (Binance) |
| `date` | string | ISO 8601 timestamp (UTC) | "2026-01-15T14:30:00Z" |
| `data` | Record<string, any> | Type-specific alert data | `{ "price": 42.5, "volume": 150000 }` |
| `age_hours` | number | Pre-calculated age in hours | 48.5 |

### Fields Used for Filtering

- **`date`**: Primary field for age calculation (current time - alert date)
- **`age_hours`**: Pre-calculated but recalculate for accuracy

### Fields Used for Deduplication

- **`asset_code`**: Asset identifier
- **`country_code`**: Exchange market (handle null for Binance)
- **`alert_type`**: Alert category

---

## Filtering Logic

### Age Calculation

**Formula**:
```
age_hours = (current_time_utc - alert.date) / (1000 * 60 * 60)
```

**Implementation**:
```typescript
const calculateAgeHours = (isoDateString: string): number => {
  const alertDate = new Date(isoDateString);
  const now = new Date();
  const diffMs = now.getTime() - alertDate.getTime();
  return diffMs / (1000 * 60 * 60);
};
```

### Filtering Criteria

**Rule**: Keep alert IF `age_hours <= 120`

**Constants**:
```typescript
export const FIVE_DAYS_HOURS = 120;  // 5 days * 24 hours/day
```

**Filter Function Signature**:
```typescript
export const filterRecentAlerts = (
  alerts: AlertItem[],
  maxAgeHours: number = FIVE_DAYS_HOURS
): AlertItem[]
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| Alert at exactly 120 hours | Include (use `<=` comparison) |
| Alert at 120.1 hours | Exclude (outside 5-day window) |
| Invalid date string | Exclude and log warning |
| Missing date field | Exclude and log warning |
| Future date (clock skew) | Include (negative age treated as 0) |

---

## Deduplication Logic

### Deduplication Key

**Format**:
```
"${asset_code}:${country_code || 'null'}:${alert_type}"
```

**Examples**:
| Alert | Deduplication Key | Notes |
|-------|-------------------|-------|
| ITP:xpar COMBO | `"ITP:xpar:COMBO"` | Saxo stock |
| ITP:xpar CONGESTION20 | `"ITP:xpar:CONGESTION20"` | Different type, not deduplicated |
| BTCUSDT (null) COMBO | `"BTCUSDT:null:COMBO"` | Binance crypto |
| AAPL:xnas COMBO | `"AAPL:xnas:COMBO"` | Saxo US stock |

### Deduplication Strategy

**Rule**: For each unique deduplication key, keep only the alert with the most recent `date` timestamp.

**Algorithm**:
1. Create a Map with deduplication key → AlertItem
2. For each alert in the input list:
   - Generate deduplication key
   - If key not in Map OR alert.date > existing.date:
     - Store alert in Map with key
3. Return all values from Map

**Implementation**:
```typescript
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
```

### Deduplication Scope

**Per-Asset Deduplication**: Each asset can have one alert per type.

**Example**:
```
Input:
  - ITP:xpar COMBO (2 hours ago)
  - ITP:xpar COMBO (1 day ago)
  - ITP:xpar COMBO (3 days ago)
  - ITP:xpar CONGESTION20 (1 day ago)
  - BTCUSDT COMBO (5 hours ago)

Output after deduplication:
  - ITP:xpar COMBO (2 hours ago)          // Most recent COMBO for ITP
  - ITP:xpar CONGESTION20 (1 day ago)     // Different type, kept
  - BTCUSDT COMBO (5 hours ago)           // Different asset, kept
```

### Tiebreaker

**Scenario**: Multiple alerts with identical timestamps for same key.

**Rule**: Keep the first one encountered in the input array.

**Rationale**: Timestamp collisions are rare (sub-second precision); deterministic behavior via input order is sufficient.

---

## Processing Pipeline

### Combined Processing Function

**Function Signature**:
```typescript
export const processAlerts = (alerts: AlertItem[]): AlertItem[]
```

**Pipeline Steps**:
```
Input: AlertItem[]
  ↓
Step 1: filterRecentAlerts(alerts, 120)
  → Remove alerts older than 5 days
  ↓
Step 2: deduplicateAlertsByType(filtered)
  → Keep only most recent alert per (asset, type) key
  ↓
Step 3: Sort by date descending
  → Newest alerts first
  ↓
Output: AlertItem[] (filtered, deduplicated, sorted)
```

**Implementation**:
```typescript
export const processAlerts = (alerts: AlertItem[]): AlertItem[] => {
  const recent = filterRecentAlerts(alerts);
  const deduped = deduplicateAlertsByType(recent);
  return deduped.sort((a, b) =>
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};
```

**Why This Order**:
1. Filter first: Reduces dataset size for deduplication (performance optimization)
2. Deduplicate second: Operates on smaller filtered set
3. Sort last: Prepares final display order

---

## Data Flow

### Alerts Page Data Flow

```
1. Component Mount
   ↓
2. alertService.getAll()
   → Fetch all alerts from API
   ↓
3. processAlerts(data.alerts)
   → Filter (5 days) → Deduplicate → Sort
   ↓
4. setAlerts(processedAlerts)
   → Store in React state
   ↓
5. Render AlertList
   → Display filtered & deduplicated alerts
```

### Asset Detail Page Data Flow

```
1. Component Mount (with asset_code, country_code)
   ↓
2. alertService.getAll({ asset_code, country_code })
   → Fetch alerts for specific asset
   ↓
3. processAlerts(response.alerts)
   → Filter (5 days) → Deduplicate → Sort
   ↓
4. setAlertsData(processedAlerts)
   → Store in React state
   ↓
5. Render First 3 Alerts (expandable to all)
   → Display filtered & deduplicated alerts
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Typical Time (500 alerts) |
|-----------|------------|---------------------------|
| Filter by age | O(n) | ~5ms |
| Deduplicate by key | O(n) | ~10ms |
| Sort by date | O(n log n) | ~15ms |
| **Total Pipeline** | **O(n log n)** | **~30ms** |

**Performance Goal**: <50ms for 500 alerts (NFR-001) ✅

### Space Complexity

| Data Structure | Complexity | Notes |
|----------------|------------|-------|
| Input array | O(n) | Original alerts |
| Filtered array | O(n) | Worst case: all alerts within 5 days |
| Deduplication Map | O(k) | k = unique (asset, type) combinations |
| Output array | O(k) | Deduplicated alerts |

**Memory Impact**: Minimal; operates on in-memory data already fetched from API.

---

## Validation Rules

### Input Validation

```typescript
// Validate alert has required fields for filtering
const isValidAlert = (alert: AlertItem): boolean => {
  return (
    alert.date !== undefined &&
    alert.date !== null &&
    !isNaN(new Date(alert.date).getTime())
  );
};
```

### Output Guarantees

After processing, the output array guarantees:
1. All alerts are ≤120 hours old
2. No duplicate (asset, type) combinations exist
3. Alerts are sorted by date descending (newest first)
4. Invalid date alerts are excluded

---

## Backward Compatibility

### No Breaking Changes

- AlertItem interface unchanged
- API contracts unchanged
- Existing filter logic in Alerts.tsx remains functional
- Asset Detail page alert rendering unchanged

### Migration Notes

**Deployment Impact**:
- Users will immediately see fewer alerts (5 days instead of 7 days)
- Duplicate alerts will be automatically hidden
- No data migration required (client-side filtering only)

---

## Testing Considerations

### Unit Test Cases

**Filtering**:
- Alert at 1 hour old → included
- Alert at 119 hours old → included
- Alert at 120 hours old → included (boundary)
- Alert at 121 hours old → excluded
- Alert with invalid date → excluded

**Deduplication**:
- 3 COMBO alerts for same asset → keep most recent
- 1 COMBO + 1 CONGESTION20 for same asset → keep both
- 2 COMBO alerts for different assets → keep both
- Alerts with identical timestamps → deterministic (first in input)

**Integration**:
- Empty input array → empty output
- All alerts >5 days old → empty output
- Mixed valid/invalid dates → valid alerts processed, invalid excluded

---

## Next Steps

1. Proceed to `quickstart.md` for development setup and manual testing checklist
2. Implement `frontend/src/utils/alertFilters.ts` with these data model specifications
3. Update Alerts.tsx and AssetDetail.tsx to use processAlerts() function
