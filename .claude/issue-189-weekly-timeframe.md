# Implementation Plan for Issue #189: Manage Weekly Timeframe in Candles

## Overview
Add weekly timeframe support to the candles service by implementing candle building logic from daily candles. Weekly candles will be built directly from daily candles, NOT through the hour-based building process.

## Current State Analysis
- ✅ `UnitTime.W` enum already exists
- ✅ Binance client fully supports weekly (`"1w"` interval)
- ✅ Saxo API horizon 10080 defined and working in IndicatorService
- ✅ API already exposes weekly timeframe
- ❌ No `build_weekly_candles_from_daily()` helper function
- ❌ WorkflowEngine doesn't handle weekly timeframe

## Implementation Steps

### 1. Add Weekly Candle Building Helper Function
**File**: `utils/helper.py`

Add `build_weekly_candles_from_daily()` function that:
- Takes a list of daily candles (newest first, index 0)
- Groups them by ISO week using `date.isocalendar()[:2]`
- Aggregates each week's candles into a single weekly candle
- **Open**: from Monday's daily candle
- **Close**: from Friday's daily candle
- **Lower**: minimum of all daily lows in that week
- **Higher**: maximum of all daily highs in that week
- Returns list of weekly candles (newest first)
- Handles incomplete current week gracefully

**Pattern to follow**: Similar to `build_h4_candles_from_h1()` and `build_daily_candles_from_h1()`

### 2. Update WorkflowEngine
**File**: `engines/workflow_engine.py`

Modify `_get_candles_from_indicator_ut()` method (lines 148-182):
- Add `UnitTime.W` to the conditional handling
- For weekly: fetch daily candles directly, then build weekly from daily
- Calculate appropriate multiplicator (likely 5× daily for 5 trading days per week)
- Do NOT call `build_hour_candles()` for weekly - use a separate path

### 3. Add Comprehensive Tests
**Files**:
- `tests/utils/test_helper.py` - Test weekly building logic
- `tests/services/test_candles_service.py` - Test service integration (if needed)

Test cases:
- Complete weeks (Monday-Friday)
- Incomplete current week
- Week boundaries and ISO week numbering
- Edge cases (holidays, market closures)
- Aggregation correctness (Monday open, Friday close, min/max OHLC)

### 4. Update SaxoClient Caching (Optional Enhancement)
**File**: `client/saxo_client.py`

Consider adding weekly horizon (10080) to the cache:
- Currently only H1 (60) and Daily (1440) are cached
- Weekly data changes less frequently, good candidate for caching
- Add to `_should_use_cache()` logic (lines 447-463)

## Technical Details

**Week Boundaries**: Use ISO week definition (Monday-Sunday) via `date.isocalendar()[:2]`

**Candle Aggregation Logic**:
```
For each ISO week:
- Open: Monday's daily candle open value
- Close: Friday's daily candle close value
- Lower: minimum of all daily lows in that week
- Higher: maximum of all daily highs in that week
- Date: Monday of that week
- UnitTime: UnitTime.W
```

**Current Week Handling**: The current incomplete week should be included as a weekly candle with whatever data is available (Monday's open, last available day's close).

**Note**: Building weekly from daily is separate from the hour-based building process in `CandlesService.build_hour_candles()`.

## Files to Modify
1. `utils/helper.py` - New function (~60 lines)
2. `engines/workflow_engine.py` - Add weekly handling (~10 lines)
3. `tests/utils/test_helper.py` - New test cases (~100 lines)
4. `client/saxo_client.py` - Optional caching update (~3 lines)

## Implementation Order
1. Write helper function `build_weekly_candles_from_daily()` with comprehensive tests
2. Update WorkflowEngine to handle weekly timeframe (separate path from hourly)
3. Add integration tests
4. Optional: Add caching for weekly horizon

## Estimated Complexity
**Medium** - Following established patterns, but requires careful handling of week boundaries and Monday open/Friday close logic.
