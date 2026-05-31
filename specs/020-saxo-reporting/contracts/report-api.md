# HTTP Contract: `/api/report/*`

**Status**: Retroactive — describes the existing FastAPI routes in `api/routers/report.py`.

All endpoints are authenticated through the same session/cookie mechanism used by the rest of the API. Responses are JSON. Error payloads follow FastAPI's default `{"detail": "..."}` shape with the matching HTTP status code.

Account routing: when the supplied `account_id` starts with `binance_`, the request is delegated to `BinanceReportService` (see `specs/471-binance-reporting`). Otherwise it is delegated to `ReportService` (the Saxo backend documented here).

---

## `GET /api/report/config`

Returns the controlled vocabularies the UI needs to render dropdowns.

**Response 200**
```json
{
  "strategies": ["BREAKOUT", "PULLBACK", "MEAN_REVERSION", "..."],
  "signals":    ["BULLISH_ENGULFING", "HAMMER", "..."]
}
```

---

## `GET /api/report/orders`

Fetch the list of executed orders for an account over a period, with EUR conversion applied.

**Query**
| Name | Type | Required | Description |
|---|---|---|---|
| `account_id` | string | yes | Saxo account key, or `binance_*` pseudo-id |
| `from_date` | string (`YYYY/MM/DD` or `YYYY-MM-DD`) | yes | Inclusive start date |

**Response 200**
```json
{
  "orders": [
    {
      "code": "AIR:xpar",
      "name": "Airbus SE",
      "direction": "BUY",
      "quantity": 10.0,
      "price": 145.32,
      "price_eur": 145.32,
      "total": 1453.2,
      "total_eur": 1453.2,
      "currency": "EURO",
      "date": "2025-04-15T09:32:11",
      "asset_type": "STOCK",
      "underlying_price": null
    }
  ],
  "total_count": 1,
  "from_date": "2025-04-01"
}
```

**Errors**
- `400` invalid date format
- `404` account not found on the user's profile
- `502` broker API failure

Caching: results are cached server-side for 5 minutes keyed by `(account_id, from_date)`.

---

## `GET /api/report/summary`

Aggregated statistics for the same period as `/orders`.

**Query**: same as `/orders`.

**Response 200**
```json
{
  "total_orders": 12,
  "total_volume_eur": 38421.55,
  "total_fees_eur": 86.40,
  "buy_count": 7,
  "sell_count": 5,
  "buy_volume_eur": 22890.10,
  "sell_volume_eur": 15531.45
}
```

---

## `POST /api/report/gsheet/create`

Create a new position row in the Google Sheets journal.

**Body**
```json
{
  "account_id": "12345678",
  "order": { /* ReportOrder-shaped payload as returned by /orders */ },
  "stop": 140.00,
  "objective": 160.00,
  "strategy": "BREAKOUT",
  "signal": "BULLISH_ENGULFING",
  "comment": "Daily breakout after 3w consolidation"
}
```

**Response 200**
```json
{ "status": "ok", "message": "Order added to gsheet" }
```

**Errors**
- `400` missing/invalid `strategy` or `signal`, or unknown enum value
- `502` Google Sheets API failure
- `409` not used — duplicate rows are allowed (the user is responsible for selecting which row to update)

---

## `POST /api/report/gsheet/update`

Update an existing journal row — either to adjust risk fields while the position is open, or to record its closure.

**Body**
```json
{
  "account_id": "12345678",
  "order": { /* ReportOrder payload */ },
  "line_number": 42,
  "close": true,
  "stopped": false,
  "be_stopped": true,
  "stop": null,
  "objective": null,
  "strategy": null,
  "signal": null,
  "comment": null
}
```

- When `close == false`: `stop` and/or `objective` may be supplied to adjust the open position. `stopped` / `be_stopped` must be `false`.
- When `close == true`: at most one of `stopped` / `be_stopped` should be `true`. The closing price is taken from `order.price`; closing taxes are computed for stocks only.

**Response 200**
```json
{ "status": "ok", "message": "Order updated in gsheet" }
```

**Errors**
- `400` invalid combination (e.g. both `stopped` and `be_stopped` true, or close-flags set while `close == false`)
- `404` `line_number` does not exist in the sheet
- `502` Google Sheets API failure

---

## Account selection

Account discovery is **not** part of this contract — the frontend obtains the account list (Saxo accounts + Binance pseudo-account) from `GET /api/fund/accounts` and passes the chosen `account_id` to the endpoints above.
