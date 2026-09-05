# Implementation Plan: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

**Branch**: `021-backtest-menu-hardcoded` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-backtest-menu-hardcoded/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a "Backtest" menu that runs one hardcoded strategy — "CAC40 Bougie de 9h" (reusing the existing `Strategy.B9H` enum) — against historical FRA40.I candles. For a given past day, the strategy takes the 9:00–10:00 Paris-local H1 candle as a reference range, then evaluates 5-minute candles from 10:00 onward for **both** a breakout-reversal long entry off the H1 low **and** the mirror-image short entry off the H1 high (added 2026-07-21, FR-019–FR-024), each with a stop-loss, a break-even-armed stop (once +20pts in profit), a take-profit, and an end-of-day exit — allowing multiple sequential (non-overlapping) trades per day, with at most one position (long or short) open at a time. Each `Trade` records its `direction` (reusing the existing `model.enum.Direction`). The UI lets a trader run a single day (full trade detail) or a date range (an 8-figure aggregate summary: days, trades, wins, losses, BE, avg win, avg loss, final result), with results computed on demand and not persisted. Implementation reuses the existing Saxo historical-candle client through a new `CandlesService` method (5-minute granularity is new; H1 already exists), adds a small set of new enums/dataclasses under the existing layered architecture, and follows the established FastAPI + React page/service/component conventions used by the Report feature. To cut repeated Saxo calls across runs (added 2026-07-24), a new DynamoDB-backed cache — keyed by (backtest definition code, trading date) — stores the raw H1/5-minute candles for each evaluated day; the strategy computation still runs fresh on every request against those (cached or freshly fetched) candles, so the cache never holds a computed trade or summary result and needs no invalidation scheme (research.md §8).

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) — no change from existing stack.
**Primary Dependencies**: FastAPI (backend, existing), Pydantic v2 (existing), `zoneinfo` (Python stdlib — new usage in this codebase for DST-aware Paris-local time math, see research.md §1), Python stdlib `csv` module (CSV export, FR-017/FR-018 — same stdlib usage as 022-trade-republic-report), existing `SaxoClient`/`CandlesService`; React Router DOM v7+, Axios, Vite (frontend, existing).
**Storage**: Computed Backtest Run/Day Result output remains ephemeral, computed on demand per request (Clarifications, Session 2026-07-14). Added 2026-07-24: a new DynamoDB table caches raw Saxo candle data (H1 reference candle + 5-minute session candles, or an explicit "no data" marker) with no TTL — see research.md §8 and data-model.md. Re-keyed 2026-07-28 from (backtest definition code, trading date) to (instrument, session window, trading date), so the definitions on an instrument share one entry instead of each storing its own copy of identical candles.
**Testing**: pytest with mocked `SaxoClient`/`MockSaxoClient` (backend, existing convention); no frontend test framework configured (existing gap, unchanged by this feature).
**Target Platform**: Existing FastAPI backend (Lambda-deployable) + React SPA (Vite), served locally via `run_api.py` / `npm run dev` in development.
**Project Type**: Web application (existing backend at repo root + `frontend/`) — matches the codebase's established layout, not the generic `backend/`+`frontend/` template split.
**Performance Goals**: Single-day run and its underlying Saxo calls complete within a few seconds (SC-001); range runs are synchronous and scale with the number of trading days requested (each day needs one H1 + one 5-minute Saxo history call) — no explicit SLA beyond "completes without a dedicated job queue," consistent with this being a single-user, on-demand analysis tool and with the "no application-level range cap" clarification.
**Constraints**: Must respect Constitution I (Layered Architecture) — new candle-fetch logic lives in `services/candles_service.py`, not called directly from the API service; must use existing enums (`Strategy.B9H`) instead of new hardcoded strings; must follow Candle conventions (index 0 = newest list ordering where lists are produced that way, `model.workflow.Candle` everywhere outside `SaxoClient`); the three numeric thresholds plus max-entry-distance are tunable per run (`BacktestParameters`, FR-025 — added 2026-07-21), defaulting to 50/10/20/20; the 9–10 window and instrument stay hardcoded per FR-002 ("no generic engine") — see Complexity Tracking.
**Scale/Scope**: One hardcoded `BacktestDefinition` (`B9H`); 5 new/changed backend endpoints' worth of surface (`/definitions`, `/run`, `/day`, plus CSV exports `/run/csv` and `/day/csv` for FR-017/FR-018); one new frontend page + sidebar entry, plus two "Export CSV" buttons; single-user tool, no concurrency/multi-tenant concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | New router (`api/routers/backtest.py`) stays thin; business logic (breakout/exit rules, aggregation) lives in a new `api/services/backtest_service.py`; new historical-candle fetch logic lives in `services/candles_service.py` (Service layer), which alone talks to `client/saxo_client.py`; new domain types live in `model/` with no external deps; frontend keeps API calls in `frontend/src/services/api.ts` only. | PASS |
| II. Clean Code First | Reuses `Strategy.B9H` instead of a new hardcoded name; new `ExitReason`/`DayStatus` enums instead of string literals; no speculative generic "backtest engine" is built (FR-002 explicitly forbids it). | PASS |
| III. Configuration-Driven Design | Strategy thresholds default in code but are tunable per request via `BacktestParameters` (FR-025, added 2026-07-21) rather than living in `config.yml` — appropriate, since they are per-run analysis inputs, not deployment configuration or external-integration settings. No new external integration or credential is introduced, so no new config surface is needed. | PASS |
| IV. Safe Deployment Practices | The candle cache (added 2026-07-24, FR-036–FR-040) requires one new Pulumi-managed DynamoDB table (`backtest_candle_cache`), following the existing `pulumi/dynamodb.py` pattern (e.g. `alert_digests_table`) and existing IAM grants (`pulumi/iam.py`); no new Lambda or external integration. Everything else remains additive within the existing API/frontend deployment. | PASS |
| V. Domain Model Integrity | New `UnitTime.M5` follows the existing enum pattern; 5-minute/H1 historical fetches for closed past days sidestep the "current day/hour not returned" Saxo limitation correctly (research.md §2) rather than ignoring it; `Candle` objects are used for all candle data outside the client layer; `exchange`/`country_code` concerns don't apply (FRA40.I is a single hardcoded Saxo instrument, not a general asset lookup). | PASS |

