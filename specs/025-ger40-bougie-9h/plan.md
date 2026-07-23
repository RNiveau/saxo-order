# Implementation Plan: Hardcoded "GER40 Bougie de 9h" Backtest (double take-profit)

**Branch**: `claude/ger40-backtest-spec-025-k9togf` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/025-ger40-bougie-9h/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a third hardcoded backtest — **"GER40 Bougie de 9h"** — to the existing Backtest menu. It reuses the entire "CAC40 Bougie de 9h" engine (spec 021): the 9:00–10:00 Paris-local H1 reference range, both-direction 5-minute breakout/reversal detection, entry-validity, exit ordering, gap-fill, one-position-at-a-time, and the range/day/CSV outputs. It differs only by: (1) instrument `GER40.I`; (2) GER40 default thresholds (stop **150**, take-profit offset **10**, break-even trigger **50**, max entry distance **40**); (3) a **two-lot / double take-profit** overlay — every entry opens two lots, the first exits at the H1 midpoint (TP1 = `(h1_high+h1_low)/2`), the runner at the full target (TP2 = H1 high − 10 / H1 low + 10), and once TP1 fills the runner's stop moves to break-even; (4) the stop-loss is measured **from the H1 reference level** (150 pts below the H1 low / above the H1 high), not from entry as CAC40 does.

