# Data Model: Alerts UI Page

**Feature**: 001-alerts-ui-page
**Created**: 2026-01-10

## Overview

This document describes the data structures for the Alerts UI Page feature. The feature exposes existing alert data (already stored in DynamoDB) through REST API endpoints and renders it in a React frontend.

**Key Principle**: No changes to existing storage or domain models. This feature adds API layer models (Pydantic) and frontend interfaces (TypeScript) that transform existing data for web consumption.

---

## Existing Domain Models (Unchanged)

### Alert (Python Dataclass)

**Location**: `model/__init__.py`
**Purpose**: Core domain model representing a single alert
**Status**: ✅ No changes required

```python
@dataclass
class Alert:
    alert_type: AlertType              # Enum: CONGESTION20, COMBO, DOUBLE_TOP, etc.
    date: datetime.datetime            # When alert was triggered
    data: Dict[str, Any]              # Pattern-specific data (varies by alert_type)
    asset_code: str                    # Asset symbol (e.g., "ITP", "BTCUSDT")
    country_code: Optional[str] = None # Exchange code (e.g., "xpar") or None

    @property
    def id(self) -> str:
        """Returns composite ID: asset_code_country_code or just asset_code"""
        if self.country_code:
            return f"{self.asset_code}_{self.country_code}"
        return self.asset_code
```

**Alert Data Structure by Type**:

| Alert Type | Data Fields | Example Values |
|------------|-------------|----------------|
| CONGESTION20/100 | `touch_points`, `candles` | Lists of price points and candle data |
| COMBO | `price`, `direction`, `strength`, `has_been_triggered`, `details` | 150.25, "Buy", "Strong", false, {...} |
| DOUBLE_TOP | `close`, `open`, `higher`, `lower` | Candle OHLC values |
| CONTAINING_CANDLE | `close`, `open`, `higher`, `lower` | Candle OHLC values |
| DOUBLE_INSIDE_BAR | `close`, `open`, `higher`, `lower` | Candle OHLC values |

### AlertType (Python Enum)

**Location**: `model/enum.py`
**Purpose**: Type-safe alert classification
**Status**: ✅ No changes required

```python
class AlertType(Enum):
    CONGESTION20 = "congestion20"
    CONGESTION100 = "congestion100"
    COMBO = "combo"
    DOUBLE_TOP = "double_top"
    DOUBLE_INSIDE_BAR = "double_inside_bar"
    CONTAINING_CANDLE = "containing_candle"
```

---

## DynamoDB Storage Model (Unchanged)

### Table: `alerts`

**Status**: ✅ Already exists, no schema changes

**Primary Key**:
- Partition Key (Hash): `asset_code` (String)
- Sort Key (Range): `country_code` (String) - empty string `""` if None

**Attributes**:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `asset_code` | String | Asset symbol | "ITP" |
| `country_code` | String | Exchange code or empty string | "xpar" or "" |
| `alerts` | List | Array of alert objects (serialized Alert dataclass) | [...] |
| `last_updated` | String | ISO 8601 timestamp of last modification | "2026-01-10T18:15:00" |
| `ttl` | Number | Unix timestamp for automatic deletion (creation + 7 days) | 1757500800 |

**TTL Configuration**: Enabled on `ttl` attribute (7-day automatic expiration)

**Sample Item**:
```json
{
  "asset_code": "ITP",
  "country_code": "xpar",
  "alerts": [
    {
      "alert_type": "combo",
      "asset_code": "ITP",
      "country_code": "xpar",
      "date": "2026-01-10T18:15:00",
      "data": {
        "price": 150.25,
        "direction": "Buy",
        "strength": "Strong",
        "has_been_triggered": false,
        "details": {...}
      }
    }
  ],
  "last_updated": "2026-01-10T18:15:00",
  "ttl": 1757500800
}
```

---

## New API Models (Pydantic)

### AlertItemResponse

**Location**: `api/models/alerting.py` (NEW)
**Purpose**: Single alert representation for API responses
**Direction**: Domain model → API model (serialization)

