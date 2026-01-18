# Data Model: Long-Term Positions Menu

**Feature**: 004-watchlist-menu
**Date**: 2026-01-18
**Purpose**: Document data structures, relationships, and validation rules

## Overview

The long-term positions feature reuses 100% of existing watchlist data models with no schema changes required. This document describes the existing models and how they're filtered for long-term positions.

---

## Entity Definitions

### WatchlistItem

**Purpose**: Represents a single asset in the watchlist with real-time market data

**Location**: `api/models/watchlist.py` (lines 39-63)

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | str | Yes | Unique identifier (asset_id, same as DynamoDB key) | Non-empty string |
| `asset_symbol` | str | Yes | Trading symbol in format "CODE:MARKET" (e.g., "itp:xpar") | Non-empty string |
| `description` | str | Yes | Human-readable asset name | Non-empty string |
| `country_code` | str | Yes | Market code (e.g., "xpar", "xetr", "xnas") | Non-empty string |
| `current_price` | float | Yes | Current price from market data | Positive float, rounded to 4 decimals |
| `variation_pct` | float | Yes | Daily percentage change | Float (can be negative) |
| `currency` | Currency | Yes | Currency enum value (EUR, USD, JPY, etc.) | Must be valid Currency enum |
| `added_at` | str | Yes | ISO 8601 timestamp of when added to watchlist | Valid ISO format |
| `labels` | list[str] | Yes | List of tag strings (use WatchlistTag enum values) | List of strings |
| `tradingview_url` | str | No | Custom TradingView chart URL | Valid URL or null |
| `exchange` | str | Yes | Exchange identifier ("saxo" or "binance") | Must be "saxo" or "binance" |

**Relationships**:
- **One-to-One** with DynamoDB `watchlist` table item
- **Many-to-One** with Currency enum
- **Many-to-Many** with WatchlistTag enum values (via labels list)

**State Transitions**: None (stateless entity)

**Lifecycle**: Created when asset added to watchlist, deleted when removed from watchlist

---

### WatchlistTag (Enum)

**Purpose**: Predefined classification labels for watchlist items

**Location**: `api/models/watchlist.py` (lines 9-13)

**Values**:

| Enum Value | String Value | Description | Usage |
|------------|--------------|-------------|-------|
| `SHORT_TERM` | `"short-term"` | Assets for short-term trading | Default watchlist sidebar view includes these |
| `LONG_TERM` | `"long-term"` | Assets for long-term holding | **Primary filter for this feature** |
| `CRYPTO` | `"crypto"` | Cryptocurrency assets | Auto-applied to Binance assets |
| `HOMEPAGE` | `"homepage"` | Featured assets for homepage | Max 6 items allowed |

**Validation Rules**:
- Labels list can contain multiple enum values
- Labels list can be empty (untagged asset)
- Homepage label limited to 6 assets (enforced in service layer)

---

### WatchlistResponse

**Purpose**: Response envelope for watchlist endpoints

**Location**: `api/models/watchlist.py` (lines 74-77)

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `items` | list[WatchlistItem] | Yes | List of enriched watchlist items |
| `total` | int | Yes | Count of items in list |

**Usage**: Returned by `/api/watchlist`, `/api/watchlist/all`, and **`/api/watchlist/long-term`** (new)

---

## Data Flow

### Long-Term Positions Filtering

```
┌─────────────────┐
│  DynamoDB Scan  │  Retrieve all watchlist items
│  (via Client)   │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────┐
│  Service Layer Filtering        │  Filter: WatchlistTag.LONG_TERM.value in labels
│  (get_long_term_positions)      │
└────────┬────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│  Enrichment                     │  Add current_price, variation_pct, tradingview_url
│  (_enrich_and_sort_watchlist)  │
└────────┬────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│  Sorting                        │  Alphabetically by description
│                                  │
└────────┬────────────────────────┘
         │
         ↓
┌─────────────────┐
│ WatchlistResponse│  Return to API router
└─────────────────┘
```

### Price Data Enrichment

```
┌────────────────┐
│ DynamoDB Item  │  Raw item with labels, no pricing
└───────┬────────┘
        │
        ↓
┌───────────────────────────┐
│ IndicatorService          │  Fetch current price based on exchange
│ get_current_price()       │
└───────┬───────────────────┘
        │
        ├──→ Binance assets: Call indicator with Exchange.BINANCE
        │
        └──→ Saxo assets: Call indicator with country_code
        │
        ↓
┌────────────────────────────┐
│ Calculate variation_pct    │  Daily change percentage
└───────┬────────────────────┘
        │
        ↓
┌────────────────────────────┐
│ Fetch TradingView URL      │  From asset_details DynamoDB table
└───────┬────────────────────┘
        │
        ↓
┌────────────────┐
│ WatchlistItem  │  Fully enriched with market data
└────────────────┘
```

---

## Filtering Logic

### Long-Term Positions Filter

**Rule**: Include ONLY items where `"long-term"` is in the `labels` list

**Python Implementation** (from `api/services/watchlist_service.py` pattern):

```python
def get_long_term_positions(self) -> WatchlistResponse:
    """
    Get long-term tagged positions for the dedicated menu.

    Returns:
        WatchlistResponse with items that have 'long-term' label
    """
    watchlist_items = self.dynamodb_client.get_watchlist()

    # Filter for ONLY long-term items
    filtered_items = []
    for item in watchlist_items:
        labels = item.get("labels", [])
        if WatchlistTag.LONG_TERM.value in labels:  # "long-term" in labels
            filtered_items.append(item)

    return self._enrich_and_sort_watchlist(filtered_items)
```

