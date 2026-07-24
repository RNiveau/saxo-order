# Data Model: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

All entities below are in-memory / request-response only (see research.md §6 — no persistence of computed results). Nothing about the computed `Trade`/`DayResult`/summary output is written to DynamoDB or any other store; there is no lifecycle beyond the duration of a single API request. The one exception, added 2026-07-24, is the `BacktestCandleCache` entity at the end of this document: it persists the *raw Saxo candle data* a day's evaluation depends on, so repeated runs skip the Saxo call, while the strategy computation itself is still redone fresh every request (research.md §8).

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

### `BacktestParameters` (added 2026-07-21 — tunable thresholds, FR-025)

Per-run strategy thresholds, defaulting to the original hardcoded values. Not persisted; constructed from the optional query parameters and passed into `BacktestService.evaluate_day` / `run_range`, which thread it through the trade engine (`_OpenPosition` stop distance, `_DirectionSearch` entry-distance validity, `_evaluate_trades` take-profit levels, `_resolve_exit` break-even arming). A `params=None` call falls back to `BacktestParameters()` so existing call sites and tests are unchanged.

| Field | Type | Default | Notes |
|---|---|---|---|
| `stop_loss_points` | `float` | `50` | Initial stop distance from entry (FR-008 / FR-022) |
| `take_profit_offset_points` | `float` | `10` | Take-profit offset inside the opposite H1 level (FR-008 / FR-022) |
| `break_even_trigger_points` | `float` | `20` | Favorable move from entry that arms break-even (FR-008a / FR-022) |
| `max_entry_distance_points` | `float` | `20` | Max distance from the H1 level for a valid entry (FR-006a / FR-020a) |

Both directions use the same values. Positivity (`> 0`) is enforced at the API boundary (`Query(gt=0)`, FR-027), not on the dataclass — consistent with how validation lives in the service/router layer rather than the model.

### `Trade`

| Field | Type | Notes |
|---|---|---|
| `entry_time` | `datetime` | Time of the confirming (breakout) 5-minute candle, not the candidate reversal candle it broke past (FR-007 / FR-021) |
| `entry_price` | `float` | Long: the candidate's high, or the confirming candle's open if it gapped above (FR-007). Short: the candidate's low, or the confirming candle's open if it gapped below (FR-021). Gap-fill per FR-010 |
| `exit_time` | `datetime` | Required — a `Trade` is only ever constructed once it has closed (the implementation never stores an open position as a `Trade`), so there is no `None` case to represent |
| `exit_price` | `float` | Per FR-010 gap-fill rule (applies to both directions) |
| `exit_reason` | `ExitReason` | One of the four members above |
| `direction` | `Direction` | `Direction.BUY` for a long, `Direction.SELL` for a short (FR-024). Reuses the existing `model.enum.Direction`; defaults to `BUY` so the original long-only construction sites and tests remain valid |
| `points` | `float` | Signed P&L in points: `exit_price - entry_price` for a long, `entry_price - exit_price` for a short (FR-024), rounded consistent with existing `Candle` price rounding (`round(..., 4)` per `client/client_helper.py` convention). Positive = winning position regardless of direction |

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

Both directions are searched concurrently while flat, but at most one position is open at a time (FR-023). The implementation keeps two independent candidate searches (`_DirectionSearch` for `BUY` and for `SELL`); whichever confirms a valid entry first opens the single position, and both searches are reset. The long branch is unchanged from the original; the short branch is its mirror around the H1 high.

**Long branch** (the breach is now measured on the close, per the 2026-07-21 clarification; the rest is the original state machine):

```
[flat, no long candidate] --(FR-006: close below H1 low then close-back >= H1 low)--> [flat, long candidate = reversal candle]
[flat, long candidate] --(later candle high <= candidate high but close >= H1 low, FR-006b)--> [flat, long candidate = that later candle]
[flat, long candidate] --(later candle closes < H1 low, FR-006b)--> [flat, no long candidate] (that candle is itself a fresh breach)
[flat, long candidate] --(candle high > candidate high; entry within 20pts of H1 low and below H1_high-10, FR-006a/FR-007)--> [open LONG, stop = entry-50]
[flat, long candidate] --(breakout confirmed but fails FR-006a bounds)--> [flat, no long candidate]
[open LONG, stop = entry-50] --(candle high >= entry+20, FR-008a)--> [open LONG, stop = entry (armed)]
[open LONG] --(candle low <= stop)--> [closed: STOP_LOSS / BREAK_EVEN if armed]
[open LONG] --(candle high >= H1_high-10)--> [closed: TAKE_PROFIT]
```

