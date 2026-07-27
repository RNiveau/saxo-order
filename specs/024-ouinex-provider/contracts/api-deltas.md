# Phase 1 Contracts: API deltas for Ouinex

This feature introduces **no new endpoints**. It extends existing endpoints to accept a new `exchange` value (`"ouinex"`) and a new account prefix (`"ouinex_"`). Request/response schemas are unchanged; only accepted values and returned lists grow.

---

## 1. `GET /api/search?keyword=...`

- **Change**: results may now include items with `exchange: "ouinex"`.
- **Response item** (`SearchResultItem`, unchanged shape):
  ```json
  { "symbol": "BTCUSD", "description": "BTC/USD", "identifier": null,
    "asset_type": "Crypto", "exchange": "ouinex" }
  ```
- **Contract test**: given an Ouinex client returning one matching `Asset`, the response `results` includes an item with `exchange == "ouinex"`; Saxo/Binance results are unaffected; if the Ouinex client raises, search still returns Saxo/Binance results (FR-012).

## 2. `GET /api/indicator/asset/{code}?exchange=ouinex&unit_time=daily`

- **Change**: `exchange` query now accepts `"ouinex"`. When `exchange=ouinex`, indicators are computed from Ouinex candles.
- **Request**: `exchange=ouinex`, `country_code` ignored (as for Binance), `unit_time` in {daily, weekly, monthly}.
- **Response**: `AssetIndicatorsResponse` (unchanged) — moving averages (7/20/50/200), `current_price`, `variation_pct`.
- **Contract test**: `Exchange.get_value("ouinex")` resolves; the route dispatches to the Ouinex candle path; a mocked `OuinexClient.get_candles` yields a valid `AssetIndicatorsResponse`.
- **Edge (VERIFY)**: weekly/monthly for Ouinex — either supported via daily aggregation or returns a clear 400 if unsupported (research Decision 4).

## 3. `GET /api/fund/accounts`

- **Change**: the returned account list now also includes an Ouinex pseudo-account.
  ```json
  { "account_id": "ouinex_main", "account_key": "ouinex",
    "account_name": "Ouinex", "total_fund": 0, "available_fund": 0 }
  ```
- **Contract test**: response contains both `binance_main` and `ouinex_main`; Saxo accounts still listed.

## 4. `GET /api/report/orders` and `GET /api/report/summary`

- **Change**: `account_id` starting with `"ouinex_"` routes to `OuinexReportService`.
- **Request**: `account_id=ouinex_main`, `from_date=YYYY-MM-DD`.
- **Response**: `ReportListResponse` / `ReportSummaryResponse` (unchanged shape).
- **Contract test**: `account_id="ouinex_main"` selects `OuinexReportService.get_orders_report`; `binance_main` still selects `BinanceReportService`; Saxo ids unaffected.

## 5. `POST /api/report/gsheet/create` and `POST /api/report/gsheet/update`

- **Change**: `account_id` starting with `"ouinex_"` routes to `OuinexReportService`, which writes the journal row using the **Binance pseudo-account identity**.
- **Request**: `CreateGSheetOrderRequest` / `UpdateGSheetOrderRequest` (unchanged), `account_id=ouinex_main`.
- **Contract/behavior test** (the core "map as binance" guarantee):
  - Given an Ouinex order written via `account_id="ouinex_main"`, the `Account` passed to `GSheetClient.create_order` has `name == "Coinbase"` and `key == "binance"` — **identical** to a Binance write.
  - The provider column value written to the sheet for an Ouinex trade equals the value written for a Binance trade (SC-002: 0% appear under a separate "ouinex" identity).

---

## Cross-cutting contract guarantees

- **Isolation (FR-012 / SC-005)**: any Ouinex client error surfaces as a provider-specific failure and never breaks Saxo or Binance responses on shared endpoints (search especially).
- **No Binance regression (FR-013 / SC-004)**: all existing Binance contract behaviors (`binance_main` routing, public search, indicator dispatch) remain byte-for-byte unchanged.