**TypeScript Type** (for frontend):

```typescript
interface WatchlistItem {
  id: string;
  asset_symbol: string;
  description: string;
  country_code: string;
  current_price: number;
  variation_pct: number;
  currency: string;
  added_at: string;
  labels: string[];
  tradingview_url: string | null;
  exchange: 'saxo' | 'binance';
}

interface WatchlistResponse {
  items: WatchlistItem[];
  total: number;
}
```

---

## Validation Rules

### Backend Validation (Service Layer)

1. **Label Enum Validation**: All labels must use `WatchlistTag` enum values (never hardcoded strings)
2. **Price Rounding**: Current prices rounded to 4 decimal places
3. **Variation Calculation**: Percentage change calculated as `((current - previous) / previous) * 100`
4. **Exchange Field**: Must be explicitly "saxo" or "binance", never inferred from country_code

### Frontend Validation

1. **Stale Data Detection**: Price data older than 15 minutes triggers warning indicator
2. **Crypto Badge Display**: Show badge only if `"crypto"` in labels array
3. **Empty State**: Show appropriate message when `items.length === 0`

---

## Database Schema

### DynamoDB Table: `watchlist`

**Table Type**: Key-Value store (no secondary indexes)

**Primary Key**: `id` (String, hash key only)

**Item Schema**:

```json
{
  "id": "asset_id",
  "asset_symbol": "itp:xpar",
  "description": "Inter Parfums",
  "country_code": "xpar",
  "added_at": "2024-12-15T10:30:00Z",
  "labels": ["long-term", "homepage"],
  "exchange": "saxo",
  "asset_identifier": 12345,
  "asset_type": "Stock"
}
```

**Notes**:
- `current_price` and `variation_pct` are NOT stored in DynamoDB (ephemeral data)
- `tradingview_url` fetched from separate `asset_details` table during enrichment
- `labels` stored as StringSet in DynamoDB, converted to list in service layer

**Query Pattern**: Full table scan (acceptable for current scale ~100 items)

---

## Scale & Performance Assumptions

### Data Volume

- **Current Scale**: ~50-100 watchlist items total
- **Long-Term Subset**: Estimated ~20-40 items with "long-term" label
- **Growth Projection**: Unlikely to exceed 500 items per user (portfolio size constraint)

### Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| DynamoDB Scan | <500ms | Time to retrieve all watchlist items |
| Price Enrichment | <2s | Parallel API calls to indicator service |
| Total Load Time | <3s | From API call to response (SC-005) |
| Refresh Interval | 60s | Auto-refresh when market open |

### Optimization Opportunities (Future)

1. **DynamoDB Query**: Add Global Secondary Index (GSI) on `labels` attribute if scale exceeds 1000 items
2. **Price Caching**: Cache enriched prices for 30 seconds to reduce indicator service load
3. **Incremental Updates**: Use WebSocket for real-time price updates instead of polling

**Current Decision**: Simple scan + filter approach is sufficient for target scale (100 items)

---

## Error Handling

### Missing Price Data

**Scenario**: Indicator service returns null for current_price (delisted stock, API outage)

**Behavior** (from FR-012):
- Display last known price (from previous successful fetch)
- Show ⚠️ stale data warning indicator
- Do NOT exclude item from list

**Implementation**:
```typescript
// Frontend detection
const isStalePrice = (lastUpdated: string): boolean => {
  const now = new Date();
  const updated = new Date(lastUpdated);
  const diffMinutes = (now.getTime() - updated.getTime()) / (1000 * 60);
  return diffMinutes > 15; // 15-minute threshold
};
```

### Missing Added_At Timestamp

**Scenario**: Legacy data missing `added_at` field

**Behavior** (from FR-015):
- Display item normally
- Show "Unknown" or "N/A" for addition date field
- Do NOT exclude item from list

---

## Testing Scenarios

### Unit Test Data Fixtures

**Test Fixture 1: Mixed Labels**
```python
{
    "id": "asset1",
    "asset_symbol": "itp:xpar",
    "description": "Inter Parfums",
    "labels": ["long-term", "homepage"],  # Should be included
    "exchange": "saxo"
}
```

**Test Fixture 2: Long-Term Only**
```python
{
    "id": "asset2",
    "asset_symbol": "btc:binance",
    "description": "Bitcoin",
    "labels": ["long-term", "crypto"],  # Should be included
    "exchange": "binance"
}
```

**Test Fixture 3: Short-Term Only**
```python
{
    "id": "asset3",
    "asset_symbol": "aapl:xnas",
    "description": "Apple Inc",
    "labels": ["short-term"],  # Should be excluded
    "exchange": "saxo"
}
```

**Test Fixture 4: No Labels**
```python
{
    "id": "asset4",
    "asset_symbol": "tsla:xnas",
    "description": "Tesla Inc",
    "labels": [],  # Should be excluded
    "exchange": "saxo"
}
```

**Expected Result**: Filter returns only asset1 and asset2

---

## Summary

- **No schema changes required**: Feature reuses existing data models
- **Single filter rule**: `"long-term" in labels`
- **Enrichment reuse**: Same price/variation logic as existing watchlist endpoints
- **Frontend typing**: WatchlistItem interface matches backend Pydantic model
- **Scale**: Current DynamoDB scan approach sufficient for target 100-item scale
- **Error handling**: Graceful degradation for missing price data and timestamps
