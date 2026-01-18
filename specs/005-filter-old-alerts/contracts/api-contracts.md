# API Contracts: Filter Old Alerts (5-Day Retention)

**Feature**: 005-filter-old-alerts
**Date**: 2026-01-18
**Status**: No New API Contracts

## Overview

This feature implements **client-side filtering only**. No backend API changes are required. This document describes the existing API contracts that the frontend will continue to use.

---

## Existing API Endpoint: Get All Alerts

### Endpoint

```
GET /api/alerts
```

### Purpose

Retrieve all alerts from DynamoDB, with optional filtering by asset and alert type via query parameters.

### Request

**Method**: `GET`

**Query Parameters** (all optional):

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `asset_code` | string | Filter by asset symbol | `ITP`, `BTCUSDT` |
| `country_code` | string | Filter by exchange market code | `xpar`, `xnas` |
| `alert_type` | string | Filter by alert category | `COMBO`, `CONGESTION20` |

**Example Requests**:

```http
GET /api/alerts
GET /api/alerts?asset_code=ITP&country_code=xpar
GET /api/alerts?alert_type=COMBO
GET /api/alerts?asset_code=BTCUSDT
```

### Response

**Status Code**: `200 OK`

**Content-Type**: `application/json`

**Response Body**:

```typescript
{
  alerts: AlertItem[],
  total_count: number,
  available_filters: {
    asset_codes: string[],
    alert_types: string[]
  }
}
```

**AlertItem Structure**:

```typescript
{
  id: string;
  alert_type: string;
  asset_code: string;
  asset_description: string;
  exchange: string;
  country_code: string | null;
  date: string;                    // ISO 8601 timestamp (UTC)
  data: Record<string, any>;
  age_hours: number;
}
```

**Example Response**:

```json
{
  "alerts": [
    {
      "id": "alert_12345",
      "alert_type": "COMBO",
      "asset_code": "ITP",
      "asset_description": "Interparfums",
      "exchange": "saxo",
      "country_code": "xpar",
      "date": "2026-01-17T14:30:00Z",
      "data": {
        "price": 42.50,
        "volume": 150000
      },
      "age_hours": 24.5
    },
    {
      "id": "alert_67890",
      "alert_type": "CONGESTION20",
      "asset_code": "BTCUSDT",
      "asset_description": "Bitcoin/USDT",
      "exchange": "binance",
      "country_code": null,
      "date": "2026-01-15T09:00:00Z",
      "data": {
        "support_level": 42000,
        "resistance_level": 43000
      },
      "age_hours": 72.3
    }
  ],
  "total_count": 2,
  "available_filters": {
    "asset_codes": ["ITP", "BTCUSDT", "AAPL"],
    "alert_types": ["COMBO", "CONGESTION20", "DOUBLE_TOP"]
  }
}
```

### Error Responses

**Status Code**: `500 Internal Server Error`

**Response Body**:

```json
{
  "error": "Failed to retrieve alerts",
  "details": "DynamoDB query error"
}
```

---

## Frontend Service Layer

### Alert Service Method

**File**: `frontend/src/services/api.ts`

**Method Signature**:

```typescript
alertService.getAll(params?: {
  asset_code?: string;
  country_code?: string;
  alert_type?: string;
}): Promise<{
  alerts: AlertItem[];
  total_count: number;
  available_filters: {
    asset_codes: string[];
    alert_types: string[];
  };
}>
```

**Usage Examples**:

```typescript
// Fetch all alerts
const response = await alertService.getAll();
const allAlerts = response.alerts;

// Fetch alerts for specific asset
const assetResponse = await alertService.getAll({
  asset_code: 'ITP',
  country_code: 'xpar'
});
const assetAlerts = assetResponse.alerts;

// Fetch alerts by type
const typeResponse = await alertService.getAll({
  alert_type: 'COMBO'
});
const comboAlerts = typeResponse.alerts;
```

---

## Client-Side Processing

### Post-Fetch Processing Pipeline

After receiving alerts from the API, the frontend applies client-side filtering and deduplication:

```typescript
import { processAlerts } from '../utils/alertFilters';

// 1. Fetch from API
const data = await alertService.getAll();

// 2. Process alerts (filter by 5 days + deduplicate)
const processedAlerts = processAlerts(data.alerts);

// 3. Store in React state
setAlerts(processedAlerts);
```

**Processing Steps**:
1. Filter alerts to keep only those ≤120 hours old
2. Deduplicate by (asset_code, country_code, alert_type), keeping most recent
3. Sort by date descending (newest first)

---

## Contract Guarantees

### Backend Guarantees

- Returns all alerts from DynamoDB (no server-side 5-day filtering)
- `date` field is always ISO 8601 format in UTC
- `age_hours` is pre-calculated at fetch time
- `country_code` is null for Binance assets, non-null for Saxo assets
- Response includes metadata (`total_count`, `available_filters`)

### Frontend Responsibilities

- Apply 5-day age filter client-side
- Deduplicate alerts by (asset, type) combination
- Handle invalid or missing date fields gracefully
- Display filtered results consistently across all pages

---

## No Breaking Changes

### Backward Compatibility

- API endpoint unchanged
- Request/response format unchanged
- AlertItem interface unchanged
- Frontend can safely deploy without backend coordination

### Why No Backend Changes Needed

1. **DynamoDB TTL**: Alerts remain in database for 7 days (eventual cleanup), but frontend filters at 5 days for display
2. **Client-Side Filtering**: All filtering and deduplication logic runs in browser
3. **Performance Acceptable**: 500 alerts process in <50ms, no need for server-side optimization

---

## Testing API Contracts

### Manual API Testing

Use curl or Postman to verify existing API behavior:

```bash
# Fetch all alerts
curl -X GET "https://api.example.com/api/alerts"

# Fetch alerts for specific asset
curl -X GET "https://api.example.com/api/alerts?asset_code=ITP&country_code=xpar"

# Fetch alerts by type
curl -X GET "https://api.example.com/api/alerts?alert_type=COMBO"
```

### Expected Behavior

- API returns alerts regardless of age (no 5-day filter on backend)
- Response includes all required AlertItem fields
- `date` field is valid ISO 8601 timestamp
- `country_code` can be null (for Binance assets)

---

## Future Considerations

If client-side filtering becomes a performance bottleneck (>1000 alerts), consider:

1. **Backend Filtering**: Add `?max_age_hours=120` query parameter
2. **Backend Deduplication**: Add `?deduplicate=true` query parameter
3. **Pagination**: Add `?page=1&limit=100` for large datasets

However, for current scale (<500 alerts expected), client-side processing is sufficient.

---

## Reference

- **API Implementation**: `api/routers/alerts.py` (backend)
- **Service Layer**: `frontend/src/services/api.ts` (frontend)
- **Data Model**: `specs/005-filter-old-alerts/data-model.md`
- **Processing Logic**: `specs/005-filter-old-alerts/quickstart.md`
