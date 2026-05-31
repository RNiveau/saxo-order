# Phase 0 Research: Saxo Order Reporting

**Status**: Retroactive — decisions documented from the existing implementation.

This file captures the design decisions that shaped the Saxo reporting feature. There were no open `[NEEDS CLARIFICATION]` markers in the spec, so the research below is a reverse-engineered decision log rather than a forward investigation.

---

## Decision 1 — Where business logic lives: a dedicated `ReportService`

- **Decision**: Put period fetch, EUR conversion, summary aggregation, and Google Sheets journal writes in a single `ReportService` in `api/services/report_service.py`. The API router stays thin; the CLI calls the same underlying client + helper functions.
- **Rationale**: The constitution forbids business logic in the CLI and the router layers. Centralising the orchestration in a service keeps the CLI and API equivalent and makes the later Binance backport straightforward (`BinanceReportService` mirrors the same shape).
- **Alternatives considered**:
  - *Logic in the router.* Rejected — violates §I Layered Architecture Discipline.
  - *Logic in the CLI, called by the router.* Rejected — pulls the API into a Click-shaped surface and makes testing awkward.
  - *Logic in `client/saxo_client.py`.* Rejected — clients must not contain business logic per the constitution.

## Decision 2 — Single report endpoint with prefix-based account routing

- **Decision**: One set of endpoints (`/api/report/*`) handles all brokers. The router inspects `account_id`: if it starts with `binance_`, delegate to `BinanceReportService`; otherwise delegate to `ReportService` (Saxo).
- **Rationale**: The frontend's `OrderModal` and orders table are platform-agnostic — they only need `account_id` + `from_date`. Per-broker URL spaces would force frontend changes every time a new broker is added.
- **Alternatives considered**:
  - *Separate `/api/saxo-report/*` and `/api/binance-report/*` routers.* Rejected — duplicate code, frontend churn.
  - *Detect broker from asset metadata (e.g. `country_code`).* Rejected — explicitly forbidden by §V (a Saxo asset can lack `country_code`).

## Decision 3 — 5-minute TTL cache on report fetches

- **Decision**: `ReportService` wraps `get_orders_report` and `_find_account` with `cachetools.TTLCache(maxsize=128, ttl=300)` via `@cachedmethod`.
- **Rationale**: A trader reviewing their journal does not need second-by-second freshness; Saxo's audit endpoint is slow and rate-limited. Five minutes balances responsiveness with cost.
- **Alternatives considered**:
  - *No cache.* Rejected — every UI re-render would hit the broker API.
  - *Longer TTL (e.g. 1 h).* Rejected — surprises the user when an order they just executed isn't visible.
  - *Persistent cache (DynamoDB).* Rejected — adds infra for no user-visible benefit; reports are derived data.

## Decision 4 — Configuration-driven currency conversion

- **Decision**: USD→EUR and JPY→EUR rates live in `config.yml` under `currencies_rate` and are applied by `calculate_currency(order, currencies_rate)` in `saxo_order/service.py`.
- **Rationale**: The journal records prices at the time of trade; live FX would distort the record. Configuration centralises the rate so it can be refreshed out-of-band by the trader.
- **Alternatives considered**:
  - *Live FX from a provider.* Rejected — adds a dependency and changes journal semantics from "trade-time price" to "mark-to-market".
  - *Per-order rate from the broker.* Rejected — Saxo does not consistently return a conversion rate per order.

## Decision 5 — `Strategy` / `Signal` are enums delivered to the UI via `/api/report/config`

- **Decision**: The backend ships the list of valid strategies and signals through `GET /api/report/config`. The frontend renders them as dropdowns.
- **Rationale**: Trade journaling discipline depends on a controlled vocabulary. Letting the user type free-text would let typos accumulate in the journal and break post-trade analysis grouped by strategy.
- **Alternatives considered**:
  - *Hardcode in the frontend.* Rejected — drifts from backend validation; the backend rejects unknown values.
  - *Open free-text field.* Rejected — defeats the purpose of journaling.

## Decision 6 — Manual journal row targeting on updates

- **Decision**: When updating a row in Google Sheets, the user supplies the row number. The service never tries to find the row for an order.
- **Rationale**: There is no stable order↔row mapping (the trader may journal an order more than once, or skip orders). Auto-matching would risk silently overwriting the wrong row.
- **Alternatives considered**:
  - *Auto-match by asset + date.* Rejected — ambiguous when the trader has multiple positions on the same asset.
  - *Maintain a side map of order→row.* Rejected — duplicates Google Sheets as the source of truth.

## Decision 7 — Regulatory taxes only for stocks

- **Decision**: `calculate_taxes(order)` returns `Taxes(cost, taxes)` for stocks (cost = `max(2, total * 0.0008)`, taxes = `0.004 * total`); for other asset types, the journal row has no tax line.
- **Rationale**: Matches the trader's actual tax exposure (French regulatory tax on stock trades). Derivatives and crypto are treated under a different regime not in scope here.
- **Alternatives considered**:
  - *Tax all asset types uniformly.* Rejected — would falsify the journal.
  - *Per-instrument tax rules via config.* Deferred — useful if the trader's regime changes; not needed for current scope.

## Decision 8 — CLI predates the API and stays

- **Decision**: Keep the Click command (`k-order get-report`) functional. It shares `SaxoClient` and `GSheetClient` with the API; the UI flow does not replace it.
- **Rationale**: Existing trader workflows depend on the CLI; deprecating it would break personal scripts. Keeping it also serves as a backstop when the UI is unavailable.
- **Alternatives considered**:
  - *Remove the CLI.* Rejected — breaks existing workflows.
  - *Re-implement the CLI on top of HTTP.* Rejected — adds a network hop for no benefit on the trader's workstation.

---

## Open Items (follow-ups, not blocking)

- No `tests/api/services/test_report_service.py` exists yet. The Binance variant added 12 unit tests as a template; an equivalent Saxo suite is the obvious next step.
- The CLI's interactive update flow and the UI's `OrderModal` have diverged in micro-details (prompt wording, default values). Reconciling them would tighten parity but is cosmetic.
