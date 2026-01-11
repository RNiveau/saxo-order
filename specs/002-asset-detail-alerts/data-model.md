# Data Model: Asset Detail Alerts Display

**Feature**: 002-asset-detail-alerts
**Created**: 2026-01-11

## Overview

This document describes the data structures for displaying alerts within the asset detail page. The feature uses existing alert data from the `/api/alerts` endpoint and renders it in a new section on the AssetDetail page. No new backend models are created - this feature uses existing `AlertItem` interfaces from the frontend API service.

**Key Principle**: Frontend-only feature using existing API. Document component props, state management, and data transformations for display.

---

## Existing API Models (Unchanged)

### AlertItem Interface

**Location**: `frontend/src/services/api.ts`
**Purpose**: TypeScript representation of alert data from backend
**Status**: ✅ No changes required

```typescript
interface AlertItem {
  id: string;                      // Composite key: asset_code_country_code
  alert_type: string;              // Alert type enum value (e.g., "combo", "congestion20")
  asset_code: string;              // Asset symbol (e.g., "ITP", "BTCUSDT")
  country_code: string | null;     // Exchange code (e.g., "xpar") or null
  date: string;                    // ISO 8601 timestamp
  data: Record<string, any>;       // Alert-specific data payload
  age_hours: number;               // Hours since alert creation (calculated by backend)
}
```

### AlertsResponse Interface

**Location**: `frontend/src/services/api.ts`
**Purpose**: API response containing alert list and metadata
**Status**: ✅ No changes required

```typescript
interface AlertsResponse {
  alerts: AlertItem[];
  total_count: number;
  available_filters: {
    asset_codes: string[];
    alert_types: string[];
    country_codes: string[];
  };
}
```

---

## New Component Models (Frontend)

### AlertCardProps

**Location**: `frontend/src/components/AlertCard.tsx` (NEW)
**Purpose**: Props interface for AlertCard component
**Direction**: Parent component (AssetDetail) → Child component (AlertCard)

```typescript
interface AlertCardProps {
  alert: AlertItem;                // Alert data to display
  showAbsoluteTime?: boolean;      // Whether to show absolute timestamp (default: false)
}
```

**Usage Example**:
```typescript
<AlertCard
  alert={alertItem}
  showAbsoluteTime={false}
/>
```

---

### AlertSectionState

**Location**: `frontend/src/pages/AssetDetail.tsx` (component state)
**Purpose**: React state for managing alerts section
**Direction**: Local component state

```typescript
// State variables (declared with useState)
const [alertsLoading, setAlertsLoading] = useState<boolean>(false);
const [alertsError, setAlertsError] = useState<string | null>(null);
const [alertsData, setAlertsData] = useState<AlertItem[]>([]);
const [alertsExpanded, setAlertsExpanded] = useState<boolean>(false);
```

**State Transitions**:

| State | alertsLoading | alertsError | alertsData | alertsExpanded |
|-------|---------------|-------------|------------|----------------|
| Initial | false | null | [] | false |
| Fetching | true | null | [] | false |
| Success | false | null | [alerts] | false |
| Error | false | "error msg" | [] | false |
| Expanded | false | null | [alerts] | true |

---

## Data Transformations

### Asset Symbol Parsing

**Purpose**: Extract asset_code and country_code from URL parameter for filtering

**Input**: `symbol` from URL (e.g., "ITP:xpar", "BTCUSDT")
**Output**: `{ code: string, countryCode: string }`

**Logic**:
```typescript
const parts = symbol.split(':');
const code = parts[0];                    // "ITP" or "BTCUSDT"
const countryCode = parts.length > 1 ? parts[1] : '';  // "xpar" or ""
```

**Cases**:
- Saxo asset with country: "ITP:xpar" → `{ code: "ITP", countryCode: "xpar" }`
- Asset without country: "BTCUSDT" → `{ code: "BTCUSDT", countryCode: "" }`
- Edge case: "ABC:" → `{ code: "ABC", countryCode: "" }`

### Alert Type Display Formatting

**Purpose**: Convert alert_type enum value to human-readable badge text

**Mapping**:
```typescript
const ALERT_TYPE_LABELS: Record<string, string> = {
  'combo': 'COMBO',
  'congestion20': 'CONGESTION20',
  'congestion100': 'CONGESTION100',
  'double_top': 'DOUBLE TOP',
  'double_inside_bar': 'DOUBLE INSIDE BAR',
  'containing_candle': 'CONTAINING CANDLE',
};
```

**Usage**:
```typescript
const displayLabel = ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type.toUpperCase();
```

