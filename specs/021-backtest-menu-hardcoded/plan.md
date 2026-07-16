# Implementation Plan: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

**Branch**: `021-backtest-menu-hardcoded` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-backtest-menu-hardcoded/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a "Backtest" menu that runs one hardcoded strategy — "CAC40 Bougie de 9h" (reusing the existing `Strategy.B9H` enum) — against historical FRA40.I candles. For a given past day, the strategy takes the 9:00–10:00 Paris-local H1 candle as a reference range, then evaluates 5-minute candles from 10:00 onward for a breakout-reversal long entry, with a stop-loss, a break-even-armed stop (once +20pts in profit), a take-profit, and an end-of-day exit — allowing multiple sequential (non-overlapping) trades per day. The UI lets a trader run a single day (full trade detail) or a date range (an 8-figure aggregate summary: days, trades, wins, losses, BE, avg win, avg loss, final result), with results computed on demand and not persisted. Implementation reuses the existing Saxo historical-candle client through a new `CandlesService` method (5-minute granularity is new; H1 already exists), adds a small set of new enums/dataclasses under the existing layered architecture, and follows the established FastAPI + React page/service/component conventions used by the Report feature.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) — no change from existing stack.
**Primary Dependencies**: FastAPI (backend, existing), Pydantic v2 (existing), `zoneinfo` (Python stdlib — new usage in this codebase for DST-aware Paris-local time math, see research.md §1), existing `SaxoClient`/`CandlesService`; React Router DOM v7+, Axios, Vite (frontend, existing).
**Storage**: N/A — ephemeral, computed on demand per request, nothing persisted (Clarifications, Session 2026-07-14).
**Testing**: pytest with mocked `SaxoClient`/`MockSaxoClient` (backend, existing convention); no frontend test framework configured (existing gap, unchanged by this feature).
**Target Platform**: Existing FastAPI backend (Lambda-deployable) + React SPA (Vite), served locally via `run_api.py` / `npm run dev` in development.
**Project Type**: Web application (existing backend at repo root + `frontend/`) — matches the codebase's established layout, not the generic `backend/`+`frontend/` template split.
**Performance Goals**: Single-day run and its underlying Saxo calls complete within a few seconds (SC-001); range runs are synchronous and scale with the number of trading days requested (each day needs one H1 + one 5-minute Saxo history call) — no explicit SLA beyond "completes without a dedicated job queue," consistent with this being a single-user, on-demand analysis tool and with the "no application-level range cap" clarification.
**Constraints**: Must respect Constitution I (Layered Architecture) — new candle-fetch logic lives in `services/candles_service.py`, not called directly from the API service; must use existing enums (`Strategy.B9H`) instead of new hardcoded strings; must follow Candle conventions (index 0 = newest list ordering where lists are produced that way, `model.workflow.Candle` everywhere outside `SaxoClient`); strategy thresholds (50/10/20 points, 9–10 window) are intentionally hardcoded in code per FR-002 ("no generic engine"), not exposed via `config.yml` — see Complexity Tracking.
**Scale/Scope**: One hardcoded `BacktestDefinition` (`B9H`); 3 new/changed backend endpoints' worth of surface (`/definitions`, `/run`, `/day`); one new frontend page + sidebar entry; single-user tool, no concurrency/multi-tenant concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | New router (`api/routers/backtest.py`) stays thin; business logic (breakout/exit rules, aggregation) lives in a new `api/services/backtest_service.py`; new historical-candle fetch logic lives in `services/candles_service.py` (Service layer), which alone talks to `client/saxo_client.py`; new domain types live in `model/` with no external deps; frontend keeps API calls in `frontend/src/services/api.ts` only. | PASS |
| II. Clean Code First | Reuses `Strategy.B9H` instead of a new hardcoded name; new `ExitReason`/`DayStatus` enums instead of string literals; no speculative generic "backtest engine" is built (FR-002 explicitly forbids it). | PASS |
| III. Configuration-Driven Design | Strategy thresholds are deliberately hardcoded in code, not `config.yml` — this is a scoped, justified exception (see Complexity Tracking), not a violation of "no hardcoded API endpoints/timeouts/retry logic." No new external integration or credential is introduced, so no new config surface is needed. | PASS (justified exception documented) |
| IV. Safe Deployment Practices | No new infrastructure, no new Lambda, no Pulumi changes required — feature is additive within the existing API/frontend deployment. | PASS |
| V. Domain Model Integrity | New `UnitTime.M5` follows the existing enum pattern; 5-minute/H1 historical fetches for closed past days sidestep the "current day/hour not returned" Saxo limitation correctly (research.md §2) rather than ignoring it; `Candle` objects are used for all candle data outside the client layer; `exchange`/`country_code` concerns don't apply (FRA40.I is a single hardcoded Saxo instrument, not a general asset lookup). | PASS |

No violations requiring justification beyond the one documented exception above (Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/021-backtest-menu-hardcoded/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   └── backtest-api.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
model/
├── enum.py                        # + ExitReason, DayStatus (new enums)
├── workflow.py                    # + UnitTime.M5
└── backtest.py                    # NEW: BacktestDefinition, Trade, DayResult,
                                    #      DayResultSummary, BacktestSummary,
                                    #      BacktestRunResult dataclasses

services/
└── candles_service.py             # + get_candles_in_window(...) — fetch candles
                                    #   for an explicit historical [start, end) UTC
                                    #   window at a given horizon (60 or 5 minutes)

api/
├── models/
│   └── backtest.py                # NEW: Pydantic request/response models
├── routers/
│   └── backtest.py                # NEW: GET /definitions, /run, /day
├── services/
│   └── backtest_service.py        # NEW: breakout/exit rule engine + aggregation
├── dependencies.py                # + get_backtest_service()
└── main.py                        # + app.include_router(backtest.router)

frontend/src/
├── pages/
│   ├── Backtest.tsx                # NEW: page (single-day + range modes)
│   └── Backtest.css                # NEW
├── components/
│   └── Sidebar.tsx                 # + "Backtest" NavLink entry
├── App.tsx                         # + <Route path="/backtest" .../>
└── services/
    └── api.ts                      # + backtestService + TS interfaces

tests/
├── services/
│   └── test_candles_service.py     # + tests for get_candles_in_window
└── api/
    ├── services/
    │   └── test_backtest_service.py  # NEW: strategy rule-engine tests
    └── routers/
        └── test_backtest.py          # NEW: endpoint tests
```

**Structure Decision**: Follows the codebase's existing flat layout (backend packages `api/`, `services/`, `client/`, `model/` at repo root, `frontend/` alongside them) rather than the generic `backend/`+`frontend/` template split — this matches every prior feature in `specs/` (e.g. 020-saxo-reporting) and Constitution's explicit File Organization guidance. No new top-level directories are introduced; the feature only adds files inside the existing `api/`, `services/`, `model/`, `frontend/src/`, and `tests/` trees.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Strategy thresholds (50pt stop, 10pt take-profit offset, 20pt break-even trigger, 9:00–10:00 window) hardcoded in `api/services/backtest_service.py` rather than `config.yml` | FR-002 explicitly requires each backtest to be a fixed, hardcoded implementation — "I don't want to create a back test engine" | Moving thresholds to configuration would be the first step toward the generic, configurable backtest engine the user explicitly rejected; for a single fixed strategy, code constants are simpler and match the spec's stated scope |
