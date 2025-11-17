# Implementation Plan for Issue #473: Binance Asset View

## Overview

Implement Binance asset detail view following the existing Saxo pattern, ensuring all Binance API calls stay within `BinanceClient` and always return `Candle` objects.

## Context

Nothing exists in the application to get candle data for Binance assets. This plan builds everything needed to support Binance asset views with indicators (moving averages, price data, etc.) following the architectural patterns established for Saxo assets.

**Key Constraints:**
- No Binance API calls outside `BinanceClient`
- Every method must return `Candle` or `List[Candle]`, never raw Binance objects
- Provide methods to fit indicator needs in the asset detail page (MA7, MA20, MA50, MA200)
- Candles are always sorted newest first (index 0 = latest candle)

## Phase 1: Extend BinanceClient with Candle Methods ✅ COMPLETED

**File:** `client/binance_client.py`

### 1.1 Add Interval Mapping Helper
Create method to convert `UnitTime` enum to Binance interval strings:
- `UnitTime.D` → `"1d"`
- `UnitTime.W` → `"1w"`
- `UnitTime.M` → `"1M"`
- `UnitTime.H1` → `"1h"`
- `UnitTime.H4` → `"4h"`
- `UnitTime.M15` → `"15m"`

```python
def _unit_time_to_binance_interval(self, unit_time: UnitTime) -> str:
    """Convert UnitTime enum to Binance interval string."""
```

### 1.2 Implement Raw Kline Fetching
Add private method to fetch raw kline data from Binance API:

```python
def _get_klines(self, symbol: str, interval: str, limit: int) -> List[List]:
    """
    Fetch klines (candlestick data) from Binance.

    Uses Binance API endpoint: GET /api/v3/klines

    Returns: List of klines in Binance format (nested arrays)
    """
```

Binance kline response format (each kline is an array):
```
[
  1499040000000,      # 0: Kline open time (milliseconds)
  "0.01634000",       # 1: Open price
  "0.80000000",       # 2: High price
  "0.01575800",       # 3: Low price
  "0.01577100",       # 4: Close price
  "148976.11427815",  # 5: Volume
  1499644799999,      # 6: Kline close time
  "2434.19055334",    # 7: Quote asset volume
  308,                # 8: Number of trades
  "1756.87402397",    # 9: Taker buy base asset volume
  "28.46694368",      # 10: Taker buy quote asset volume
  "0"                 # 11: Unused field
]
```

### 1.3 Add Mapping from Binance to Candle
Create private method to convert Binance kline array to `Candle` object:

```python
def _map_kline_to_candle(self, kline: List, unit_time: UnitTime) -> Candle:
    """
    Convert Binance kline array to Candle object.

    Args:
        kline: Binance kline array [timestamp, open, high, low, close, ...]
        unit_time: Time unit for the candle

    Returns: Candle object with rounded prices and proper datetime
    """
```

Mapping details:
- `open` ← kline[1] (convert to float, round to 4 decimals)
- `higher` ← kline[2] (convert to float, round to 4 decimals)
- `lower` ← kline[3] (convert to float, round to 4 decimals)
- `close` ← kline[4] (convert to float, round to 4 decimals)
- `date` ← kline[0] (convert milliseconds to datetime)
- `ut` ← unit_time parameter

### 1.4 Implement Public Candle Methods

**Get multiple candles:**
```python
def get_candles(self, symbol: str, unit_time: UnitTime, limit: int) -> List[Candle]:
    """
    Get historical candles for a Binance symbol.

    Args:
        symbol: Binance symbol (e.g., "BTCUSDT")
        unit_time: Time unit (D, W, M, H1, H4, M15)
        limit: Number of candles (max 1000)

    Returns: List of Candle objects, sorted newest first (index 0 = latest)
    """
```

**Get latest candle (for current price):**
```python
def get_latest_candle(self, symbol: str) -> Candle:
    """
    Get the most recent 1-minute candle for current price.

    Args:
        symbol: Binance symbol (e.g., "BTCUSDT")

    Returns: Latest 1-minute Candle
    """
```

### Error Handling
- Log API errors with appropriate context
- Raise meaningful exceptions for invalid symbols
- Handle rate limiting gracefully
- Validate symbol format before API calls

## Phase 2: Update Indicator Service ✅ COMPLETED

**File:** `api/services/indicator_service.py`

### 2.1 Add Binance Support to get_asset_indicators()

