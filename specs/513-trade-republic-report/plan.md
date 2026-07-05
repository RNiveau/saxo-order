# Implementation Plan: Trade Republic Report

**Branch**: `513-trade-republic-report` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/513-trade-republic-report/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a "Trade Republic Report" section to the web UI where a trader uploads a Trade Republic CSV export. The backend parses the file line by line into transactions and returns them to the frontend, which displays them in a table. The trader can then select one or more transactions and export them to Google Sheets; both the display data and the exported data are transient (no server-side persistence), and the exact Google Sheets column layout is a placeholder pending a follow-up spec. No duplicate detection is performed.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI (existing `api/` app), Python standard library `csv` module, existing `client/gsheet_client.py` (Google Sheets API via `googleapiclient`), Axios + React Router DOM v7+ (frontend, existing `frontend/src/services/api.ts`)
**Storage**: N/A — per spec (FR-010), uploaded transactions are held only for the current browser session (React state); no database table or file store is introduced
**Testing**: pytest (backend: CSV parsing service + router, mirroring `tests/api/services/` and `tests/api/routers/`); no frontend test framework is configured in this repo (per constitution, TBD) — frontend is validated by manual smoke test per `quickstart.md`
**Target Platform**: Existing web app (FastAPI backend + Vite/React SPA), same deployment target as the rest of the API (local `run_api.py` / Lambda)
**Project Type**: Web application (backend `api/` + frontend `frontend/`) — existing Option 2 structure, no new top-level project
**Performance Goals**: Parse and display a typical monthly statement (up to a few hundred rows) in under 5 seconds (spec SC-001)
**Constraints**: No new persistent storage; export is per-selected-transaction, not whole-batch (spec FR-011); no duplicate detection (spec FR-012); Google Sheets column layout is a placeholder, not final (spec FR-013)
**Scale/Scope**: Single trader, one file at a time, statements in the tens-to-low-hundreds of rows

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | New `api/routers/trade_republic.py` (thin) → new `api/services/trade_republic_service.py` (parsing + orchestration, no direct external calls except through the client) → existing `client/gsheet_client.py` (extended, encapsulates all Sheets API access) → new `model` dataclass/enums. Frontend: new `pages/TradeRepublicReport.tsx` calls only `services/api.ts`; no inline axios. | PASS |
| II. Clean Code First | Reuse existing `Currency` enum where it fits (native `currency`/`original_currency` fields). `category`/`type`/`account_type` are Trade-Republic-controlled vocabularies for which only one sample value each is known; treating them as validated strings (not a guessed, possibly-wrong enum) avoids over-engineering and brittle parsing — documented as a deliberate exception in research.md, not a hardcoded-string anti-pattern. | PASS (see research.md §3) |
| III. Configuration-Driven Design | No new secrets. One new non-sensitive config key (`trade_republic_sheet_name`) added to `config.yml` for the placeholder export tab name, following the existing `spreadsheet_id` pattern. | PASS |
| IV. Safe Deployment Practices | No new AWS resources (no persistence = no new DynamoDB table), no Pulumi changes. Existing deploy pipeline (`./deploy.sh`) picks up the new code unchanged. | PASS |
| V. Domain Model Integrity | New `TradeRepublicTransaction` model includes an explicit `source: str = "trade_republic"` field, consistent with the constitution's requirement to identify data origin explicitly rather than inferring it from which fields are populated. | PASS |

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
api/
├── models/
│   └── trade_republic.py          # NEW — Pydantic request/response models
├── routers/
│   └── trade_republic.py          # NEW — POST /upload, POST /gsheet/export
├── services/
│   └── trade_republic_service.py  # NEW — CSV parsing + export orchestration
└── dependencies.py                # UPDATED — get_trade_republic_service()

client/
└── gsheet_client.py                # UPDATED — add append-to-placeholder-sheet method

model/
├── enum.py                         # UPDATED — no new enums (see research.md §3)
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
