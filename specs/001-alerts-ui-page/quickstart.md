# Quickstart Guide: Alerts UI Page

**Feature**: 001-alerts-ui-page
**Audience**: Developers implementing or testing the Alerts UI Page
**Prerequisites**: Python 3.11+, Node.js 18+, AWS credentials configured

---

## Overview

This guide walks through developing, testing, and deploying the Alerts UI Page feature locally.

**What you'll build**:
- Backend API endpoints (`GET /api/alerts`)
- Frontend React page displaying alerts
- Filtering by asset code and alert type

**What already exists**:
- DynamoDB table with alerts (generated daily by Lambda)
- Alert domain model and storage client
- Frontend application shell

---

## Quick Start (5 minutes)

### 1. Backend API Server

```bash
# From repository root
poetry install                    # Install dependencies
poetry run python run_api.py      # Start FastAPI server on port 8000
```

**Verify**: http://localhost:8000/docs (Swagger UI)

### 2. Frontend Development Server

```bash
# In a second terminal
cd frontend
npm install                       # Install dependencies
npm run dev                       # Start Vite dev server on port 5173
```

**Verify**: http://localhost:5173 (Homepage should load)

### 3. View Alerts Page

Navigate to: http://localhost:5173/alerts

**Expected**:
- List of alerts from last 7 days
- Filter dropdowns for asset and alert type
- Alert cards showing asset, type, timestamp, and details

---

## Development Workflow

### Backend Development

**File Structure**:
```
api/
├── routers/alerting.py         # FastAPI router (NEW)
├── services/alerting_service.py # Business logic (NEW)
├── models/alerting.py           # Pydantic models (NEW)
└── main.py                      # Register router (MODIFY)
```

**Step 1: Create Pydantic Models** (`api/models/alerting.py`)

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class AlertItemResponse(BaseModel):
    id: str
    alert_type: str
    asset_code: str
    country_code: Optional[str] = None
    date: datetime
    data: Dict[str, Any]
    age_hours: int

class AlertsResponse(BaseModel):
    alerts: List[AlertItemResponse]
    total_count: int
    available_filters: Dict[str, List[str]]
```

**Step 2: Create Service** (`api/services/alerting_service.py`)

```python
from client.aws_client import DynamoDBClient
from model import Alert
from api.models.alerting import AlertItemResponse, AlertsResponse
from datetime import datetime
from typing import List, Optional

class AlertingService:
    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb = dynamodb_client

    def get_all_alerts(
        self,
        asset_code: Optional[str] = None,
        alert_type: Optional[str] = None,
        country_code: Optional[str] = None
    ) -> AlertsResponse:
        # Fetch all alerts from DynamoDB
        all_alerts: List[Alert] = self.dynamodb.get_all_alerts()

        # Filter by parameters
        if asset_code:
            all_alerts = [a for a in all_alerts if a.asset_code == asset_code]
        if alert_type:
            all_alerts = [a for a in all_alerts if a.alert_type.value == alert_type]
        if country_code is not None:
            all_alerts = [a for a in all_alerts if a.country_code == country_code]

        # Sort by date descending
        all_alerts.sort(key=lambda a: a.date, reverse=True)

        # Transform to response models
        alert_items = [self._to_response(alert) for alert in all_alerts]

        # Calculate available filters
        filters = self._calculate_filters(all_alerts)

        return AlertsResponse(
            alerts=alert_items,
            total_count=len(alert_items),
            available_filters=filters
        )

    def _to_response(self, alert: Alert) -> AlertItemResponse:
        age = datetime.now() - alert.date
        return AlertItemResponse(
            id=alert.id,
            alert_type=alert.alert_type.value,
            asset_code=alert.asset_code,
            country_code=alert.country_code,
            date=alert.date,
            data=alert.data,
            age_hours=int(age.total_seconds() / 3600)
        )

    def _calculate_filters(self, alerts: List[Alert]) -> Dict[str, List[str]]:
        asset_codes = sorted(set(a.asset_code for a in alerts))
        alert_types = sorted(set(a.alert_type.value for a in alerts))
        country_codes = sorted(set(a.country_code or "" for a in alerts))
        return {
            "asset_codes": asset_codes,
            "alert_types": alert_types,
            "country_codes": country_codes
        }
```

**Step 3: Create Router** (`api/routers/alerting.py`)

```python
from fastapi import APIRouter, Depends, Query
from api.services.alerting_service import AlertingService
from api.models.alerting import AlertsResponse
from client.aws_client import DynamoDBClient
from typing import Optional

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