No violations requiring justification (the earlier hardcoded-thresholds exception was resolved when the thresholds became per-run parameters — see Complexity Tracking).

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

client/
└── aws_client.py                  # + DynamoDBClient.get_cached_backtest_candles(...)
                                    #   / store_backtest_candles(...) — raw H1/M5
                                    #   candle cache keyed by (instrument +
                                    #   session window, trading_date), no TTL
                                    #   (added 2026-07-24, re-keyed 2026-07-28)

pulumi/
└── dynamodb.py                    # + backtest_candle_cache_table() (added 2026-07-24)

api/
├── models/
│   └── backtest.py                # NEW: Pydantic request/response models
├── routers/
│   └── backtest.py                # NEW: GET /definitions, /run, /day,
                                    #      /run/csv, /day/csv (FR-017/FR-018)
├── services/
│   └── backtest_service.py        # NEW: breakout/exit rule engine + aggregation;
                                    #      + candle-cache lookup/store around the
                                    #      per-day candle fetch (FR-036–FR-040,
                                    #      added 2026-07-24)
├── dependencies.py                # + get_backtest_service()
└── main.py                        # + app.include_router(backtest.router)

frontend/src/
├── pages/
│   ├── Backtest.tsx                # NEW: page (single-day + range modes);
                                    #      + "Export CSV" buttons (FR-017/FR-018)
│   └── Backtest.css                # NEW
├── components/
│   └── Sidebar.tsx                 # + "Backtest" NavLink entry
├── App.tsx                         # + <Route path="/backtest" .../>
└── services/
    └── api.ts                      # + backtestService + TS interfaces;
                                    #   + exportRunCsv/exportDayCsv helpers

tests/
├── services/
│   └── test_candles_service.py     # + tests for get_candles_in_window
├── client/
│   └── test_aws_client_backtest_cache.py  # NEW: tests for the candle-cache
                                             #      get/store methods (2026-07-24)
└── api/
    ├── services/
    │   └── test_backtest_service.py  # NEW: strategy rule-engine tests;
                                       #      + cache-hit/miss tests (added 2026-07-24)
    └── routers/
        └── test_backtest.py          # NEW: endpoint tests
```

**Structure Decision**: Follows the codebase's existing flat layout (backend packages `api/`, `services/`, `client/`, `model/` at repo root, `frontend/` alongside them) rather than the generic `backend/`+`frontend/` template split — this matches every prior feature in `specs/` (e.g. 020-saxo-reporting) and Constitution's explicit File Organization guidance. No new top-level directories are introduced; the feature only adds files inside the existing `api/`, `services/`, `model/`, `frontend/src/`, and `tests/` trees.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| ~~Strategy thresholds (50pt stop, 10pt take-profit offset, 20pt break-even trigger, 9:00–10:00 window) hardcoded in `api/services/backtest_service.py` rather than `config.yml`~~ **Resolved 2026-07-21** | Originally justified by FR-002 ("I don't want to create a back test engine"). Superseded: the three numeric thresholds plus max-entry-distance became per-run parameters (`BacktestParameters`, FR-025), defaulting to the original constants; they are analysis inputs, not deployment configuration, so this is no longer a Configuration-Driven Design exception. The instrument and 9:00–10:00 window remain hardcoded per FR-002. | N/A — no longer a violation |
