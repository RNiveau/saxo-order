# API Contract: Backtest

Base prefix: `/api/backtest` (new router `api/routers/backtest.py`, registered in `api/main.py` next to the other routers).

All response models are Pydantic `BaseModel`s in `api/models/backtest.py`, built from the domain dataclasses in `model/backtest.py` (see data-model.md) — following the `ReportOrderResponse.from_report_order(...)` convention already used by `api/models/report.py`.

## `GET /api/backtest/definitions`

Lists the hardcoded backtests available in the "Backtest" menu (FR-001).

**Response 200** — `List[BacktestDefinitionResponse]`

```json
[
  {
    "code": "B9H",
    "display_name": "CAC40 Bougie de 9h",
    "instrument": "FRA40.I"
  }
]
```

No query parameters. No error cases beyond the standard 500 (unexpected error), since this is a static, hardcoded list — no external call is made.

## `GET /api/backtest/run`

Runs a hardcoded backtest across a UI-provided date range and returns the aggregate summary plus a compact per-day list (FR-012, FR-013). This is the endpoint behind User Story 2. A single-day request (`start_date == end_date`) is valid and simply returns a range of one day, but the frontend should prefer `GET /api/backtest/day` (below) for a single day, since that endpoint returns full trade detail (User Story 1's acceptance scenarios need entry/exit prices, not just counts).

**Query parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `definition` | `str` | yes | Must match a `BacktestDefinition.code` (currently only `"B9H"`) |
| `start_date` | `str` (`YYYY-MM-DD`) | yes | |
| `end_date` | `str` (`YYYY-MM-DD`) | yes | |

**Response 200** — `BacktestRunResponse`

```json
{
  "summary": {
    "definition_code": "B9H",
    "start_date": "2026-06-01",
    "end_date": "2026-06-30",
    "number_of_days": 21,
    "number_of_trades": 9,
    "number_of_winning_positions": 4,
    "number_of_losing_positions": 3,
    "number_of_be": 2,
    "average_win": 34.5,
    "average_loss": 42.0,
    "final_result": 27.0
  },
  "days": [
    {
      "date": "2026-06-01",
      "status": "no_trade",
      "trade_count": 0,
      "points": 0.0
    },
    {
      "date": "2026-06-02",
      "status": "traded",
      "trade_count": 2,
      "points": -8.0
    }
  ]
}
```

Note: `days` omits any date with `status == "no_data"` per FR-013's "number of days" definition (no-data days are excluded, not silently zero-filled) — matches the "no data" vs. "no trade" distinction from the spec's Edge Cases.

**Errors**

| Status | Condition |
|---|---|
| 400 | `end_date < start_date`, or `start_date`/`end_date` in the future (FR-016) |
| 400 | Unknown `definition` code |
| 500 | Unexpected error (Saxo API failure not classified as per-day "no data", etc.) |

## `GET /api/backtest/day`

Returns full detail for exactly one day — H1 reference levels, the 5-minute candle series from 10:00 Paris local onward, and every trade with entry/exit markers (FR-015, User Stories 1 and 3). Computed independently of `/run`; no shared state (research.md §5, §6).

**Query parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `definition` | `str` | yes | |
| `date` | `str` (`YYYY-MM-DD`) | yes | |

**Response 200** — `DayDetailResponse`

```json
{
  "date": "2026-06-02",
  "status": "traded",
  "h1_high": 8042.5,
  "h1_low": 8011.0,
  "candles": [
    {"date": "2026-06-02T10:00:00", "open": 8009.5, "higher": 8013.0, "lower": 8005.0, "close": 8012.0}
  ],
  "trades": [
    {
      "entry_time": "2026-06-02T10:20:00",
      "entry_price": 8012.5,
      "exit_time": "2026-06-02T11:05:00",
      "exit_price": 7962.5,
      "exit_reason": "stop_loss",
      "points": -50.0
    }
  ]
}
```

`status == "no_data"` returns `h1_high`/`h1_low`/`candles`/`trades` as `null`/empty rather than a 404 — a missing historical day is a valid, expected result for this domain (FR-004), not an API error.

**Errors**

| Status | Condition |
|---|---|
| 400 | `date` in the future, or unknown `definition` code |
| 500 | Unexpected error |

## Frontend service mapping (`frontend/src/services/api.ts`)

```ts
export const backtestService = {
  getDefinitions: (): Promise<BacktestDefinition[]> => ...,
  runRange: (definition: string, startDate: string, endDate: string): Promise<BacktestRunResponse> => ...,
  getDayDetail: (definition: string, date: string): Promise<DayDetailResponse> => ...,
};
```

TypeScript interfaces mirror the Pydantic response models field-for-field (Constitution: "API Contract Standards").
