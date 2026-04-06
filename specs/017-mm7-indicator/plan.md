# Implementation Plan: MM7 Indicator & Workflow

**Branch**: `017-mm7-indicator` | **Date**: 2026-03-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-mm7-indicator/spec.md`

## Summary

Add MM7 (7-period simple moving average) as a workflow trigger indicator, mirroring the existing MM50 implementation. The change touches four files: the `IndicatorType` enum, the workflow class registry, the workflow engine dispatch, and the test suite. No API, frontend, or storage changes are required.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: existing `mobile_average()` in `services/indicator_service.py`; `AbstractWorkflow` in `engines/workflows.py`
**Storage**: N/A — no persistence changes
**Testing**: pytest with `unittest.mock`; mirror existing `test_run_ma_50_workflow` pattern
**Target Platform**: AWS Lambda + local CLI (no change)
**Performance Goals**: N/A — computation is O(n) on 12 candles, negligible
**Constraints**: Must follow existing structural patterns exactly; no new abstractions
**Scale/Scope**: 4 files modified, ~40 lines of new code

## Constitution Check

*GATE: Must pass before implementation.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | ✅ Pass | `MA7Workflow` in engine layer; `IndicatorType.MA7` in model layer; no cross-layer violations |
| I. Client encapsulation | ✅ Pass | No client layer touched |
| II. Clean Code First | ✅ Pass | No inline comments; mirrors existing clean pattern |
| II. Enum-Driven | ✅ Pass | New enum value `IndicatorType.MA7`; no hardcoded strings |
| III. Configuration-Driven | ✅ Pass | Traders configure via `workflows.yml`; no hardcoded workflow data |
| IV. Safe Deployment | ✅ Pass | No infrastructure changes |
| V. Domain Model Integrity | ✅ Pass | Uses `Candle` objects throughout; `mobile_average` returns domain type |

**No violations. Complexity Tracking section not required.**

## Project Structure

### Documentation (this feature)

```text
specs/017-mm7-indicator/
├── plan.md              ← this file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit.tasks
```

### Source Code (repository root)

```text
model/
└── workflow.py          # +1 line: MA7 = "ma7" in IndicatorType

engines/
├── workflows.py         # +MA7Workflow class (~25 lines)
└── workflow_engine.py   # +1 import, +3 case branches (~15 lines)

tests/
└── engines/
    └── test_workflow_engine.py  # +MA7 test cases mirroring MA50
```

**Structure Decision**: Single-project backend only. No frontend or API layer touched.

## Implementation Tasks

### Task 1 — Enum: Add `MA7` to `IndicatorType`

**File**: `model/workflow.py`
**Change**: Add `MA7 = "ma7"` after `MA50 = "ma50"` in `IndicatorType`
**Acceptance**: `IndicatorType.get_value("ma7")` returns `IndicatorType.MA7`

---

### Task 2 — Workflow class: Add `MA7Workflow`

**File**: `engines/workflows.py`
**Change**: Add `MA7Workflow` class after `MA50Workflow`, using `mobile_average(candles, 7)`
**Acceptance**:
- `below_condition` returns `True` when candle close or high is within spread below MM7
- `above_condition` returns `True` when candle close or low is within spread above MM7
- Element-only variant works correctly for both conditions

---

### Task 3 — Engine dispatch: Wire MA7 in `workflow_engine.py`

**File**: `engines/workflow_engine.py`
**Changes** (3 locations):
1. Import `MA7Workflow` alongside `MA50Workflow`
2. Add `case IndicatorType.MA7` in main `run()` dispatch → instantiate `MA7Workflow()`
3. Add `case IndicatorType.MA7: nbr_weeks = 12` in weekly candle-count match
4. Add `case IndicatorType.MA7: nbr_hour = 12 * multiplicator` in hourly candle-count match

**Acceptance**: Engine processes an MA7 workflow end-to-end without hitting the `case _: raise SaxoException()` fallthrough

---

### Task 4 — Tests: Add MA7 workflow test cases

**File**: `tests/engines/test_workflow_engine.py`
**Change**: Add parametrized test cases for `IndicatorType.MA7` mirroring `test_run_ma_50_workflow` — covering BELOW and ABOVE directions with mocked MA7 value

**Acceptance**:
- All new MA7 tests pass
- All existing MA50 tests still pass (no regressions)
- `poetry run mypy` passes on modified files
