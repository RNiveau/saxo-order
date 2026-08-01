# API Contract Delta: "GER40 Combo" Backtest

**No new endpoint.** The three combo backtests are ordinary entries in
the existing definition registry, so every existing route serves them
unchanged. This document records only what changes in the payloads.

Existing routes (`api/routers/backtest.py`, prefix `/api/backtest`):

| Route | Change |
|---|---|
| `GET /definitions` | Three new entries; one new response field (§1). |
| `GET /day` | Serves a combo code; `h1_*` are `null` (§2). |
| `GET /run` | Serves a combo code; `h1_*` are `null` on every day row (§2). |
| `GET /day/csv` | Unchanged shape; empty H1 cells. |
| `GET /run/csv` | Unchanged shape; empty H1 cells. |

---

## 1. `GET /api/backtest/definitions`

### New field on `BacktestDefinitionResponse`

```python
class BacktestDefinitionResponse(BaseModel):
    code: str
    display_name: str
    instrument: str
    double_take_profit: bool = False
    tunable_parameters: List[str] = []     # NEW - FR-C16
    default_parameters: BacktestParametersResponse
```

`tunable_parameters` lists the `BacktestParameters` field names a run may
override for this definition. Existing definitions report all four, so no
client behavior changes for them:

```json
["stop_loss_points", "take_profit_offset_points",
 "break_even_trigger_points", "max_entry_distance_points"]
```

The combo definitions report `["stop_loss_points"]` only.

### New entries

```json
[
  {
    "code": "C5M",
    "display_name": "GER40 Combo 5m",
    "instrument": "GER40.I",
    "double_take_profit": true,
    "tunable_parameters": ["stop_loss_points"],
    "default_parameters": {
      "stop_loss_points": 50.0,
      "take_profit_offset_points": 10.0,
      "break_even_trigger_points": 20.0,
      "max_entry_distance_points": 20.0
    }
  },
  { "code": "C15M", "display_name": "GER40 Combo 15m", "...": "..." },
  { "code": "C1H",  "display_name": "GER40 Combo H1",  "...": "..." }
]
```

The three non-tunable values are the `BacktestParameters` dataclass
defaults, carried only because the response model requires all four
fields. They are never read by the combo strategy (FR-C16).

### Matching TypeScript (`frontend/src/services/api.ts`)

```ts
export interface BacktestDefinition {
  code: string;
  display_name: string;
  instrument: string;
  double_take_profit: boolean;
  tunable_parameters: string[];              // NEW
  default_parameters: BacktestDefinitionParameters;
}
```

Constitution §I requires the TypeScript interface to mirror the Pydantic
model exactly — same field name, same type.

---

## 2. `GET /api/backtest/day` and `GET /api/backtest/run`

Request parameters are unchanged. Passing a non-tunable override
(`take_profit_offset_points`, `break_even_trigger_points`,
`max_entry_distance_points`) with a combo `definition` is **accepted and
ignored** — the existing `Query(gt=0)` validation still applies, so an
invalid value still returns 422. No new error case is introduced.

### Response deltas

`DayDetailResponse` and `DayResultSummaryResponse` already declare
`h1_high`, `h1_low` and `h1_open` as optional. For a combo definition all
three are `null` — there is no reference range. `mm50_slope`, `adx14` and
`overnight_gap` are still populated (they measure the instrument, not the
strategy).

`TradeResponse.exit_reason` gains one possible value, `"end_of_run"`
(FR-C12), alongside the existing `stop_loss`, `break_even`,
`take_profit`, `end_of_day`, `time_cut` and `trailing_stop`. It is
already typed as `str`, so the schema is unchanged.

Semantics that differ without any shape change, and that a client must
not assume away:

- A day row's `points` can be `0` with `status: "no_trade"` while a
  position opened on an earlier day is still running through it.
- A trade's `exit_time` may fall on a **later day** than its
  `entry_time` (FR-C11). Nothing in the response shape prevented this
  before; nothing in the frontend may assume otherwise now.
- `GET /day` for a combo definition force-closes an open position at that
  day's last candle as `end_of_run`, so a single-day view of a trade that
  really ran for three days reports a different exit than the range view
  (research R9). This is the same caveat FR-C12 already carries.

---

## 3. Compatibility

- No route added, removed or renamed.
- One optional field added to one response model, defaulted so existing
  clients that ignore it keep working.
- No request parameter added, removed or made required.
- Existing definitions' payloads are byte-identical apart from the new
  `tunable_parameters` array.
