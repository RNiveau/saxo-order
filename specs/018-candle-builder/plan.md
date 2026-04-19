# Implementation Plan: Unified Candle Builder

**Branch**: `018-candle-builder` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-candle-builder/spec.md`

## Summary

Refactor the existing candle-building pipeline to be fully parameterized by Market, remove CFD fallback, merge duplicate entry points, and fix model inaccuracies. This is an incremental refactoring of working code (12/17 requirements already implemented), not a rewrite.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Saxo API client (existing), pytest, unittest.mock
**Storage**: N/A (no persistence changes)
**Testing**: pytest with mocked Saxo client
**Target Platform**: AWS Lambda + local CLI
**Project Type**: single (backend only)
**Performance Goals**: N/A (no new performance requirements)
**Constraints**: Must not break existing workflow engine, indicator service, or snapshot command
**Scale/Scope**: ~10 files modified, 0 new files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | Changes stay within Service/Utils/Model layers. No cross-layer violations. |
| II. Clean Code First | PASS | Removing hardcoded `== 7`/`== 13` checks. Adding M30 enum instead of raw values. No unnecessary comments. |
| III. Configuration-Driven | PASS | Market parameters drive behavior, not hardcoded values. |
| IV. Safe Deployment | PASS | No infrastructure changes. |
| V. Domain Model Integrity | PASS | Candle ordering preserved (index 0 = newest). Market model corrected to match real UTC hours. Enum-driven UnitTime. |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/018-candle-builder/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── checklists/
    └── requirements.md
```

### Source Code (files to modify)

```text
model/
├── __init__.py          # Fix EUMarket/USMarket close_hour values
└── workflow.py          # Add M30 to UnitTime enum

services/
└── candles_service.py   # Remove CFD fallback, merge methods, pass Market

utils/
└── helper.py            # Parameterize H4/Daily builders, remove legacy function

engines/
└── workflow_engine.py   # Update callers (remove cfd_code, use unified method)

saxo_order/commands/
├── snapshot.py          # Update callers (remove cfd_code)
└── alerting.py          # Migrate from legacy build_daily_candle_from_hours

tests/
├── utils/test_helper.py # Update H4/Daily builder tests, remove legacy test
└── services/test_candles_service.py  # Update for merged method, no CFD
```

**Structure Decision**: No new files. All changes are modifications to existing modules in the established project structure.

## Phase 0: Research

### R-001: How to parameterize H4 grouping from Market parameters

**Decision**: Add an `h4_blocks` attribute to the Market dataclass that defines the H1 grouping pattern for H4 candles.

**Rationale**: H4 groupings are irregular (EU: 3/4/2, US: 4/3) because trading sessions don't divide evenly into 4-hour blocks. There is no mathematical formula that produces these exact groupings from just open_hour/close_hour. They are business-defined boundaries. Encoding them in the Market definition keeps the builder generic while allowing each market to specify its own pattern.

**Alternatives considered**:
- Algorithmic computation (divide session into ~4h chunks): Rejected because the current groupings don't follow a simple division rule (EU has 3+4+2, not 4+4+1 or 3+3+3)
- Hardcoded if/elif per market: Rejected because adding a new market requires modifying builder functions (violates FR-011)

### R-002: How to compute daily H1 count from Market parameters

**Decision**: Derive the H1 count algorithmically from Market parameters:
- When `open_minutes == 0`: `num_h1 = close_hour - open_hour + 1` (EU: 15-7+1 = 9)
- When `open_minutes == 30`: `num_h1 = close_hour - open_hour` (US: 20-13 = 7)

General formula: `num_h1 = close_hour - open_hour + (1 if open_minutes == 0 else 0)`

**Rationale**: Unlike H4, daily grouping is straightforward - it's just "all H1 candles in the session." The count can be derived from the session boundaries. No need for an extra Market attribute.

**Alternatives considered**:
- Adding a `daily_h1_count` attribute to Market: Rejected because it's redundant with the hours already stored

### R-003: Scope of CFD removal

**Decision**: Remove only the `cfd_code` parameter from `build_hour_candles` and `build_weekly_candles`, and the CFD fallback logic (lines 306-320 in candles_service.py). Keep `Workflow.cfd` as-is.

