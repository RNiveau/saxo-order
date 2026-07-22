# Implementation Plan: Ouinex crypto provider

**Branch**: `024-ouinex-provider` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/024-ouinex-provider/spec.md`

## Summary

Introduce Ouinex as a new crypto provider that mirrors the existing Binance feature set — instrument search, watchlist add/classification, candle retrieval for indicators, and trade-history reporting — while writing all journal entries under the existing Binance pseudo-account identity ("map as binance"). Ouinex coexists with Binance (both remain available); order execution is out of scope.

The technical approach follows the established layered pattern: a new `OuinexClient` in the Client layer exposing the same method surface as `BinanceClient` (`search`, `get_candles`, `get_latest_candle`, `get_report_all`), a new `OuinexReportService` that reuses the Binance pseudo-account when writing to Google Sheets, a new `Exchange.OUINEX` enum value, and routing additions everywhere Binance is currently routed (search, indicators, watchlist, homepage, report, accounts). The key divergence from Binance is the Ouinex API itself: it is a **GraphQL API** (`POST https://live-api.ouinex.com/graphql`) with **JWT bearer authentication** and delivers OHLC bars via **WebSocket subscription**, versus Binance's simple public REST endpoints and static key/secret HMAC. This drives the bulk of the new Client-layer work and the primary risk (see `research.md`).

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend — minimal changes)
**Primary Dependencies**: FastAPI, Pydantic v2, `cachetools` (TTLCache), `googleapiclient` (Google Sheets); NEW: a GraphQL/HTTP client for Ouinex (`httpx` or `requests` — POST GraphQL + JWT auth flow); frontend Axios + React Router DOM v7+
**Storage**: AWS DynamoDB `watchlist` table (existing `exchange` attribute, unchanged schema); Google Sheets trading journal (existing "Liste d'ordre" sheet, unchanged schema). No new tables.
**Testing**: `pytest` with `unittest.mock` mocking the Ouinex client; test data files under `tests/services/files/`
**Target Platform**: Linux server / AWS Lambda (backend), plus local FastAPI + Vite dev
**Project Type**: web (backend `api/` + frontend `frontend/`)
**Performance Goals**: Parity with Binance — report fetches cached with 5-min TTL; candle/search requests complete within a few seconds; no added latency to Saxo/Binance paths
**Constraints**: Ouinex requires valid credentials for **every** call (search, candles, reporting) — unlike Binance's public market-data endpoints (per Clarifications). JWT tokens are short-lived and must be refreshed. An Ouinex failure MUST NOT degrade Binance or Saxo.
**Scale/Scope**: Single-user personal trading tool; crypto watchlist on the order of tens of instruments

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture Discipline | PASS | `OuinexClient` lives in `client/` and returns domain models (`Asset`, `Candle`, `ReportOrder`), never raw GraphQL responses. `OuinexReportService` in `api/services/` orchestrates the client. Routers stay thin. No service accesses client internals. Public methods carry no `_` prefix. |
| II. Clean Code First | PASS | Mirror the `BinanceClient`/`BinanceReportService` shape; no speculative abstraction. The Binance→Ouinex mapping stays explicit, not clever. No unnecessary comments. |
| III. Configuration-Driven Design | PASS | Ouinex credentials read from `secrets.yml` via a new `Configuration.ouinex_keys` property (mirrors `binance_keys`); GraphQL base URL in `config.yml`, no hardcoding. |
| IV. Safe Deployment Practices | PASS | No infrastructure change (no new AWS resources). Conventional commits. |
| V. Domain Model Integrity | PASS | Add explicit `Exchange.OUINEX = "ouinex"`; never infer exchange from `country_code`. Candle ordering (index 0 = newest) preserved in `OuinexClient.get_candles`. Reconstruction of current day/hour follows the existing pattern. Reporting maps to Binance identity **explicitly** at the write boundary, not by inference. |

**Result**: No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/024-ouinex-provider/
├── plan.md              # This file
├── research.md          # Phase 0 output — Ouinex API decisions & risks
├── data-model.md        # Phase 1 output — entities, enum, client interface
├── quickstart.md        # Phase 1 output — configure & verify
├── contracts/           # Phase 1 output — API contract deltas
│   └── api-deltas.md
├── checklists/
│   └── requirements.md  # From /speckit.specify
└── tasks.md             # From /speckit.tasks (NOT created here)
```

### Source Code (repository root)

```text
client/
├── ouinex_client.py          # NEW — GraphQL+JWT client; same method surface as BinanceClient
└── binance_client.py         # reference implementation (unchanged)

