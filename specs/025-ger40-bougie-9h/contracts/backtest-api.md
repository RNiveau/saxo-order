# API Contract: GER40 Bougie de 9h (spec 025 delta)

This feature adds **no new endpoint**. It adds a third `BacktestDefinition` (`"G9H"`) reachable through the existing `/api/backtest/*` endpoints (spec 021, `api/routers/backtest.py`) and makes two backward-compatible additions:

1. `GET /api/backtest/definitions` now returns three definitions, each carrying its **default thresholds** and a `double_take_profit` flag.
2. The optional strategy-threshold query parameters now fall back to the **selected definition's** defaults instead of a single global default set (per-definition resolution). CAC40 defaults are unchanged (50/10/20/20); GER40 defaults are 150/10/50/40.

See `specs/021-backtest-menu-hardcoded/contracts/backtest-api.md` for the full endpoint set (`/run`, `/day`, `/run/csv`, `/day/csv`) — request shapes, validation (400 for bad range/date/unknown definition, 422 for a non-positive threshold), and CSV formats are all unchanged.

## `GET /api/backtest/definitions` (extended response)

```json
[
  {
    "code": "B9H",
    "display_name": "CAC40 Bougie de 9h",
    "instrument": "FRA40.I",
    "double_take_profit": false,
    "default_parameters": {
      "stop_loss_points": 50,
      "take_profit_offset_points": 10,
      "break_even_trigger_points": 20,
      "max_entry_distance_points": 20
    }
  },
  {
    "code": "B9HTC",
    "display_name": "CAC40 Bougie de 9h (time cut)",
    "instrument": "FRA40.I",
    "double_take_profit": false,
    "default_parameters": {
      "stop_loss_points": 50,
      "take_profit_offset_points": 10,
      "break_even_trigger_points": 20,
      "max_entry_distance_points": 20
    }
  },
  {
    "code": "G9H",
    "display_name": "GER40 Bougie de 9h",
    "instrument": "GER40.I",
    "double_take_profit": true,
    "default_parameters": {
      "stop_loss_points": 150,
      "take_profit_offset_points": 10,
      "break_even_trigger_points": 50,
      "max_entry_distance_points": 40
    }
  }
]
```

`default_parameters` and `double_take_profit` are **additive** fields — existing clients that ignore them are unaffected. The frontend uses `default_parameters` to pre-fill the threshold inputs for the selected definition (replacing the hardcoded `PARAM_FIELDS` defaults in `Backtest.tsx`).

## Threshold parameters (per-definition defaults)

The four optional query parameters (`stop_loss_points`, `take_profit_offset_points`, `break_even_trigger_points`, `max_entry_distance_points`) are unchanged in name, type, and `> 0` validation (422 on a non-positive value, before any day runs). The only change is the **fallback**: an omitted parameter now resolves to the *selected definition's* `default_parameters` value rather than a single global default. Concretely, for `definition=G9H` an omitted `stop_loss_points` resolves to **150** (measured from the H1 low/high, FR-G05), an omitted `break_even_trigger_points` to **50**, and an omitted `max_entry_distance_points` to **40**. For `definition=B9H`/`B9HTC` the resolved values are exactly as before.

Resolution happens after the definition is looked up (unknown definition → 400 as today), so the endpoint must resolve `definition` before merging overrides.

## `GET /api/backtest/run` / `GET /api/backtest/day` for `G9H`

Identical request/response **shapes** to CAC40. A `G9H` day that traded returns each two-lot position as **one aggregated `Trade`** (FR-G07/FR-G10): `entry_price` is the shared entry, `exit_price`/`exit_time`/`exit_reason` reflect the runner's final exit, and `points` is the **net of both lots**. Example `/day` trade for a TP1-then-TP2 full winner (entry 18000, H1 low 17990 → stop 17840, H1 high 18120 → TP2 18110, midpoint TP1 18055):

```json
{
  "entry_time": "2026-06-02T10:20:00",
  "entry_price": 18000.0,
  "exit_time": "2026-06-02T11:05:00",
  "exit_price": 18110.0,
  "exit_reason": "take_profit",
  "direction": "Buy",
  "points": 165.0
}
```

`points = (18055 − 18000) + (18110 − 18000) = 55 + 110 = 165`. A both-lots stop-out on the same setup would report `exit_price = 17840`, `exit_reason = "stop_loss"`, `points = 2 · (17840 − 18000) = −320` (the "SL is x2"). A TP1-then-break-even runner reports `exit_reason = "break_even"` with a **net-positive** `points` (≈ the banked 55).

## Aggregate summary (`/run`) classification for `G9H`

Unchanged response shape. For a `double_take_profit` definition the counts are classified by the **sign of each position's net points** (FR-G08): net > 0 → winning, net < 0 → losing, net == 0 → BE. `average_win`/`average_loss` use the net points; the BE bucket holds only genuinely-flat positions. CAC40's mechanism-based classification is unchanged.

## CSV exports

`/run/csv` and `/day/csv` are unchanged in format. For `G9H` each row/trade is the aggregated position (one row per position, net points). The leading parameters block echoes the **resolved** thresholds (so a GER40 export shows 150/10/50/40 when defaults are used).

## Frontend service mapping (`frontend/src/services/api.ts`)

```ts
export interface BacktestParameters {
  stop_loss_points?: number;
  take_profit_offset_points?: number;
  break_even_trigger_points?: number;
  max_entry_distance_points?: number;
}

export interface BacktestDefinition {
  code: string;
  display_name: string;
  instrument: string;
  double_take_profit: boolean;              // NEW
  default_parameters: Required<BacktestParameters>; // NEW — four numbers
}
```

`runRange` / `getDayDetail` / `exportRunCsv` / `exportDayCsv` signatures are unchanged; the page seeds its threshold inputs from `selectedDefinition.default_parameters` instead of the hardcoded constants.
