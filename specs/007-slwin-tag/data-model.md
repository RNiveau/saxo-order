# Data Model: SLWIN Tag

**Feature**: 007-slwin-tag
**Date**: 2026-02-08
**Phase**: Phase 1 - Design

## Overview

This document defines the data structures and entities for the SLWIN tag feature. The feature extends the existing watchlist data model with a new tag value and associated business rules.

## Entity Changes

### WatchlistTag Enum (Backend)

**Location**: `api/models/watchlist.py`

**Current Definition**:
```python
class WatchlistTag(str, Enum):
    SHORT_TERM = "short-term"
    LONG_TERM = "long-term"
    CRYPTO = "crypto"
    HOMEPAGE = "homepage"
```

**Updated Definition**:
```python
class WatchlistTag(str, Enum):
    SHORT_TERM = "short-term"
    LONG_TERM = "long-term"
    CRYPTO = "crypto"
    HOMEPAGE = "homepage"
    SLWIN = "slwin"  # Stop Loss Win - mutually exclusive with SHORT_TERM
```

**Validation Rules**:
- SLWIN and SHORT_TERM are mutually exclusive (enforced in service layer)
- SLWIN can coexist with LONG_TERM, CRYPTO, and HOMEPAGE tags
- Tag value stored as lowercase string "slwin" in DynamoDB

### WatchlistItem Model

**Location**: `api/models/watchlist.py`

**Current Definition** (no changes needed):
```python
class WatchlistItem(BaseModel):
    id: str = Field(description="Unique identifier for the watchlist item")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    description: str = Field(description="Asset description/name")
    country_code: str = Field(description="Country code (e.g., 'xpar')")
    current_price: float = Field(description="Current price of the asset")
    variation_pct: float = Field(description="Percentage variation from previous period")
    currency: Currency = Field(description="Currency code (e.g., 'EUR', 'USD')")
    added_at: str = Field(description="ISO timestamp when added to watchlist")
    labels: List[str] = Field(
        default_factory=list,
        description="Labels for the asset (e.g., ['short-term', 'slwin'])",
    )
    tradingview_url: Optional[str] = Field(default=None, description="Custom TradingView URL")
    exchange: str = Field(default="saxo", description="Exchange (saxo or binance)")
```

**Notes**:
- `labels` field already supports arbitrary strings, including "slwin"
- No schema migration required
- Existing items without "slwin" in labels continue to work

### DynamoDB Schema

**Table**: `watchlist` (existing)

**Item Structure** (no changes):
```json
{
  "id": "string",                    // Partition key
  "asset_symbol": "string",
  "description": "string",
  "country_code": "string",
  "added_at": "ISO-8601 timestamp",
  "labels": ["string"],              // Can include "slwin"
  "asset_identifier": "number",
  "asset_type": "string",
  "exchange": "string"
}
```

**Example Items**:

```json
// SLWIN asset (no other tags)
{
  "id": "aapl",
  "asset_symbol": "aapl:xnas",
  "description": "Apple Inc.",
  "country_code": "xnas",
  "added_at": "2026-02-08T10:00:00Z",
  "labels": ["slwin"],
  "exchange": "saxo"
}

// SLWIN + LONG_TERM
{
  "id": "googl",
  "asset_symbol": "googl:xnas",
  "description": "Alphabet Inc.",
  "country_code": "xnas",
  "added_at": "2026-02-01T15:30:00Z",
  "labels": ["slwin", "long-term"],
  "exchange": "saxo"
}

// SLWIN + CRYPTO (crypto not excluded)
{
  "id": "btcusd",
  "asset_symbol": "btcusd",
  "description": "Bitcoin",
  "country_code": "",
  "added_at": "2026-02-05T09:00:00Z",
  "labels": ["slwin", "crypto"],
  "exchange": "binance"
}
```

**Invalid State** (enforced by backend):
```json
// INVALID: Cannot have both SLWIN and SHORT_TERM
{
  "id": "tsla",
  "labels": ["slwin", "short-term"]  // Backend auto-removes one
}
```

## Business Rules

### Tag Mutual Exclusivity

**Rule**: SLWIN and SHORT_TERM are mutually exclusive

**Enforcement Location**: `api/services/watchlist_service.py` (service layer)

**Enforcement Logic**:
```python
def _enforce_mutual_exclusivity(new_labels: List[str]) -> List[str]:
    """
    Enforce mutual exclusivity between SLWIN and SHORT_TERM tags.

    Args:
        new_labels: Requested labels array

    Returns:
        Filtered labels array with mutual exclusivity enforced
    """
    has_slwin = WatchlistTag.SLWIN.value in new_labels
    has_short_term = WatchlistTag.SHORT_TERM.value in new_labels

    if has_slwin and has_short_term:
        # Remove short-term when both present (SLWIN takes precedence by order of request)
        # In practice, frontend will only send one at a time
        new_labels = [l for l in new_labels if l != WatchlistTag.SHORT_TERM.value]

    return new_labels
```