api/
├── dependencies.py           # MODIFY — add get_ouinex_client(), get_ouinex_report_service()
├── services/
│   ├── ouinex_report_service.py   # NEW — reuses Binance pseudo-account ("map as binance")
│   ├── binance_report_service.py  # reference (unchanged)
│   ├── search_service.py     # MODIFY — include Ouinex results alongside Saxo+Binance
│   ├── indicator_service.py  # MODIFY — route Exchange.OUINEX to Ouinex candles
│   └── watchlist_service.py  # MODIFY — treat OUINEX like BINANCE (crypto tag, USD, indicators)
└── routers/
    ├── search.py             # MODIFY — inject Ouinex client
    ├── indicator.py          # MODIFY — inject Ouinex client; accept exchange=ouinex
    ├── report.py             # MODIFY — route account_id "ouinex_" → Ouinex report service
    ├── fund.py               # MODIFY — add "ouinex_main" pseudo-account to /accounts
    └── homepage.py           # MODIFY — map exchange_str "ouinex" → Exchange.OUINEX

model/
└── enum.py                   # MODIFY — add Exchange.OUINEX = "ouinex"

utils/
└── configuration.py          # MODIFY — add ouinex_keys property + graphql url

saxo_order/commands/
└── ouinex.py                 # NEW (optional) — CLI report command mirroring binance.py

frontend/src/
└── pages/SearchResults.css   # MODIFY — .exchange-badge.ouinex style (cosmetic)

tests/
├── client/test_ouinex_client.py            # NEW
├── api/services/test_ouinex_report_service.py  # NEW
├── api/routers/test_search.py              # MODIFY — assert Ouinex results included
└── api/routers/test_report.py              # MODIFY — assert ouinex_ routing + binance identity
```

**Structure Decision**: Web application (backend + frontend) using the existing layered architecture. Ouinex is added as a sibling to Binance at each layer — a new Client, a new report Service, a new enum value, and routing branches in existing routers/services — rather than a parallel subsystem. The frontend is largely exchange-agnostic (it passes the `exchange` string through), so frontend work is limited to a badge style and the report account dropdown auto-populating from `/api/fund/accounts`.

## Key Integration Points (Binance parity map)

| Capability | Binance today | Ouinex change |
|-----------|---------------|---------------|
| Instrument search | `SearchService` calls `BinanceClient.search()` | Also call `OuinexClient.search()`; results tagged `Exchange.OUINEX` |
| Indicators / candles | `IndicatorService._get_binance_asset_indicators` via `BinanceClient.get_candles` | Route `Exchange.OUINEX` → `OuinexClient.get_candles` |
| Watchlist add | `watchlist_service` treats `exchange == "binance"` as crypto (USD, crypto tag) | Same treatment for `"ouinex"` |
| Homepage enrichment | maps `"binance"` → `Exchange.BINANCE` | map `"ouinex"` → `Exchange.OUINEX` |
| Accounts list | `/api/fund/accounts` prepends `binance_main` | Also prepend `ouinex_main` |
| Report routing | `account_id.startswith("binance_")` → `BinanceReportService` | `startswith("ouinex_")` → `OuinexReportService` |
| Journal write (gsheet) | `BinanceReportService._get_binance_account()` → `Account(key="binance", name="Coinbase")` | `OuinexReportService` reuses the **same** Binance pseudo-account → "map as binance" |
| Credentials | `Configuration.binance_keys` from `secrets.yml` | NEW `Configuration.ouinex_keys` |

## Scope notes / faithful parity

- **Alerts**: `run_detection_for_asset` currently builds candles only via `saxo_client` and returns early when `saxo_uic is None`, so **crypto assets (Binance today) receive no alert detection**. Faithful parity means Ouinex inherits the same behavior — no new crypto alert capability is built as part of this feature. FR-007 is satisfied ("same alerts as Binance" = none in practice). Building real crypto alert detection would be a separate feature. This is called out so we neither over-build nor claim a capability that does not exist.
- **Order execution**: out of scope per Clarifications (Binance has none).

## Complexity Tracking

No constitution violations — section intentionally empty.
