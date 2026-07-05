# API Contract: Trade Republic Report

Base path: `/api/trade-republic` (new router, `api/routers/trade_republic.py`)

## POST /api/trade-republic/upload

Upload and parse a Trade Republic CSV export. Nothing is persisted server-side; the full result is returned to the caller.

**Request**: `multipart/form-data`

| Field | Type | Notes |
|---|---|---|
| `file` | file | The CSV export |

**Response 200** (`UploadTradeRepublicResponse`):

```json
{
  "transactions": [
    {
      "source": "trade_republic",
      "datetime": "2026-03-01T11:31:45.309887Z",
      "date": "2026-03-01",
      "account_type": "DEFAULT",
      "category": "CASH",
      "type": "INTEREST_PAYMENT",
      "asset_class": null,
      "name": null,
      "symbol": null,
      "shares": null,
      "price": null,
      "amount": -2.97,
      "fee": null,
      "tax": null,
      "currency": "EUR",
      "original_amount": null,
      "original_currency": null,
      "fx_rate": null,
      "description": "Interest payment for payout collection 019ca7a8-6f3f-72da-8766-5ad26381f838",
      "transaction_id": "019ca92b-2e1d-7a63-831a-88c8927ba850",
      "counterparty_name": null,
      "counterparty_iban": null,
      "payment_reference": null,
      "mcc_code": null
    }
  ],
  "errors": [
    { "row_number": 14, "raw_line": "...", "reason": "missing required field: amount" }
  ],
  "total_rows": 2
}
```

**Errors**:
- `400` — file is not parseable as CSV at all, or the header doesn't match the expected columns (FR-006). No `transactions`/`errors` body; a single `detail` message.
- `422` — no file provided / wrong field name (FastAPI default validation).

**Empty file** (header only, zero data rows): `200` with `transactions: []`, `errors: []`, `total_rows: 0` — the frontend renders the explicit empty state (FR-007), not an error.

---

## POST /api/trade-republic/gsheet/export

Export one or more previously-parsed transactions to Google Sheets. Because nothing is stored server-side, the caller must send the full transaction objects it wants exported — not an id/index referencing a prior upload.

**Request** (`ExportTradeRepublicRequest`):

```json
{
  "transactions": [ /* one or more TradeRepublicTransaction objects, as returned by /upload */ ]
}
```

**Response 200**:

```json
{ "status": "success", "exported_count": 1 }
```

**Errors**:
- `400` — empty `transactions` list (FR: export requires at least one selected transaction).
- `500` — Google Sheets write failure (connectivity/permission); response body carries a clear `detail` message; no partial state is implied since each transaction is appended independently and the response only reports success for rows that actually made it (`exported_count`).

**Note**: The Google Sheets row layout produced by this endpoint is a placeholder (one column per `TradeRepublicTransaction` field, see research.md §5) and is expected to change once the follow-up spec defines the real layout — this contract's request/response shapes are stable, the sheet's column layout is not.
