# Data Model: On-Demand Alerts Execution

**Feature**: 003-on-demand-alerts
**Created**: 2026-01-12
**Purpose**: Document data structures for on-demand alert detection API and UI state

## Overview

This feature extends the existing alert detection system (batch/scheduled) with on-demand, per-asset execution. The data model defines:
1. API request/response structures for triggering detection
2. Cooldown tracking mechanism (prevent abuse)
3. Frontend component state for loading/success/error states
4. "NEW" badge tracking for newly detected alerts

## Backend Data Models

### RunAlertsRequest (API Request)

Sent by frontend when user clicks "Run Alerts" button.

```python
class RunAlertsRequest(BaseModel):
    asset_code: str                 # Required: Asset identifier (e.g., "ITP", "BTCUSDT")
    country_code: Optional[str]     # Optional: Country code (e.g., "xpar", None for crypto)
    exchange: str                   # Required: Exchange identifier ("saxo" or "binance")
```

**Example**:
```json
{
  "asset_code": "ITP",
  "country_code": "xpar",
  "exchange": "saxo"
}
```

**Validation Rules**:
- `asset_code`: Non-empty string, 1-20 characters
- `country_code`: Nullable, 2-10 characters if present
- `exchange`: Must be "saxo" or "binance"

---

### RunAlertsResponse (API Response)

Returned by backend after detection execution completes.

```python
class RunAlertsResponse(BaseModel):
    status: str                     # "success", "no_alerts", or "error"
    alerts_detected: int            # Count of newly detected alerts (0+)
    alerts: List[AlertItemResponse] # Array of newly detected Alert objects
    execution_time_ms: int          # Milliseconds taken for detection
    message: str                    # Human-readable status message
    next_allowed_at: datetime       # ISO timestamp when next execution allowed (5 min from now)
```

**Success Example** (new alerts found):
```json
{
  "status": "success",
  "alerts_detected": 2,
  "alerts": [
    {
      "id": "ITP_xpar",
      "alert_type": "combo",
      "asset_code": "ITP",
      "asset_description": "Intertrust NV",
      "exchange": "saxo",
      "country_code": "xpar",
      "date": "2026-01-12T14:30:00Z",
      "data": {"direction": "buy", "price": 12.45, "strength": 0.85},
      "age_hours": 0
    },
    {
      "id": "ITP_xpar",
      "alert_type": "congestion20",
      "asset_code": "ITP",
      "asset_description": "Intertrust NV",
      "exchange": "saxo",
      "country_code": "xpar",
      "date": "2026-01-12T14:30:00Z",
      "data": {"touch_points": 3, "zone_high": 12.80, "zone_low": 12.40},
      "age_hours": 0
    }
  ],
  "execution_time_ms": 3452,
  "message": "Detected 2 new alerts",
  "next_allowed_at": "2026-01-12T14:35:00Z"
}
```

**No Alerts Example** (no new signals):
```json
{
  "status": "no_alerts",
  "alerts_detected": 0,
  "alerts": [],
  "execution_time_ms": 2890,
  "message": "No new alerts detected",
  "next_allowed_at": "2026-01-12T14:35:00Z"
}
```

**Error Example** (cooldown violation):
```json
{
  "status": "error",
  "alerts_detected": 0,
  "alerts": [],
  "execution_time_ms": 5,
  "message": "Alerts recently run. Please wait 3 minutes before running again.",
  "next_allowed_at": "2026-01-12T14:33:00Z"
}
```

**Status Values**:
- `"success"`: Detection completed, alerts detected (count >= 0)
- `"no_alerts"`: Detection completed, no new alerts found
- `"error"`: Detection failed (cooldown violation, API error, timeout)

---

### Cooldown Tracking (DynamoDB Extension)

Existing `alerts` table extended with cooldown field.

**Table**: `alerts`
**Partition Key**: `asset_code` (string)
**Sort Key**: `country_code` (string, "NONE" if null)

**New Field**:
```python
last_run_at: Optional[datetime]  # ISO 8601 timestamp of last on-demand execution
```

**Example Item** (after on-demand execution):
```json
{
  "asset_code": "ITP",
  "country_code": "xpar",
  "alerts": [...],
  "last_updated": "2026-01-12T14:30:00Z",
  "last_run_at": "2026-01-12T14:30:00Z",  // NEW FIELD
  "ttl": 1737123000
}
```

**Cooldown Logic**:
1. On `POST /api/alerts/run` request, query DynamoDB for `last_run_at`
2. If `last_run_at` is within 5 minutes of now, return 429 error with `next_allowed_at`
3. If cooldown expired or never run, proceed with detection
4. After detection, update `last_run_at` to current timestamp

---

## Frontend Data Models

### AssetDetail Component State

New state variables added to `AssetDetail.tsx` for on-demand alerts.