The implementation stays inside the existing layered architecture: a new `Strategy.G9H` enum value, per-definition **default parameters** and **double-TP properties** on `BacktestDefinition`, a double-TP branch in the existing `api/services/backtest_service.py` trade engine, no new response shape (a two-lot position is surfaced as **one aggregated `Trade`**, FR-G07/FR-G10), and the definition auto-appears in the frontend menu. The `/definitions` response is extended to carry each definition's default thresholds so the frontend pre-fills the correct GER40 defaults. No new external dependency, no persistence, no infrastructure change.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) — no change from existing stack.
**Primary Dependencies**: FastAPI + Pydantic v2 (existing), `zoneinfo` (already used by the backtest service for Paris-local math), Python stdlib `csv` (existing exports), existing `SaxoClient`/`CandlesService`; React Router DOM v7+, Axios, Vite (frontend, existing). **No new dependency.**
**Storage**: N/A — ephemeral, computed on demand per request, nothing persisted (inherits spec 021's decision).
**Testing**: pytest with the existing mocked-`CandlesService` convention used by `tests/api/services/test_backtest_service.py`; no frontend test framework (existing gap, unchanged).
**Target Platform**: Existing FastAPI backend (Lambda-deployable) + React SPA (Vite).
**Project Type**: Web application (backend packages at repo root + `frontend/`) — the codebase's established flat layout.
**Performance Goals**: Single-day run within a few seconds (SC-G01); range runs synchronous, scaling with the number of trading days (one H1 + one 5-minute Saxo call per day) — identical cost profile to CAC40; the double-TP overlay is pure in-memory arithmetic per candle.
**Constraints**: Constitution I (Layered Architecture) — engine logic stays in `api/services/backtest_service.py`, candle fetches in `services/candles_service.py`; Constitution II — reuse `Strategy` enum (new `G9H` member), no hardcoded strings, no speculative generic engine; the 50% first-target fraction and two-lot count are **fixed** strategy properties (not tunable), the four numeric thresholds stay tunable per run with **GER40 defaults** (FR-G09). GER40.I uses the same `EUMarket`/Europe/Paris session logic as FRA40.I (Xetra ≈ Euronext hours), so no new market/timezone code is needed.
**Scale/Scope**: One new `BacktestDefinition` (`G9H`); no new endpoints (the existing `/definitions`, `/run`, `/day`, `/run/csv`, `/day/csv` all take the definition code); `/definitions` response gains per-definition default-threshold + double-TP fields; one new `Strategy` enum value; a double-TP branch in the trade engine; frontend pre-fills per-definition defaults. Single-user tool, no concurrency concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | No new router; the existing thin `api/routers/backtest.py` gains only per-definition default resolution. Double-TP rule logic lives in the Service layer (`api/services/backtest_service.py`); candle fetches stay in `services/candles_service.py`. New domain fields live in `model/backtest.py` (dataclasses, no external deps). Frontend keeps all API calls in `frontend/src/services/api.ts`; the page reads per-definition defaults from the definitions response (props in). | PASS |
| II. Clean Code First | Reuses the `Strategy` enum via a new `G9H` member instead of a hardcoded name; reuses `Direction`/`ExitReason`/`DayStatus`; the two-lot mechanic is expressed as fields on the existing `_OpenPosition`/`BacktestDefinition`, not a parallel engine; no generic backtest-authoring capability is built (FR-G01). No `assert` in production code (Constitution II.5 / 1.3.0) — invariant violations raise explicit exceptions, matching `_candle_date`. | PASS |
| III. Configuration-Driven Design | Thresholds remain per-run analysis inputs (defaults now attached per `BacktestDefinition` rather than a single global default), not deployment config — appropriate, same rationale as spec 021's resolved exception. No new external integration or credential. | PASS |
| IV. Safe Deployment Practices | Additive within the existing API/frontend deployment; no new Lambda, ECR, or Pulumi change. Conventional commits (`feat:`). | PASS |
| V. Domain Model Integrity | Reuses `model.workflow.Candle` everywhere outside the client; GER40.I is a single hardcoded Saxo instrument (index), so the `exchange`/`country_code` inference rule does not apply; the H1/5-minute historical fetches for closed past days respect the "current period not returned" Saxo limitation the same way CAC40 does. | PASS |

No violations requiring justification — see Complexity Tracking for the one design point (stop measured from the H1 level) that is a spec-mandated per-definition difference, not a constitutional exception.

## Project Structure

### Documentation (this feature)

```text
specs/025-ger40-bougie-9h/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── backtest-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
model/
├── enum.py                        # + Strategy.G9H = "Bougie de 9h GER40"
└── backtest.py                    # BacktestDefinition: + default_parameters,
                                    #   double_take_profit, first_target_fraction,
                                    #   stop_from_reference_level fields.
                                    #   BacktestParameters unchanged (shape); its
                                    #   defaults stay the CAC40 values, GER40 supplies
                                    #   its own via default_parameters.

api/
├── models/
│   └── backtest.py                # BacktestDefinitionResponse: + default_parameters
                                    #   (+ double_take_profit flag) so the frontend
                                    #   pre-fills GER40 defaults. Trade/Day/Run
                                    #   response shapes UNCHANGED (FR-G10).
├── routers/
│   └── backtest.py                # _params -> optional overrides; resolve against
                                    #   the definition's default_parameters after the
                                    #   definition is looked up (per-definition
                                    #   defaults, not a single global default).
└── services/
    └── backtest_service.py        # BACKTEST_DEFINITIONS: + G9H entry (GER40.I,
                                    #   GER40 defaults, double-TP props). _OpenPosition:
                                    #   + first_target_level/first_target_taken/
                                    #   banked_points + reference-based stop. New
                                    #   double-TP exit path in _resolve_exit +
                                    #   aggregated-trade close helper. _build_summary:
                                    #   points-sign classification for double-TP defs
                                    #   (FR-G08). resolve_parameters helper.

frontend/src/
├── pages/
│   └── Backtest.tsx               # Pre-fill threshold inputs from the selected
                                    #   definition's default_parameters (falls back
                                    #   to the current constants for CAC40).
└── services/
    └── api.ts                     # BacktestDefinition interface + default_parameters
                                    #   (+ double_take_profit) fields.

tests/
└── api/
    ├── services/
    │   └── test_backtest_service.py  # + GER40 double-TP engine tests (all SC-G02
                                    #   outcome types) mirroring the acceptance scenarios
    └── routers/
        └── test_backtest.py          # + G9H definition listed w/ GER40 defaults;
                                    #   run/day/csv against G9H; per-definition default
                                    #   resolution; positivity validation still 422
```

**Structure Decision**: Follows the codebase's existing flat layout (backend packages `api/`, `services/`, `model/` at repo root, `frontend/` alongside), matching spec 021 and every prior feature. The feature extends the existing backtest modules rather than adding new ones, and introduces no new top-level directory.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations. Two design points are recorded here because they are deliberate deviations from "CAC40 Bougie de 9h" mandated by the spec, not because they need justification against a principle:

| Design point | Why | Note |
|---|---|---|
| Stop-loss measured from the **H1 reference level** (150 pts beyond it) for `G9H`, while `B9H` measures its stop from **entry**. | Spec FR-G05 / user rule "SL 150 points below the lower". | Implemented as a `stop_from_reference_level` flag on `BacktestDefinition` so `B9H`/`B9HTC` behavior is byte-for-byte unchanged; only `G9H` takes the reference-based branch. Surfaced in the spec Clarifications for the owner to confirm during validation. |
| A two-lot position is surfaced as **one aggregated `Trade`** whose `points` ≠ `exit_price − entry_price`. | Spec FR-G07 (owner chose one aggregated trade over two rows). | Kept within the existing `Trade` shape (no response change, FR-G10); the engine computes the summed points explicitly via a dedicated close helper. The aggregated `exit_price`/`exit_reason` reflect the runner's final exit. |
