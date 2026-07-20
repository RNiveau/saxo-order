# Data Model: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

All entities below are in-memory / request-response only (see research.md §6 — no persistence). Nothing is written to DynamoDB or any other store; there is no lifecycle beyond the duration of a single API request.

## New enums (`model/enum.py`, `model/workflow.py`)

### `ExitReason` (new, `model/enum.py`, extends `EnumWithGetValue`)

| Member | Value | Meaning |
|---|---|---|
| `STOP_LOSS` | `"stop_loss"` | Closed because price fell to/below the active stop-loss level (original entry-minus-50, per FR-008) |
| `BREAK_EVEN` | `"break_even"` | Closed because price fell to/below the stop-loss after it was moved to break-even (FR-008a) |
| `TAKE_PROFIT` | `"take_profit"` | Closed because price reached H1 high minus 10 points (FR-008) |
| `END_OF_DAY` | `"end_of_day"` | Closed at the last 5-minute candle of the session with no other exit reached (FR-008) |

### `UnitTime.M5` (new member, `model/workflow.py`)

Add `M5 = "5m"` alongside the existing `D`, `M15`, `M30`, `H1`, `H4`, `W`, `M` members (research.md §2). Used to tag the 5-minute candles fetched for this feature; no other existing feature is affected by adding this member.

### `DayStatus` (new, `model/enum.py`, extends `EnumWithGetValue`)

| Member | Value | Meaning |
|---|---|---|
| `NO_DATA` | `"no_data"` | The 9:00–10:00 H1 reference candle could not be retrieved for this day (FR-004) |
| `NO_TRADE` | `"no_trade"` | H1 data was available but no breakout-reversal signal occurred (FR-006) |
| `TRADED` | `"traded"` | One or more trades occurred (FR-006, FR-011) |

## Domain entities (`model/backtest.py`, new module — dataclasses, no external dependencies, per Constitution's Model Layer rule)

### `BacktestDefinition`

