# Tasks: Trade Republic Report

**Input**: Design documents from `/specs/022-trade-republic-report/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/trade-republic-api.md, quickstart.md

**Tests**: Included. This repo's constitution makes backend test coverage a pre-merge gate (mirror `tests/` structure, no mock-only tests), and plan.md/quickstart.md already commit to specific new test files — so backend tests are part of "done" for each story, not optional. No frontend test framework is configured in this repo, so frontend verification is the manual `quickstart.md` walkthrough, not automated tests.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Tasks touching the same file are never marked `[P]`, even if logically independent

## Path Conventions

Existing web app layout, extended in place (see plan.md Project Structure): `api/`, `client/`, `model/` for backend; `frontend/src/` for frontend; `tests/` mirrors `api/`/`client/` structure.

---

## Phase 1: Setup

**Purpose**: Dependency and configuration groundwork required before any code can run

- [x] T001 Add `python-multipart` dependency via `poetry add python-multipart` (updates `pyproject.toml` and `poetry.lock`) — required by FastAPI's `UploadFile`; see research.md §7 and plan.md Technical Context
- [x] T002 Add `trade_republic_sheet_name: "ETF / DCA"` key to `config.yml`, a `trade_republic_sheet_name` property to `Configuration` in `utils/configuration.py` (following the existing `spreadsheet_id` property pattern), and the matching property to `MockConfiguration` in `tests/utils/configuration.py`
- [x] T003 [P] Create the CSV test fixture `tests/services/files/trade_republic_sample.csv` using the header and sample row from spec.md (plus a couple of additional rows: one `STOCK` trade row with shares/price/symbol populated, one row missing a required field, to support later test tasks)

**Checkpoint**: Dependency installed, config wired, fixture ready — implementation can begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared domain model, service scaffolding, and router registration that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Add the `TradeRepublicTransaction` dataclass to `model/__init__.py` per data-model.md (fields, types incl. `Union[Currency, str]` for `currency`/`original_currency`, `Optional[AssetType]` for `asset_class`; no origin-marker field — see plan.md Constitution Check V)
- [x] T005 [P] Create `api/models/trade_republic.py` with the Pydantic API models: `TradeRepublicTransactionResponse` (with a `from_transaction` classmethod mirroring `ReportOrderResponse.from_report_order` in `api/models/report.py`), `ParseErrorResponse`, `UploadTradeRepublicResponse`, `ExportTradeRepublicRequest`, `ExportTradeRepublicResponse` — shapes per contracts/trade-republic-api.md
- [x] T006 Create `api/services/trade_republic_service.py` with a `TradeRepublicService` class (constructor takes the existing `GSheetClient`, dependency-injected — no parsing/export logic yet, just the class shell)
- [x] T007 Wire `get_trade_republic_service()` into `api/dependencies.py` (constructs `TradeRepublicService` from `get_gsheet_client()`, following the existing `get_report_service()` pattern)
- [x] T008 Create `api/routers/trade_republic.py` with an empty `APIRouter(prefix="/api/trade-republic", tags=["trade_republic"])` and register it via `app.include_router(trade_republic.router)` in `api/main.py`

**Checkpoint**: Model, service shell, and router are wired — user story implementation can now begin

---

## Phase 3: User Story 1 - Upload a Trade Republic statement and review its transactions (Priority: P1) 🎯 MVP

**Goal**: A trader can upload a well-formed Trade Republic CSV and see every transaction displayed in the UI, with fields correctly blank where the source column is empty and foreign-currency amounts shown alongside native ones.

**Independent Test**: Upload the fixture CSV from T003 and verify the UI shows one row per transaction with the CSV's values correctly mapped (per spec.md US1 Acceptance Scenarios 1–3).

### Tests for User Story 1

- [x] T009 [P] [US1] Write unit tests in `tests/api/services/test_trade_republic_service.py` for `TradeRepublicService.parse_csv`: delimiter detection (comma and semicolon input), a `CASH`/`INTEREST_PAYMENT` row with blank optional fields, a `STOCK` trade row with shares/price/symbol populated, a foreign-currency row (`original_amount`/`original_currency`/`fx_rate`), and `asset_class` mapping (`FUND`→`AssetType.ETF`, `STOCK`→`AssetType.STOCK`, empty→`None`)
- [x] T010 [P] [US1] Write a router test in `tests/api/routers/test_trade_republic.py` for `POST /api/trade-republic/upload` happy path: upload the fixture CSV via `TestClient`, assert the response's `transactions`/`total_rows` match, using `app.dependency_overrides[get_trade_republic_service]` per the pattern in `tests/api/routers/test_watchlist.py`

### Implementation for User Story 1

- [x] T011 [US1] Implement `parse_csv(file_content: str) -> Tuple[List[TradeRepublicTransaction], List[ParseError]]` in `api/services/trade_republic_service.py`: sniff the delimiter with `csv.Sniffer` (fallback to comma, research.md §2), iterate rows with `csv.DictReader`, map each row to a `TradeRepublicTransaction` (including the `asset_class`→`AssetType` and `currency`→`Union[Currency, str]` mappings)
- [x] T012 [US1] Implement `POST /api/trade-republic/upload` in `api/routers/trade_republic.py`: accept `file: UploadFile`, decode and pass its content to `TradeRepublicService.parse_csv`, return `UploadTradeRepublicResponse` built from the results (depends on T011)
- [x] T013 [P] [US1] Add `tradeRepublicService.upload(file: File)` to `frontend/src/services/api.ts` with TypeScript interfaces mirroring `UploadTradeRepublicResponse`/`TradeRepublicTransactionResponse` (contracts/trade-republic-api.md)
- [x] T014 [US1] Create `frontend/src/pages/TradeRepublicReport.tsx` + `TradeRepublicReport.css`: file upload input, calls `tradeRepublicService.upload`, renders parsed transactions in a table (blank cells for empty optional fields, both native and original currency/amount shown for foreign-currency rows) (depends on T013)
- [x] T015 [US1] Add the `/trade-republic-report` route to `frontend/src/App.tsx` and a "Trade Republic Report" nav entry to `frontend/src/components/Sidebar.tsx` (depends on T014)

**Checkpoint**: Uploading a well-formed CSV displays every transaction in the UI — User Story 1 is independently functional

---

## Phase 4: User Story 2 - Export reviewed transactions to Google Sheets (Priority: P1)

**Goal**: A trader can select one or more displayed transactions and export them as new rows in the existing "ETF / DCA" Google Sheet, with a clear success/failure outcome and no partial writes on failure.

**Independent Test**: From a populated report (via US1), select a transaction, export it, and verify one new row appears in the "ETF / DCA" sheet with the FR-013 field mapping, per spec.md US2 Acceptance Scenarios 1–3.

### Tests for User Story 2

- [x] T016 [P] [US2] Write unit tests in `tests/client/test_gsheet_client.py` for `GSheetClient.append_etf_dca_rows`: a single mocked `spreadsheets().values().append()` call carrying all rows in one request, `Sens` derived from `type` (`BUY`→`Achat`, `SELL`→`Vente`, blank for `TRANSFER_INBOUND`/`DIVIDEND`/`INTEREST_PAYMENT`/`IPO_SUBSCRIPTION`), and `Total`/`Total TTC` written as formulas (`=E{r}*F{r}`, `=H{r}+G{r}`) referencing each row's own computed row number (research.md §6), following the `MockGsheetClient` pattern already in this file
- [x] T017 [P] [US2] Write unit tests in `tests/api/services/test_trade_republic_service.py` for `TradeRepublicService.export_transactions` (delegates to `GSheetClient.append_etf_dca_rows`, propagates its exceptions) and a router test in `tests/api/routers/test_trade_republic.py` for `POST /api/trade-republic/gsheet/export`: success (`exported_count` equals selection size), empty selection → `400`, `GSheetClient` raising → `500` with no partial `exported_count`

### Implementation for User Story 2

- [x] T018 [US2] Implement `append_etf_dca_rows(transactions: List[TradeRepublicTransaction])` in `client/gsheet_client.py`: read the "ETF / DCA" sheet's current row count once (reusing the `_get_number_rows()` pattern), build one row per transaction with the FR-013 column mapping and `Total`/`Total TTC` formulas, and write all rows in a single `spreadsheets().values().append()` call using `self.trade_republic_sheet_name` from configuration (depends on T016)
- [x] T019 [US2] Implement `export_transactions(transactions: List[TradeRepublicTransaction])` in `api/services/trade_republic_service.py`, calling `GSheetClient.append_etf_dca_rows` (depends on T011, T018)
- [x] T020 [US2] Implement `POST /api/trade-republic/gsheet/export` in `api/routers/trade_republic.py`: validate the `transactions` list is non-empty (`400` otherwise), call `TradeRepublicService.export_transactions`, return `ExportTradeRepublicResponse`, and map any `GSheetClient` failure to `500` (depends on T019)
- [x] T021 [P] [US2] Add `tradeRepublicService.export(transactions)` to `frontend/src/services/api.ts` per `ExportTradeRepublicRequest`/`ExportTradeRepublicResponse`
- [x] T022 [US2] Add row-selection checkboxes and an "Export" button to `frontend/src/pages/TradeRepublicReport.tsx`: button disabled when no row is selected (spec.md US2 Acceptance Scenario 3), calls `tradeRepublicService.export` with only the selected rows, shows a success/error message without clearing the table on failure (depends on T014, T021)

**Checkpoint**: User Stories 1 and 2 both work independently and together — upload, review, select, export

---

## Phase 5: User Story 3 - Get clear feedback on an invalid or malformed upload (Priority: P3)

**Goal**: Non-CSV files, empty CSVs, and CSVs with some unparseable rows each produce a clear, distinct outcome instead of a blank screen or a fully-aborted upload.

**Independent Test**: Upload a non-CSV file, an empty (header-only) CSV, and a CSV with one malformed row; verify each produces the distinct outcome described in spec.md US3 Acceptance Scenarios 1–3.

### Tests for User Story 3

- [ ] T023 [P] [US3] Extend `tests/api/services/test_trade_republic_service.py`: a CSV whose header doesn't match the expected columns raises a clear parse error (FR-006). (Note: per-row required-field validation producing `ParseError` — the other half of FR-008 originally scoped here — was already implemented as part of T011, since a type-safe `parse_csv` couldn't skip it; see `test_parses_well_formed_rows_and_flags_the_malformed_one` in the same file for that coverage.)
- [ ] T024 [P] [US3] Extend `tests/api/routers/test_trade_republic.py`: `POST /api/trade-republic/upload` with a non-CSV file returns `400` with no transactions, and a header-only CSV returns `200` with empty `transactions`/`errors` (FR-007 — already covered implicitly since an empty-body CSV simply yields zero `DictReader` rows; add an explicit test for it)

### Implementation for User Story 3

- [ ] T025 [US3] Extend `parse_csv` in `api/services/trade_republic_service.py`: validate the sniffed header against the expected column set and raise a clear exception if it doesn't match (FR-006). (Per-row required-field validation is already implemented, from T011.)
- [ ] T026 [US3] Update `POST /api/trade-republic/upload` in `api/routers/trade_republic.py` to catch the header-validation exception from T025 and return `400` with a clear `detail` message (depends on T012, T025)
- [ ] T027 [US3] Add to `frontend/src/pages/TradeRepublicReport.tsx`: an explicit "no transactions found" empty state when `transactions` is empty and no error occurred, an upload-rejection error banner for `400` responses, and a visually flagged row (or separate list) for entries in `errors` (depends on T014)

**Checkpoint**: All three user stories are independently functional — malformed input no longer produces a blank or broken screen

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T028 [P] Run `poetry run black .`, `poetry run isort .`, `poetry run mypy .`, `poetry run flake8` and fix any violations across all new/changed backend files
- [ ] T029 [P] Run `npm run build` and `npm run lint` in `frontend/` and fix any TypeScript/ESLint violations
- [ ] T030 Walk through every step of `quickstart.md` manually against a running `run_api.py` + `npm run dev` (upload, reload-loses-data, export, no-selection-disabled, non-CSV rejection, empty-file state, partial-parse-error flagging, export failure) and fix any discrepancy found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 dependency must be installed before `UploadFile` is used; T002 config must exist before the service/router reference it) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion only
- **User Story 2 (Phase 4)**: Depends on Foundational completion; T019 also depends on T011 (parsing must produce the `TradeRepublicTransaction` objects export consumes) and T018; T022 also depends on T014 (the page component export UI extends)
- **User Story 3 (Phase 5)**: Depends on Foundational completion; extends the `parse_csv`/router/page created in Phase 3 (T011, T012, T014) rather than creating new files
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests before implementation (write T009/T010, T016/T017, T023/T024 first; confirm they fail against the not-yet-implemented code)
- Backend model/service before router before frontend service before frontend UI
- Story complete before moving to the next priority (US1 → US2 → US3, though US1 and US2 are both spec priority P1 and may be worked in either order once Foundational is done)

### Parallel Opportunities

- T004 and T005 (different files: `model/__init__.py` vs `api/models/trade_republic.py`) can run in parallel
- T009 and T010 (different test files, both only need Foundational to be done) can be written in parallel
- T013 (frontend service) can be built in parallel with T011/T012 (backend), since the contract shape is already fixed by contracts/trade-republic-api.md
- T016 and T017 (different test files) can be written in parallel
- T021 (frontend service) can likewise run in parallel with T018/T019/T020
- T023 and T024 (different test files) can be written in parallel
- T028 and T029 (backend lint/typecheck vs frontend lint/build) can run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
Task: "Add the TradeRepublicTransaction dataclass to model/__init__.py per data-model.md"
Task: "Create api/models/trade_republic.py with the Pydantic API models"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: upload the fixture CSV and confirm the table matches (US1 Independent Test)
5. Demo if ready — export (US2) can follow as the next increment

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 → validate independently → demo (upload + review only)
3. Add User Story 2 → validate independently → demo (adds export)
4. Add User Story 3 → validate independently → demo (adds error resilience/UX)
5. Polish

---

## Notes

- 30 tasks total: 3 Setup, 5 Foundational, 7 US1, 7 US2, 5 US3, 3 Polish
- `[P]` tasks touch different files with no incomplete-task dependency
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing

**Progress (2026-07-05)**: Phases 1–3 (T001–T015) implemented and checked off — Setup, Foundational, and User Story 1 (upload + review) are done, tested (8 new backend tests passing, no regressions in the existing suite), and lint/type-clean.

**Progress (2026-07-05, cont'd)**: Phase 4 (T016–T022) implemented and checked off — User Story 2 (Google Sheets export). `GSheetClient` gained a `trade_republic_sheet_name` constructor param and `append_etf_dca_rows` (single batched `values.append` call, FR-013 column mapping, `Total`/`Total TTC` as formulas). The frontend gained row-selection checkboxes and an Export button (disabled with no selection). 14 new backend tests total for this phase, all passing; full suite still shows only the same 14 pre-existing unrelated failures. Phase 5 (invalid-input UX) and Phase 6 (polish) remain.

**Correction (2026-07-05, PR #620 review)**: The trader confirmed the full set of CSV `type` values (`BUY`, `SELL`, `TRANSFER_INBOUND`, `DIVIDEND`, `INTEREST_PAYMENT`, `IPO_SUBSCRIPTION`) and specified that `Sens` should map `BUY`→`Achat`, `SELL`→`Vente`, and blank for the other four — not derived from the sign of `amount` as originally implemented. Fixed in `GSheetClient._generate_etf_dca_row` (`ETF_DCA_SENS_MAP`); spec.md FR-013/Assumptions and research.md §6 updated to match. Tests updated/added accordingly.