**Trigger Points**:
- `update_labels()` method in `watchlist_service.py`
- Called before DynamoDB write operation
- Applied to all label update requests (UI, API, scripts)

### Sorting Priority

**Rule**: Watchlist items sorted by tag priority, then alphabetically by description

**Priority Order**:
1. SHORT_TERM (priority 0)
2. SLWIN (priority 1)
3. Untagged or other tags (priority 2)

**Implementation**:
```python
def sort_key(item: WatchlistItem) -> tuple:
    """
    Generate sort key for watchlist item.

    Returns:
        Tuple of (priority, description) for sorting
    """
    has_short_term = WatchlistTag.SHORT_TERM.value in item.labels
    has_slwin = WatchlistTag.SLWIN.value in item.labels
    description = item.description.lower() if item.description else ""

    # Priority: 0=short-term, 1=slwin, 2=other
    if has_short_term:
        priority = 0
    elif has_slwin:
        priority = 1
    else:
        priority = 2

    return (priority, description)
```

**Sort Result Example**:
```
1. Apple Inc. (short-term)
2. Tesla Inc. (short-term)
3. ──────────────────────── [divider]
4. Bitcoin (slwin, crypto)
5. Google (slwin, long-term)
6. ──────────────────────── [divider]
7. Amazon (long-term)
8. Microsoft (homepage)
```

### Crypto Asset Filtering

**Rule**: Crypto assets excluded from sidebar UNLESS tagged with SHORT_TERM or SLWIN

**Current Logic** (needs update):
```python
has_crypto = WatchlistTag.CRYPTO.value in labels
has_short_term = WatchlistTag.SHORT_TERM.value in labels
if has_crypto and not has_short_term:
    continue  # Exclude from sidebar
```

**Updated Logic**:
```python
has_crypto = WatchlistTag.CRYPTO.value in labels
has_short_term = WatchlistTag.SHORT_TERM.value in labels
has_slwin = WatchlistTag.SLWIN.value in labels

# Exclude crypto UNLESS it has short-term OR slwin
if has_crypto and not has_short_term and not has_slwin:
    continue  # Exclude from sidebar
```

**Examples**:
- `["crypto"]` → Excluded from sidebar ❌
- `["crypto", "short-term"]` → Included in sidebar ✅
- `["crypto", "slwin"]` → Included in sidebar ✅
- `["crypto", "slwin", "long-term"]` → Excluded (long-term filter takes precedence) ❌

### Long-Term Tag Interaction

**Rule**: Long-term tag filtering takes precedence over SLWIN

**Logic**: Assets with `long-term` tag are excluded from main sidebar regardless of other tags

**Examples**:
- `["slwin"]` → Included in sidebar ✅
- `["slwin", "long-term"]` → Excluded from sidebar (long-term view only) ❌
- `["slwin", "homepage"]` → Included in sidebar ✅

## State Transitions

### Tag Toggle State Machine

**States**:
- `NO_TAG`: No SLWIN or SHORT_TERM tag
- `HAS_SLWIN`: Has SLWIN tag (no SHORT_TERM)
- `HAS_SHORT_TERM`: Has SHORT_TERM tag (no SLWIN)

**Transitions**:

```
NO_TAG
  → [Click SLWIN button] → HAS_SLWIN
  → [Click Short-Term button] → HAS_SHORT_TERM

HAS_SLWIN
  → [Click SLWIN button] → NO_TAG
  → [Click Short-Term button] → HAS_SHORT_TERM (SLWIN auto-removed)

HAS_SHORT_TERM
  → [Click Short-Term button] → NO_TAG
  → [Click SLWIN button] → HAS_SLWIN (SHORT_TERM auto-removed)
```

**Transition Enforcement**: Backend service layer

**Frontend Behavior**:
- Frontend sends full desired labels array
- Backend enforces mutual exclusivity before writing
- Frontend re-fetches watchlist status after update

## Data Integrity

### Invariants

1. **Mutual Exclusivity**: An asset MUST NOT have both "slwin" and "short-term" in labels array
2. **Tag Values**: All tag values MUST match `WatchlistTag` enum values (lowercase strings)
3. **Labels Array**: Labels array MUST be a list (can be empty)
4. **Idempotency**: Applying same label update twice MUST produce same result

### Validation Rules

**Backend Validation** (in service layer):
- Remove duplicate labels: `list(set(new_labels))`
- Enforce mutual exclusivity: `_enforce_mutual_exclusivity(new_labels)`
- Validate tag values against enum: Optional (DynamoDB accepts arbitrary strings)

**Frontend Validation**:
- Disable button during update: `disabled={updatingLabel}`
- Optimistic UI update: Set `isSLWIN` state immediately
- Rollback on error: Revert `isSLWIN` state if API call fails

### Concurrency Handling

**Strategy**: Last-write-wins with DynamoDB atomic operations