**Short branch (mirror, FR-020–FR-022):**

```
[flat, no short candidate] --(FR-020: close above H1 high then close-back <= H1 high)--> [flat, short candidate = reversal candle]
[flat, short candidate] --(later candle low >= candidate low but close <= H1 high, FR-020)--> [flat, short candidate = that later candle]
[flat, short candidate] --(later candle closes > H1 high, FR-020)--> [flat, no short candidate] (that candle is itself a fresh breach above the high)
[flat, short candidate] --(candle low < candidate low; entry within 20pts of H1 high and above H1_low+10, FR-020a/FR-021)--> [open SHORT, stop = entry+50]
[flat, short candidate] --(breakdown confirmed but fails FR-020a bounds)--> [flat, no short candidate]
[open SHORT, stop = entry+50] --(candle low <= entry-20, FR-022)--> [open SHORT, stop = entry (armed)]
[open SHORT] --(candle high >= stop)--> [closed: STOP_LOSS / BREAK_EVEN if armed]
[open SHORT] --(candle low <= H1_low+10)--> [closed: TAKE_PROFIT]
```

**Shared (both directions):**

```
[open, any direction/state] --(session end reached)--> [closed: END_OF_DAY]
[closed] --(FR-011/FR-023: time remains)--> [flat, both searches reset] --> (cycle repeats, either direction may open next)
```

A same-candle double confirmation (both a valid long and a valid short on one candle) resolves to the long (FR-023); in practice this is unreachable because the move that breaches the opposite extreme reaches the open position's take-profit first.

The numeric magnitudes in the diagrams above (`entry-50`, `entry+50`, `H1_high-10`, `H1_low+10`, `entry+20`, `entry-20`, "within 20pts") show the **default** thresholds; each is the corresponding `BacktestParameters` field (FR-025), so a parametrized run substitutes its own values — e.g. `stop = entry - stop_loss_points`, take-profit at `H1_high - take_profit_offset_points`, break-even armed at `entry + break_even_trigger_points`, entry valid within `max_entry_distance_points` of the H1 level. The state machine is otherwise identical.

## `BacktestCandleCache` (persisted, added 2026-07-24 — FR-032–FR-036)

The one entity in this feature that is actually written to DynamoDB. One item per (backtest definition code, trading date) pair, storing the raw Saxo candle data that pair's day evaluation depends on — never the computed `Trade`/`DayResult`/summary (research.md §8, Clarifications Session 2026-07-24).

| Field | Type | Notes |
|---|---|---|
| `definition_code` | `str` (hash key) | `BacktestDefinition.code` (e.g. `"B9H"`) — each hardcoded backtest caches its candles separately, even where two definitions share the same underlying instrument/day |
| `trading_date` | `str`, ISO date (range key) | The trading day this entry's candles cover |
| `has_data` | `bool` | `False` when no 9:00–10:00 H1 reference candle was available for this day (FR-004/FR-034); when `False`, `h1_candle` and `m5_candles` are absent |
| `h1_candle` | `Optional[Dict]` | The 9:00–10:00 H1 reference candle (open/high/low/close/date), serialized the same way `Candle` fields are stored elsewhere in this codebase (`Decimal` for prices, per `DynamoDBClient._convert_floats_to_decimal`) |
| `m5_candles` | `Optional[List[Dict]]` | The 5-minute candles from 10:00 Paris local to end of day, same serialization as `h1_candle` |
| `cached_at` | `int` | Unix timestamp of first write, for observability only — not used for expiry (no TTL, FR-036) |

**No TTL attribute** — entries never expire (FR-036); a bad entry is corrected by manually deleting that item, not through any feature capability.

**Read/write path**: `api/services/backtest_service.py` calls `DynamoDBClient.get_cached_backtest_candles(definition_code, trading_date)` before fetching candles for a day; on a hit, it reconstructs the `Candle` objects (`model.workflow.Candle`) directly from the cached fields instead of calling `CandlesService.get_candles_in_window`. On a miss, it fetches from Saxo as today, then calls `DynamoDBClient.store_backtest_candles(...)` (or a `has_data=False` variant, FR-034) before proceeding to `evaluate_day`, which is unchanged and always runs against the resulting `Candle` list.
