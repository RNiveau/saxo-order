# Research: MM7 Indicator & Workflow

## Findings

### 1. MA50Workflow Pattern (canonical blueprint)

**Decision**: Mirror `MA50Workflow` exactly, changing only the period from 50 to 7.

**Rationale**: `MA50Workflow` in `engines/workflows.py` is a clean, minimal class. Its `init_workflow` calls `mobile_average(candles, 50)` and stores the result as `self.indicator_value`. The `below_condition` and `above_condition` methods delegate entirely to `_is_within_indicator_range_minus_spread` / `_is_within_indicator_range_plus_spread` from `AbstractWorkflow`. No slope logic is involved — that lives in `indicator_service.combo()`, which is explicitly out of scope.

**Alternatives considered**: Subclassing `MA50Workflow` with an overridden period — rejected as over-engineering; a direct parallel class is cleaner and more readable.

---

### 2. IndicatorType Enum Extension

**Decision**: Add `MA7 = "ma7"` to `IndicatorType` in `model/workflow.py`.

**Rationale**: `IndicatorType` already has `MA50 = "ma50"` as the moving-average indicator pattern. The string value `"ma7"` follows the naming convention. `workflows.yml` references indicator names by string (e.g., `name: ma50`), so the new enum value `"ma7"` will be the YAML key traders use in workflow configurations.

**Alternatives considered**: Reusing `MA50` with a `value` field — rejected; that breaks type safety and clarity.

---

### 3. Workflow Engine Dispatch (3 touch points in `workflow_engine.py`)

**Decision**: Add `IndicatorType.MA7` as a new `case` in three `match` blocks.

**Rationale**: The engine dispatches on `indicator.name` in three places:
1. **Main dispatch** (line ~79): `case IndicatorType.MA50` → `MA50Workflow()`. Add parallel case for `MA7`.
2. **Weekly candle count** (line ~199): `case IndicatorType.MA50` → `nbr_weeks = 55`. Add `IndicatorType.MA7` → `nbr_weeks = 12` (7 candles + 5 buffer).
3. **Hourly candle count** (line ~234): `case IndicatorType.MA50` → `nbr_hour = 55 * multiplicator`. Add `IndicatorType.MA7` → `nbr_hour = 12 * multiplicator`.

**Candle count rationale**: MA50 requests 55 (50 + 5 buffer). MA7 requests 12 (7 + 5 buffer). This ensures the engine always has enough candles before `mobile_average` is called, preventing `SaxoException` in normal operation.

**Alternatives considered**: Grouping MA7 and MA50 in the same case with dynamic period — rejected; the match statement is the established dispatch pattern and combining would require restructuring the workflow factory.

---

### 4. `mobile_average` Function Compatibility

**Decision**: No changes to `mobile_average`. It already accepts a variable `period: int` parameter.

**Rationale**: `mobile_average(candles: List[Candle], period: int) -> float` already handles any period. It raises `SaxoException` when `len(candles) < period`, consistent with how MA50 behaves. The candle-count buffer (12 requested for MA7) handles the normal case. If a new instrument has fewer than 7 candles in history, the `SaxoException` propagates — this is the same behavior as MA50 with insufficient history and is acceptable.

---

### 5. No API or Frontend Changes

**Decision**: This feature is entirely within the backend workflow engine layer.

**Rationale**: No new HTTP endpoints are introduced. No new data is persisted. The `workflows.yml` YAML format already supports any `IndicatorType` string value via the existing deserialization. Traders add `name: ma7` to their workflow YAML config to use the new indicator.
