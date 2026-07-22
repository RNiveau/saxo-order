# Phase 1 Data Model: Ouinex crypto provider

No new persistence schema. This feature adds one enum value, one Client, one Service, and configuration — reusing existing domain models (`Asset`, `Candle`, `ReportOrder`, `Account`).

## Enum change — `model/enum.py`

```python
class Exchange(EnumWithGetValue):
    SAXO = "saxo"
    BINANCE = "binance"
    OUINEX = "ouinex"   # NEW
```

- `Exchange.get_value("ouinex")` must resolve (used by `indicator.py`, `homepage.py`).
- Wherever code branches on `Exchange.BINANCE` for crypto treatment, it must also accept `Exchange.OUINEX` (indicator routing, watchlist crypto tagging, homepage mapping). Prefer a small helper (e.g., `Exchange.is_crypto()` or `exchange in CRYPTO_EXCHANGES`) over scattered `in (BINANCE, OUINEX)` checks, to keep the intent explicit and avoid missed branches.

## Reused domain models (unchanged)

- **`Asset`** (`model/asset.py`): `symbol`, `description`, `asset_type`, `exchange`, `identifier`. Ouinex search returns `Asset(exchange=Exchange.OUINEX, asset_type=AssetType.CRYPTO)`.
- **`Candle`** (`model/workflow.py`): `open`, `higher`, `lower`, `close`, `ut`, `date`. `OuinexClient.get_candles` returns a list ordered **index 0 = newest** (Constitution V.1).
- **`ReportOrder`** (`model/`): produced by `OuinexClient.get_report_all`; `asset_type=AssetType.CRYPTO`, `currency=Currency.USD` (or quote), commissions applied — same shape Binance produces.
- **`Account`** (`model/__init__.py`): `key`, `name`, `fund`, `available_fund`, `client_key`. The **Binance pseudo-account is reused verbatim** for Ouinex journal writes:
  - `Account(key="binance", name="Coinbase", fund=0, client_key="binance")`
  - This is the concrete meaning of "map as binance": `account.name` is what the gsheet provider column stores.

## New Client interface — `client/ouinex_client.py`

Public method surface (must match what Services already call on `BinanceClient`):

| Method | Signature | Returns | Notes |
|--------|-----------|---------|-------|
| `search` | `(keyword: str)` | `List[Asset]` | GraphQL `instruments`, client-side keyword filter, `exchange=OUINEX` |
| `get_candles` | `(symbol: str, unit_time: UnitTime, limit: int = 200)` | `List[Candle]` | newest-first; **historical-bars query — see research Decision 4 (VERIFY)** |
| `get_latest_candle` | `(symbol: str)` | `Candle` | most recent fine-grained bar for current price |
| `get_report` | `(symbol: str, date: str, usdeur_rate: float)` | `List[ReportOrder]` | GraphQL `closed_orders`/`account_transactions` |
| `get_report_all` | `(date: str, usdeur_rate: float)` | `List[ReportOrder]` | iterate tracked symbols |

Internal (private, `_`-prefixed) helpers: JWT sign-in/refresh, GraphQL POST, periodicity mapping (`UnitTime` → Ouinex periodicity), bar→`Candle` mapping, trade→`ReportOrder` mapping.

**UnitTime → Ouinex periodicity map** (VERIFY; note missing W/M):

| UnitTime | Ouinex periodicity | Status |
|----------|--------------------|--------|
| M15 | `15m` | OK |
| H1 | `1h` | OK |
| H4 | `4h` | OK |
| D | `1d` | OK |
| W | — | **VERIFY** — aggregate from `1d` or unsupported |
| M | — | **VERIFY** — aggregate from `1d` or unsupported |

## New Service — `api/services/ouinex_report_service.py`

Mirrors `BinanceReportService`:

- `get_orders_report(account_id, from_date)` — TTLCache (128, 300s); calls `OuinexClient.get_report_all`.
- `convert_order_to_eur`, `calculate_summary` — identical logic (reuse or share with Binance).
- `create_gsheet_order` / `update_gsheet_order` — write via `GSheetClient` using the **shared Binance pseudo-account**.
- Account factory centralized so `BinanceReportService` and `OuinexReportService` return an identical `Account` (single source of truth for the "binance" identity).

## Configuration — `utils/configuration.py`

```python
@property
def ouinex_keys(self) -> Tuple:
    return (
        self.secrets["ouinex_api_key"],
        self.secrets["ouinex_secret_key"],
    )

@property
def ouinex_graphql_url(self) -> str:
    return self.config.get("ouinex_graphql_url", "https://live-api.ouinex.com/graphql")
```

- `secrets.yml` (gitignored) gains `ouinex_api_key`, `ouinex_secret_key`.
- `config.yml` may set `ouinex_graphql_url` (non-secret).

## State / lifecycle

- No stored state changes. Watchlist items simply carry `exchange="ouinex"` (existing free-form attribute).
- JWT token lifecycle lives entirely inside `OuinexClient` (in-memory, refreshed on expiry).
