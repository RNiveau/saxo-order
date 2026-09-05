---
description: "Task list for 030-mcp-asset-analysis"
---

# Tasks: Local MCP Server for Asset Analysis

**Input**: Design documents from `/specs/030-mcp-asset-analysis/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tools.md
**Branch**: `claude/local-mcp-asset-analysis-ek8xag` (run speckit scripts with `SPECIFY_FEATURE=030-mcp-asset-analysis`)

**Tests**: INCLUDED. Not a TDD preference — the constitution's Testing Standards require them, and two acceptance criteria are only verifiable by test: **SC-004** (alert store byte-identical after detection) and **SC-003** (per-indicator failure isolation). Per the constitution, do *not* write tests that merely assert a mock was called.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable — different file, no dependency on an incomplete task
- **[Story]**: US1–US4 (US5 is out of this slice)

## Path Conventions

Backend entry point at repo root: `mcp_server/`, peer to `saxo_order/` and `api/`. Shared logic in `services/`. Tests mirror source under `tests/`.

---

## Phase 1: Setup

**Purpose**: Dependency, entry point and client registration.

- [x] T001 Add `mcp` to `[tool.poetry.dependencies]` in `pyproject.toml` and run `poetry lock`
- [x] T002 Add `k-mcp = "mcp_server.server:main"` to `[tool.poetry.scripts]` in `pyproject.toml`
- [x] T003 [P] Create `.mcp.json` at repo root registering server `saxo-analysis` as `poetry run k-mcp` (per contracts/tools.md)
- [x] T004 [P] Create package skeleton: `mcp_server/__init__.py`, `mcp_server/tools/__init__.py`, `tests/mcp_server/__init__.py`, `tests/mcp_server/tools/__init__.py`

---

## Phase 2: Foundational (BLOCKING — no user story can start until this completes)

**Purpose**: The Phase 0 findings every tool depends on, plus the three helper extractions that make full scan parity (SC-006) reachable.

### Prerequisite corrections to existing code

- [x] T005 Replace the three `print()` calls with `self.logger` calls in `client/saxo_client.py` at lines 263, 595 and 614 — stdout is the MCP protocol wire (research.md §3). No behaviour change; the two rate-limiting prints become `logger.warning`
- [x] T006 Extract `_build_candles` (`saxo_order/commands/alerting.py:721`) into `services/candle_source.py` as `build_daily_series`, parameterised by `asset_type: AssetType` and `market: Market` (defaults preserving today's behaviour: `AssetType.STOCK`, `EUMarket()`). Keep the `1440 count=250` + `60 count=10` top-up shape exactly (research.md §10)
- [x] T007 Extract `_build_weekly_candles` (`alerting.py:751`) into `services/candle_source.py` as `build_weekly_series`, parameterised by `asset_type`, taking the already-fetched daily candles so the forming week is still assembled from them rather than bought again. **Preserve its docstring** — it independently argues the same case as research.md §10 against `CandlesService.build_weekly_candles` (three requests per asset vs. one)
- [x] T008 Extract `_run_congestion_indicator` (`alerting.py:659`) into `services/detection_service.py`, keeping the `(alert_type, length, minimal_touch_points)` table — `(CONGESTION20, 20, 2)`, `(CONGESTION100, 100, 3)` — as a module constant so both callers drive it identically
- [x] T009 Extract `_run_double_top` (`alerting.py:675`) and `_run_double_bottom` (`:698`) into `services/detection_service.py`, parameterised by `asset_type` instead of the hardcoded `AssetType.STOCK` at `:680`/`:703`. **Preserve both behaviours that live only in these wrappers**: the tick lookup (`get_asset_detail` + `client_helper.get_tick_size`, defaulting to `0.0` when the asset has no `TickSizeScheme`) and the **2-day recency filter** — without it a double top from three weeks ago reports as a current hit that the scan would never have alerted on
- [x] T010 Rewire `saxo_order/commands/alerting.py` to call `services/candle_source.py` and `services/detection_service.py`, deleting the five local helpers. Scan behaviour MUST be unchanged
- [x] T011 Prove T006–T010 changed nothing: `poetry run pytest tests/ -k "alerting or congestion or double" -v`

### New shared vocabulary

- [x] T012 [P] Add `Provenance` (`LIVE`, `SIMULATED`), `IndicatorName` (MM7/MM20/MM50/MM200 + their `_SLOPE` variants, `BOLLINGER`, `ATR`, `ADX`, `MACD0LAG`) and `MarketName` (`EU`, `US` only — `DaxCfdMarket`/`EuCfdMarket` exist for the backtest engine's CFD windows and no analysis path uses them, so listing them would put dead ends in the tool schema) to `model/enum.py`, all extending `EnumWithGetValue`

### Server foundation

- [x] T013 Create `mcp_server/dependencies.py`: `resolve_market_client() -> tuple[SaxoClient | MockSaxoClient, Provenance]` returning provenance explicitly. Do NOT reuse `api/dependencies.get_saxo_client` and do NOT apply `@lru_cache()` — provenance must be re-evaluated per request so a mid-session token expiry is caught (research.md §5)
- [x] T014 Add the DynamoDB lifespan to `mcp_server/dependencies.py`: one `aioboto3` resource held for the server's lifetime feeding a single `DynamoDBClient`, modelled on `saxo_order/async_utils.create_dynamodb_client` but not per-call (research.md §7)
- [x] T015 Create `mcp_server/errors.py` with the `@tool_boundary` decorator: translate `SaxoException` and client errors to `ToolError` (import from `mcp.server.mcpserver.exceptions` — it is **not** re-exported from `mcp.server`). Do not blanket-catch `ValueError`: inside a pydantic validator it is already an anticipated argument-validation failure that keeps its message (unhandled exceptions are masked by the SDK as `Error executing tool <name>` — research.md §2), and enforce the simulated-data refusal (FR-004a) so no individual tool can forget it
- [x] T016 [P] Create `mcp_server/models.py` with `ResponseMeta`, `InstrumentRef`, `BarSeries`, `IndicatorValue`, `IndicatorSnapshot`, `PatternHit`, `DetectorFailure`, `DetectionResult`, `StoredAlert`, `DigestEntry`, `AssetContext` per data-model.md. Every asset-bearing model carries an explicit `exchange: Exchange` (Constitution V.4)
- [x] T017 [P] Create `mcp_server/formatters.py`: `Candle` list → columnar `{columns, rows}` newest-first, 4dp rounding, bar cap + truncation flag
- [x] T018 Create `mcp_server/server.py` with the `MCPServer` instance, the DynamoDB lifespan wiring and `main()` calling `mcp.run()` under a `if __name__ == "__main__":` guard; zero tools registered yet
- [x] T019 [P] Test `@tool_boundary` in `tests/mcp_server/test_errors.py`: a `SaxoException` surfaces as a readable `ToolError`; a simulated-provenance call without `allow_simulated` is refused; with `allow_simulated=True` it proceeds
- [x] T020 [P] Test `mcp_server/formatters.py` in `tests/mcp_server/test_formatters.py`: newest-first ordering preserved (Constitution V.1), rounding, cap and truncation flag
- [x] T021 Verify the server boots and answers an MCP client with an empty tool list: `poetry run k-mcp`

**Checkpoint**: server runs, errors translate, provenance gates, scan helpers are shared. User stories may now start.

---

## Phase 3: User Story 1 — Resolve an asset and read its state (P1) 🎯 MVP

**Goal**: Plain name → resolved instrument → full technical state in one exchange.

**Independent test**: ask for a known asset by name only; indicator values match the web UI for the same asset and period.

- [ ] T022 [P] [US1] Implement `search_asset` in `mcp_server/tools/assets.py` per contracts/tools.md — `SaxoClient.search` via `asyncio.to_thread` (research.md §4). Catch the zero-result `SaxoException` from `saxo_client.py:125` explicitly and return `[]`, so "no match" stays distinct from "venue unreachable". Return `asset_type` and `exchange` on every candidate; a candidate without `instrument_id` is returned with `unavailable_reason`, never dropped by *this* layer
- [ ] T023 [US1] Create `services/indicator_bundle_service.py` with the depth registry: each `IndicatorName` → `(minimum_bars, callable)` over existing `services/indicator_service.py` functions. `macd0lag` = 235 (guard at `indicator_service.py:577`), `mobile_average(200)` = 200, `mobile_average(7)` = 7 (research.md §6). Reimplement no calculation
- [ ] T024 [US1] Add `compute_bundle(candles, requested)` to `services/indicator_bundle_service.py`: fetch depth is `max(minimum_bars)` over the **requested** set only (FR-010/FR-012); each indicator computed in its own `try/except` recording `unavailable_reason` on failure; raise only when **every** indicator is unavailable (FR-011)
- [ ] T025 [US1] Implement `get_indicators` in `mcp_server/tools/indicators.py`: takes `instrument_id`, `asset_type`, `unit_time`, `include`, `exchange`, `market`, `allow_simulated`; sources candles via `services/candle_source.py` (NOT `CandlesService` — research.md §10); returns `IndicatorSnapshot` with `provenance`, `last_bar_date` and `bars_fetched`. `include=[]` raises `ToolError`
- [ ] T026 [US1] Register `search_asset` and `get_indicators` on the server in `mcp_server/server.py`, both wrapped in `@tool_boundary`
- [ ] T027 [P] [US1] Test `search_asset` in `tests/mcp_server/tools/test_assets.py` with a mocked `SaxoClient`: multiple candidates returned with `exchange` and `asset_type`; zero results → `[]` not an error; candidate lacking `instrument_id` carries `unavailable_reason`
- [ ] T028 [P] [US1] Test the depth registry in `tests/services/test_indicator_bundle_service.py`: requesting only `MM7` computes a depth of 7, not 235 (SC-002); requesting `MACD0LAG` computes 235
- [ ] T029 [P] [US1] Test isolation in `tests/services/test_indicator_bundle_service.py` with an 80-bar series: MM7/MM20/MM50 return values, MM200 and MACD0LAG carry `unavailable_reason` naming bars needed vs. available, and the call **succeeds** (SC-003). Assert `len(indicators) == len(requested)` — absence is never expressed by omission
- [ ] T030 [US1] Test in `tests/mcp_server/tools/test_indicators.py` that a snapshot carries `provenance`, `exchange`, `unit_time` and `last_bar_date`, and that one base series fetch plus at most one top-up is issued for a single snapshot (SC-002)

**Checkpoint**: US1 ships alone as a usable MVP.

---

## Phase 4: User Story 2 — Inspect the bars (P2)

**Goal**: see the price action behind the indicators.

**Independent test**: bars for a known instrument match its chart, including the in-progress period.

- [ ] T031 [US2] Implement `get_candles` in `mcp_server/tools/assets.py` per contracts/tools.md: newest-first columnar rows via `mcp_server/formatters.py`, `current_incomplete` flag, cap + `meta.truncated`. Where the market cannot be determined, **skip** the current-period top-up and report `current_incomplete = False` rather than assembling today's bar against guessed session hours (research.md §10)
- [ ] T032 [US2] Register `get_candles` in `mcp_server/server.py` with `@tool_boundary`
- [ ] T033 [P] [US2] Test `get_candles` in `tests/mcp_server/tools/test_assets.py`: newest-first ordering; in-progress period present and flagged; `count` above the cap sets `meta.truncated`; empty history returns `count=0` not an error; undeterminable market skips the top-up

---

## Phase 5: User Story 3 — On-demand setup detection (P2)

**Goal**: run the project's own detectors without touching the alert store, at **full parity** with the scheduled scan.

**Independent test**: an asset that triggered in the scheduled scan reports the same setups — and the store is unchanged afterwards.

> **Coverage is the point of this phase.** `hits = []` is specified as a confident "nothing is firing" (Story 3, scenario 3), so a setup this tool cannot see becomes a false negative rather than a gap — worse than an error, and a direct contradiction of SC-006. The scan emits **ten** `AlertType`s; all ten must be reachable here.

- [ ] T034 [US3] Extend `services/detection_service.py` with the remaining detectors. Only four are direct `indicator_service` calls — `combo`, `mm7_break`, `mm50_touch`, `containing_candle`. `double_top`/`double_bottom` go through the wrappers extracted in T009 (they need a tick and the 2-day recency filter), and `double_inside_bar` returns **`bool`** (`indicator_service.py:774`), so it needs the wrapper's `candles[0]` adaptation to build a `PatternHit`. **Do NOT import `run_detection_for_asset`** — it persists via `store_alerts` (research.md §8). Each detector runs in its own `try/except`; a raising detector lands in `failed` with a reason, never dropped from `evaluated`. Note `inside_bar` is *not* in this list: it is a helper for `double_inside_bar` (`indicator_service.py:762`/`:774`) and maps to no `AlertType`
- [ ] T035 [US3] Add `CONGESTION20` and `CONGESTION100` to `services/detection_service.py`, driving the table extracted in T008 through `congestion_indicator.calculate_congestion_indicator`
- [ ] T036 [US3] Add `COMBO_WEEKLY` to `services/detection_service.py`: build the weekly series via `services/candle_source.build_weekly_series` (T007) from the daily candles already held, then run `indicator_service.combo` with `COMBO_SETTINGS[UnitTime.W]` — **not** the daily settings (`alerting.py:386`). This costs one extra provider series fetch. Together with the per-detection `get_asset_detail` call the double-top/bottom tick lookup needs (T009), the detection path's request accounting is **not** just the two series — record all of it
- [ ] T037 [US3] Implement `detect_patterns` in `mcp_server/tools/detection.py` returning `DetectionResult` with `hits`, `evaluated` and `failed`, using the existing `AlertType`/`Direction` vocabulary (FR-014). `evaluated` MUST list all ten types when the full set is requested
- [ ] T038 [US3] Register `detect_patterns` in `mcp_server/server.py` with `@tool_boundary`
- [ ] T039 [US3] **SC-004 test** in `tests/mcp_server/tools/test_detection.py`: snapshot a mocked alert store, call `detect_patterns` repeatedly, assert the store is byte-identical afterwards and that no write method was reachable
- [ ] T040 [P] [US3] **SC-006 parity test** in `tests/services/test_detection_service.py`: assert the set of `AlertType`s this service can emit equals the set `run_detection_for_asset` emits — enumerated from `model.enum.AlertType`, so a new alert type added to the scan later fails this test instead of silently becoming a false negative. Add a comment in the test recording that this enumeration is valid because all ten enum members are currently emitted by the scan — the assertion depends on that and should say so
- [ ] T041 [P] [US3] Test in `tests/services/test_detection_service.py`: a series with a known setup reports it with direction and supporting values; a series with none returns `hits=[]` with `evaluated` populated (distinct from failure); a raising detector appears in `failed` with a reason while the others still return

---

## Phase 6: User Story 4 — Past alerts and current exposure (P3)

**Goal**: explain why something fired and whether it is already held.

**Independent test**: for a date with stored alerts, the answer cites the stored data plus watchlist labels and open workflow orders.

- [ ] T042 [P] [US4] Implement `get_alerts` and `get_digest` in `mcp_server/tools/context.py` (guard `ServerContext.dynamodb is None` first — see T045). **Call `DynamoDBClient` methods only** — add methods there if one is missing, never reach for the resource or a table. The free-form `data` map passes through unchanged. No alerts for a date → `[]`; no digest → `None`. Both distinct from failure
- [ ] T043 [P] [US4] Implement `get_watchlist` and `get_workflow_orders` in `mcp_server/tools/context.py` (guard `ServerContext.dynamodb is None` first — see T045), through `DynamoDBClient` methods only. An asset in neither returns `in_watchlist=False` with empty lists — never an error (Constitution I)
- [ ] T044 [US4] Register the four context tools in `mcp_server/server.py` with `@tool_boundary`
- [ ] T045 [US4] Make the stored-context tools degrade independently: with DynamoDB unreachable they raise a `ToolError` naming the cause while the market-data tools keep working (spec edge case). **Each stored-context tool MUST check `ServerContext.dynamodb is not None` and answer "unavailable" itself** — `_get_table` raises a bare `RuntimeError` for a client with no resource, which `@tool_boundary` deliberately does not soften, so relying on the boundary here would surface the opaque `Error executing tool <name>`
- [ ] T046 [P] [US4] Test in `tests/mcp_server/tools/test_context.py` with a mocked `DynamoDBClient`: alerts returned with their `data` map intact; an unknown asset returns the explicit not-held result; an unreachable store fails without affecting market-data tools

---

## Phase 7: Polish & Cross-Cutting

- [ ] T047 Measure SC-007 against a real asset: snapshot < 2,000 tokens, capped bar series < 3,000. Tune the bar cap constant in `mcp_server/formatters.py` if exceeded
- [ ] T048 [P] Walk `specs/030-mcp-asset-analysis/quickstart.md` end to end from an MCP client in this repo, confirming all four story checks and every troubleshooting row
- [ ] T049 Verify FR-002 by inspection: grep `mcp_server/` for any write/store/put/set call and confirm none exists
- [ ] T050 Run the full gate: `poetry run black .`, `poetry run isort .`, `poetry run mypy .`, `poetry run flake8`, `poetry run pytest --cov`
- [ ] T051 Update `README.md` with a short "MCP server" section pointing at quickstart.md

---

## Dependencies

```text
Phase 1 (Setup)
   ↓