1. **Inject BinanceClient dependency** in constructor
2. **Accept exchange parameter** to explicitly specify the exchange:
   - Exchange parameter passed from API router (Exchange.SAXO or Exchange.BINANCE)
   - **Note:** Cannot rely on symbol format (some Saxo assets don't have ':')
   - Frontend must specify exchange when calling the API
3. **Route to appropriate client:**
   - If exchange == Exchange.SAXO: Use existing SaxoClient flow
   - If exchange == Exchange.BINANCE: Use new BinanceClient flow
4. **Fetch data for Binance assets:**
   - Get 210 daily candles (safety margin for MA200 calculation)
   - Get latest 1m candle for current price
   - Calculate variation from previous period's close
5. **Reuse existing indicator calculations:**
   - All MA calculations already work with `Candle` objects
   - No changes needed to `mobile_average()` function

### 2.2 Handle Binance-Specific Differences

- **No market/country_code parameters needed** (Binance uses single symbol)
- **24/7 trading** (no market hours logic)
- **Symbol format validation** (no colon character)
- **Currency handling** (most pairs are USDT quoted)

### 2.3 Create Helper Methods (if needed)

```python
def _get_binance_asset_indicators(self, symbol: str, unit_time: UnitTime) -> AssetIndicatorsResponse:
    """Get indicators for Binance asset."""

def _get_saxo_asset_indicators(self, code: str, country_code: str, unit_time: UnitTime) -> AssetIndicatorsResponse:
    """Get indicators for Saxo asset (refactored from main method)."""
```

## Phase 3: Update API Router ✅ COMPLETED

**File:** `api/routers/indicator.py`

**Status:** Completed as part of Phase 2 implementation.

### 3.1 Update Endpoint to Accept Exchange Parameter ✅

Implemented at `api/routers/indicator.py:29-50`:
- ✅ Added `exchange` query parameter (defaults to "saxo")
- ✅ Injected `BinanceClient` dependency
- ✅ `country_code` is `Optional[str]` with default "xpar"
- ✅ Exchange validation via `Exchange.get_value(exchange)`
- ✅ Passes exchange to `indicator_service.get_asset_indicators()`

### 3.2 Update Endpoint Logic ✅

Implemented at `api/routers/indicator.py:70-88`:
- ✅ Validates and converts exchange parameter to enum
- ✅ Validates unit_time against SUPPORTED_UNIT_TIMES
- ✅ Creates IndicatorService with both clients
- ✅ Passes exchange, country_code, and unit_time to service
- ✅ Backward compatible (defaults to SAXO exchange)

### 3.3 Update API Documentation ✅

Updated docstring at `api/routers/indicator.py:51-86`:
- ✅ Documents exchange parameter with examples for both Saxo and Binance
- ✅ Explains country_code usage (required/optional/ignored based on exchange)
- ✅ Provides usage examples for different asset types
- ✅ Documents all parameters with detailed descriptions
- ✅ Clarifies symbol format differences between exchanges

## Phase 4: Add Tests ✅ COMPLETED

### 4.1 Test BinanceClient Candle Methods

**File:** `tests/client/test_binance_client.py`

Test cases:
1. ✅ **test_map_kline_to_candle()** - COMPLETED
   - Tests with realistic BTC kline data
   - Verifies price rounding (4 decimals)
   - Validates timestamp conversion
   - Checks UnitTime assignment
   - Location: `tests/client/test_binance_client.py:132-157`

2. ✅ **test_unit_time_to_binance_interval()** - COMPLETED
   - Verifies all UnitTime enums map correctly to Binance intervals
   - Location: `tests/client/test_binance_client.py:159-168`

3. ✅ **test_get_klines_success()** - COMPLETED
   - Mocks successful Binance API response
   - Verifies correct endpoint/parameters called
   - Location: `tests/client/test_binance_client.py:170-214`

4. ✅ **test_get_candles_newest_first()** - COMPLETED
   - Mocks multiple klines
   - Verifies candles sorted newest first (index 0 = latest)
   - Location: `tests/client/test_binance_client.py:216-276`

5. ✅ **test_get_latest_candle()** - COMPLETED
   - Verifies uses 1m interval, limit=1
   - Returns proper Candle object
   - Location: `tests/client/test_binance_client.py:278-310`

6. ✅ **test_get_candles_error_handling()** - COMPLETED
   - Tests invalid symbol error handling
   - Tests API ClientError exceptions
   - Location: `tests/client/test_binance_client.py:312-329`

**Result:** All 12 BinanceClient tests passing ✅

### 4.2 Test Indicator Service with Binance ✅

**Note:** Service is tested indirectly through router tests which provide better integration coverage.

### 4.3 Test API Router ✅

**File:** `tests/api/routers/test_indicator.py` (updated)

Test cases added:
1. ✅ **test_get_asset_indicators_binance_symbol()** - COMPLETED
   - Calls endpoint with "BTCUSDT" and exchange=binance
   - Verifies BinanceClient methods called correctly
   - Verifies response format (symbol, MA periods, currency=USD)
   - Location: `tests/api/routers/test_indicator.py:393-443`

2. ✅ **test_get_asset_indicators_binance_variation()** - COMPLETED
   - Tests variation calculation for Binance assets
   - Verifies percentage change from previous close
   - Location: `tests/api/routers/test_indicator.py:445-481`

3. ✅ **test_get_asset_indicators_exchange_parameter()** - COMPLETED
   - Tests that exchange parameter correctly routes to appropriate client
   - Verifies Saxo client used when exchange=saxo
   - Location: `tests/api/routers/test_indicator.py:483-498`

4. ✅ **test_get_asset_indicators_country_code_optional_for_binance()** - COMPLETED
   - Tests that country_code is ignored for Binance assets
   - Verifies BinanceClient called even with country_code parameter
   - Location: `tests/api/routers/test_indicator.py:500-538`

**Result:** All 15 indicator router tests passing (11 original + 4 new) ✅

## Technical Notes

### Binance API Limits
- **Max candles per request:** 1000 (vs 1200 for Saxo)
- **Rate limits:** Weight-based system
- **No authentication needed** for klines endpoint (public data)

### Symbol Format Differences

| Aspect | Saxo | Binance |
|--------|------|---------|
| Symbol format | "CODE:MARKET" (e.g., "AAPL:xnas") | "BASEQUOTE" (e.g., "BTCUSDT") |
| Identifier | UIC integer (required) | None |
| Interval format | Horizon in minutes (1440) | String intervals ("1d", "1h") |
| Max candles | 1200 per request | 1000 per request |
| Market hours | Varies by exchange | 24/7 for crypto |
| Authentication | OAuth with token refresh | API key/secret (not needed for klines) |

### Candle Model (Existing - No Changes)

```python
@dataclass
class Candle:
    lower: float        # Low price
    higher: float       # High price
    open: float         # Open price
    close: float        # Close price
    ut: UnitTime        # Time unit (D, W, M, H1, H4, M15)
    date: Optional[datetime.datetime] = None
```

**Critical:** Candles are **always** sorted newest first (index 0 = latest)

### UnitTime Enum (Existing - No Changes)

```python
class UnitTime(EnumWithGetValue):
    D = "daily"
    M15 = "15m"
    H1 = "h1"
    H4 = "h4"
    W = "weekly"
    M = "monthly"
```

### Indicator Requirements (Asset Detail Page)

The asset detail page requires:
- **Current price** (from latest 1m candle)
- **Variation percentage** (current price vs previous period close)
- **Moving averages:** MA7, MA20, MA50, MA200
  - Requires minimum 200 candles
  - Fetch 210 for safety margin
- **TradingView URL** (optional, may not apply to Binance)
- **Currency and metadata**

## Files to Modify

### Phase 1 (BinanceClient)
- `client/binance_client.py` - Add all candle methods

### Phase 2 (Indicator Service)
- `api/services/indicator_service.py` - Add exchange routing

### Phase 3 (API Router)
- `api/routers/indicator.py` - Inject BinanceClient, detect symbol
- `api/dependencies.py` - Ensure get_binance_client() exists (may already exist from issue #472)

### Phase 4 (Tests)
- `tests/client/test_binance_client.py` - New or update existing
- `tests/api/services/test_indicator_service.py` - Update existing
- `tests/api/routers/test_indicator.py` - Update existing

## Dependencies

- Binance API documentation: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-api-information
- Existing `binance.spot.Spot` client (already imported in BinanceClient)
- Existing `Candle` model from `model/workflow.py` (no changes needed)
- Existing indicator functions from `services/indicator_service.py` (reuse as-is)

## Design Principles (from Issue Context)

✅ **No Binance API calls outside BinanceClient** - All API interactions encapsulated
✅ **Always return Candle objects** - Never expose raw Binance data structures
✅ **Methods fit indicator needs** - Support MA7, MA20, MA50, MA200 calculations
✅ **Candles newest first** - Maintain consistent ordering (index 0 = latest)
✅ **Exchange-agnostic indicators** - Reuse existing calculation functions

## Implementation Status

- ✅ Phase 1: Extend BinanceClient with Candle Methods (COMPLETED - Merged in PR #485)
- ✅ Phase 2: Update Indicator Service (COMPLETED - In PR #487)
- ✅ Phase 3: Update API Router (COMPLETED - In PR #487)
- ✅ Phase 4: Add Tests (COMPLETED - In PR #487)

## Additional Work Completed

- Fixed country_code handling to allow None for Saxo assets
- Updated type signatures to use Optional[str] for country_code
- Removed incorrect validation requiring country_code
- All 27 tests passing (12 BinanceClient + 15 indicator router)

## Test Coverage Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| BinanceClient candle methods | 12 | ✅ All passing |
| Indicator router (Saxo) | 11 | ✅ All passing |
| Indicator router (Binance) | 4 | ✅ All passing |
| **Total** | **27** | **✅ 100%** |