```python
class AlertItemResponse(BaseModel):
    id: str                              # Composite key: asset_code_country_code
    alert_type: str                      # Alert type enum value
    asset_code: str                      # Asset symbol
    country_code: Optional[str] = None   # Exchange code or None
    date: datetime                       # Alert creation timestamp
    data: Dict[str, Any]                # Alert-specific data payload
    age_hours: int                       # Hours since alert creation (calculated)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ITP_xpar",
                "alert_type": "combo",
                "asset_code": "ITP",
                "country_code": "xpar",
                "date": "2026-01-10T18:15:00",
                "data": {
                    "price": 150.25,
                    "direction": "Buy",
                    "strength": "Strong"
                },
                "age_hours": 12
            }
        }
```

**Transformation Logic**:
```python
def from_domain(alert: Alert) -> AlertItemResponse:
    age = datetime.now() - alert.date
    return AlertItemResponse(
        id=alert.id,
        alert_type=alert.alert_type.value,  # Enum → string
        asset_code=alert.asset_code,
        country_code=alert.country_code,
        date=alert.date,
        data=alert.data,
        age_hours=int(age.total_seconds() / 3600)
    )
```

### AlertsResponse

**Location**: `api/models/alerting.py` (NEW)
**Purpose**: Collection of alerts with metadata for API responses
**Direction**: Service layer → API response

```python
class AlertsResponse(BaseModel):
    alerts: List[AlertItemResponse]     # List of alert items
    total_count: int                    # Total alerts returned
    available_filters: Dict[str, List[str]]  # Available filter values

    class Config:
        json_schema_extra = {
            "example": {
                "alerts": [...],
                "total_count": 42,
                "available_filters": {
                    "asset_codes": ["ITP", "AAPL", "GOOGL"],
                    "alert_types": ["combo", "congestion20", "double_top"],
                    "country_codes": ["xpar", "xnas", ""]
                }
            }
        }
```

---

## New Frontend Models (TypeScript)

### AlertItem Interface

**Location**: `frontend/src/services/api.ts` (NEW)
**Purpose**: TypeScript representation matching AlertItemResponse
**Direction**: API response → Frontend component props

```typescript
interface AlertItem {
  id: string;
  alert_type: string;
  asset_code: string;
  country_code: string | null;
  date: string;                    // ISO 8601 string
  data: Record<string, any>;
  age_hours: number;
}
```

### AlertsResponse Interface

**Location**: `frontend/src/services/api.ts` (NEW)
**Purpose**: TypeScript representation matching AlertsResponse
**Direction**: API response → Frontend state

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

### AlertFilters Interface

**Location**: `frontend/src/pages/Alerts.tsx` (NEW)
**Purpose**: Component state for user-selected filters
**Direction**: User interaction → API query parameters

```typescript
interface AlertFilters {
  asset_code?: string;      // Selected asset or undefined for "all"
  alert_type?: string;      // Selected alert type or undefined for "all"
  country_code?: string;    // Selected exchange or undefined for "all"
}
```

---

## Data Flow

### Alert Display Flow

```text
1. DynamoDB Table (alerts)
   ↓ [DynamoDBClient.get_all_alerts()]
2. List[Alert] (domain model)
   ↓ [AlertingService.get_all_alerts()]
3. List[AlertItemResponse] (Pydantic model)
   ↓ [AlertingRouter GET /api/alerts]
4. JSON Response (HTTP)
   ↓ [axios.get('/api/alerts')]
5. AlertsResponse (TypeScript interface)
   ↓ [useState in Alerts.tsx]
6. React Component Rendering
   ↓ [AlertCard component]
7. User sees formatted alert cards
```

### Filtering Flow