### Relative Timestamp Calculation

**Purpose**: Convert age_hours to human-readable relative time

**Input**: `age_hours` (number, from backend)
**Output**: String like "2 hours ago", "3 days ago"

**Logic**:
```typescript
const formatRelativeTime = (ageHours: number): string => {
  if (ageHours < 1) return 'Less than 1 hour ago';
  if (ageHours < 24) return `${Math.floor(ageHours)} hour${Math.floor(ageHours) !== 1 ? 's' : ''} ago`;

  const days = Math.floor(ageHours / 24);
  return `${days} day${days !== 1 ? 's' : ''} ago`;
};
```

**Examples**:
- 0.5 hours → "Less than 1 hour ago"
- 2.7 hours → "2 hours ago"
- 25 hours → "1 day ago"
- 50 hours → "2 days ago"

### Alert Data Field Extraction

**Purpose**: Extract type-specific fields from alert.data for display

**By Alert Type**:

```typescript
// COMBO Alert
interface ComboAlertData {
  price: number;
  direction: 'Buy' | 'Sell';
  strength: 'Strong' | 'Medium' | 'Weak';
  has_been_triggered?: boolean;
  details?: Record<string, any>;
}

// CONGESTION Alert
interface CongestionAlertData {
  touch_points: number[];
  candles: any[];  // Candle data
}

// Candle Pattern Alerts (DOUBLE_TOP, CONTAINING_CANDLE, DOUBLE_INSIDE_BAR)
interface CandlePatternAlertData {
  close: number;
  open: number;
  higher: number;
  lower: number;
}
```

**Rendering Logic**:
```typescript
const renderAlertData = (alert: AlertItem) => {
  switch (alert.alert_type) {
    case 'combo':
      return (
        <>
          <div>Price: {alert.data.price}</div>
          <div>Direction: {alert.data.direction}</div>
          <div>Strength: {alert.data.strength}</div>
        </>
      );
    case 'congestion20':
    case 'congestion100':
      return <div>Touch Points: {alert.data.touch_points?.length || 0}</div>;
    case 'double_top':
    case 'containing_candle':
    case 'double_inside_bar':
      return (
        <>
          <div>H: {alert.data.higher} | L: {alert.data.lower}</div>
          <div>O: {alert.data.open} | C: {alert.data.close}</div>
        </>
      );
    default:
      return <pre>{JSON.stringify(alert.data, null, 2)}</pre>;
  }
};
```

---

## Data Flow

### Alert Display Flow

```text
1. User navigates to asset detail page (/asset/ITP:xpar)
   ↓ [URL parameter extracted]
2. AssetDetail component mounts
   ↓ [useEffect triggered with symbol dependency]
3. Parse symbol → code="ITP", countryCode="xpar"
   ↓ [fetchAlerts() called]
4. API call: alertService.getAll({ asset_code: "ITP", country_code: "xpar" })
   ↓ [HTTP GET /api/alerts?asset_code=ITP&country_code=xpar]
5. Backend filters alerts for this asset
   ↓ [API response]
6. AlertsResponse received
   ↓ [setAlertsData(response.alerts)]
7. State update triggers re-render
   ↓ [Map alerts → AlertCard components]
8. AlertCard components render with alert data
   ↓ [User sees formatted alert cards]
```

### Expand/Collapse Flow

```text
1. Initial state: alertsExpanded = false
   ↓ [Show top 3 alerts]
2. User clicks "Show All" button
   ↓ [onClick event]
3. setAlertsExpanded(true)
   ↓ [State update]
4. Re-render with condition: alertsExpanded ? alertsData : alertsData.slice(0, 3)
   ↓ [All alerts displayed]
5. User clicks "Show Less" button
   ↓ [onClick event]
6. setAlertsExpanded(false)
   ↓ [State update]
7. Re-render showing top 3 alerts
```

---

## Component Hierarchy

```text
AssetDetail (Page)
├── asset-header (existing)
├── indicators-container (existing)
├── alerts-section (NEW)
│   ├── alerts-header
│   │   └── <h3>Alerts</h3>
│   ├── alerts-list
│   │   ├── AlertCard (alert #1)
│   │   ├── AlertCard (alert #2)
│   │   ├── AlertCard (alert #3)
│   │   └── ... (if expanded)
│   ├── expand-button (if > 3 alerts)
│   └── empty-state | error-state (conditionally)
└── workflows-section (existing)
```

---

## Validation Rules

### Component Props Validation

