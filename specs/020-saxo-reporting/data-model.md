# Phase 1 Data Model: Saxo Order Reporting

**Status**: Retroactive — entities reflect what is already in `model/`, `api/models/report.py`, and the Google Sheets layout.

This feature reads orders from Saxo, derives an EUR view, summarises the period, and writes selected entries to Google Sheets. There is **no new persistent storage** introduced by this feature; the entities below describe the in-memory and Sheet-resident shapes.

---

## Domain entities (`model/`)

### `Order` (`model/__init__.py`)

The base order shape used across the codebase.

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | Asset code / symbol |
| `name` | `str` | Human-readable asset name |
| `direction` | `Direction` enum | `BUY` / `SELL` |
| `quantity` | `float` | Order size |
| `price` | `float` | Execution price (original currency) |
| `currency` | `Currency` enum | `EURO`, `USD`, `JPY`, ... |
| `asset_type` | `AssetType` enum | `STOCK`, `CFD`, `WARRANT`, `CRYPTO`, ... |
| `stop` | `Optional[float]` | Stop-loss; populated when journaling |
| `objective` | `Optional[float]` | Target price; populated when journaling |
| `strategy` | `Optional[Strategy]` | Required at journal-creation |
| `signal` | `Optional[Signal]` | Required at journal-creation |
| `comment` | `Optional[str]` | Free-text note |
| `underlying` | `Optional[UnderlyingOrder]` | For derivatives — underlying price/asset |
| `taxes` | `Optional[Taxes]` | Computed at journal time for stocks |

### `ReportOrder(Order)` (`model/__init__.py`)

Adds lifecycle fields needed for journaling.

| Field | Type | Notes |
|---|---|---|
| `date` | `datetime` | Execution date returned by Saxo |
| `open_position` | `bool` | `True` when the order opens a new position |
| `stopped` | `bool` | Position closed by stop-loss |
| `be_stopped` | `bool` | Position closed at break-even |

### `Account` (`model/__init__.py`, dataclass)

| Field | Type | Notes |
|---|---|---|
| `key` | `str` | Saxo account key (or `binance_main` for Binance) |
| `name` | `str` | Display name |
| `fund` | `float` | Total balance |
| `available_fund` | `float` | Free balance |
| `client_key` | `str` | Saxo client key (empty for pseudo-accounts) |

> The API exposes its own `AccountInfo` Pydantic model — clients never see the dataclass directly.

### `Taxes` (`model/__init__.py`)

| Field | Type | Notes |
|---|---|---|
| `cost` | `float` | Broker commission (`max(2, total * 0.0008)` for stocks) |
| `taxes` | `float` | Regulatory tax (`0.004 * total` for stocks; `0` for non-stocks) |

### `UnderlyingOrder` (`model/__init__.py`)

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | Underlying asset code |
| `price` | `float` | Underlying price at execution (EUR) |

---

## Controlled vocabularies (`model/enum.py`)

| Enum | Purpose | Representative values |
|---|---|---|
| `Strategy` | Why the trader entered the trade | breakout, pullback, mean-reversion, ... (~37 members) |
| `Signal` | Signal type that triggered the trade | bullish engulfing, hammer, ... (~19 members) |
| `Currency` | Order currency | `EURO`, `USD`, `JPY` |
| `Direction` | Order direction | `BUY`, `SELL` |
| `AssetType` | Class of instrument | `STOCK`, `CFD`, `WARRANT`, `CRYPTO`, ... |

`Strategy` and `Signal` are surfaced to the UI via `GET /api/report/config` so dropdowns stay in sync with backend validation.

---

## API surface models (`api/models/report.py`)

These are Pydantic v2 models — the serialisation contract between FastAPI and the React client.

| Model | Role |
|---|---|
| `ReportOrderResponse` | Single order projected for the UI: `code`, `name`, `direction`, `quantity`, `price`, `price_eur`, `total`, `total_eur`, `currency`, `date`, `asset_type`, optional `underlying_price` |
| `ReportListResponse` | `{ orders: List[ReportOrderResponse], total_count: int, from_date: str }` |
| `ReportSummaryResponse` | Aggregates — `total_orders`, `total_volume_eur`, `total_fees_eur`, `buy_count`, `sell_count`, `buy_volume_eur`, `sell_volume_eur` |
| `CreateGSheetOrderRequest` | Create-journal payload: `account_id`, `order` (raw), `stop`, `objective`, `strategy`, `signal`, optional `comment` |
| `UpdateGSheetOrderRequest` | Update-journal payload: `account_id`, `order`, `line_number`, `close: bool`, `stopped: bool`, `be_stopped: bool`, optional `stop`/`objective`/`strategy`/`signal`/`comment` |

`Strategy` and `Signal` values arrive as strings on the wire and are parsed back into the enums by the request models, with explicit validation errors on unknown values.

---

## External entity — Google Sheets journal row

Each persisted position is one row in the trader's spreadsheet. The exact column ranges live in `client/gsheet_client.py`; the logical layout is:

| Group | Fields | Filled by |
|---|---|---|
| Identity | Asset code, asset name, type (CASH / CFD / WARRANT / CRYPTO), direction (BUY/SELL) | Create |
| Entry | Date, quantity, entry price (original), entry price (EUR) | Create |
| Risk | Strategy, signal, comment, stop, objective | Create |
| Cost | Broker cost, regulatory taxes (stocks only) | Create / Update on close |
| Closure | Stopped flag, BE-stopped flag, close date, close price | Update on close |
| Computed | Risk/reward, P&L formulas | Sheet formulas |

The feature appends (create) and batch-updates (update) cells; it never deletes rows.

---

## State transitions

A trade flows through these states from the journal's point of view:

```
(no entry)  ──create──▶  Open
   Open     ──adjust──▶  Open       (stop / objective / strategy / signal updates)
   Open     ──close───▶  Closed     (writes closing price + stopped/BE-stopped flags)
```

- `create` requires `strategy` and `signal`.
- `adjust` modifies a subset of risk fields without affecting closure state.
- `close` is one-way; reopening a closed position would require a new row.

---

## Caching shape (in-memory)

`ReportService` keeps two caches via `cachetools.TTLCache`:

| Cache | Key | Value | TTL |
|---|---|---|---|
| `_report_cache` | `(account_id, from_date)` | `List[ReportOrder]` | 300 s |
| `_account_cache` | `account_identifier` | `Account` | 300 s |

The frontend has no knowledge of the cache — staleness is bounded by the TTL.