```typescript
// On-demand alerts execution state
const [runAlertsLoading, setRunAlertsLoading] = useState<boolean>(false);
const [runAlertsError, setRunAlertsError] = useState<string | null>(null);
const [runAlertsSuccess, setRunAlertsSuccess] = useState<string | null>(null);
const [nextAllowedAt, setNextAllowedAt] = useState<Date | null>(null);
const [newAlertIds, setNewAlertIds] = useState<Set<string>>(new Set());
```

**State Variables**:

| Variable | Type | Purpose |
|----------|------|---------|
| `runAlertsLoading` | boolean | True during API call, shows spinner on button |
| `runAlertsError` | string \| null | Error message from API (displayed for 3s, then cleared) |
| `runAlertsSuccess` | string \| null | Success message from API (displayed for 3s, then cleared) |
| `nextAllowedAt` | Date \| null | Timestamp when next execution allowed (for countdown timer) |
| `newAlertIds` | Set<string> | IDs of alerts detected in last execution (for "NEW" badge) |

---

### AlertService Extension (API Client)

Extended `alertService` in `frontend/src/services/api.ts`.

```typescript
export const alertService = {
  // Existing method
  getAll: async (params?: {
    asset_code?: string;
    alert_type?: string;
    country_code?: string;
  }): Promise<AlertsResponse> => { ... },

  // NEW METHOD
  run: async (
    asset_code: string,
    country_code: string | null,
    exchange: string
  ): Promise<RunAlertsResponse> => {
    const response = await axios.post(
      `${API_URL}/api/alerts/run`,
      { asset_code, country_code, exchange },
      { timeout: 60000 }  // 60-second timeout
    );
    return response.data;
  }
};
```

**TypeScript Interfaces**:
```typescript
interface RunAlertsResponse {
  status: "success" | "no_alerts" | "error";
  alerts_detected: number;
  alerts: AlertItem[];
  execution_time_ms: number;
  message: string;
  next_allowed_at: string;  // ISO 8601 timestamp
}
```

---

## State Transitions

### Execution Flow (Happy Path)

```
1. Initial State:
   - runAlertsLoading: false
   - nextAllowedAt: null
   - Button: Enabled

2. User clicks "Run Alerts":
   - runAlertsLoading: true
   - Button: Disabled, text "Running...", spinner visible

3. API call in progress (3-10 seconds):
   - Loading spinner animates
   - Button remains disabled

4. API returns success:
   - runAlertsLoading: false
   - runAlertsSuccess: "Detected 2 new alerts"
   - nextAllowedAt: Date 5 minutes in future
   - newAlertIds: Set(["alert_id_1", "alert_id_2"])
   - Alerts section auto-refreshes
   - Button: Disabled (cooldown active)

5. After 3 seconds:
   - runAlertsSuccess: null (message fades out)

6. Cooldown countdown (every second):
   - Display: "Next run in 4:32" (MM:SS format)
   - Button remains disabled

7. After 5 minutes:
   - nextAllowedAt: null
   - Button: Re-enabled
   - Countdown timer hidden
```

### Error Flow (Cooldown Violation)

```
1. User clicks "Run Alerts" within 5 minutes of last run:
   - runAlertsLoading: true

2. API returns 429 error:
   - runAlertsLoading: false
   - runAlertsError: "Alerts recently run. Please wait 3 minutes..."
   - nextAllowedAt: Date from API response

3. After 3 seconds:
   - runAlertsError: null
   - Countdown timer continues showing remaining time
```

### Error Flow (Detection Timeout)

```
1. User clicks "Run Alerts":
   - runAlertsLoading: true

2. After 60 seconds with no response:
   - Frontend axios timeout triggers
   - runAlertsLoading: false
   - runAlertsError: "Alert detection timed out. Please try again."

3. After 3 seconds:
   - runAlertsError: null
   - Button: Re-enabled (no cooldown on timeout)
```

---

## Data Transformations

### Backend: Alert Deduplication

Existing deduplication logic in `DynamoDBClient.store_alerts()`:

```python
def _deduplicate_alerts(existing_alerts: List[Alert], new_alerts: List[Alert]) -> List[Alert]:
    """
    Deduplicates alerts based on (alert_type, date.date()) signature.
    Only one alert per type per day is kept.
    """
    seen_signatures = set()
    for alert in existing_alerts:
        signature = (alert.alert_type, alert.date.date().isoformat())
        seen_signatures.add(signature)

    deduplicated = []
    for alert in new_alerts:
        signature = (alert.alert_type, alert.date.date().isoformat())
        if signature not in seen_signatures:
            deduplicated.append(alert)
            seen_signatures.add(signature)

    return existing_alerts + deduplicated
```

