# Data Model: Unified Candle Builder

**Feature**: 018-candle-builder | **Date**: 2026-04-19

## Entity Changes

### UnitTime (modified)

**File**: `model/workflow.py`

| Value | Label | Change |
|-------|-------|--------|
| D | "daily" | Existing |
| M15 | "15m" | Existing |
| H1 | "h1" | Existing |
| H4 | "h4" | Existing |
| W | "weekly" | Existing |
| M | "monthly" | Existing |
| **M30** | **"30m"** | **Added** |

### Market (modified)

**File**: `model/__init__.py`

| Field | Type | Change |
|-------|------|--------|
| open_hour | int | Existing |
| open_minutes | int | Existing |
| close_hour | int | Existing - **values corrected** |
| **h4_blocks** | **List[int]** | **Added** - H1 counts per H4 block |

#### Derived properties

These are computed from Market fields, not stored:

- `num_h1_per_day = close_hour - open_hour + (1 if open_minutes == 0 else 0)`
- `daily_ending_hour = close_hour - (1 if open_minutes == 30 else 0)`

### EUMarket (modified)

| Field | Before | After |
|-------|--------|-------|
| open_hour | 7 | 7 (unchanged) |
| open_minutes | 0 | 0 (unchanged) |
| close_hour | **17** | **15** |
| h4_blocks | - | **[3, 4, 2]** |

Derived: `num_h1_per_day = 15 - 7 + 1 = 9`, `daily_ending_hour = 15`

### USMarket (modified)

| Field | Before | After |
|-------|--------|-------|
| open_hour | 13 | 13 (unchanged) |
| open_minutes | 30 | 30 (unchanged) |
| close_hour | **21** | **20** |
| h4_blocks | - | **[4, 3]** |

Derived: `num_h1_per_day = 20 - 13 = 7`, `daily_ending_hour = 19`

### Candle (unchanged)

**File**: `model/workflow.py`

| Field | Type | Notes |
|-------|------|-------|
| lower | float | Low price |
| higher | float | High price |
| open | float | Open price |
| close | float | Close price |
| ut | UnitTime | Now includes M30 as possible value |
| date | Optional[datetime] | Timestamp |

## Validation Rules

- `Market.open_minutes` must be 0 or 30 (existing validation in `build_hour_candles`)
- `Market.h4_blocks` must sum to `num_h1_per_day` (EU: 3+4+2=9, US: 4+3=7)
- `Market.close_hour > Market.open_hour` (implicit, not currently validated)

## No New Entities

No new tables, APIs, or persistence changes. All modifications are to existing in-memory data structures.
