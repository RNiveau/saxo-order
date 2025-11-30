# Implementation Plan for Issue #189: Manage Weekly Timeframe in Candles

## Overview
Add weekly timeframe support to the candles service by fetching weekly candles directly from Saxo API (horizon 10080) and only building the current incomplete week from daily candles when needed.

## Current State Analysis
- ✅ `UnitTime.W` enum already exists
- ✅ Binance client fully supports weekly (`"1w"` interval)
- ✅ Saxo API horizon 10080 defined and working in IndicatorService
- ✅ API already exposes weekly timeframe
- ✅ `build_weekly_candles_from_daily()` helper function (for full rebuilding)
- ✅ `build_current_weekly_candle_from_daily()` helper function (for current week only)
- ✅ `CandlesService.build_weekly_candles()` method
- ✅ WorkflowEngine handles weekly timeframe

## Implementation Steps

### ✅ 1. Add Weekly Candle Building Helper Functions
**File**: `utils/helper.py`

**Completed:**
- ✅ `build_weekly_candles_from_daily()` - Rebuilds all weekly candles from daily data
- ✅ `build_current_weekly_candle_from_daily()` - Builds only current incomplete week

**Implementation details:**
- Groups candles by ISO week using `date.isocalendar()[:2]`
- Monday's open, latest day's close for current week
- Min/max for OHLC aggregation
- Returns weekly candles with proper UnitTime.W

### ✅ 2. Add CandlesService Method
**File**: `services/candles_service.py`

**Completed:**
- ✅ `build_weekly_candles()` method added
- Fetches weekly candles from Saxo API (horizon 10080)
- Only builds current incomplete week from daily candles if needed
- Follows the same pattern as daily candle handling

### ✅ 3. Update WorkflowEngine
**File**: `engines/workflow_engine.py`

**Completed:**
- ✅ Added `UnitTime.W` handling in `_get_candles_from_indicator_ut()`
- Calls `candles_service.build_weekly_candles()` for all weekly indicators
- Clean, non-duplicated code

### ✅ 4. Add Comprehensive Tests
**File**: `tests/utils/test_helper.py`

**Completed:**
- ✅ 6 test cases for `build_weekly_candles_from_daily()`
- ✅ 3 test cases for `build_current_weekly_candle_from_daily()`
- All tests passing (34/34 total)

### 5. Update SaxoClient Caching (Optional Enhancement - PENDING)
**File**: `client/saxo_client.py`

Consider adding weekly horizon (10080) to the cache:
- Currently only H1 (60) and Daily (1440) are cached
- Weekly data changes less frequently, good candidate for caching
- Add to `_should_use_cache()` logic (lines 447-463)

## Technical Details

**Approach**: Fetch weekly candles directly from Saxo API, only build current week manually

**Week Boundaries**: Use ISO week definition (Monday-Sunday) via `date.isocalendar()[:2]`

**Candle Aggregation Logic**:
```
For current incomplete week only:
- Open: Monday's daily candle open value
- Close: Latest available day's close value
- Lower: minimum of all daily lows in that week
- Higher: maximum of all daily highs in that week
- Date: Monday of that week
- UnitTime: UnitTime.W
```

**Performance**:
- Before optimization: Fetched 825 daily candles + rebuilt all 55 weekly candles
- After optimization: Fetch 55 weekly candles from API + build 1 current week if needed
- Follows the same pattern as daily candle handling

## Files Modified
1. ✅ `utils/helper.py` - Added 2 functions (~110 lines)
2. ✅ `services/candles_service.py` - New `build_weekly_candles()` method (~70 lines)
3. ✅ `engines/workflow_engine.py` - Weekly handling simplified (~30 lines)
4. ✅ `tests/utils/test_helper.py` - 9 new test cases (~60 lines)
5. ⏳ `client/saxo_client.py` - Optional caching (pending)

## Next Steps

### Step 5: Optional Weekly Caching Enhancement
**Status**: PENDING
**Effort**: Low (~10 minutes)
**File**: `client/saxo_client.py`

Add horizon 10080 to the caching logic to improve performance:
- Weekly data changes less frequently than hourly/daily
- Good candidate for 30-minute TTL caching
- Would reduce API calls for workflows and indicators

### Alternative: Manual Testing
Before merging, consider testing with a real workflow:
1. Add a test workflow to `workflows.yml` with `ut: w`
2. Run: `poetry run k-order workflow run --force-from-disk y --select-workflow y`
3. Verify weekly candles are fetched and processed correctly

## Status
**Overall**: ~95% Complete
- Core functionality: ✅ Done
- Tests: ✅ Done
- Optional caching: ⏳ Pending
- Manual testing: ⏳ Recommended before merge