```typescript
// AlertCard validation (TypeScript enforced)
- alert: Required, must be AlertItem type
- alert.id: Non-empty string
- alert.alert_type: String (enum value from backend)
- alert.asset_code: Non-empty string
- alert.date: ISO 8601 string
- alert.age_hours: Non-negative number
- alert.data: Object (any shape)
```

### State Validation

```typescript
// AssetDetail state validation
- alertsData: Array of AlertItem (can be empty)
- alertsExpanded: Boolean (defaults to false)
- alertsLoading: Boolean (defaults to false)
- alertsError: String | null (null = no error)
```

### Runtime Checks

```typescript
// Check if alerts section should display
const shouldShowAlertsSection =
  !alertsLoading &&
  alertsError === null &&
  (alertsData.length > 0 || true);  // Always show section for empty state

// Check if expand button should show
const shouldShowExpandButton = alertsData.length > 3;

// Check if alert data field exists before rendering
const hasPrice = alert.data.price !== undefined;
```

---

## Performance Considerations

### Data Fetching

1. **Parallel Loading**: Alerts fetch in parallel with indicators/workflows
   - No blocking between sections
   - Each section has independent loading state
   - Page remains interactive during all fetches

2. **Filtering**: Done server-side (backend filters by asset_code + country_code)
   - No client-side filtering overhead
   - Minimal data transfer (only relevant alerts)
   - Typical response: 0-10 alerts (~2-5 KB)

### Rendering Optimization

1. **Conditional Rendering**: Only render visible alerts
   - Top 3 alerts initially (slice(0, 3))
   - All alerts when expanded
   - No virtualization needed (max 50 alerts expected)

2. **Component Memoization**: Not needed initially
   - AlertCard is lightweight (~50-100ms render time)
   - Re-renders only on state changes
   - Can add React.memo later if performance issues arise

---

## Error Handling

### API Error Scenarios

| Error Type | Condition | alertsError | alertsData | Display |
|------------|-----------|-------------|------------|---------|
| Network failure | fetch() throws | "Unable to load alerts..." | [] | Error message with no cards |
| 404 Not Found | Asset doesn't exist | null | [] | Empty state (valid - no alerts) |
| 500 Server Error | Backend failure | "Unable to load alerts..." | [] | Error message with retry guidance |
| Invalid JSON | Malformed response | "Unable to load alerts..." | [] | Error message |

### Data Validation Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Missing alert.id | Backend data issue | Skip alert, log error |
| Invalid alert.date | Non-ISO timestamp | Display raw date string |
| Empty alert.data | No alert-specific data | Display "No details available" |
| Unknown alert.alert_type | New type added | Display uppercase type + raw JSON data |

---

## Extensibility

### Adding New Alert Types

**Steps**:
1. Add new type to `ALERT_TYPE_LABELS` mapping
2. Add new case to `renderAlertData()` switch statement
3. Define TypeScript interface for new alert data shape
4. Add corresponding CSS class for badge color

**Example**:
```typescript
// 1. Add label
const ALERT_TYPE_LABELS = {
  ...existing,
  'new_pattern': 'NEW PATTERN',
};

// 2. Add render case
case 'new_pattern':
  return <div>New Field: {alert.data.newField}</div>;

// 3. Define interface
interface NewPatternAlertData {
  newField: string;
}

// 4. Add CSS
.alert-type-badge.new-pattern {
  background-color: #ff6b6b;
  color: #fff;
}
```

### Future Enhancements

**Potential additions** (not in current scope):
- Click alert to navigate to full alerts page with this alert highlighted
- Filter alerts by type within asset detail page
- Sort alerts by different criteria (age, type)
- Alert detail modal/expand for complex alert data
- Real-time alert updates (WebSocket subscription)

---

## Testing Considerations

**Manual Test Cases**:

1. **Asset with alerts**: Navigate to asset with 5 alerts, verify all display correctly
2. **Asset without alerts**: Navigate to asset with 0 alerts, verify empty state
3. **Asset with >3 alerts**: Verify expand/collapse button works
4. **Mixed alert types**: Verify different alert types render with correct badges and data
5. **Asset without country_code**: Verify filtering works (country_code="")
6. **API failure**: Simulate 500 error, verify error message displays
7. **Slow API**: Throttle network, verify loading spinner shows
8. **Timestamp hover**: Hover over relative time, verify absolute time appears

**Component Tests** (if testing framework added):
- AlertCard renders correct alert type badge
- AlertCard renders correct relative timestamp
- AlertCard renders type-specific data fields
- AssetDetail fetches alerts on symbol change
- AssetDetail expands/collapses alerts correctly
- AssetDetail handles API errors gracefully