**Implication for On-Demand**:
- If user runs alerts twice in same day for same asset, second run won't create duplicate alerts
- Only new alert types (not yet detected today) will be added

---

### Frontend: "NEW" Badge Logic

```typescript
// After successful API call
const handleRunAlerts = async () => {
  try {
    const response = await alertService.run(assetCode, countryCode, exchange);

    // Track new alert IDs for badge display
    const newIds = new Set(response.alerts.map(a => a.id));
    setNewAlertIds(newIds);

    // Auto-remove "NEW" badges after 60 seconds
    setTimeout(() => {
      setNewAlertIds(new Set());
    }, 60000);

    // Refresh alerts section to show new alerts
    await fetchAlerts(symbol);
  } catch (error) {
    // Handle error
  }
};
```

**Badge Display Logic** (in alerts map):
```tsx
{alertsData.map((alert) => (
  <div key={alert.id}>
    <AlertCard alert={alert} />
    {newAlertIds.has(alert.id) && (
      <span className="alert-badge-new">NEW</span>
    )}
  </div>
))}
```

---

## Performance Considerations

### Backend Performance

**Detection Execution Time**:
- Candle fetch: 1-2 seconds (250 daily + 10 hourly candles from Saxo API)
- Indicator calculations: 1-3 seconds (6 detection algorithms run in sequence)
- DynamoDB write: 100-300ms (single PutItem operation)
- **Total**: 3-10 seconds typical, 30 seconds worst case

**Cooldown Overhead**:
- DynamoDB read: 10-50ms (GetItem by partition/sort key)
- Negligible impact on total execution time

### Frontend Performance

**UI Responsiveness**:
- Button state change: Immediate (<16ms, single setState)
- Spinner animation: 60fps CSS animation
- Countdown timer: Updates every 1 second (setInterval)
- Alerts section refresh: 200-500ms (existing fetchAlerts() logic)

**Memory Usage**:
- `newAlertIds` Set: ~1KB (stores 1-10 alert IDs)
- Auto-cleanup after 60 seconds prevents memory leaks

---

## Validation Rules

### Backend Validation (FastAPI)

```python
@router.post("/api/alerts/run")
async def run_alerts(
    request: RunAlertsRequest,
    service: AlertingService = Depends(get_alerting_service)
):
    # Validate asset_code
    if not request.asset_code or len(request.asset_code) > 20:
        raise HTTPException(400, "Invalid asset_code")

    # Validate exchange
    if request.exchange not in ["saxo", "binance"]:
        raise HTTPException(400, "Invalid exchange")

    # Cooldown validation
    if not service.is_execution_allowed(request.asset_code, request.country_code):
        raise HTTPException(429, "Cooldown active")

    # Proceed with detection
    ...
```

### Frontend Validation (TypeScript)

```typescript
// Validate inputs before API call
if (!assetCode || !exchange) {
  setRunAlertsError("Invalid asset data");
  return;
}

// Enforce cooldown client-side (UX only, backend validates)
if (nextAllowedAt && new Date() < nextAllowedAt) {
  setRunAlertsError("Please wait before running alerts again");
  return;
}
```

---

## Error Scenarios

| Scenario | Backend Response | Frontend Handling |
|----------|------------------|-------------------|
| Cooldown active | 429 Too Many Requests, `next_allowed_at` | Show error message, display countdown timer |
| Saxo API timeout | 500 Internal Server Error | Show "Service unavailable" error |
| Invalid asset code | 400 Bad Request | Show "Invalid asset" error |
| DynamoDB unavailable | 503 Service Unavailable | Show "Storage unavailable" error |
| Detection timeout (60s) | 504 Gateway Timeout | Show "Detection timed out" error |
| Network failure | axios network error | Show "Network error" message |

---

## Summary

**Key Data Structures**:
1. **RunAlertsRequest**: API request (asset_code, country_code, exchange)
2. **RunAlertsResponse**: API response (status, alerts_detected, next_allowed_at)
3. **Cooldown Tracking**: DynamoDB `last_run_at` field (5-minute enforcement)
4. **Frontend State**: 5 new state variables (loading, error, success, cooldown, new badges)

**Data Flow**:
```
Frontend Button Click
  → API POST /api/alerts/run (RunAlertsRequest)
  → Backend checks cooldown (DynamoDB query)
  → Backend runs detection (6 algorithms)
  → Backend stores alerts (DynamoDB PutItem with deduplication)
  → Backend updates last_run_at
  → API returns RunAlertsResponse
  → Frontend displays success message + new alerts with "NEW" badges
  → Frontend starts 5-minute cooldown timer
```

**Validation Layers**:
- Backend: Cooldown enforcement (mandatory, security boundary)
- Frontend: Cooldown timer (UX only, can be bypassed)
- Backend: Input validation (FastAPI Pydantic models)
- Frontend: Basic input checks before API call
