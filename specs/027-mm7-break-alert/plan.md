# Implementation Plan: MM7 Break Alert

**Branch**: `027-mm7-break-alert` (developed on `claude/triage-agent-ma7-alerting-mypata`) | **Date**: 2026-08-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/027-mm7-break-alert/spec.md`

## Summary

Add a new `AlertType` (`MM7_BREAK`) emitted during the existing daily alerting pipeline when the latest daily close crosses decisively through the 7-period moving average — more than 0.5% clear of it — after at least 3 prior candles closed on the other side. The detector is a pure function in `services/indicator_service.py`, wired into `run_detection_for_asset` the same way `mm50_touch` is, and carries its direction (`Direction.BUY` reclaim / `Direction.SELL` breakdown) inside the alert `data` rather than splitting into two alert types.

The load-bearing part is not the detector — it is the qualifier and the prompt. A raw MA7 cross fires on a large share of the universe every day; unqualified, it would arrive in the triage payload as background rather than evidence and make the digest worse, not better. So the detector gates on distance **and** streak, and `TRIAGE_SYSTEM_PROMPT` gains a pattern-semantics entry (like `mm50_touch` and `double_top` already have) that fixes MM7 as a short-term timing trigger read against the *sign* of `ma50_slope`, never sufficient alone for "high" conviction.

DynamoDB persistence, the alerts API, and the deterministic triage fallback are already generic over `AlertType` and need no changes. The frontend needs one entry in its label map, which is a hand-maintained dictionary rather than a derived helper.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend — one label map entry)
**Primary Dependencies**: existing — `services/indicator_service.py` (`mobile_average`), `saxo_order/commands/alerting.py` (`run_detection_for_asset`, `_safe_detect`), `services/alert_triage_service.py` (`TRIAGE_SYSTEM_PROMPT`), `model.Alert`, `model.AlertType`, `model.Direction`, `client/aws_client.py` (`DynamoDBClient.store_alerts`). **No new dependency.**
**Storage**: AWS DynamoDB `alerts` table (existing, schema unchanged — `data` is a free-form `Dict[str, Any]`, same-type-same-date dedup)
**Testing**: pytest with `unittest.mock` (`tests/services/test_indicator_service.py`, `tests/saxo_order/commands/test_alerting.py`)
**Target Platform**: AWS Lambda (scheduled EventBridge, daily) + on-demand FastAPI endpoint (`POST /api/alerts/run`)
**Project Type**: web (backend + frontend) — this feature is backend plus one frontend constant
**Performance Goals**: No measurable regression. The detector is O(period × streak) on candles already in memory — bounded by 10 × 7 close reads per asset, effectively free next to the Saxo fetch.
**Constraints**: Must reuse the candle series already loaded for each asset (no extra Saxo API calls). Must skip silently below 10 candles. Must not fire often enough to dilute the digest — the binding constraint, and the one that cannot be verified before a live run (spec SC-003).
**Scale/Scope**: ~700 instruments scanned per daily run (French stocks via Saxo `/ref/v1/instruments` + `followup-stocks.json`). Target match rate: a handful per day, same order as the other detectors.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture Discipline | ✅ Pass | Detection is a pure function on `List[Candle]` in `services/`; orchestration stays in `saxo_order/commands/alerting.py`; the enum stays in `model/enum.py`. No client internals touched. The frontend change is a constant in the page that already owns the label map. |
| II. Clean Code First | ✅ Pass | Direction reuses the existing `Direction` enum rather than a `"up"`/`"down"` string (CLAUDE.md rule). Thresholds are named constants next to the `MM50_TOUCH_*` ones, not magic numbers. No `assert` in production code. Comments explain *why* the qualifier exists, not what the code does. |
| III. Configuration-Driven Design | ✅ Pass | `MM7_BREAK_MIN_DISTANCE` / `MM7_BREAK_MIN_STREAK` are module constants, not config: they define the alert's identity, and changing them means a different alert. Consistent with `MM50_TOUCH_PROXIMITY`. No new credentials or environment variables. |
| IV. Safe Deployment Practices | ✅ Pass | Ships via the existing `./deploy.sh` flow; Lambda and EventBridge schedule unchanged. Conventional commits (`feat:`, `docs:`). Additive — no existing alert type changes behavior. |
| V. Domain Model Integrity | ✅ Pass | Uses `Candle` objects with newest at index 0 throughout; the MM7 at offset *i* is `mobile_average(candles[i:], 7)`, which respects that ordering. `Alert` already carries `exchange`; no country-code-based exchange inference (CLAUDE.md rule) — a Saxo asset without a country code stays a Saxo asset. |

**Result**: All gates pass. Complexity Tracking intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/027-mm7-break-alert/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Task breakdown
```