def get_alerting_service() -> AlertingService:
    dynamodb = DynamoDBClient()
    return AlertingService(dynamodb)

@router.get("", response_model=AlertsResponse)
async def get_alerts(
    asset_code: Optional[str] = Query(None, description="Filter by asset code"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    service: AlertingService = Depends(get_alerting_service)
) -> AlertsResponse:
    """
    Get all active alerts from the last 7 days.
    Supports filtering by asset_code, alert_type, and country_code.
    """
    return service.get_all_alerts(asset_code, alert_type, country_code)
```

**Step 4: Register Router** (`api/main.py`)

```python
from api.routers import alerting

# Add to app initialization
app.include_router(alerting.router)
```

**Test Backend**:
```bash
curl http://localhost:8000/api/alerts | jq .
curl "http://localhost:8000/api/alerts?asset_code=ITP" | jq .
```

---

### Frontend Development

**File Structure**:
```
frontend/src/
├── pages/Alerts.tsx             # Alerts page (NEW)
├── components/AlertCard.tsx     # Alert card component (NEW)
├── services/api.ts              # API client (MODIFY)
└── App.tsx                      # Add route (MODIFY)
```

**Step 1: Extend API Service** (`frontend/src/services/api.ts`)

```typescript
// Add interfaces
export interface AlertItem {
  id: string;
  alert_type: string;
  asset_code: string;
  country_code: string | null;
  date: string;
  data: Record<string, any>;
  age_hours: number;
}

export interface AlertsResponse {
  alerts: AlertItem[];
  total_count: number;
  available_filters: {
    asset_codes: string[];
    alert_types: string[];
    country_codes: string[];
  };
}

// Add service object
export const alertService = {
  async getAll(params?: {
    asset_code?: string;
    alert_type?: string;
    country_code?: string;
  }): Promise<AlertsResponse> {
    const response = await axios.get<AlertsResponse>('/api/alerts', { params });
    return response.data;
  }
};
```

**Step 2: Create Alert Card Component** (`frontend/src/components/AlertCard.tsx`)

```typescript
import React from 'react';
import { AlertItem } from '../services/api';

interface AlertCardProps {
  alert: AlertItem;
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert }) => {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  return (
    <div className="alert-card">
      <div className="alert-header">
        <span className="alert-type">{alert.alert_type}</span>
        <span className="alert-age">{alert.age_hours}h ago</span>
      </div>
      <div className="alert-body">
        <h3>{alert.asset_code}</h3>
        {alert.country_code && <span className="country">{alert.country_code}</span>}
        <p className="date">{formatDate(alert.date)}</p>
        <pre className="data">{JSON.stringify(alert.data, null, 2)}</pre>
      </div>
    </div>
  );
};
```

**Step 3: Create Alerts Page** (`frontend/src/pages/Alerts.tsx`)

```typescript
import React, { useState, useEffect } from 'react';
import { alertService, AlertsResponse } from '../services/api';
import { AlertCard } from '../components/AlertCard';

