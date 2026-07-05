# Implementation Plan: Trade Republic Report

**Branch**: `513-trade-republic-report` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/513-trade-republic-report/spec.md`

## Summary

Add a "Trade Republic Report" section to the web UI where a trader uploads a Trade Republic CSV export. The backend parses the file line by line into transactions and returns them to the frontend, which displays them in a table. The trader can then select one or more transactions and export them as new rows in the existing "ETF / DCA" Google Sheet (field mapping per FR-013); the parsed/displayed data is transient (no server-side persistence). No duplicate detection is performed.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI (existing `api/` app), **`python-multipart` (NEW — required by FastAPI's `UploadFile`/multipart form parsing; not currently in `pyproject.toml`/`poetry.lock`, only present as fastapi's optional `standard` extra, see research.md §7)**, Python standard library `csv` module, existing `client/gsheet_client.py` (Google Sheets API via `googleapiclient`), Axios + React Router DOM v7+ (frontend, existing `frontend/src/services/api.ts`)
**Storage**: N/A — per spec (FR-010), uploaded transactions are held only for the current browser session (React state); no database table or file store is introduced
**Testing**: pytest (backend: CSV parsing service + router, mirroring `tests/api/services/` and `tests/api/routers/`); no frontend test framework is configured in this repo (per constitution, TBD) — frontend is validated by manual smoke test per `quickstart.md`
**Target Platform**: Existing web app (FastAPI backend + Vite/React SPA), same deployment target as the rest of the API (local `run_api.py` / Lambda)
**Project Type**: Web application (backend `api/` + frontend `frontend/`) — existing Option 2 structure, no new top-level project
**Performance Goals**: Parse and display a typical monthly statement (up to a few hundred rows) in under 5 seconds (spec SC-001)
**Constraints**: No new persistent storage; export is per-selected-transaction, not whole-batch (spec FR-011); no duplicate detection (spec FR-012); export targets the existing "ETF / DCA" Google Sheet with the fixed field mapping in spec FR-013
**Scale/Scope**: Single trader, one file at a time, statements in the tens-to-low-hundreds of rows

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | New `api/routers/trade_republic.py` (thin) → new `api/services/trade_republic_service.py` (parsing + orchestration, no direct external calls except through the client) → existing `client/gsheet_client.py` (extended, encapsulates all Sheets API access) → new `model` dataclass/enums. Frontend: new `pages/TradeRepublicReport.tsx` calls only `services/api.ts`; no inline axios. | PASS |
| II. Clean Code First | Reuse existing `AssetType` enum for `asset_class` (see FR-014) and existing `Currency` enum for `currency`/`original_currency` wherever the code matches one of its members (typed `Union[Currency, str]` since the enum doesn't cover every real-world code — see research.md §5). `category`/`type`/`account_type` are Trade-Republic-controlled vocabularies for which only one sample value each is known; treating them as validated strings (not a guessed, possibly-wrong enum) avoids over-engineering and brittle parsing — documented as a deliberate exception in research.md, not a hardcoded-string anti-pattern. | PASS (see research.md §4, §5) |
| III. Configuration-Driven Design | No new secrets. One new non-sensitive config key (`trade_republic_sheet_name`, value `"ETF / DCA"`) added to `config.yml`, following the existing `spreadsheet_id` pattern. | PASS |
| IV. Safe Deployment Practices | No new AWS resources (no persistence = no new DynamoDB table), no Pulumi changes. One new dependency (`python-multipart`, see Technical Context) must be added via `poetry add python-multipart` and will be picked up by the existing Docker/Lambda build — no manual deployment step beyond the normal `./deploy.sh`. | PASS |
| V. Domain Model Integrity | N/A — the constitution's explicit-`exchange`-field requirement targets Alert/Order/Asset representations where Saxo vs. Binance identity is genuinely ambiguous (the `country_code` pitfall). `TradeRepublicTransaction` is a distinct, single-broker entity with no such ambiguity to guard against, so no origin-marker field is required. | PASS |

No violations — Complexity Tracking section is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/513-trade-republic-report/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── trade-republic-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
pyproject.toml / poetry.lock         # UPDATED — `poetry add python-multipart` (required by UploadFile)

api/
├── models/
│   └── trade_republic.py          # NEW — Pydantic request/response models
├── routers/
│   └── trade_republic.py          # NEW — POST /upload, POST /gsheet/export
├── services/
│   └── trade_republic_service.py  # NEW — CSV parsing + export orchestration
└── dependencies.py                # UPDATED — get_trade_republic_service()

client/
└── gsheet_client.py                # UPDATED — add append_etf_dca_rows method (single batched write, see research.md §6)

model/
├── enum.py                         # UNCHANGED — reuses existing AssetType/Currency, no new enums (see research.md §1, §4)
└── __init__.py                     # UPDATED — add TradeRepublicTransaction dataclass

tests/
├── api/
│   ├── services/
│   │   └── test_trade_republic_service.py  # NEW
│   └── routers/
│       └── test_trade_republic.py          # NEW
└── services/files/
    └── trade_republic_sample.csv           # NEW — fixture (from the CSV format in spec)

frontend/src/
├── pages/
│   ├── TradeRepublicReport.tsx      # NEW
│   └── TradeRepublicReport.css      # NEW
├── components/
│   └── Sidebar.tsx                  # UPDATED — add nav entry
├── services/
│   └── api.ts                       # UPDATED — add tradeRepublicService
└── App.tsx                          # UPDATED — add /trade-republic-report route
```

**Structure Decision**: Existing web application layout (`api/` + `frontend/`) is extended in place — no new project, mirroring how the Saxo/Binance reporting feature (`specs/020-saxo-reporting`, `specs/471-binance-reporting`) added its own router/service/page. No persistence layer is added anywhere (per FR-010).

## Complexity Tracking

*No constitution violations — section not applicable.*
