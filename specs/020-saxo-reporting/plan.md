# Implementation Plan: Saxo Order Reporting

**Branch**: `020-saxo-reporting` | **Date**: 2026-05-31 (retroactive documentation) | **Spec**: [spec.md](./spec.md)
**Input**: Reverse-engineered from the existing CLI command, API router, service, client integrations, and React page

## Summary

Expose the trader's executed Saxo orders for a chosen period through two equivalent surfaces — an interactive Click CLI and a FastAPI + React web UI — and let the trader create or update positions in a Google Sheets trading journal with risk-management metadata (stop, objective, strategy, signal, comment, closure flags).

The implementation introduces a single `ReportService` in the API layer that orchestrates `SaxoClient`, `GSheetClient`, and currency/tax helpers. The same service is reused by the API router for HTTP traffic and (later, in the Binance backport) became the template that `BinanceReportService` mirrored. The frontend is platform-agnostic and selects the backend via an `account_id` (Saxo account key, or the `binance_*` pseudo-account). The CLI command (`k-order get-report`) predates the API and remains as a power-user surface; it shares the underlying `SaxoClient.get_report` and `GSheetClient` integrations.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI, Click, `cachetools` (TTLCache), Pydantic v2, Axios, React Router DOM v7+, Vite 7+
**Storage**: Google Sheets (persisted trading journal); in-memory `TTLCache` for report fetches (5 min TTL); no database for this feature
**Testing**: `pytest` with `unittest.mock` for backend; no frontend test framework yet (per constitution §Testing Standards)
**Target Platform**: Web app (React SPA + FastAPI behind uvicorn locally / Lambda in production) + CLI tool (`k-order`)
**Project Type**: Full-stack web application + CLI (matches Option 2 from the template)
**Performance Goals**: <3 s for a typical month of orders on first fetch; <500 ms on cache hits; aggregated summary recomputed inline from the order list
**Constraints**: CLI must remain functional and produce equivalent results to the UI; Google Sheets writes are append/update only (no delete); regulatory taxes apply to stocks only; conversion rates come from configuration
**Scale/Scope**: Single-trader use; up to ~hundreds of orders per period; one trading journal (single spreadsheet); two brokers covered by the shared report surface (Saxo here, Binance in spec 471)

## Constitution Check

*GATE: Passes for both Phase 0 and post-Phase 1 design.*

✅ **I. Layered Architecture Discipline**:
- CLI (`saxo_order/commands/get_report.py`) → orchestrates `SaxoClient` + `GSheetClient` + helpers; no business logic.
- API router (`api/routers/report.py`) → thin orchestration of `ReportService`.
- Service (`api/services/report_service.py`) → owns business logic (period fetch, EUR conversion, summary, journal writes); receives clients via constructor (DI).
- Clients (`client/saxo_client.py`, `client/gsheet_client.py`) → external integrations only; return domain models (`ReportOrder`, `Order`).
- Models (`model/__init__.py`, `model/enum.py`) → no external dependencies; `Strategy` / `Signal` / `Currency` / `Direction` / `AssetType` are enums.
- Frontend: `Report.tsx` (page) → `reportService` in `frontend/src/services/api.ts` for all HTTP calls. `OrderModal` is a sub-component receiving data via props.

✅ **II. Clean Code First**:
- Self-documenting Click options and Pydantic fields.
- Enum-driven (`Strategy`, `Signal`, `Currency`, `Direction`, `AssetType`).
- No inline `// what this does` comments in the affected files.

✅ **III. Configuration-Driven Design**:
- Currency conversion rates, Google Sheets credentials path, spreadsheet id, and Saxo credentials all come from `config.yml` / `secrets.yml` via `Configuration`.
- Frontend uses `import.meta.env.VITE_API_URL` (no hardcoded API URL).

✅ **IV. Safe Deployment Practices**:
- Conventional commits (this feature is delivered as `docs:` because the code already shipped).
- Backend deploys via the standard Lambda/ECR/Pulumi pipeline; no infra change required for this feature.