Hardcoded, not persisted — one Python constant, not a DB row.

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | `"B9H"` — matches `Strategy.B9H.name` |
| `name` | `str` | `Strategy.B9H.value` → `"Bougie de 9h"` |
| `display_name` | `str` | `"CAC40 Bougie de 9h"` (per user's naming — instrument-qualified for the menu) |
| `instrument` | `str` | `"FRA40.I"` |

### `Trade`

| Field | Type | Notes |
|---|---|---|
| `entry_time` | `datetime` | Time of the confirming (breakout) 5-minute candle, not the candidate reversal candle it broke above (FR-007) |
| `entry_price` | `float` | The candidate reversal candle's high, or the confirming candle's open if it gapped above that high (FR-007, FR-010's gap-fill convention) |
| `exit_time` | `datetime` | Required — a `Trade` is only ever constructed once it has closed (the implementation never stores an open position as a `Trade`), so there is no `None` case to represent |
| `exit_price` | `float` | Per FR-010 gap-fill rule |
| `exit_reason` | `ExitReason` | One of the four members above |
| `points` | `float` | `exit_price - entry_price`, rounded consistent with existing `Candle` price rounding (`round(..., 4)` per `client/client_helper.py` convention, then reported to the trader in points) |

**Validation rules** (enforced in `api/services/backtest_service.py`, not at the dataclass level — consistent with how other domain models in this codebase are built by services rather than self-validating):
- `entry_time < exit_time` when `exit_time` is set.
- `exit_reason == BREAK_EVEN` normally implies `points == 0`, but not always: FR-010's gap-fill rule applies uniformly to all exit types, so a break-even exit whose triggering candle opens beyond the break-even level records that candle's open price (and therefore a small non-zero points value) rather than being forced to exactly 0. `exit_reason` reflects which mechanism closed the trade (the stop had moved to break-even before being hit), not a guarantee of the resulting points — see spec.md's Assumptions for the reasoning.
- At most one `Trade` per `DayResult` may be "open" at construction time — trades are only appended once closed (FR-011: at most one open position at any time).

### `DayResult`

Full per-day detail — this is the shape returned by the day-detail endpoint (research.md §5) and also embedded (without `candles`) in a lighter form for the range/summary endpoint.

| Field | Type | Notes |
|---|---|---|
| `date` | `date` | Trading day (Paris local calendar date) |
| `status` | `DayStatus` | `NO_DATA` / `NO_TRADE` / `TRADED` |
| `h1_high` | `Optional[float]` | `None` when `status == NO_DATA` |
| `h1_low` | `Optional[float]` | `None` when `status == NO_DATA` |
| `candles` | `List[Candle]` | 5-minute candles from 10:00 Paris local to end of day; only populated by the day-detail endpoint (FR-015), omitted from the range/summary response |
| `trades` | `List[Trade]` | Chronological; empty when `status != TRADED` |

`Candle` here is the existing `model.workflow.Candle` (per Constitution V — "Outside SaxoService, use Candle objects everywhere").

### `DayResultSummary` (compact, range/summary endpoint only)

| Field | Type | Notes |
|---|---|---|
| `date` | `date` | |
| `status` | `DayStatus` | |
| `trade_count` | `int` | `len(trades)` |
| `points` | `float` | Sum of `points` across that day's trades (0 for `NO_DATA`/`NO_TRADE`) |

### `BacktestSummary`

Maps directly to FR-013's seven aggregate figures (the eighth, "number of days," is included here too — total of 8 fields from the spec plus the definition/range echo):

| Field | Type | Notes |
|---|---|---|
| `definition_code` | `str` | Echo of the requested `BacktestDefinition.code` |
| `start_date` | `date` | As requested (post-validation, FR-016) |
| `end_date` | `date` | As requested |
| `number_of_days` | `int` | Days with `status != NO_DATA` (Assumptions) |
| `number_of_trades` | `int` | `winning + losing + be` |
| `number_of_winning_positions` | `int` | `points > 0` |
| `number_of_losing_positions` | `int` | `points < 0` |
| `number_of_be` | `int` | `exit_reason == BREAK_EVEN` |
| `average_win` | `Optional[float]` | `None` when `number_of_winning_positions == 0` |
| `average_loss` | `Optional[float]` | Positive magnitude; `None` when `number_of_losing_positions == 0` |
| `final_result` | `float` | Sum of `points` across every trade in the range |

### `BacktestRunResult` (range/summary endpoint response shape)

| Field | Type | Notes |
|---|---|---|
| `summary` | `BacktestSummary` | |
| `days` | `List[DayResultSummary]` | One entry per day with `status != NO_DATA`, chronological |

## Relationships

```
BacktestDefinition (1, hardcoded) ─┬─> BacktestRunResult (per request)
                                    │     └─ BacktestSummary (1)
                                    │     └─ DayResultSummary (0..n)
                                    └─> DayResult (per request, single day)
                                          └─ Trade (0..n, chronological, non-overlapping)
```

## State transitions (`Trade`, within a single day's evaluation — not persisted, computed in one pass)

```
[no position, no candidate] --(FR-006: breach then close-back >= H1 low)--> [no position, candidate = reversal candle]
[no position, candidate] --(later candle's high does not exceed candidate's high, but stays >= H1 low, FR-006b)--> [no position, candidate = that later candle]
[no position, candidate] --(later candle closes < H1 low, FR-006b)--> [no position, no candidate] (that candle is itself a fresh breach)
[no position, candidate] --(later candle's high > candidate's high, i.e. breakout, entry within 20pts of H1 low and below take-profit, FR-006a/FR-007)--> [open, stop = entry-50]
[no position, candidate] --(breakout confirmed, FR-006b, but fails FR-006a's distance/take-profit bounds)--> [no position, no candidate] (resumes searching for a fresh breach)
[open, stop = entry-50] --(candle high >= entry+20, FR-008a)--> [open, stop = entry (break-even armed)]
[open, stop = entry-50] --(candle low <= entry-50)--> [closed: STOP_LOSS]
[open, stop = entry-50] --(candle high >= H1_high-10)--> [closed: TAKE_PROFIT]
[open, stop = entry (armed)] --(candle low <= entry)--> [closed: BREAK_EVEN]
[open, stop = entry (armed)] --(candle high >= H1_high-10)--> [closed: TAKE_PROFIT]
[open, any state] --(session end reached)--> [closed: END_OF_DAY]
[closed] --(FR-011: time remains)--> [no position, no candidate] --> (cycle repeats from FR-006)
```