**Rationale**: `Workflow.cfd` is used beyond the fallback - it's the asset code for fetching close/trigger candles in the workflow engine (`get_candle_per_hour(workflow.cfd, ...)`). Only the candle-building fallback mechanism is misleading.

### R-004: How to merge get_candle_per_hour and build_hour_candles

**Decision**: Keep `build_hour_candles` as the single entry point (renamed to `build_candles`). Remove `get_candle_per_hour`. Callers that need a single candle take `[0]` from the returned list.

**Rationale**: `build_hour_candles` already supports H1/H4/D. `get_candle_per_hour` duplicates its logic with different count calculations. The "get single candle" use case is just `build_candles(..., count=N)[0]`.

Key difference to reconcile: `get_candle_per_hour` uses small fixed counts (4 for H1, 16 for H4, 40 for D) while `build_hour_candles` takes `nbr_hours` from the caller. The merged method should accept a `count` parameter representing the number of target-UT candles needed, and internally compute how many 30m candles to fetch.

### R-005: Daily builder - ending hour detection

**Decision**: The daily builder currently detects the end of a day by matching the last H1's hour (15 for EU, 19 for US). In the parameterized version, the ending H1 hour can be derived:
- When `open_minutes == 0`: ending hour = `close_hour` (EU: 15)
- When `open_minutes == 30`: ending hour = `close_hour - 1` (US: 20-1 = 19, because the last H1 starts at 19:30)

General formula: `ending_hour = close_hour - (1 if open_minutes == 30 else 0)`

**Rationale**: This replaces the hardcoded `hour == 15` / `hour == 19` checks with a derivation from Market parameters.

## Phase 1: Design

### Data Model Changes

See [data-model.md](./data-model.md) for details.

**UnitTime enum**: Add `M30 = "30m"` value.

**Market dataclass**: Add `h4_blocks` attribute and fix close_hour values:
```
Market:
  open_hour: int
  open_minutes: int      # 0 or 30
  close_hour: int
  h4_blocks: List[int]   # H1 counts per H4 block, e.g. [3, 4, 2]

EUMarket: open_hour=7, open_minutes=0, close_hour=15, h4_blocks=[3, 4, 2]
USMarket: open_hour=13, open_minutes=30, close_hour=20, h4_blocks=[4, 3]
```

### Implementation Phases

#### Step 1: Model changes (FR-002, FR-017)
**Files**: `model/workflow.py`, `model/__init__.py`
**Risk**: Low - additive changes

1. Add `M30 = "30m"` to `UnitTime` enum
2. Fix `EUMarket.close_hour` from 17 to 15
3. Fix `USMarket.close_hour` from 21 to 20
4. Add `h4_blocks: List[int]` field to `Market` dataclass
5. Set `h4_blocks=[3, 4, 2]` in `EUMarket.__init__`
6. Set `h4_blocks=[4, 3]` in `USMarket.__init__`

**Tests**: Verify existing tests still pass. No new tests needed for model changes.

#### Step 2: Remove CFD fallback (FR-014)
**Files**: `services/candles_service.py`, `engines/workflow_engine.py`, `saxo_order/commands/snapshot.py`
**Risk**: Medium - removes existing behavior, must verify no other code depends on it

1. Remove `cfd_code` parameter from `build_hour_candles` signature
2. Remove CFD fallback logic (lines 306-320) from `build_hour_candles`
3. Remove `cfd_code` parameter from `build_weekly_candles` signature
4. Remove `cfd_code` argument from `build_weekly_candles`'s internal call to `build_hour_candles`
5. Update caller in `workflow_engine.py:232` - remove `cfd_code=workflow.cfd`
6. Update caller in `workflow_engine.py:199` - remove `cfd_code=workflow.cfd`
7. Update 3 callers in `snapshot.py` - remove `cfd_code=index`
8. Update tests in `test_candles_service.py` and `test_workflow_engine.py`

**Tests**: Run full test suite. Verify no test depends on CFD fallback behavior.

#### Step 3: Parameterize H4 and Daily builders (FR-005, FR-006, FR-011)
**Files**: `utils/helper.py`, `services/candles_service.py`
**Risk**: High - core algorithmic change, must preserve exact grouping behavior

