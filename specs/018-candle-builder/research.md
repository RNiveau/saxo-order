# Research: Unified Candle Builder

**Feature**: 018-candle-builder | **Date**: 2026-04-19

## R-001: Parameterize H4 grouping from Market parameters

**Decision**: Add `h4_blocks: List[int]` attribute to Market dataclass.

**Rationale**: H4 groupings are business-defined boundaries, not mathematically derivable from session hours. EU (9 H1s) splits as 3+4+2, US (7 H1s) splits as 4+3. No formula produces these from just open/close hours. Encoding them in Market keeps the builder generic.

**Alternatives considered**:
- Algorithmic division (session_h1s / 4, distribute remainder): Produces 3+3+3 or 4+4+1 for EU, not the actual 3+4+2
- Hardcoded if/elif per open_hour: Current approach. Violates FR-011 (adding a market requires modifying builder code)

## R-002: Derive daily H1 count from Market parameters

**Decision**: Compute `num_h1 = close_hour - open_hour + (1 if open_minutes == 0 else 0)`.

**Rationale**:
- EU: open_minutes=0, so 15 - 7 + 1 = 9 H1 candles (07:00 through 15:00 inclusive)
- US: open_minutes=30, so 20 - 13 + 0 = 7 H1 candles (13:30 through 19:30)

The +1 for open_minutes=0 accounts for the inclusive first hour: H1s at 7:00, 8:00, ..., 15:00 = 9 values spanning 8 hours + the starting hour.

**Ending hour detection** (replaces hardcoded 15/19):
- `ending_hour = close_hour - (1 if open_minutes == 30 else 0)`
- EU: 15 - 0 = 15 (last H1 starts at 15:00, covers 15:00-15:30)
- US: 20 - 1 = 19 (last H1 starts at 19:30, `hour` field = 19)

## R-003: CFD fallback removal scope

**Decision**: Remove `cfd_code` parameter from `build_hour_candles` and `build_weekly_candles` only. Keep `Workflow.cfd` field.

**Rationale**: `Workflow.cfd` serves dual purposes:
1. CFD fallback in candle building (being removed)
2. Asset code for close/trigger candle fetching in workflow engine (`get_candle_per_hour(workflow.cfd, ...)`)

Only purpose #1 is misleading. Purpose #2 is correct behavior - workflows intentionally use the CFD code for close/trigger evaluation because CFDs have extended trading hours.

**Blast radius**: 5 call sites lose `cfd_code` argument. No model/API/frontend changes needed.

## R-004: Merging get_candle_per_hour and build_hour_candles

**Decision**: Keep `build_hour_candles` (renamed `build_candles`) as single entry point. Remove `get_candle_per_hour`.

**Key reconciliation**: The two methods differ in count calculation:
- `get_candle_per_hour`: fixed counts (H1=4, H4=16, D=40 thirty-minute candles)
- `build_hour_candles`: caller-specified `nbr_hours`

Unified approach: accept `count` (number of target-UT candles desired) and compute internally:
- H1 needs 2 × count 30m candles
- H4 needs 8 × count 30m candles
- D needs (session_h1_count × 2) × count 30m candles

## R-005: _build_h1_from_30m close_hour impact

**Decision**: After fixing EUMarket.close_hour from 17 to 15, verify `_build_h1_from_30m` filtering is correct.

**Current behavior with close_hour=17 (wrong)**:
```python
close_hour_ok = data[i]["Time"].hour <= 17  # EU, accepts h16
```
This produces H1 candles at hours 7-16 (10 candles), but the daily builder only consumes 9 (up to hour 15). The extra H1 at hour 16 is wasted.

**After fix with close_hour=15**:
```python
close_hour_ok = data[i]["Time"].hour <= 15  # EU, stops at h15
```
Now exactly 9 H1 candles are produced (7-15), matching what the daily builder expects. Cleaner pipeline, no wasted work.

**US market**: close_hour 21→20. The `_build_h1_from_30m` check for US (open_minutes=30) is `hour <= close_hour + 1 = 21`. After fix: `hour <= 21`. The last valid 30m candle is at 19:30 (hour=19), well within this range. Behavior unchanged.