✅ **V. Domain Model Integrity**:
- `ReportOrder` extends `Order` with journaling fields; both live in `model/`.
- `Account` is a dataclass in `model/__init__.py` (not a Pydantic model leak across the API boundary — the API exposes its own `AccountInfo`).
- Account routing is prefix-based (`binance_*` → Binance, otherwise Saxo); does NOT infer broker from `country_code` (matches the constitution's explicit prohibition).

✅ **No constitution violations identified.** "Complexity Tracking" therefore has nothing to justify.

## Project Structure

### Documentation (this feature)

```text
specs/020-saxo-reporting/
├── spec.md                      # User stories & requirements (already written)
├── plan.md                      # This file
├── research.md                  # Phase 0: architectural decisions (retroactive)
├── data-model.md                # Phase 1: entities & relationships (retroactive)
├── quickstart.md                # Phase 1: how to exercise the feature locally
├── contracts/
│   └── report-api.md            # Phase 1: HTTP endpoints & payload shapes
└── checklists/
    └── requirements.md          # Already written
```

### Source Code (already implemented in the repo)

```text
# Backend
api/
├── routers/report.py                       # FastAPI routes (5 endpoints)
├── services/report_service.py              # ReportService — business logic
├── models/report.py                        # Pydantic request/response models
└── dependencies.py                         # get_saxo_client / get_binance_client / get_configuration

client/
├── saxo_client.py                          # get_report(account, from_date) -> List[ReportOrder]
└── gsheet_client.py                        # create_order / update_order

saxo_order/
├── commands/get_report.py                  # Click CLI: k-order get-report
└── service.py                              # calculate_currency / calculate_taxes (shared helpers)

model/
├── __init__.py                             # Order, ReportOrder, Account (dataclass), Taxes
└── enum.py                                 # Strategy, Signal, Currency, Direction, AssetType

# Frontend
frontend/src/
├── pages/Report.tsx                        # Report page + OrderModal sub-component
├── services/api.ts                         # reportService + reportConfigService
└── (styles colocated, e.g. Report.css)

# Tests
tests/
└── client/test_gsheet_client.py            # GSheet client unit tests
# Note: no dedicated tests for ReportService (Saxo side) — the Binance variant
#       in spec 471 added 12 tests for BinanceReportService; an equivalent suite
#       for ReportService is a follow-up.
```

**Structure Decision**: Full-stack web application + CLI tool. The web stack mirrors the layered architecture mandated by the constitution; the CLI sits beside `api/` and shares clients and helpers but does NOT depend on FastAPI. The frontend is generic — it talks to `account_id` rather than to a "Saxo report" endpoint — which is what later allowed Binance to be added without frontend changes (see `specs/471-binance-reporting`).

## Phase 0 — Research (retroactive)

The detailed decision log lives in [research.md](./research.md). Headline decisions:

1. **Single report endpoint with prefix-based account routing.** Saxo account keys go to `ReportService`; `binance_*` ids go to `BinanceReportService` (added later). One frontend, one URL space.
2. **`ReportService` as the seam between CLI and API.** Business logic (period fetch, EUR conversion, summary, journal writes) lives in one class; the CLI uses the same client and helpers, the API delegates to the service.
3. **5-minute TTL cache on report fetches** via `cachetools.TTLCache`, keyed by `(account_id, from_date)`. Trading-journal use does not need real-time freshness.
4. **Conversion rates are configuration-driven, not live.** Acceptable because the journal records entry/exit prices, not mark-to-market.
5. **Strategy/Signal are enums shipped via `/api/report/config`** so the UI picks from a controlled vocabulary instead of free-text input.
6. **Google Sheets row targeting is manual.** The user supplies the row number; the system never auto-matches an order to an existing journal row.

## Phase 1 — Design Artefacts (retroactive)

- [data-model.md](./data-model.md) — entities: `ReportOrder`, `Order`, `Account`, `Taxes`, controlled vocabularies (`Strategy`, `Signal`, `Currency`, `Direction`, `AssetType`), and the Google Sheets journal row layout.
- [contracts/report-api.md](./contracts/report-api.md) — HTTP contract for `/api/report/*`: `GET /config`, `GET /orders`, `GET /summary`, `POST /gsheet/create`, `POST /gsheet/update`.
- [quickstart.md](./quickstart.md) — how to run the CLI and the UI flow end-to-end, plus the smoke-test checklist.

## Complexity Tracking

> No constitution violations — section intentionally empty.

Noteworthy design choices that *avoided* complexity:

| Decision | Rationale | Simpler Alternative Rejected Because |
|----------|-----------|--------------------------------------|
| Prefix-based account routing in the API | Single endpoint set covers all brokers | Per-broker URL space (`/api/saxo-report/*`) would force frontend changes for every new broker |
| Manual row-number for journal updates | The user already knows which row maps to which trade; auto-match would need a second source of truth | Auto-detection of the journal row via heuristics would silently overwrite the wrong row when ambiguous |
| In-memory `TTLCache` instead of a database for report results | Reports are derived data, not state; staleness is bounded by TTL | A persistent cache would add infra cost and migrations for no user-visible benefit |
| `ReportOrder` as a subtype of `Order` rather than a new model | Journaling fields (`stopped`, `be_stopped`, `open_position`) are additive | A separate `JournalEntry` model would duplicate every order field and force conversions at every boundary |
| Strategy/Signal as enums served by `/api/report/config` | Single source of truth for the UI dropdowns; values change in one place | Hardcoding the lists in the frontend would drift from the backend's validation |

## Retroactive Verification Notes

- **Behaviour parity CLI ↔ UI**: both call `SaxoClient.get_report` and write through `GSheetClient`; the CLI prompts interactively whereas the UI uses the `OrderModal` form. Same outputs for identical inputs.
- **CORS**: `api/main.py` allows `localhost:3000` and `localhost:5173` per the constitution.
- **Open follow-up**: no dedicated `tests/api/services/test_report_service.py` yet — the Binance variant added 12 tests in `tests/api/services/test_binance_report_service.py`; an equivalent suite for the Saxo service is a sensible next step but is out of scope for this retro-documentation effort.
