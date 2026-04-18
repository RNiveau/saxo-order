# Implementation Plan: Inclined Line Indicator (ROB/SOH)

**Branch**: `512-inclined-line-indicator` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/512-inclined-line-indicator/spec.md`

## Summary

Add an "inclined" indicator type to the workflow engine that projects a linear trend line from two user-defined reference points (date + price), using business days as the X axis. The workflow evaluates whether the current price is above or below the projected line within a spread tolerance, enabling ROB (support bounce) and SOH (resistance breakout) strategies. Significant partial implementation exists on the `inclined-indicator` branch that will be merged and completed.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI (backend API), Click (CLI), React Router DOM v7+, Vite 7+, Axios (frontend)
**Storage**: AWS DynamoDB (workflow persistence via existing `workflow_service.py`)
**Testing**: pytest with unittest.mock for external API calls
**Target Platform**: AWS Lambda (backend), Web browser (frontend)
**Project Type**: web (backend + frontend)
**Performance Goals**: N/A — calculation is O(1) linear equation evaluation per workflow run
**Constraints**: Saxo API required for `is_day_open()` calls; business day calculation adds 1 API call per reference point gap
**Scale/Scope**: Single new indicator type added to existing workflow engine (~6 existing types)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | InclinedWorkflow in engines/, calculation in services/, model in model/, API in api/routers/, frontend in frontend/src/ |
| II. Clean Code First | PASS | Uses existing IndicatorType enum, no hardcoded strings, no unnecessary comments |
| III. Configuration-Driven | PASS | Workflow definition via YAML/DynamoDB, no hardcoded thresholds |
| IV. Safe Deployment | PASS | No infrastructure changes, follows existing workflow deployment pattern |
| V. Domain Model Integrity | PASS | Uses Candle objects, respects candle ordering (index 0 = newest), no country_code inference |

## Project Structure

### Documentation (this feature)

```text
specs/512-inclined-line-indicator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
# Backend
model/
├── workflow.py           # Point, IndicatorInclined, IndicatorType.INCLINED (partially exists)
└── workflow_api.py       # WorkflowIndicatorInput extension for x1/x2 fields

engines/
├── workflows.py          # InclinedWorkflow class (skeleton exists, needs init_workflow logic)
├── workflow_engine.py    # INCLINED case in dispatcher (exists)
└── workflow_loader.py    # YAML parsing for inclined indicator (exists)

services/
├── indicator_service.py  # find_linear_function, apply_linear_function, number_of_day_between_dates (exist)
└── workflow_service.py   # Validation for inclined indicator fields

api/routers/
└── workflow.py           # Add INCLINED to indicator type labels

frontend/src/
├── components/
│   └── WorkflowCreateModal.tsx  # Dynamic fields for x1/x2 reference points
└── services/
    └── api.ts            # No changes expected (uses existing workflow endpoints)

# Tests
tests/
├── engines/
│   └── test_workflows.py        # InclinedWorkflow unit tests (NEW)
└── services/
    └── test_indicator_service.py # find_linear_function, apply_linear_function tests (NEW)
```

**Structure Decision**: Follows existing project layout. No new directories needed. All changes are additions to existing files or new test files mirroring the source structure.

## Complexity Tracking

No constitution violations. No complexity justification needed.
