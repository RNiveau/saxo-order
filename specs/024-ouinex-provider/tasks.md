---

description: "Task list for Ouinex crypto provider implementation"
---

# Tasks: Ouinex crypto provider

**Input**: Design documents from `/specs/024-ouinex-provider/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-deltas.md

**Tests**: Included — the project constitution mandates pytest coverage and `contracts/api-deltas.md` defines contract tests. Mock the Ouinex client; do NOT test mocks (per CLAUDE.md).

**Organization**: Tasks are grouped by user story (US1–US4) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3, US4 (from spec.md)

## Path Conventions

Web app with existing layout: backend Client `client/`, Services `api/services/`, Routers `api/routers/`, Models `model/`, Config `utils/`, CLI `saxo_order/commands/`, Frontend `frontend/src/`, Tests `tests/` (mirrors source).

---

## ⚠️ Blocking research items (resolve before US3/US4 implementation)

These come from `research.md` and gate specific stories. They are not code tasks but MUST be answered:

- **R1 (blocks US3)**: Confirm a Ouinex GraphQL **query** returns historical bars for an instrument+periodicity+range (not just the WS subscription). If only the subscription exists, US3 is blocked — escalate.
- **R2 (US3)**: Confirm weekly/monthly periodicity, else aggregate from daily.
- **R3 (US4)**: Confirm `closed_orders`/`account_transactions` field shapes (symbol, side, price, qty, fee, timestamp, quote currency).
- **R4 (Foundational)**: Confirm JWT sign-in mutation, token lifetime/refresh, and whether HMAC signing is required.
- **R5 (US2/US3)**: Confirm instrument identifier model (numeric `instrument_id` vs symbol) and mapping to the `code`/`symbol` used across the app.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and configuration surface for Ouinex

- [ ] T001 [P] Verify/add an HTTP client capable of GraphQL POST (prefer existing `requests`; add `httpx` via `poetry add httpx` only if async WS work is needed) in `pyproject.toml`
- [ ] T002 [P] Add `ouinex_graphql_url` (default `https://live-api.ouinex.com/graphql`) to `config.yml` and document `ouinex_api_key` / `ouinex_secret_key` in the secrets template (`secrets.yml` is gitignored)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core enum, config, client transport, and DI that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add `OUINEX = "ouinex"` to the `Exchange` enum in `model/enum.py`
- [ ] T004 [P] Add an explicit crypto-exchange helper (e.g., `Exchange.is_crypto()` returning True for `BINANCE`/`OUINEX`) in `model/enum.py` to avoid scattered `in (BINANCE, OUINEX)` checks
- [ ] T005 [P] Add `ouinex_keys` (tuple from `secrets["ouinex_api_key"]`, `secrets["ouinex_secret_key"]`) and `ouinex_graphql_url` properties to `utils/configuration.py`
- [ ] T006 Create `client/ouinex_client.py` with the GraphQL transport (`POST` to `ouinex_graphql_url`) and private JWT sign-in/refresh helpers (resolves R4); constructor signature `OuinexClient(key: str, secret: str, graphql_url: str)`
- [ ] T007 [P] Extract the Binance pseudo-account into a single shared factory (e.g., `crypto_account()` returning `Account(key="binance", name="Coinbase", fund=0, client_key="binance")`) and refactor `BinanceReportService._get_binance_account` to use it — this is the single source of truth for the "map as binance" identity
- [ ] T008 Add `get_ouinex_client()` (cached) to `api/dependencies.py`, reading `config.ouinex_keys` and `config.ouinex_graphql_url`
- [ ] T009 [P] Add `tests/client/test_ouinex_client.py` skeleton with a mocked GraphQL transport fixture (shared by later client tests)

**Checkpoint**: Enum, config, client transport/auth, and DI ready — user stories can begin

---

## Phase 3: User Story 1 - Recognize Ouinex as a selectable crypto provider (Priority: P1) 🎯 MVP