`research.md`, `data-model.md`, and `contracts/` are omitted deliberately: no new data model (the alert `data` payload is a free-form dict on an unchanged table), no new API contract (the alerts endpoints are generic over `AlertType`), and no open research question — the one real unknown, the live hit rate, is answerable only by running the job, and is tracked as spec SC-003 rather than as desk research.

### Source Code (repository root)

Existing Python backend + React frontend. No new directories.

```text
model/
└── enum.py                   # +1 member: AlertType.MM7_BREAK

services/
├── indicator_service.py      # +constants MM7_PERIOD, MM7_BREAK_MIN_DISTANCE,
│                             #  MM7_BREAK_MIN_STREAK, MM7_BREAK_MIN_CANDLES
│                             # +_mm7_at, _mm7_streak, mm7_break
└── alert_triage_service.py   # +pattern-semantics entry in TRIAGE_SYSTEM_PROMPT

saxo_order/commands/
└── alerting.py               # +1 detection block in run_detection_for_asset

frontend/src/pages/
└── Alerts.tsx                # +ALERT_TYPE_LABELS entries (mm7_break, mm50_touch)

api/                          # (no change — generic over AlertType.value)
client/aws_client.py          # (no change — data is Dict[str, Any])

tests/
├── services/test_indicator_service.py    # +detector tests
└── saxo_order/commands/test_alerting.py  # +pipeline emission tests
```

**Structure Decision**: Backend-only change plus one frontend constant. Layering is preserved: pure detection in `services/indicator_service.py`, orchestration in `saxo_order/commands/alerting.py`, vocabulary in `model/enum.py`. The alerts API and DynamoDB schema are untouched because they are already generic over `AlertType`.

## Key Design Decisions

1. **One alert type, direction in `data`** — rather than `MM7_BREAK_UP` / `MM7_BREAK_DOWN`. Follows `COMBO`, which stores `direction` in its payload. Keeps the UI filter list and the triage pattern vocabulary from doubling, and lets the triage prompt state the semantics once.

2. **The MM7 is evaluated at each candle's own offset**, not held fixed at today's value. `_mm7_streak` compares `candles[i].close` against `mobile_average(candles[i:], 7)`, so "the prior candles closed on the other side" means what it says on each of those days, rather than measuring the past against an average it could not have known.

3. **Distance is exclusive, the streak inclusive.** A break must *clear* 0.5%; exactly 3 qualifying prior candles is enough. A prior close exactly equal to its MM7 counts as still on that side — a candle sitting on the average has not left it.

4. **The streak counter stops when history runs out** rather than raising. With the 10-candle minimum an asset can reach but not exceed the required streak, which is why `MM7_BREAK_MIN_CANDLES` is derived (`MM7_PERIOD + MM7_BREAK_MIN_STREAK`) rather than written as a literal.

5. **No change to the deterministic triage fallback.** MM7 forms its own pattern family in `_PATTERN_FAMILY`, and one family alone already caps at `watch` — so FR-010 (never "high" on an MM7 break alone) holds on the fallback path without new code. This was verified against `_fallback_conviction`, not assumed.

## Risks

| Risk | Mitigation |
|------|------------|
| The 0.5% / 3-candle thresholds are calibrated from the shape of neighbouring detectors, not from measured hit rates. Too loose and MM7 dominates every digest. | Both are named constants in one file, so re-tuning is a one-line change. Spec SC-003 makes the live hit rate an explicit acceptance check on the first runs rather than an assumption. |
| An LLM prompt change is not covered by a deterministic test — FR-009/FR-010 are verified by reading the digest, not by CI. | The fallback path is deterministic and *is* covered. The prompt states the constraint explicitly ("never enough for high") rather than relying on the model's judgment of an undescribed pattern. |
| A short-term signal added to a payload previously dominated by structural patterns could shift the agent's overall ranking behavior. | The prompt entry frames MM7 as a timing trigger subordinate to trend context, so it can strengthen or weaken an existing thesis but not create one. |

## Complexity Tracking

> No constitution violations. Section intentionally empty.