1. **Rewrite `build_h4_candles_from_h1`**: Replace `if open_hour_utc0 == 7` / `elif open_hour_utc0 == 13` with a single loop that uses `Market.h4_blocks` to determine group sizes. The function signature changes from `(candles, open_hour_utc0)` to `(candles, market)`.

   Algorithm (newest-first processing):
   - Compute the ending H1 hours for each H4 block by walking backward from the session end using h4_blocks sizes
   - Iterate through candles, matching ending hours to determine group boundaries
   - Use `_internal_build_candle` for aggregation (unchanged)

2. **Rewrite `build_daily_candles_from_h1`**: Replace hardcoded hour checks with derived values. Signature changes from `(candles, open_hour_utc0)` to `(candles, market)`.

   Algorithm:
   - Compute `ending_hour = close_hour - (1 if open_minutes == 30 else 0)`
   - Compute `num_h1 = close_hour - open_hour + (1 if open_minutes == 0 else 0)`
   - Match on `ending_hour` and group `num_h1` candles (replaces hardcoded 15/19 and 8/6)

3. **Update `_build_h1_from_30m`**: Already uses Market object - verify close_hour filtering works correctly with the fixed values.

4. **Update callers**: `build_hour_candles` and `get_candle_per_hour` pass Market to the helper functions instead of `open_hour_utc0`.

**Tests**: This is the critical step. Must verify:
- EU H4 grouping produces exactly 3/4/2 H1 groups (same as current)
- US H4 grouping produces exactly 4/3 H1 groups (same as current)
- EU Daily groups 9 H1 candles (same as current)
- US Daily groups 7 H1 candles (same as current)
- All existing parametrized test cases pass without modification to expected values

#### Step 4: Merge into single entry point (FR-015)
**Files**: `services/candles_service.py`, `engines/workflow_engine.py`
**Risk**: Medium - changes the public interface, all callers must be updated

1. Rename `build_hour_candles` to `build_candles` (it already handles H1, H4, D)
2. Change signature to accept `Market` object instead of individual hour parameters
3. Add `count` parameter (number of target-UT candles to produce)
4. Internally compute `nbr_30m = count * multiplier * 2` where multiplier depends on UT
5. Remove `get_candle_per_hour` method
6. Update workflow_engine callers:
   - `_get_candles_from_indicator_ut`: use `build_candles(code, ut, market, count=N)`
   - `_run_workflow` (close candle): use `build_candles(code, ut, market, count=1)[0]`
   - `_get_trigger_candle`: use `build_candles(code, ut, market, count=1)[0]`
7. Update snapshot.py callers
8. Update `build_weekly_candles` internal call

**Tests**: Verify all callers produce the same results as before. Focus on workflow engine tests.

#### Step 5: Remove legacy function (FR-016)
**Files**: `utils/helper.py`, `saxo_order/commands/alerting.py`, `tests/utils/test_helper.py`
**Risk**: Low - single production caller, straightforward migration

1. Identify usage in `alerting.py:663`: `hour_candle = build_daily_candle_from_hours(hour_candles, today.day)`
2. Migrate to use the unified pipeline: call `build_candles` with `ut=UnitTime.D` and `Market` (determine if EU or US from the asset context in alerting.py)
3. Remove `build_daily_candle_from_hours` from `utils/helper.py`
4. Remove corresponding test `test_build_daily_candle_from_hours` from `tests/utils/test_helper.py`
5. Remove the import in `alerting.py`

**Tests**: Run full test suite. Verify alerting behavior is preserved.

### Execution Order & Dependencies

```
Step 1 (Model) ─────────────────┐
                                 ├──> Step 3 (Parameterize builders)
Step 2 (Remove CFD) ────────────┘           │
                                            v
                                 Step 4 (Merge entry points)
                                            │
                                            v
                                 Step 5 (Remove legacy)
```

Steps 1 and 2 are independent and can be done in parallel. Step 3 depends on both (needs h4_blocks from Step 1, and cleaner interface from Step 2). Step 4 depends on Step 3 (the parameterized builders). Step 5 depends on Step 4 (needs the unified entry point to migrate the alerting.py caller).

## Complexity Tracking

No constitution violations. No complexity justifications needed.