**DynamoDB Operation**:
```python
table.update_item(
    Key={'id': asset_id},
    UpdateExpression='SET labels = :labels',
    ExpressionAttributeValues={':labels': new_labels}
)
```

**Concurrency Scenario**:
1. User A clicks "SLWIN" button at T=0
2. User B clicks "Short-Term" button at T=0.1
3. Both requests reach backend simultaneously
4. DynamoDB processes in order (non-deterministic)
5. Last write wins: Either SLWIN or SHORT_TERM persists

**Mitigation**: Acceptable for this use case (low probability, minimal impact)

## Frontend State Management

### React State Variables

**Location**: `frontend/src/pages/AssetDetail.tsx`

**State Variables**:
```typescript
const [isSLWIN, setIsSLWIN] = useState<boolean>(false);
const [isShortTerm, setIsShortTerm] = useState<boolean>(false);
const [isLongTerm, setIsLongTerm] = useState<boolean>(false);
const [isHomepage, setIsHomepage] = useState<boolean>(false);
const [updatingLabel, setUpdatingLabel] = useState<boolean>(false);
```

**State Initialization** (from API response):
```typescript
if (response.in_watchlist) {
  const watchlistData = await watchlistService.getAllWatchlist();
  const item = watchlistData.items.find(item => item.id === code);
  if (item) {
    setIsShortTerm(item.labels.includes('short-term'));
    setIsSLWIN(item.labels.includes('slwin'));
    setIsLongTerm(item.labels.includes('long-term'));
    setIsHomepage(item.labels.includes('homepage'));
  }
}
```

### Label Update Logic

**Toggle Handler**:
```typescript
const handleToggleSLWIN = async () => {
  if (!symbol) return;

  try {
    setUpdatingLabel(true);
    setWatchlistError(null);
    setWatchlistSuccess(null);

    const [code] = symbol.split(':');
    const assetName = indicatorData?.description || symbol;

    // Build labels array: remove short-term if present, toggle slwin
    const newLabels: string[] = [];
    if (isLongTerm) newLabels.push('long-term');
    if (isHomepage) newLabels.push('homepage');
    if (!isSLWIN) newLabels.push('slwin');  // Add if not present, remove if present

    await watchlistService.updateLabels(code, newLabels);

    setIsSLWIN(!isSLWIN);
    if (isShortTerm) setIsShortTerm(false);  // Update UI for mutual exclusivity

    const action = isSLWIN ? 'Removed from' : 'Added to';
    setWatchlistSuccess(`${action} SLWIN positions: ${assetName}`);

    setTimeout(() => setWatchlistSuccess(null), 3000);
  } catch (err: any) {
    const errorMessage = err.response?.data?.detail || 'Failed to update label';
    setWatchlistError(errorMessage);
    setTimeout(() => setWatchlistError(null), 5000);
  } finally {
    setUpdatingLabel(false);
  }
};
```

**Short-Term Toggle Update** (enforce mutual exclusivity):
```typescript
const handleToggleShortTerm = async () => {
  // ... existing code ...

  // Build labels array: remove slwin if present, toggle short-term
  const newLabels: string[] = [];
  if (isLongTerm) newLabels.push('long-term');
  if (isHomepage) newLabels.push('homepage');
  if (!isShortTerm) newLabels.push('short-term');

  await watchlistService.updateLabels(code, newLabels);

  setIsShortTerm(!isShortTerm);
  if (isSLWIN) setIsSLWIN(false);  // NEW: Update UI for mutual exclusivity

  // ... rest of existing code ...
};
```

## API Contract

No changes to API contracts required. Existing endpoints handle SLWIN tag:

- `GET /api/watchlist` - Returns items with SLWIN tag in labels array
- `PUT /api/watchlist/{asset_id}/labels` - Accepts "slwin" in labels array
- Backend enforces mutual exclusivity automatically

See `contracts/watchlist-api.yaml` for complete API specification (no updates needed).

## Migration Strategy

**No migration required**:
- New enum value added (backward compatible)
- Existing labels arrays support arbitrary strings
- No database schema changes
- No data transformation needed

**Deployment**:
1. Deploy backend with new enum value
2. Deploy frontend with SLWIN button
3. No downtime or rollback concerns

**Rollback**:
- Remove SLWIN enum value and button
- Existing "slwin" labels in DynamoDB harmless (ignored by code)
- No data cleanup required

## Summary

The SLWIN tag extends the existing watchlist data model with minimal changes:

- **Backend**: Add SLWIN enum value, update sorting logic, extend crypto filter
- **Frontend**: Add boolean state variable, add toggle button, update sidebar divider logic
- **Database**: No schema changes (labels array already supports arbitrary strings)
- **Business Rules**: Mutual exclusivity enforced in service layer, sorting priority defined
- **Migration**: None required (fully backward compatible)

All changes follow existing patterns and constitution principles. Ready for contract generation.