**Goal**: Ouinex is offered wherever Binance is, and actions use Ouinex credentials (not Binance).

**Independent Test**: `GET /api/fund/accounts` returns an `ouinex_main` account alongside `binance_main`; `Exchange.get_value("ouinex")` resolves; homepage maps `"ouinex"` → `Exchange.OUINEX`.

### Tests for User Story 1

- [ ] T010 [P] [US1] Contract test in `tests/api/routers/test_fund.py`: `/api/fund/accounts` includes `ouinex_main` (account_key `ouinex`, name `Ouinex`) and still includes `binance_main`
- [ ] T011 [P] [US1] Unit test in `tests/model/test_enum.py`: `Exchange.get_value("ouinex") == Exchange.OUINEX` and `Exchange.OUINEX.is_crypto()` is True

### Implementation for User Story 1

- [ ] T012 [US1] Add the `ouinex_main` pseudo-account (`account_id="ouinex_main"`, `account_key="ouinex"`, `account_name="Ouinex"`, funds 0) to the account list in `api/routers/fund.py`
- [ ] T013 [US1] Map `exchange_str == "ouinex"` → `Exchange.OUINEX` in `api/routers/homepage.py` (use the crypto helper where a binance branch exists)

**Checkpoint**: Ouinex is a recognized, selectable provider end-to-end (accounts + enum + homepage)

---

## Phase 4: User Story 2 - Search and add Ouinex crypto instruments to the watchlist (Priority: P1)

**Goal**: Search Ouinex instruments and add them to the watchlist, classified as crypto like Binance.

**Independent Test**: `GET /api/search?keyword=btc` returns items with `exchange: "ouinex"`; adding one stores it as crypto (USD, crypto tag); a Ouinex client error still returns Saxo/Binance results.

### Tests for User Story 2

- [ ] T014 [P] [US2] Contract test in `tests/api/routers/test_search.py`: results include an `exchange == "ouinex"` item; when the Ouinex client raises, Saxo/Binance results are still returned (FR-012)
- [ ] T015 [P] [US2] Unit test in `tests/client/test_ouinex_client.py`: `search()` returns `Asset` objects with `exchange=Exchange.OUINEX`, `asset_type=AssetType.CRYPTO`
- [ ] T016 [P] [US2] Unit test in `tests/api/services/test_watchlist_service.py`: a `"ouinex"` exchange item is tagged crypto and priced in USD (resolves R5 symbol handling)

### Implementation for User Story 2

- [ ] T017 [US2] Implement `OuinexClient.search(keyword)` in `client/ouinex_client.py` via the `instruments` GraphQL query with client-side keyword filtering, returning `Asset(exchange=Exchange.OUINEX, asset_type=AssetType.CRYPTO)` (resolves R5)
- [ ] T018 [US2] Inject the Ouinex client and include its results in `api/services/search_service.py` (own try/except so one provider failing does not break others)
- [ ] T019 [US2] Add `binance_client`/`ouinex_client` wiring for search in `api/routers/search.py` (inject `get_ouinex_client`, pass into `SearchService`)
- [ ] T020 [US2] Treat `exchange == "ouinex"` like `"binance"` (crypto tag, USD, indicator-based price) in `api/services/watchlist_service.py`
- [ ] T021 [P] [US2] Add a `.exchange-badge.ouinex` style in `frontend/src/pages/SearchResults.css` (cosmetic parity with the binance badge)

**Checkpoint**: Ouinex instruments are searchable and watch-listable as crypto

---

## Phase 5: User Story 3 - Retrieve Ouinex market data for indicators and alerts (Priority: P2)

**Goal**: Indicators for Ouinex instruments computed from Ouinex candles, matching Binance behavior.

**Independent Test**: `GET /api/indicator/asset/{symbol}?exchange=ouinex&unit_time=daily` returns MAs (7/20/50/200), current price, and variation.