Phase 2 (Foundational) ─── BLOCKING
   ↓
   ├─→ Phase 3 (US1, P1) ─── MVP
   │        ↓
   │   ┌────┴────┐
   │   ↓         ↓
   ├─→ Phase 4  Phase 5      (US2 and US3 are independent of each other)
   │   (US2,P2) (US3,P2)
   │
   └─→ Phase 6 (US4, P3)     (needs only Phase 2 — no market data)
                ↓
           Phase 7 (Polish)
```

**Notes on the graph**:

- **US4 does not depend on US1.** Stored-context reads are keyed by date or code and need no instrument resolution, so Phase 6 can run any time after Phase 2 — useful if a Saxo token is unavailable.
- **US2 and US3 both build on US1's candle sourcing** but not on each other.
- **T005–T011 gate everything.** They touch existing code; landing them first keeps the scan-behaviour proof (T011) separate from new-feature noise.

### Within-phase ordering

- T006, T007, T008 → T010 → T011 strictly sequential (extract ×3, rewire, prove).
- T023 → T024 → T025 sequential (registry, then computation, then tool).
- T034 → T035 → T036 → T037 sequential (all edit `services/detection_service.py`, then the tool).
- Registration tasks (T026, T032, T038, T044) all edit `mcp_server/server.py` — never parallel with each other.

### Parallel opportunities

- **Phase 1**: T003, T004
- **Phase 2**: T006 ∥ T007 (candle_source) and T008 ∥ T009 (detection_service) — one rewire after; T012, T016, T017; then T019, T020
- **Phase 3**: T022 ∥ T023; then T027, T028, T029 together
- **Phase 5**: T040 ∥ T041
- **Phase 6**: T042 ∥ T043

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3.** That delivers name → resolved instrument → full technical state, which is the workflow that currently requires a throwaway script. Everything after it is additive.

Suggested increments:

1. **Increment 1** (T001–T030): MVP. Stop here and use it for a few days before building more — the tool granularity is the riskiest guess in this design, and real use is the only way to find out whether one bundled snapshot is the right shape.
2. **Increment 2** (T031–T041): bars and detection. US2 and US3 can land in either order.
3. **Increment 3** (T042–T046): stored context.
4. **Increment 4** (T047–T051): polish.

**Out of this slice**: User Story 5 (Ouinex). Its seam is the market-data boundary in `services/candle_source.py` plus resolution in `mcp_server/tools/assets.py`; no abstraction is built for it now (research.md §9).

---

## Task Summary

| Phase | Story | Tasks | Count |
|---|---|---|---|
| 1 Setup | — | T001–T004 | 4 |
| 2 Foundational | — | T005–T021 | 17 |
| 3 | US1 (P1) | T022–T030 | 9 |
| 4 | US2 (P2) | T031–T033 | 3 |
| 5 | US3 (P2) | T034–T041 | 8 |
| 6 | US4 (P3) | T042–T046 | 5 |
| 7 Polish | — | T047–T051 | 5 |
| **Total** | | | **51** |

Phase 2 is large because seven of its tasks (T005–T011) correct and consolidate existing code before any new code depends on it: the stdout hazard, and **five** helpers that had to move out of `alerting.py` so the scan and the MCP server share one implementation rather than two that can drift. Two of those five (`_run_double_top`/`_run_double_bottom`) carry a tick lookup and a 2-day recency filter that exist nowhere else — calling `indicator_service.double_top` directly would silently widen what counts as a hit.
