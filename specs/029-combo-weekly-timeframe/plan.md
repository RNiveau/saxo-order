# Implementation Plan: Weekly-Timeframe Combo Detection

**Branch**: `029-combo-weekly-timeframe` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/029-combo-weekly-timeframe/spec.md`

## Summary

The combo indicator is already timeframe-agnostic — it takes a candle list and never inspects
`candle.ut`. What is daily about today's combo is the candles it is handed, the constants it is
scored against, and the 235-bar floor one of its five criteria imposes. This feature supplies weekly
candles, a second set of constants, and a reduced criteria set, then gives the result its own
identity end to end.

The scan gains one provider request per asset (`horizon=10080`, 70 bars) and builds the forming week
from the daily candles it has already fetched, so nothing is fetched twice. Scoring runs through a
`ComboSettings` object keyed by `UnitTime`, which drops the `macd` criterion on weekly — the single
criterion responsible for the 235-bar requirement — bringing the history needed down to 60 bars and
the eligible universe up with it. The result is stored as `AlertType.COMBO_WEEKLY`, whose repeat
suppression keys on the weekly bar and direction rather than the scan date, so a setup holding all
week is recorded once while a mid-week direction flip is recorded as a new signal. Suppression
touches only what is written: detection re-runs every scan, so the digest keeps reflecting the
forming bar as it stands that day.

The triage brief learns the new pattern's rank and its long-only consequence — a Buy weekly combo is
the strongest reason to surface an asset, a Sell weekly combo disqualifies it as a long. The
frontend and the API separate it from the daily combo by its type, as they already do for every
other detector.

Two things gate release rather than follow it: the weekly thresholds must be calibrated against
historical weekly bars, and the labelled sample SC-001 verifies against must exist.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: existing only — `services/indicator_service.py` (`combo`,
`mobile_average`, `bollinger_bands`, `average_true_range`), `utils/helper.py`
(`build_current_weekly_candle_from_daily`), `client/saxo_client.py` (`get_historical_data`,
already caching `horizon=10080`), `aioboto3` (DynamoDB), `anthropic` SDK, `slack_sdk`; Axios +
React Router DOM v7+ on the frontend. **No new dependency.**
**Storage**: existing `alerts` table, unchanged schema — `data` is already a free-form map and gains
two keys. Calibration reads the existing `backtest_candle_cache` table. **No new table, no
migration, no Pulumi change.**
**Testing**: pytest with `unittest.mock`; tests mirror source structure under `tests/`
**Target Platform**: AWS Lambda (`alerting` command, weekday end-of-day) + FastAPI API + Vite SPA
**Project Type**: Web (backend + frontend) with a Lambda entry point
**Performance Goals**: +1 provider request per asset per scan and one extra indicator pass; the
weekly pass is cheaper than the daily one because `macd0lag` — roughly 80% of a combo call — is not
computed (SC-003)
**Constraints**: must not delay the end-of-day scan past its window; must reproduce today's alert
set exactly when the toggle is off (SC-007); the de-dup change must be inert for every other alert
type (FR-007, FR-013)
**Scale/Scope**: a few hundred French stocks plus followups, scanned sequentially, once per weekday

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| **I. Layered Architecture** | PASS. Indicator logic stays in the Service layer; the de-dup signature is domain logic and lands in the Model layer, called by the client rather than computed inside it. The CLI command orchestrates and holds no scoring logic. No service reaches into client internals — the weekly fetch goes through the existing `get_historical_data` method. Frontend changes stay in `utils/alertLabels.ts` (label) and a component (render). |
| **II. Clean Code First** | PASS. One parameterised `combo()` rather than a weekly copy (R2). `ComboSettings` exists because two timeframes need it now, not speculatively. No new metric store for a one-off measurement (R12). No `assert` — the settings invariants are asserted in tests, and malformed stored alert rows degrade to the default signature rather than raising. |
| **III. Configuration-Driven** | PARTIAL — the off switch is configuration; the calibrated thresholds stay in code. Justified in Complexity Tracking. |
| **IV. Safe Deployment** | PASS. No infrastructure change; existing tables and IAM grants suffice. Conventional commits throughout. |
| **V. Domain Model Integrity** | PASS. Weekly candles are `Candle` objects with `ut=UnitTime.W`, newest at index 0. The provider's missing current week is rebuilt from a smaller horizon, which is exactly the documented Saxo constraint. `AlertType` and `UnitTime` are used as enums, never as strings. The alert carries its explicit `exchange`; nothing infers an exchange from `country_code`. |
| **Planning Requirement** | PASS. Spec and this plan precede implementation; `/speckit.implement` awaits human validation. |
| **Testing Standards** | PASS. Tests assert behaviour — a combo found on weekly bars, a second scan recording nothing, a flip recording a second row, an untouched daily de-dup — not that mocks were called. |

**Post-Phase-1 re-check**: no new violations. The design added no client-internals access, no new
table, and no cross-layer call. The single deviation is unchanged and recorded below.

## Project Structure

### Documentation (this feature)

```text
specs/029-combo-weekly-timeframe/
├── plan.md              # This file
├── research.md          # Phase 0 output — R1..R12
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── alerts.openapi.yaml
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
model/
├── enum.py                          # + AlertType.COMBO_WEEKLY
└── __init__.py                      # + alert de-dup signature (domain logic)

services/
├── indicator_service.py             # + ComboSettings, COMBO_SETTINGS; combo() parameterised
└── alert_triage_service.py          # + COMBO_WEEKLY in _DIRECTIONAL_PATTERNS; prompt semantics

client/
└── aws_client.py                    # store_alerts calls the model-layer signature

saxo_order/commands/
└── alerting.py                      # + _build_weekly_candles, weekly detection behind the toggle

utils/
└── configuration.py                 # + weekly_combo_enabled property

scripts/
└── calibrate_weekly_combo.py        # one-off threshold calibration (release prerequisite)

config.yml                           # + weekly_combo_enabled

frontend/src/
├── utils/alertLabels.ts             # + combo_weekly label
└── components/AlertCard.tsx         # + combo_weekly in the directional list

tests/
├── services/test_indicator_service.py
├── services/test_alert_triage_service.py
├── saxo_order/commands/test_alerting.py
├── client/test_aws_client.py
└── utils/test_helper.py
```

**Structure Decision**: existing web layout (backend packages at the repository root, `frontend/`
for the SPA, `saxo_order/commands/` for the Lambda-invoked CLI). No new top-level directory. The
only new file in the shipped tree is the calibration script, which is a development tool rather
than part of the scan.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Constitution III — the calibrated weekly thresholds live in `services/indicator_service.py` as module constants rather than in `config.yml` | These values define what the weekly indicator *is*. They are derived by the calibration pass (R8), reviewed as code alongside the criteria they gate, and identical in every environment — unlike `triage_slope_threshold`, which a user may reasonably want to tune per deployment. FR-011's requirement is that weekly be tunable *independently of daily*, which the `COMBO_SETTINGS` map satisfies. | Moving only the weekly set to `config.yml` would split a matched pair of constants across two homes and make the timeframes harder to compare than either home alone. Moving both sets would change the daily combo's configuration surface — out of scope, and a behaviour-change risk on a detector this feature is not meant to touch. The genuinely environment-dependent knob, the off switch, *is* in `config.yml` (R10). |