> ⚠️ Gated by **R1** (historical-bars query). Do not start T024+ until R1 is confirmed. Alerts remain a no-op for crypto (parity with Binance — see plan Scope notes); no alert task is generated.

### Tests for User Story 3

- [ ] T022 [P] [US3] Unit test in `tests/client/test_ouinex_client.py`: `get_candles()` returns `Candle` list ordered newest-first (index 0 = latest), prices rounded, correct `ut`
- [ ] T023 [P] [US3] Contract test in `tests/api/routers/test_indicator.py`: `exchange=ouinex` dispatches to the Ouinex candle path and yields a valid `AssetIndicatorsResponse`

### Implementation for User Story 3

- [ ] T024 [US3] Implement `OuinexClient.get_candles(symbol, unit_time, limit=200)` and `get_latest_candle(symbol)` in `client/ouinex_client.py`, including the `UnitTime`→periodicity map and bar→`Candle` mapping (newest-first ordering per Constitution V.1); handle weekly/monthly per R2
- [ ] T025 [US3] Route `Exchange.OUINEX` to the Ouinex candle path in `api/services/indicator_service.py` (accept the Ouinex client in the constructor; add a `_get_ouinex_asset_indicators` or generalize `_get_binance_asset_indicators` to take the crypto client)
- [ ] T026 [US3] Inject the Ouinex client and pass it through in `api/routers/indicator.py`; ensure `exchange=ouinex` is accepted (validate via `Exchange.get_value`)
- [ ] T027 [US3] Reconstruct the in-progress current day/hour candle for Ouinex from a smaller periodicity where the provider omits it, consistent with the Binance/Saxo pattern (Constitution V.2, FR-006)

**Checkpoint**: Ouinex indicators work across supported timeframes

---

## Phase 6: User Story 4 - Report Ouinex trading activity into the journal as Binance (Priority: P2)

**Goal**: Report Ouinex trades and write them to the Google Sheet under the Binance identity.

**Independent Test**: `GET /api/report/orders?account_id=ouinex_main&from_date=...` returns Ouinex trades; writing one to the sheet passes an `Account` with `name="Coinbase"`, `key="binance"` — indistinguishable from a Binance row (SC-002).

> ⚠️ Trade-field mapping gated by **R3**.

### Tests for User Story 4

- [ ] T028 [P] [US4] Unit test in `tests/client/test_ouinex_client.py`: `get_report`/`get_report_all` map Ouinex trades to `ReportOrder` (`asset_type=CRYPTO`, currency, direction, commission)
- [ ] T029 [P] [US4] Behavior test in `tests/api/services/test_ouinex_report_service.py`: `create_gsheet_order` passes an `Account` equal to the Binance pseudo-account (`name="Coinbase"`, `key="binance"`) to `GSheetClient.create_order` — the "map as binance" guarantee
- [ ] T030 [P] [US4] Contract test in `tests/api/routers/test_report.py`: `account_id="ouinex_main"` selects `OuinexReportService`; `binance_main` still selects `BinanceReportService`

### Implementation for User Story 4

- [ ] T031 [US4] Implement `OuinexClient.get_report(symbol, date, usdeur_rate)` and `get_report_all(date, usdeur_rate)` in `client/ouinex_client.py` via `closed_orders`/`account_transactions`, mapping to `ReportOrder` with commission handling (resolves R3)
- [ ] T032 [US4] Create `api/services/ouinex_report_service.py` mirroring `BinanceReportService` (TTLCache 128/300s; `get_orders_report`, `convert_order_to_eur`, `calculate_summary`, `create_gsheet_order`, `update_gsheet_order`) and use the shared crypto-account factory from T007 for all gsheet writes
- [ ] T033 [US4] Add `get_ouinex_report_service()` to `api/dependencies.py`
- [ ] T034 [US4] Route `account_id.startswith("ouinex_")` → `OuinexReportService` in all four handlers of `api/routers/report.py` (orders, summary, gsheet/create, gsheet/update); inject the new service dependency
- [ ] T035 [P] [US4] (Optional) Add a `saxo_order/commands/ouinex.py` CLI report command mirroring `saxo_order/commands/binance.py`, and register it in `saxo_order/commands/k_order.py`

