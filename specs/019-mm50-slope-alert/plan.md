# Implementation Plan: MM50 Proximity Alert with Slope Filter

**Branch**: `019-mm50-slope-alert` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-mm50-slope-alert/spec.md`

## Summary

Add a new `AlertType` (`MM50_TOUCH`) emitted during the existing daily alerting pipeline when an asset's latest close is within 1% of its 50-period moving average AND the MM50 slope (base-100, 10-candle window) is ≥ 3. The detector is a small pure function added to `services/indicator_service.py`, wired into `run_detection_for_asset` in `saxo_order/commands/alerting.py` alongside the existing detectors, and surfaced through the existing Slack `#stock` grouped message. The alerts API, DynamoDB persistence, and frontend `AlertCard` already handle arbitrary alert types generically and need no schema changes; the frontend label updates automatically via the existing `formatAlertType` snake_case→TitleCase helper.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend — no changes required)
**Primary Dependencies**: existing — `services/indicator_service.py` (`mobile_average`, `slope_percentage`), `saxo_order/commands/alerting.py` (`run_detection_for_asset`, `_build_candles`), `model.Alert`, `model.AlertType`, `client/aws_client.py` (`DynamoDBClient.store_alerts`), `slack_sdk.WebClient`
**Storage**: AWS DynamoDB `alerts` table (existing, schema unchanged — `data` is a free-form `Dict[str, Any]`, alert_type is appended to the existing alerts list with same-type-same-date dedup)
**Testing**: pytest with `unittest.mock` (existing `tests/saxo_order/commands/test_alerting.py`, `tests/services/test_indicator_service.py`)
**Target Platform**: AWS Lambda (scheduled EventBridge 6:15 PM Paris) + on-demand FastAPI endpoint (`POST /api/alerts/run`)
**Project Type**: web (backend + frontend) — but this feature only touches backend
**Performance Goals**: No measurable regression vs. current job duration. The new check is O(period) on top of an MM50 computation that is already performed for `ma50_slope` — effectively free.
**Constraints**: Must reuse the candle series already loaded for each asset (no extra Saxo API calls). Must follow same-alert-type-same-date dedup. Must skip silently when fewer than 60 candles are available.
**Scale/Scope**: ~330 stocks scanned per daily run (French stocks via Saxo `/ref/v1/instruments` + `followup-stocks.json`). Expected match rate: a handful per day, varies with market conditions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture Discipline | ✅ Pass | Indicator detection lives in `services/`, orchestration in `saxo_order/commands/`. No client internals accessed. Detector is a pure function on `List[Candle]`. |
| II. Clean Code First | ✅ Pass | New enum member reuses `EnumWithGetValue`. No hardcoded strings (alert type referenced as `AlertType.MM50_TOUCH`). No new abstractions — just one new pure function and one new branch in the existing detection pipeline. |
| III. Configuration-Driven Design | ✅ Pass | Thresholds (1% proximity, slope ≥ 3) are baked into the detector since they define the alert's identity (changing them would mean a different alert). No new credentials or environment variables. |
| IV. Safe Deployment Practices | ✅ Pass | Deployed via existing `./deploy.sh` flow; Lambda function and EventBridge schedule unchanged. Conventional commit `feat:` will be used. |
| V. Domain Model Integrity | ✅ Pass | Uses `Candle` objects (newest at index 0). `Alert` already includes `exchange` field. No `country_code`-based exchange inference. The 60-candle minimum is documented and enforced. |

**Result**: All gates pass. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/019-mm50-slope-alert/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── mm50-touch-alert.md
├── checklists/
│   └── requirements.md  # Already created by /speckit.specify
└── spec.md
```

### Source Code (repository root)

The project is an existing Python backend + React frontend. This feature only modifies the backend; no new directories are created.

```text
model/
├── enum.py              # +1 enum member: AlertType.MM50_TOUCH
└── __init__.py          # (no change)

services/
└── indicator_service.py # +1 function: mm50_touch(candles) -> Optional[dict]

saxo_order/commands/
└── alerting.py          # +1 detection block in run_detection_for_asset
                         # +1 Slack message group ("mm50_touch") in run_alerting

api/
├── routers/alerting.py  # (no change — alert_type is passed through as string)
├── services/alerting_service.py  # (no change — generic over AlertType.value)
└── models/alerting.py   # (no change — AlertItemResponse.alert_type is str)

frontend/src/
├── components/AlertCard.tsx  # (no change — formatAlertType handles new value)
├── utils/alertFilters.ts     # (no change — dedup keyed by alert_type string)
└── pages/Alerts.tsx          # (no change — available_filters is server-computed)

tests/
├── services/test_indicator_service.py    # +tests for mm50_touch detector
└── saxo_order/commands/test_alerting.py  # +tests for alert emission in pipeline
```

**Structure Decision**: Single-codebase change confined to backend. The Service / Command / Model layering is preserved: pure detection logic stays in `services/indicator_service.py`, orchestration and Slack delivery stay in `saxo_order/commands/alerting.py`, and the enum stays in `model/enum.py`. The frontend, alerts API, and DynamoDB schema are intentionally untouched because they are already generic over `AlertType`.

## Complexity Tracking

> No constitution violations. Section intentionally empty.
