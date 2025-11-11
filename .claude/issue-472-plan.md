# Implementation Plan for Issue #472: Adapt Search Section for Binance

## Overview

Adapt the search functionality to handle both Saxo Bank and Binance assets, with a unified Asset model and consistent API interface.

## Phase 1: Create Asset Model ✅ COMPLETED

**File:** `model/asset.py` (new file)

Created simple Asset dataclass:

```python
from dataclasses import dataclass
from typing import Optional
from model.enum import AssetType, Exchange


@dataclass
class Asset:
    symbol: str                      # e.g., "AAPL:xnas" or "BTCUSDT"
    description: str                 # Human-readable name
    asset_type: AssetType           # Using existing enum
    exchange: Exchange               # Exchange.SAXO or Exchange.BINANCE
    identifier: Optional[int] = None # Saxo UIC only
```

**File:** `model/enum.py` (updated)

Added Exchange enum:

```python
class Exchange(EnumWithGetValue):
    SAXO = "saxo"
    BINANCE = "binance"
```

## Phase 2: Implement BinanceClient.search() ✅ COMPLETED

**File:** `client/binance_client.py`

Added `search(keyword: str) -> List[Asset]` method:

1. ✅ Makes unauthenticated GET request to `https://api.binance.com/api/v3/exchangeInfo` using requests library
2. ✅ Filters symbols by keyword (case-insensitive match on symbol, baseAsset, or quoteAsset)
3. ✅ Only includes `status == "TRADING"` and `permissions` contains "SPOT"
4. ✅ Returns all matches (no whitelist filtering)
5. ✅ Returns `List[Asset]` with:
   - symbol: raw Binance symbol (e.g., "BTCUSDT")
   - description: "{baseAsset}/{quoteAsset}" (e.g., "BTC/USDT")
   - asset_type: AssetType.CRYPTO
   - exchange: "binance"
   - identifier: None
6. ✅ Error handling with logging for API failures

## Phase 3: Update SaxoClient.search() ✅ COMPLETED

**File:** `client/saxo_client.py`

Modified `search()` method to return `List[Asset]`:

1. ✅ Kept existing API call logic via `_find_asset()`
2. ✅ Transforms dict responses to Asset objects:
   - symbol: from "Symbol" field
   - description: from "Description" field
   - asset_type: AssetType enum from "AssetType" field with ValueError handling
   - exchange: "saxo"
   - identifier: from "Identifier" field
3. ✅ Logs warnings for unknown asset types and skips them

## Phase 4: Update SearchService ✅ COMPLETED

**File:** `api/services/search_service.py`

1. ✅ Updated constructor: `__init__(self, saxo_client: SaxoClient, binance_client: BinanceClient)` (both required)
2. ✅ Updated return type: `search_instruments(...) -> List[Asset]`
3. ✅ Calls both clients and merges results:
   - Gets `List[Asset]` from saxo_client.search()
   - Gets `List[Asset]` from binance_client.search()
   - Combines and returns merged list
4. ✅ Graceful error handling with try/except for each client

## Phase 5: Update API Models ✅ COMPLETED

**File:** `api/models/search.py`

Updated SearchResultItem to match Asset model:

- ✅ Kept: symbol, description, asset_type
- ✅ Changed `identifier: int` to `identifier: Optional[int]` with default=None
- ✅ Added `exchange: str` field with description
- ✅ Updated all field descriptions

## Phase 6: Update API Router & Dependencies ✅ COMPLETED

**File:** `api/dependencies.py`

- ✅ Added `get_binance_client() -> BinanceClient` with @lru_cache
- ✅ Uses empty key/secret since search endpoint is public
- ✅ Added documentation explaining no auth needed

**File:** `api/routers/search.py`

1. ✅ Injects both SaxoClient and BinanceClient (both required)
2. ✅ Passes both to SearchService
3. ✅ Transforms `List[Asset]` to `List[SearchResultItem]` using asset.asset_type.value
4. ✅ Updated endpoint documentation

## Phase 7: Update Frontend ⏳ PENDING

**File:** `frontend/src/services/api.ts`

- Add `exchange` field to SearchResultItem interface
- Change `identifier` to optional number

**File:** `frontend/src/pages/AssetDetail.tsx`

- Handle symbols without ':' (Binance format)
- If `symbol.includes(':')`: parse as `code:country_code` (Saxo)
- Else: use full symbol as code, empty country_code (Binance)

## Backend Implementation Status

### ✅ COMPLETED
- ✅ Unified Asset model throughout backend
- ✅ Both clients return List[Asset]
- ✅ Search always combines Saxo + Binance results
- ✅ No authentication needed for Binance search (public endpoint)
- ✅ All Binance calls encapsulated in BinanceClient only
- ✅ Code formatted with black and isort
- ✅ Error handling and logging implemented

### ⏳ REMAINING
- ⏳ Frontend TypeScript interface updates
- ⏳ Frontend asset detail page symbol handling

## Technical Notes

### Binance API Details

- **Endpoint:** `GET https://api.binance.com/api/v3/exchangeInfo`
- **Authentication:** None required (public endpoint)
- **Rate Limits:** Subject to Binance public API rate limits
- **Response Fields:**
  - `symbol`: Trading pair (e.g., "BTCUSDT")
  - `status`: Trading status (filter for "TRADING")
  - `baseAsset`: Base currency (e.g., "BTC")
  - `quoteAsset`: Quote currency (e.g., "USDT")
  - `permissions`: Array of permissions (filter for "SPOT")

### Symbol Format Differences

- **Saxo:** `CODE:MARKET` format (e.g., "AAPL:xnas")
- **Binance:** `BASEQUOTE` format (e.g., "BTCUSDT")

The frontend asset detail page needs to handle both formats gracefully.

### Asset Type Enum

The existing `AssetType` enum in `model/enum.py` already includes `CRYPTO = "Crypto"`, which will be used for all Binance assets.

## Implementation Details

### Files Changed

**Backend (All Completed):**
1. `model/asset.py` - New Asset dataclass model with Exchange enum
2. `model/enum.py` - Added Exchange enum for type safety
3. `client/binance_client.py` - Added search() method with requests library
4. `client/saxo_client.py` - Updated search() to return List[Asset]
5. `api/services/search_service.py` - Updated to use both clients
6. `api/models/search.py` - Updated SearchResultItem model
7. `api/dependencies.py` - Added get_binance_client() dependency
8. `api/routers/search.py` - Updated to inject both clients

**Frontend (Pending):**
1. `frontend/src/services/api.ts` - TypeScript interface updates needed
2. `frontend/src/pages/AssetDetail.tsx` - Symbol parsing logic updates needed

### Code Quality
- All Python code formatted with `black`
- Imports organized with `isort`
- Type hints added throughout
- Error handling with try/except blocks
- Logging added for debugging

### Testing Recommendations
1. Test Saxo search continues to work
2. Test Binance search returns crypto pairs
3. Test combined results from both exchanges
4. Test error handling when one exchange fails
5. Test frontend displays both exchange types correctly
6. Test asset detail page with Binance symbols (no colon format)
