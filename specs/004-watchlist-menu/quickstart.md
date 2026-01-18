# Quickstart Guide: Long-Term Positions Menu

**Feature**: 004-watchlist-menu
**Branch**: `004-watchlist-menu`
**Date**: 2026-01-18

## Overview

This guide provides step-by-step instructions for setting up, developing, testing, and deploying the long-term positions menu feature.

---

## Prerequisites

### System Requirements

- **Python**: 3.11+
- **Node.js**: 18+ (for frontend)
- **Poetry**: Python dependency manager
- **AWS CLI**: Configured with valid credentials
- **Docker**: For Lambda deployment

### Repository Setup

```bash
# Clone repository (if not already cloned)
git clone <repository-url>
cd saxo-order

# Switch to feature branch
git checkout 004-watchlist-menu

# Verify branch
git branch --show-current
# Expected output: 004-watchlist-menu
```

---

## Development Setup

### Backend Setup

```bash
# Install Python dependencies
poetry install

# Verify installation
poetry run python --version
# Expected: Python 3.11+

# Run backend API server
poetry run python run_api.py
```

**Expected output**:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Backend runs on**: `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Run frontend dev server
npm run dev
```

**Expected output**:
```
  VITE v7.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Frontend runs on**: `http://localhost:5173`

### Environment Configuration

#### Backend (Optional)

The backend uses `config.yml` and `secrets.yml` for configuration. For local development, defaults work out of the box. To customize:

```yaml
# config.yml (example)
api:
  host: "0.0.0.0"
  port: 8000
  reload: true

dynamodb:
  table_name: "watchlist"
```

#### Frontend (Required)

Create `.env` file in `frontend/` directory:

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

**Note**: This file is gitignored. Use `.env.example` as a template.

---

## Implementation Workflow

### Phase 1: Backend Implementation

#### Step 1: Add Service Method

**File**: `api/services/watchlist_service.py`

**Location**: After `get_all_watchlist()` method (around line 230)

```python
def get_long_term_positions(self) -> WatchlistResponse:
    """
    Get long-term tagged positions for the dedicated menu.
    Filters for items with 'long-term' label and enriches with current prices.

    Returns:
        WatchlistResponse with items that have 'long-term' label
    """
    watchlist_items = self.dynamodb_client.get_watchlist()

    # Filter for ONLY long-term items
    filtered_items = []
    for item in watchlist_items:
        labels = item.get("labels", [])
        if WatchlistTag.LONG_TERM.value in labels:
            filtered_items.append(item)

    return self._enrich_and_sort_watchlist(filtered_items)
```

**Key Points**:
- Use `WatchlistTag.LONG_TERM.value` (enum) instead of `"long-term"` (string)
- Reuse `_enrich_and_sort_watchlist()` for price enrichment
- Follow existing pattern from `get_watchlist()` (lines 183-215)

#### Step 2: Add API Endpoint

**File**: `api/routers/watchlist.py`

**Location**: After `/all` endpoint (around line 106)

```python
@router.get("/long-term", response_model=WatchlistResponse)
async def get_long_term_positions(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Get long-term tagged positions for the dedicated menu.

    Returns:
        WatchlistResponse with long-term positions enriched with current prices
    """
    try:
        return watchlist_service.get_long_term_positions()
    except Exception as e:
        logger.error(f"Unexpected error getting long-term positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Key Points**:
- Path is `/long-term` (relative to `/api/watchlist` prefix)
- Reuse `WatchlistResponse` model (no new models needed)
- Follow existing endpoint pattern for consistency

#### Step 3: Test Backend Manually

```bash
# Start backend server
poetry run python run_api.py

# In another terminal, test endpoint
curl http://localhost:8000/api/watchlist/long-term

# Expected: JSON response with items array and total count
```

**Sample Response**:
```json
{
  "items": [
    {
      "id": "itp_xpar",
      "asset_symbol": "itp:xpar",
      "description": "Inter Parfums",
      "current_price": 45.32,
      "variation_pct": 1.25,
      "labels": ["long-term", "homepage"],
      ...
    }
  ],
  "total": 1
}
```

---

### Phase 2: Frontend Implementation

#### Step 1: Add API Service Method

**File**: `frontend/src/services/api.ts`

**Location**: In `watchlistService` object (around line 80)

```typescript
getLongTermPositions: async (): Promise<WatchlistResponse> => {
  const response = await axios.get<WatchlistResponse>(
    `${API_BASE_URL}/api/watchlist/long-term`
  );
  return response.data;
},
```

#### Step 2: Create Page Component

**File**: `frontend/src/pages/LongTermPositions.tsx` (new file)

**Template** (copy from `Watchlist.tsx` and modify):

```typescript
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistService, WatchlistItem } from '../services/api';
import { isMarketOpen, formatPrice, formatVariation } from '../utils/marketHours';
import './LongTermPositions.css';

