# Phase 1 Data Model: Trade Republic Report

## TradeRepublicTransaction

Represents a single parsed row from an uploaded Trade Republic CSV export. Held only in-memory (backend response payload / frontend state) — never persisted (see research.md §2).

| Field | Type | Required | Notes |
|---|---|---|---|
| `source` | `str` | always `"trade_republic"` | Explicit origin marker per constitution's Domain Model Integrity principle (analogous to the `exchange` field on other models) |
| `datetime` | `datetime` | yes | Parsed from CSV `datetime` column (ISO-8601, e.g. `2026-03-01T11:31:45.309887Z`) |
| `date` | `date` | yes | Parsed from CSV `date` column |
| `account_type` | `str` | yes | Raw value from CSV (e.g. `DEFAULT`) — see research.md §3 |
| `category` | `str` | yes | Raw value from CSV (e.g. `CASH`) — see research.md §3 |
| `type` | `str` | yes | Raw value from CSV (e.g. `INTEREST_PAYMENT`) — see research.md §3 |
| `asset_class` | `Optional[str]` | no | Empty for cash-only rows |
| `name` | `Optional[str]` | no | Asset name; empty for cash-only rows |
| `symbol` | `Optional[str]` | no | Asset ticker; empty for cash-only rows |
| `shares` | `Optional[float]` | no | Empty for non-trade rows |
| `price` | `Optional[float]` | no | Empty for non-trade rows |
| `amount` | `float` | yes | Signed transaction amount in `currency` |
| `fee` | `Optional[float]` | no | |
| `tax` | `Optional[float]` | no | |
| `currency` | `Currency` (existing enum) | yes | Reused from `model.enum.Currency`; unknown codes kept as raw string (research.md §4) |
| `original_amount` | `Optional[float]` | no | Populated only for foreign-currency transactions |
| `original_currency` | `Optional[Currency]` | no | Populated only for foreign-currency transactions |
| `fx_rate` | `Optional[float]` | no | Populated only for foreign-currency transactions |
| `description` | `Optional[str]` | no | Free text |
| `transaction_id` | `str` | yes | Unique id from the broker; no uniqueness enforcement is performed by this feature (no duplicate detection, FR-012) |
| `counterparty_name` | `Optional[str]` | no | |
| `counterparty_iban` | `Optional[str]` | no | |
| `payment_reference` | `Optional[str]` | no | |
| `mcc_code` | `Optional[str]` | no | Merchant category code, card payments only |

**Validation rules**:
- A row missing `datetime`, `date`, `account_type`, `category`, `type`, `amount`, `currency`, or `transaction_id` is treated as a parse failure for that row (FR-008: flagged, not silently dropped, rest of the file still processed).
- All other fields may be blank/empty — this is expected, not an error (spec Edge Cases: "missing optional fields").

## ParseError

Represents one row that failed to parse, surfaced to the trader per FR-008.

| Field | Type | Notes |
|---|---|---|
| `row_number` | `int` | 1-indexed line number in the uploaded file (header excluded) |
| `raw_line` | `str` | The original unparsed line, for troubleshooting |
| `reason` | `str` | Human-readable reason (e.g. "missing required field: amount") |

## UploadBatch (response-only shape, not a stored entity)

The result of one upload, returned directly in the HTTP response body — not persisted (see plan.md Storage: N/A).

| Field | Type | Notes |
|---|---|---|
| `transactions` | `List[TradeRepublicTransaction]` | Successfully parsed rows, in file order |
| `errors` | `List[ParseError]` | Rows that failed to parse |
| `total_rows` | `int` | `len(transactions) + len(errors)` |

## Relationships

- `UploadBatch` is a transient container produced by one upload; it has no identity and is not referenced by any other entity.
- `TradeRepublicTransaction` has no relationship to existing models (`ReportOrder`, `Order`, etc.) — it is a distinct entity for a distinct broker, consistent with the Assumptions in spec.md (no reconciliation with Saxo/Binance data in this feature).