export const Alerts: React.FC = () => {
  const [data, setData] = useState<AlertsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    asset_code: undefined,
    alert_type: undefined,
    country_code: undefined
  });

  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await alertService.getAll(filters);
        setData(result);
      } catch (err) {
        setError('Failed to load alerts');
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, [filters]);

  if (loading) return <div>Loading alerts...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data || data.total_count === 0) return <div>No active alerts</div>;

  return (
    <div className="alerts-page">
      <h1>Alerts</h1>

      {/* Filters */}
      <div className="filters">
        <select
          value={filters.asset_code || ''}
          onChange={(e) => setFilters({ ...filters, asset_code: e.target.value || undefined })}
        >
          <option value="">All Assets</option>
          {data.available_filters.asset_codes.map(code => (
            <option key={code} value={code}>{code}</option>
          ))}
        </select>

        <select
          value={filters.alert_type || ''}
          onChange={(e) => setFilters({ ...filters, alert_type: e.target.value || undefined })}
        >
          <option value="">All Types</option>
          {data.available_filters.alert_types.map(type => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
      </div>

      {/* Alert List */}
      <div className="alerts-list">
        {data.alerts.map(alert => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
      </div>
    </div>
  );
};
```

**Step 4: Add Route** (`frontend/src/App.tsx`)

```typescript
import { Alerts } from './pages/Alerts';

// In your router configuration
<Route path="/alerts" element={<Alerts />} />
```

---

## Testing

### Backend Unit Tests

**Create**: `tests/api/services/test_alerting_service.py`

```python
from api.services.alerting_service import AlertingService
from model import Alert, AlertType
from datetime import datetime
from unittest.mock import Mock

def test_get_all_alerts():
    # Mock DynamoDBClient
    mock_db = Mock()
    mock_db.get_all_alerts.return_value = [
        Alert(
            alert_type=AlertType.COMBO,
            date=datetime(2026, 1, 10, 18, 15),
            data={"price": 150.25},
            asset_code="ITP",
            country_code="xpar"
        )
    ]

    # Test service
    service = AlertingService(mock_db)
    result = service.get_all_alerts()

    assert result.total_count == 1
    assert result.alerts[0].asset_code == "ITP"
    assert result.alerts[0].alert_type == "combo"

def test_filter_by_asset_code():
    mock_db = Mock()
    mock_db.get_all_alerts.return_value = [
        Alert(AlertType.COMBO, datetime.now(), {}, "ITP", "xpar"),
        Alert(AlertType.COMBO, datetime.now(), {}, "AAPL", "xnas")
    ]

    service = AlertingService(mock_db)
    result = service.get_all_alerts(asset_code="ITP")

    assert result.total_count == 1
    assert result.alerts[0].asset_code == "ITP"
```

**Run tests**:
```bash
poetry run pytest tests/api/services/test_alerting_service.py -v
```

### Backend Integration Tests

**Create**: `tests/api/routers/test_alerting.py`

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_get_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total_count" in data
    assert "available_filters" in data

def test_get_alerts_with_filter():
    response = client.get("/api/alerts?asset_code=ITP")
    assert response.status_code == 200
    data = response.json()
    assert all(alert["asset_code"] == "ITP" for alert in data["alerts"])
```

**Run tests**:
```bash
poetry run pytest tests/api/routers/test_alerting.py -v
```

### Manual Testing

1. **Verify DynamoDB has data**:
   ```bash
   aws dynamodb scan --table-name alerts --max-items 5
   ```

2. **Test API endpoints**:
   ```bash
   # All alerts
   curl http://localhost:8000/api/alerts | jq '.total_count'

   # Filtered by asset
   curl "http://localhost:8000/api/alerts?asset_code=ITP" | jq '.alerts[].asset_code'

   # Filtered by type
   curl "http://localhost:8000/api/alerts?alert_type=combo" | jq '.alerts[].alert_type'
   ```

3. **Test frontend**:
   - Navigate to http://localhost:5173/alerts
   - Verify alerts display
   - Test filter dropdowns
   - Verify filtering updates the list

---

## Troubleshooting

### Problem: "No active alerts" displayed

**Cause**: DynamoDB table is empty or all alerts expired
**Solution**:
1. Check if alerting Lambda has run: `aws logs tail /aws/lambda/alerting_lambda --follow`
2. Manually trigger alerting: `poetry run k-order alerting`
3. Verify alerts in DynamoDB: `aws dynamodb scan --table-name alerts`

### Problem: API returns 503 error

**Cause**: DynamoDB connection failure
**Solution**:
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check DynamoDB table exists: `aws dynamodb describe-table --table-name alerts`
3. Review `config.yml` and `secrets.yml` configuration

### Problem: Frontend shows CORS error

**Cause**: API server not allowing frontend origin
**Solution**:
1. Verify CORS config in `api/main.py` includes `http://localhost:5173`
2. Restart backend server after CORS changes
3. Check browser console for specific error details

### Problem: TypeScript compilation errors

**Cause**: Interface mismatch between backend and frontend
**Solution**:
1. Verify TypeScript interfaces match Pydantic models exactly
2. Run `npm run build` to catch type errors
3. Check API response in browser DevTools Network tab

---

## Deployment

### Backend Deployment

```bash
# Build Docker image and deploy to Lambda
./deploy.sh

# Verify deployment
curl https://your-api-url.com/api/alerts | jq '.total_count'
```

### Frontend Deployment

```bash
cd frontend
npm run build          # Creates frontend/dist/

# Deploy dist/ folder to your hosting provider (Vercel, Netlify, S3, etc.)
# Update VITE_API_URL in .env.production before building
```

---

## Asset Exclusion

### Overview

Assets can be excluded from alert processing to reduce noise and improve batch run efficiency. Excluded assets are automatically:
- Skipped during batch alerting runs
- Filtered out from alert view
- Removed from filter dropdowns

### Accessing Exclusion Management

1. Navigate to `/exclusions` or click "Asset Exclusions" in the sidebar
2. View excluded and active assets in separate sections
3. Use search box to quickly find assets

### Excluding/Un-excluding Assets

**Via UI**:
1. Find asset in the appropriate section (Active Assets or Excluded Assets)
2. Click "Exclude" or "Un-exclude" button
3. Confirm in dialog
4. Changes take effect on next batch run (within 24 hours)

**Programmatically**:
```python
# Via DynamoDB client
from client.aws_client import DynamoDBClient

dynamodb = DynamoDBClient()

# Exclude an asset
dynamodb.update_asset_exclusion("SAN", True)

# Un-exclude an asset
dynamodb.update_asset_exclusion("SAN", False)

# Get list of excluded assets
excluded = dynamodb.get_excluded_assets()
print(f"Excluded assets: {excluded}")
```

**Via API**:
```bash
# Exclude an asset
curl -X PUT http://localhost:8000/api/asset-details/SAN/exclusion \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": true}'

# Un-exclude an asset
curl -X PUT http://localhost:8000/api/asset-details/SAN/exclusion \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": false}'

# Get all excluded assets
curl http://localhost:8000/api/asset-details/excluded/list | jq .

# Get all assets with exclusion status
curl http://localhost:8000/api/asset-details | jq .
```

### Effects of Exclusion

**Batch Alerting**:
- Excluded assets are filtered from watchlist before processing begins
- No detection algorithms run for excluded assets
- Batch run time reduces proportionally (10 excluded ≈ 10% faster)
- Logs show filtered count: `Filtered out 10 excluded assets`

**Alert View**:
- Existing alerts for excluded assets are hidden from UI
- Excluded assets don't appear in filter dropdowns
- Alerts remain in DynamoDB until TTL expires (7 days)

**Manual Alerting**:
```bash
# This will respect exclusions and skip processing
poetry run k-order alerting --code=SAN --country-code=xpar
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/asset-details` | Get all assets with exclusion status |
| GET | `/api/asset-details/{asset_id}` | Get single asset details |
| PUT | `/api/asset-details/{asset_id}/exclusion` | Toggle exclusion status |
| GET | `/api/asset-details/excluded/list` | Get only excluded assets |

See `contracts/asset-exclusion-api.yaml` for full OpenAPI specification.

### Troubleshooting Exclusions

**Problem: Asset still generating alerts after exclusion**

**Cause**: Exclusion takes effect on next batch run (not immediate)

**Solution**:
1. Verify exclusion was successful:
   ```bash
   curl http://localhost:8000/api/asset-details/SAN | jq '.is_excluded'
   # Should return: true
   ```
2. Wait for next scheduled batch run (6:15 PM Paris time, Mon-Fri)
3. Or manually trigger: `poetry run k-order alerting`
4. Check logs confirm filtering: `Filtered out N excluded assets`

**Problem: Excluded asset appears in alert view**

**Cause**: Backend filtering not applied or cache issue

**Solution**:
1. Refresh the page (frontend cache clear)
2. Check backend logs for filtering message
3. Verify API response excludes asset:
   ```bash
   curl http://localhost:8000/api/alerts | jq '.alerts[].asset_code' | grep SAN
   # Should return nothing if SAN is excluded
   ```

**Problem: Cannot find asset in exclusion management page**

**Cause**: Asset not yet in `asset_details` table

**Solution**:
- Assets only appear after first manual interaction (e.g., setting TradingView link)
- You can still exclude via API by creating the record:
  ```bash
  curl -X PUT http://localhost:8000/api/asset-details/NEWASSET/exclusion \
    -H "Content-Type: application/json" \
    -d '{"is_excluded": true}'
  ```

---

## Next Steps

After completing this quickstart:

1. **Implement pagination** (frontend): Display 50 alerts per page
2. **Add styling** (frontend): Create CSS for alert cards and page layout
3. **Add sorting** (frontend): Allow sorting by date, asset, or type
4. **Add detail view** (frontend): Click alert to see full data payload
5. **Add refresh button** (frontend): Manual refresh without page reload

See `tasks.md` for full implementation checklist.