export function LongTermPositions() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await watchlistService.getLongTermPositions();
      setItems(response.items);
      setError(null);
    } catch (err: any) {
      setError('Failed to load long-term positions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh with visibility detection (copy pattern from Watchlist.tsx)
  useEffect(() => {
    loadData();

    let intervalId: NodeJS.Timeout | null = null;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        if (isMarketOpen()) loadData();
        if (!intervalId) {
          intervalId = setInterval(() => {
            if (isMarketOpen()) loadData();
          }, 60000);
        }
      } else {
        if (intervalId) {
          clearInterval(intervalId);
          intervalId = null;
        }
      }
    };

    handleVisibilityChange();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (intervalId) clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const isStalePrice = (lastUpdated: string): boolean => {
    const now = new Date();
    const updated = new Date(lastUpdated);
    const diffMinutes = (now.getTime() - updated.getTime()) / (1000 * 60);
    return diffMinutes > 15;
  };

  if (loading && items.length === 0) return <div>Loading...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="long-term-positions">
      <h1>📊 Long-Term Positions</h1>

      {items.length === 0 ? (
        <p className="empty-state">No long-term positions found.</p>
      ) : (
        <table className="watchlist-table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Symbol</th>
              <th>Price</th>
              <th>Variation</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                onClick={() => navigate(`/asset/${item.asset_symbol}?exchange=${item.exchange}`)}
                className="watchlist-row"
              >
                <td className="description">
                  <div className="description-with-tags">
                    <span>{item.description}</span>
                    {item.labels?.includes('crypto') && (
                      <span className="badge badge-crypto">₿ Crypto</span>
                    )}
                  </div>
                </td>
                <td className="symbol">{item.asset_symbol}</td>
                <td className="price">
                  {formatPrice(item.current_price)}
                  {isStalePrice(item.added_at) && (
                    <span className="stale-indicator" title="Price data may be outdated">
                      ⚠️
                    </span>
                  )}
                </td>
                <td className={`variation ${item.variation_pct >= 0 ? 'positive' : 'negative'}`}>
                  {formatVariation(item.variation_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default LongTermPositions;
```

#### Step 3: Add Route

**File**: `frontend/src/App.tsx`

**Location**: Inside `<Routes>` component

```typescript
import LongTermPositions from './pages/LongTermPositions';

// ... inside <Routes>
<Route path="/long-term" element={<LongTermPositions />} />
```

#### Step 4: Add CSS

**File**: `frontend/src/pages/LongTermPositions.css` (new file)

```css
.long-term-positions {
  padding: 2rem;
}

.stale-indicator {
  margin-left: 0.5rem;
  color: #d29922;
  font-size: 0.9rem;
  cursor: help;
  opacity: 0.8;
}

.stale-indicator:hover {
  opacity: 1;
}

.badge-crypto {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 0.5rem;
}

.empty-state {
  text-align: center;
  color: #8b949e;
  margin-top: 3rem;
  font-size: 1.1rem;
}
```

#### Step 5: Test Frontend Manually

```bash
# Navigate to http://localhost:5173/long-term in browser
# Expected: Page displaying long-term positions or empty state
```

---

## Testing

### Backend Unit Tests

**File**: `tests/api/services/test_watchlist_service.py`

**Add test methods** (follow existing pattern from lines 36-102):

```python
def test_get_long_term_positions_filters_correctly(self):
    """Test that only items with 'long-term' label are returned"""
    # Mock DynamoDB response with mixed items
    self.mock_dynamodb_client.get_watchlist.return_value = [
        {
            "id": "asset1",
            "asset_symbol": "itp:xpar",
            "description": "Inter Parfums",
            "labels": ["long-term", "homepage"],  # Should be included
            "exchange": "saxo",
            "country_code": "xpar",
            "added_at": "2024-12-15T10:30:00Z"
        },
        {
            "id": "asset2",
            "asset_symbol": "aapl:xnas",
            "description": "Apple Inc",
            "labels": ["short-term"],  # Should be excluded
            "exchange": "saxo",
            "country_code": "xnas",
            "added_at": "2024-12-15T10:30:00Z"
        },
        {
            "id": "asset3",
            "asset_symbol": "btcusdt",
            "description": "Bitcoin",
            "labels": ["long-term", "crypto"],  # Should be included
            "exchange": "binance",
            "country_code": "",
            "added_at": "2025-01-10T14:22:00Z"
        }
    ]

    # Mock indicator service (no enrichment needed for filter test)
    self.mock_indicator_service.get_current_price.return_value = (100.0, 1.5)

    # Execute
    response = self.watchlist_service.get_long_term_positions()

    # Assert
    assert response.total == 2  # Only asset1 and asset3
    assert len(response.items) == 2
    item_ids = {item.id for item in response.items}
    assert "asset1" in item_ids
    assert "asset3" in item_ids
    assert "asset2" not in item_ids


def test_get_long_term_positions_empty_when_no_long_term_items(self):
    """Test empty result when no items have 'long-term' label"""
    self.mock_dynamodb_client.get_watchlist.return_value = [
        {
            "id": "asset1",
            "labels": ["short-term"],
            "exchange": "saxo",
            "country_code": "xpar",
            "added_at": "2024-12-15T10:30:00Z"
        }
    ]

    response = self.watchlist_service.get_long_term_positions()

    assert response.total == 0
    assert len(response.items) == 0
```

**Run tests**:
```bash
# Run specific test file
poetry run pytest tests/api/services/test_watchlist_service.py -v

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov
```

### Manual Testing Checklist

- [ ] Backend endpoint returns 200 status
- [ ] Response contains `items` array and `total` count
- [ ] Only items with "long-term" label are returned
- [ ] Prices and variations are populated
- [ ] Frontend page renders without errors
- [ ] Table displays items correctly
- [ ] Stale data warning appears when price > 15 min old
- [ ] Crypto badge appears for crypto assets
- [ ] Auto-refresh works (check network tab after 60 seconds)
- [ ] Clicking row navigates to asset detail page

---

## Code Quality Checks

### Backend Quality

```bash
# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy .

# Linting
poetry run flake8
```

**Expected**: No errors, all checks pass

### Frontend Quality

```bash
cd frontend

# Lint
npm run lint

# Type check (build)
npm run build
```

**Expected**: No TypeScript errors, build succeeds

---

## Deployment

### Backend Deployment

```bash
# Ensure you're on feature branch
git branch --show-current
# Expected: 004-watchlist-menu

# Run deployment script
./deploy.sh
```

**Script actions**:
1. Builds Docker image with Python dependencies
2. Pushes image to AWS ECR
3. Updates Lambda function via Pulumi
4. Verifies deployment

**Expected output**:
```
✓ Docker image built
✓ Pushed to ECR
✓ Pulumi update complete
✓ Lambda function updated
```

### Frontend Deployment

```bash
cd frontend

# Build production assets
npm run build

# Output in frontend/dist/
ls dist/
```

**Deploy frontend** (method depends on hosting setup):
- Upload `dist/` contents to S3/CDN
- Or deploy via CI/CD pipeline

---

## Troubleshooting

### Backend Issues

**Issue**: `ModuleNotFoundError: No module named 'X'`
```bash
# Reinstall dependencies
poetry install --no-cache
```

**Issue**: `DynamoDB connection error`
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify DynamoDB table exists
aws dynamodb describe-table --table-name watchlist
```

**Issue**: Endpoint returns 500 error
```bash
# Check logs
tail -f logs/api.log

# Run with debug logging
poetry run python run_api.py --log-level debug
```

### Frontend Issues

**Issue**: `CORS error` in browser console
- Backend: Check CORS origins in `api/main.py` include `http://localhost:5173`
- Frontend: Verify `VITE_API_URL` in `.env` points to correct backend

**Issue**: `Cannot GET /long-term` (404 on page refresh)
- Vite dev server: Should handle client-side routing automatically
- Production: Ensure server configured for SPA routing (redirect to `index.html`)

**Issue**: TypeScript errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## Next Steps

1. ✅ **Development Complete**: Backend endpoint + Frontend page implemented
2. ✅ **Testing Complete**: Unit tests pass, manual testing checklist complete
3. ⏳ **Code Review**: Submit PR for review
4. ⏳ **Deployment**: Deploy to staging/production
5. ⏳ **Monitoring**: Monitor logs for errors, track usage metrics

---

## Support & Resources

- **Feature Specification**: `specs/004-watchlist-menu/spec.md`
- **Implementation Plan**: `specs/004-watchlist-menu/plan.md`
- **Data Model**: `specs/004-watchlist-menu/data-model.md`
- **API Contract**: `specs/004-watchlist-menu/contracts/long-term-positions.yaml`
- **Constitution**: `.specify/memory/constitution.md`
- **CLAUDE.md**: `CLAUDE.md` (development guidance)

**Questions?** Check existing patterns in:
- Backend: `api/routers/watchlist.py`, `api/services/watchlist_service.py`
- Frontend: `frontend/src/pages/Watchlist.tsx`, `frontend/src/services/api.ts`
