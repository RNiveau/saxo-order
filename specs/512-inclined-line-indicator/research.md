# Research: Inclined Line Indicator (ROB/SOH)

**Date**: 2026-04-12
**Feature**: 512-inclined-line-indicator

## Existing Implementation Analysis

### Decision: Reuse code from `inclined-indicator` branch
**Rationale**: The branch contains ~170 lines of working code across 7 files. The model layer (Point, IndicatorInclined, IndicatorType.INCLINED), workflow loader parsing, workflow engine dispatch, and math utilities are complete and follow project conventions. Only `InclinedWorkflow.init_workflow()` and the condition methods need actual logic.
**Alternatives considered**:
- Start from scratch: Rejected — would duplicate 70% of existing work
- Cherry-pick individual commits: Rejected — the two commits are interdependent; merging the full diff is cleaner

### Decision: Use PolariteWorkflow as the pattern for InclinedWorkflow
**Rationale**: PolariteWorkflow is the closest analog — it evaluates candle position relative to a single indicator value (a price level). The inclined workflow does the same, except the price level is dynamically computed from a linear equation rather than statically configured. The `below_condition()` / `above_condition()` logic should mirror PolariteWorkflow's approach (checking close/high for below, close/low for above).
**Alternatives considered**:
- ZoneWorkflow pattern (two values): Rejected — inclined line projects to a single value at any point in time, not a zone
- ComboWorkflow pattern (direction-only): Rejected — too coarse; we need spread-aware comparison

### Decision: Business day calculation via `number_of_day_between_dates()`
**Rationale**: This function already exists, is tested, and accounts for market holidays via `saxo_client.is_day_open()`. It counts only days the market was open between two dates.
**Alternatives considered**:
- Simple weekday count (no holiday awareness): Rejected — would drift on holidays, producing incorrect line projections
- Cache holiday data: Deferred — could be a performance optimization later if API calls become bottleneck

### Decision: Store computed line value as `self.indicator_value` (single float)
**Rationale**: All existing workflows store their computed indicator as either a float or a tuple. Storing the projected line value at the current date as a single float lets the standard `_is_within_indicator_range_minus_spread()` / `_is_within_indicator_range_plus_spread()` helpers work directly.
**Alternatives considered**:
- Store the full LineFormula: Rejected — downstream condition methods only need the current projected value
- Store as IndicatorValue with direction: Rejected — direction is determined by comparing price to line, not pre-computed

### Decision: X axis always in business days, regardless of workflow unit time
**Rationale**: Confirmed by user in spec clarification. Intraday workflows (H1, H4) compare against the same daily projected level. This simplifies implementation — no need for hourly interpolation.
**Alternatives considered**:
- Hourly interpolation: Rejected by user — adds complexity with marginal precision benefit
- Per-UT granularity: Rejected by user — would require separate X-axis calculation per unit time

### Decision: Extend WorkflowIndicatorInput with optional x1/x2 Pydantic models for API
**Rationale**: The existing `WorkflowIndicatorInput` has `name`, `ut`, `value`, `zone_value`. Adding optional `x1` and `x2` fields (each with `date` and `price` subfields) follows the same pattern as `zone_value` — only used when indicator type requires it.
**Alternatives considered**:
- Separate InclinedIndicatorInput model: Rejected — breaks the uniform condition structure and requires API/frontend branching
- Encode points as value/zone_value: Rejected — semantically incorrect, confusing, and can't encode dates

### Decision: Validate x1.date != x2.date at loader and API level
**Rationale**: If both points have the same date, the X distance is 0 and slope calculation produces division by zero. Fail fast at configuration time rather than at runtime.
**Alternatives considered**:
- Runtime error in init_workflow: Rejected — late failure is harder to debug
- Allow same date with horizontal line: Rejected — use POL indicator for horizontal levels instead

## Candle Count for Inclined Indicator

### Decision: Request 1 candle only (same as POL/ZONE)
**Rationale**: The inclined indicator doesn't need historical candle data to compute its value — the line is fully defined by the two reference points and the current date's business day distance. The `init_workflow()` only needs access to the indicator's reference points and the saxo_client for date calculation. The candle passed to condition methods comes from the close candle fetch, not the indicator candle fetch.
**Alternatives considered**:
- Fetch candles spanning the reference point dates: Rejected — unnecessary; the line equation is computed from the configured points, not from candle data