**Checkpoint**: Ouinex trades report and write to the journal under the Binance identity

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verification and quality gates across all stories

- [ ] T036 [P] Run quality gates: `poetry run black . && poetry run isort . && poetry run mypy . && poetry run flake8`
- [ ] T037 [P] Run backend tests: `poetry run pytest tests/client/test_ouinex_client.py tests/api/services/test_ouinex_report_service.py` and the modified router tests
- [ ] T038 [P] Frontend build check: `cd frontend && npm run build`
- [ ] T039 Execute `specs/024-ouinex-provider/quickstart.md` end-to-end (accounts, search, indicators, report-as-binance, failure isolation)
- [ ] T040 Update `README.md` provider list to mention Ouinex (crypto, reported under Binance identity)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)**: No dependencies
- **Foundational (P2)**: Depends on Setup — BLOCKS all user stories (enum, config, client transport/auth, DI, shared account factory)
- **US1 (P3)**: After Foundational
- **US2 (P4)**: After Foundational (adds `OuinexClient.search`)
- **US3 (P5)**: After Foundational + research **R1** confirmed (adds `OuinexClient.get_candles`)
- **US4 (P6)**: After Foundational + research **R3** (adds report methods + service); reuses T007 account factory
- **Polish (P7)**: After the desired stories

### User Story Dependencies

- US1, US2, US3, US4 are independently testable and share only the foundational `OuinexClient`.
- US2/US3/US4 each add a distinct method to `OuinexClient` (`search` / `get_candles` / `get_report*`) plus their own routing — no cross-story code dependency.
- US4 depends on the shared crypto-account factory (T007, Foundational), not on US1–US3.

### Within Each User Story

- Tests written first and failing → client method → service → router → frontend/CLI.

### Parallel Opportunities

- Setup: T001, T002 in parallel.
- Foundational: T004, T005, T007, T009 in parallel (T003 before T004; T006 before T008).
- Once Foundational is done, US1/US2/US3/US4 can proceed in parallel (different files), subject to R1/R3 for US3/US4.
- All `[P]` test tasks within a story run in parallel.

---

## Parallel Example: User Story 2

```bash
# Tests first (parallel):
Task: "Contract test /api/search includes ouinex in tests/api/routers/test_search.py"   # T014
Task: "OuinexClient.search unit test in tests/client/test_ouinex_client.py"              # T015
Task: "watchlist crypto-tag test in tests/api/services/test_watchlist_service.py"        # T016

# Then implementation (T017 → T018 → T019, T020; T021 parallel):
Task: "Implement OuinexClient.search in client/ouinex_client.py"                          # T017
Task: "Add .exchange-badge.ouinex in frontend/src/pages/SearchResults.css"               # T021 [P]
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 Setup → Phase 2 Foundational (critical).
2. US1 (provider selectable) → validate `/api/fund/accounts`.
3. US2 (search + watchlist) → validate a Ouinex instrument is searchable and watch-listable.
4. STOP and demo: Ouinex is a usable crypto provider for tracking.

### Incremental Delivery

- US3 (indicators) once R1 is confirmed.
- US4 (report-as-binance) once R3 is confirmed — delivers the headline "map as binance" behavior.
- Each story ships independently without breaking Binance/Saxo (FR-013).

---

## Notes

- `[P]` = different files, no dependencies.
- Do NOT test mocks — assert real mapping/behavior (CLAUDE.md).
- Every Ouinex op requires credentials (Clarifications); missing keys must fail Ouinex-only, never Saxo/Binance (FR-012).
- Alerts: no crypto detection is built — faithful parity with Binance (plan Scope notes).
- Order execution: out of scope (FR-014).
- Commit after each task or logical group; keep Binance paths byte-for-byte unchanged (SC-004).
