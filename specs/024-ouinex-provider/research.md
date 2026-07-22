# Phase 0 Research: Ouinex crypto provider

Source: Ouinex API landing (https://api.ouinex.com/, live endpoint https://live-api.ouinex.com/graphql), plus the existing Binance implementation (`client/binance_client.py`, `api/services/binance_report_service.py`) used as the parity baseline.

> ⚠️ The Ouinex API surface below was derived from the public landing page and is **incomplete**. Items marked **VERIFY** must be confirmed against full Ouinex docs (or the Ouinex team) before or during implementation. They do not block planning but shape the task list and risk profile.

---

## Decision 1: Provider modeled as a new `Exchange.OUINEX`, mapped to Binance only at the journal boundary

- **Decision**: Add `Exchange.OUINEX = "ouinex"`. Ouinex flows through search / indicators / watchlist / homepage / reporting as its own exchange (real data source). Only when a trade is written to the Google Sheet does it adopt the Binance pseudo-account identity.
- **Rationale**: Constitution V.4 forbids inferring the source exchange and requires an explicit `exchange` field. Ouinex is a genuinely distinct data source with its own credentials and API, so it must be a distinct enum value. "Map as binance" is a deliberate, explicit mapping at the write boundary — not a reuse of the Binance identity throughout.
- **Alternatives considered**:
  - *Make Ouinex masquerade as `Exchange.BINANCE` everywhere* — rejected: violates V.4 (source inference), and Ouinex candles/search would be indistinguishable from Binance, breaking watchlist provenance and routing.
  - *Fully generic `CryptoProvider` abstraction* — rejected as over-engineering (Principle II); only two crypto providers exist.

## Decision 2: New `OuinexClient` mirroring the `BinanceClient` method surface

- **Decision**: Create `client/ouinex_client.py` exposing the same public methods the rest of the app already depends on:
  - `search(keyword: str) -> List[Asset]` (assets tagged `Exchange.OUINEX`)
  - `get_candles(symbol, unit_time, limit=200) -> List[Candle]` (index 0 = newest)
  - `get_latest_candle(symbol) -> Candle`
  - `get_report_all(date: str, usdeur_rate: float) -> List[ReportOrder]` (+ `get_report` per symbol)
- **Rationale**: Keeps the Service/Router layers unchanged in shape — they already call these method names on `BinanceClient`. Client returns domain models, never raw GraphQL (Principle I, V.3).
- **Alternatives considered**: A shared interface/ABC between the two clients — deferred; duplication of a 4-method surface is cheaper than premature abstraction.

## Decision 3: Ouinex API is GraphQL + JWT (the main divergence from Binance)

- **Findings** (VERIFY):
  - **Transport**: `POST https://live-api.ouinex.com/graphql` with JSON `{query, variables}`. Not REST.
  - **Auth**: JWT bearer token (`Authorization: Bearer <token>`), obtained by signing in with API-key credentials; tokens are short-lived and refreshed by re-signing in. Optional per-key HMAC signing.
  - **Instruments (search)**: GraphQL query `instruments` returning name, base/quote currencies, decimal precision. Client-side keyword filtering (as Binance does over `exchangeInfo`).
  - **Trade history (reporting)**: GraphQL queries `account_transactions` (by `wallet_id`, optional `currency_id`/`dateRange`/`pager`) and `closed_orders` (filter by status/side/date/instrument).
- **Decision**: Implement a thin GraphQL transport in `OuinexClient` (using `httpx` or `requests`) plus a JWT sign-in/refresh helper. Base URL and any non-secret config in `config.yml`; API key/secret in `secrets.yml`.
- **Rationale**: Encapsulate all GraphQL/JWT mechanics inside the Client layer so Services stay transport-agnostic.
- **Dependency choice** (VERIFY): prefer `httpx` if async is desired for the WebSocket path; otherwise `requests` (already used by `BinanceClient.search`). No heavyweight GraphQL SDK — hand-built query strings are sufficient for ~4 operations.

## Decision 4: Historical candles — PRIMARY RISK

- **Finding** (VERIFY): OHLC bars appear to be exposed only via a **WebSocket subscription** `instrument_price_bar` (`wss://live-api.ouinex.com/graphql`) with `instrument_id` + `periodicity`. Supported periodicities observed: **1m, 5m, 15m, 1h, 4h, 1d** — no `1w` / `1M`.
- **Problem**: `get_candles(symbol, unit_time, limit=200)` needs *historical* candles (e.g., last 210 daily candles for MA200). A live subscription streams new bars; it is not a bulk history fetch. Binance solves this trivially with `GET /klines?limit=1000`.
- **Options**:
  - **A (preferred, VERIFY)**: Find a Ouinex GraphQL *query* (not subscription) that returns historical bars for an instrument+periodicity+range. Landing docs are likely incomplete; a `price_bars`/`candles` history query probably exists. Confirm first.
  - **B**: If only the subscription exists, buffer bars from the WS stream — unusable for backfilling 200 historical candles; not viable for indicators.
  - **C**: Derive higher timeframes (4h/1d) by aggregating a lower timeframe history query if only fine granularity is queryable.
- **Decision**: Task list MUST begin with confirming a historical-bars query (Option A). Treat A as the assumption; escalate if only B is available, since that would block the indicators/watchlist user stories for Ouinex.
- **Missing weekly/monthly** (VERIFY): The indicator API only supports D/W/M unit times (`SUPPORTED_UNIT_TIMES`). If Ouinex lacks native 1w/1M, weekly/monthly indicators for Ouinex must be aggregated from daily candles, or those timeframes are unsupported for Ouinex. Flag as an acceptance-scope decision.

## Decision 5: "Map as binance" — reuse the Binance pseudo-account verbatim

- **Decision**: `OuinexReportService.create_gsheet_order` / `update_gsheet_order` write using the **same** `Account(key="binance", name="Coinbase", ...)` that `BinanceReportService._get_binance_account()` returns. The gsheet provider column is driven by `account.name`, so Ouinex rows show exactly what Binance rows show.
- **Rationale**: Satisfies Clarification "Same 'binance' identity — indistinguishable from native Binance rows." To avoid duplicating the pseudo-account definition, centralize it (e.g., a shared factory) so both services return the identical `Account`.
- **Report routing**: `report.py` selects the service by `account_id` prefix. Add `ouinex_` → `OuinexReportService`; keep `binance_` → `BinanceReportService`. `/api/fund/accounts` adds an `ouinex_main` account so the frontend dropdown offers Ouinex; its journal writes still land under Binance identity.
- **Symbol/currency normalization** (VERIFY): Ouinex trade records must be mapped to `ReportOrder` with `asset_type=CRYPTO`, `currency=Currency.USD` (or the quote currency), and commissions applied, matching `BinanceClient.get_report`. Confirm Ouinex fee/commission fields.

## Decision 6: Credentials required for all Ouinex calls

- **Decision**: Per Clarifications, every Ouinex operation (search, candles, reporting) needs valid credentials. `OuinexClient` authenticates on init / lazily and refreshes JWT as needed. Missing/invalid credentials raise a clear Ouinex-specific error; callers (`SearchService`, indicator route) already wrap provider calls in try/except so Binance and Saxo remain unaffected (FR-012).
- **Rationale**: Isolates provider failure; matches the existing `SearchService` pattern that logs and continues when one provider errors.

## Decision 7: Alert parity is a no-op (documented)

- **Finding**: `run_detection_for_asset` builds candles via `saxo_client` and returns early when `saxo_uic is None`. Crypto assets have no `saxo_uic`, so Binance/crypto assets get **no** alert detection today.
- **Decision**: Ouinex inherits identical behavior — no crypto alert detection is built here. FR-007 ("same alerts as Binance") is satisfied. Real crypto alerting is out of scope and would be a separate feature.
- **Rationale**: Faithful parity; avoid over-building (Principle II) and avoid claiming a non-existent capability.

---

## Open items to confirm during `/speckit.tasks` or early implementation

1. **VERIFY** a historical-bars **query** exists (Decision 4, Option A) — highest priority; blocks indicators/watchlist for Ouinex.
2. **VERIFY** weekly/monthly periodicity support, else define aggregation-from-daily (Decision 4).
3. **VERIFY** exact GraphQL schema for `instruments`, `closed_orders`/`account_transactions` fields (symbol, side, price, qty, fee, timestamp, quote currency).
4. **VERIFY** JWT sign-in mutation and token lifetime / refresh mechanics; whether HMAC signing is required for the configured key.
5. **VERIFY** instrument identifier model (numeric `instrument_id` vs symbol string) and how it maps to the `code`/`symbol` used across watchlist, indicators, and TradingView links.