```text
1. User selects filter in UI (asset_code=ITP)
   ↓ [setState(filters)]
2. Frontend state update
   ↓ [useEffect triggers]
3. API call with query params (/api/alerts?asset_code=ITP)
   ↓ [AlertingRouter processes]
4. AlertingService filters in-memory
   ↓ [Filter List[Alert]]
5. Filtered AlertItemResponse list
   ↓ [HTTP response]
6. UI re-renders with filtered alerts
```

---

## Validation Rules

### Backend Validation (Pydantic)

```python
# AlertItemResponse validation
- id: non-empty string, max 100 chars
- alert_type: must be valid AlertType enum value
- asset_code: non-empty string, max 20 chars
- country_code: optional string, max 10 chars if provided
- date: valid datetime (ISO 8601)
- data: valid dict (no size limit - trust source)
- age_hours: non-negative integer
```

### Frontend Validation (TypeScript)

```typescript
// No input validation needed - read-only display
// Runtime type checking via TypeScript interfaces
// API responses validated against interfaces
```

---

## State Transitions

### Alert Lifecycle States

**Note**: Alerts have no explicit "state" field - their lifecycle is determined by existence in storage.

| State | Condition | Duration | Behavior |
|-------|-----------|----------|----------|
| **Active** | TTL > current_time | 0-7 days | Visible in API and UI |
| **Expired** | TTL ≤ current_time | N/A | Automatically deleted by DynamoDB |

**No manual state management required** - TTL mechanism handles all lifecycle transitions.

---

## Performance Considerations

### DynamoDB Query Patterns

1. **Scan All Alerts** (`get_all_alerts()`):
   - Operation: Full table scan
   - Expected items: ~100-150 (50-100 assets × 1-2 alerts avg)
   - Pagination: Handled by boto3 (1MB per page)
   - Response time: <500ms for 150 items

2. **Filter by Asset** (in-memory after scan):
   - No DynamoDB query optimization (single partition key per asset)
   - Service layer filters results after scan
   - Response time: <100ms filtering overhead

### Frontend State Management

1. **Initial Load**: Fetch all alerts once
2. **Filtering**: Client-side filtering (no API re-fetch)
3. **Refresh**: Manual page refresh (no auto-refresh/polling)
4. **Pagination**: Client-side (50 alerts per page)

---

## Data Consistency

### Eventual Consistency

- **DynamoDB**: Eventually consistent reads acceptable (no strong consistency requirement)
- **TTL Deletion**: May take up to 48 hours after expiration (acceptable per AWS documentation)
- **UI Impact**: Alerts may appear for up to 48 hours after 7-day mark (edge case, non-critical)

### No Conflict Resolution Needed

- **Read-only UI**: No writes from frontend
- **No optimistic updates**: Display always reflects backend state
- **No caching**: Fresh data on each page load

---

## Error Handling

### Backend Error Scenarios

| Error | Cause | Response | HTTP Status |
|-------|-------|----------|-------------|
| DynamoDB unavailable | AWS service outage | `{"detail": "Service temporarily unavailable"}` | 503 |
| No alerts found | Empty table or all expired | `{"alerts": [], "total_count": 0, ...}` | 200 |
| Invalid filter value | Malformed query param | `{"detail": "Invalid asset_code format"}` | 400 |
| Authentication failure | Missing/invalid credentials | `{"detail": "Unauthorized"}` | 401 |

### Frontend Error Scenarios

| Error | Cause | Display | User Action |
|-------|-------|---------|-------------|
| API call fails | Network/server error | Error message with retry button | Click "Retry" |
| Empty response | No alerts available | "No active alerts" message | Wait for alerts to generate |
| Slow response | API latency >2s | Loading spinner | Wait automatically |

---

## Migration Notes

**No data migration needed** - Feature uses existing data structures.

**Backward Compatibility**: ✅ Fully backward compatible
- Existing alerting command unchanged
- DynamoDB table unchanged
- Alert dataclass unchanged
- Slack notifications unchanged

**Forward Compatibility**: ✅ No breaking changes anticipated
- Adding new AlertType enum values supported (frontend displays as-is)
- Adding new fields to Alert.data supported (frontend renders JSON)
