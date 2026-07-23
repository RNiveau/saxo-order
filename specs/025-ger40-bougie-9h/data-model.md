# Data Model: Hardcoded "GER40 Bougie de 9h" Backtest (double take-profit)

All entities are in-memory / request-response only (inherits spec 021 — no persistence). This feature **adds no new response model and no new domain dataclass**; it extends the existing `model/backtest.py` types and adds one `Strategy` enum member. `Trade`, `DayResult`, `DayResultSummary`, `BacktestSummary`, `BacktestRunResult` are unchanged in shape (FR-G10). See `specs/021-backtest-menu-hardcoded/data-model.md` for their full field definitions.

## New enum member (`model/enum.py`)

### `Strategy.G9H`

Add `G9H = "Bougie de 9h GER40"` alongside the existing `B9H = "Bougie de 9h"` and `B9HTC = "Bougie de 9h (time cut)"`. Reused as the `name` of the new `BacktestDefinition` (Constitution II — no hardcoded strategy string). No new `ExitReason` or `DayStatus` member is needed: the double-TP outcomes map onto the existing `TAKE_PROFIT` / `BREAK_EVEN` / `STOP_LOSS` / `END_OF_DAY` reasons (FR-G07).

## Extended entity — `BacktestDefinition` (`model/backtest.py`)

New optional fields, all defaulting to the CAC40 behavior so `B9H`/`B9HTC` are unchanged:

| Field | Type | Default | Notes |
|---|---|---|---|
| `code` | `str` | — | existing |
| `name` | `str` | — | existing (`Strategy.*.value`) |
| `display_name` | `str` | — | existing |
| `instrument` | `str` | — | existing |
| `time_cut_minutes` | `Optional[int]` | `None` | existing (time-cut variant) |
| `time_cut_min_favorable_points` | `Optional[float]` | `None` | existing |
| **`default_parameters`** | `BacktestParameters` | `field(default_factory=BacktestParameters)` | Per-definition threshold defaults (FR-G09 / research §5). CAC40 uses the dataclass defaults (50/10/20/20); GER40 supplies `BacktestParameters(150, 10, 50, 40)`. Resolved against per-run overrides in the router. |
| **`double_take_profit`** | `bool` | `False` | When `True` (GER40), every entry opens **two lots** with the split-exit / take-first-then-break-even mechanic (FR-G02–FR-G04). When `False`, single-lot behavior exactly as today. Also selects the points-sign summary classification (FR-G08). |
| **`first_target_fraction`** | `Optional[float]` | `None` | The TP1 fraction of the H1 range; `0.5` for GER40 ⇒ TP1 = `h1_low + 0.5·(h1_high − h1_low)` = midpoint (FR-G03). `None` when `double_take_profit` is `False`. A fixed strategy property, not a `BacktestParameter`. |
| **`stop_from_reference_level`** | `bool` | `False` | When `True` (GER40), the initial stop is `stop_loss_points` **beyond the H1 reference level** (H1 low − 150 long / H1 high + 150 short, FR-G05); when `False`, `stop_loss_points` from **entry** (CAC40, unchanged). |

`BACKTEST_DEFINITIONS` gains a third entry:

```python
BacktestDefinition(
    code="G9H",
    name=Strategy.G9H.value,
    display_name="GER40 Bougie de 9h",
    instrument="GER40.I",
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    double_take_profit=True,
    first_target_fraction=0.5,
    stop_from_reference_level=True,
)
```

## `BacktestParameters` (`model/backtest.py`) — unchanged shape

The four tunable thresholds keep the same dataclass and the same **CAC40 defaults** (50/10/20/20). GER40 does **not** change these dataclass defaults; it supplies its own via `BacktestDefinition.default_parameters`. `stop_loss_points` is reinterpreted per definition: distance from entry (CAC40) or from the H1 reference level (GER40, via `stop_from_reference_level`). The 50% first-target fraction and the two-lot count are **not** parameters (FR-G09) — they live on the definition.

## `Trade` (`model/backtest.py`) — unchanged shape, new semantics for double-TP

Same seven fields (`entry_time`, `entry_price`, `exit_time`, `exit_price`, `exit_reason`, `direction`, `points`). For a two-lot GER40 position, the fields carry the **aggregated** position (FR-G07):

| Field | Double-TP meaning |
|---|---|
| `entry_time` / `entry_price` | The single confirmed entry (both lots enter here). |
| `exit_time` / `exit_price` | The **runner's** final exit (TP2 / break-even / stop / end-of-day). For a both-lots-stop-out (no TP1), this is the shared stop level. |
| `exit_reason` | How the **position finally closed** (runner's exit): `TAKE_PROFIT` (runner hit TP2), `BREAK_EVEN` (runner closed at its moved-to-entry stop after TP1, or both lots at break-even), `STOP_LOSS` (both lots stopped before any TP), `END_OF_DAY`. |
| `points` | **Net points = lot-A P&L + lot-B P&L**, computed explicitly (research §2). Not `exit_price − entry_price` in general. Examples: both-lots stop-out = `2·(stop − entry)`; TP1-then-TP2 = `(TP1 − entry) + (TP2 − entry)`; TP1-then-break-even = `(TP1 − entry) + ≈0` (net-positive). |

**Validation rules** (enforced in `api/services/backtest_service.py`, not on the dataclass — consistent with spec 021):
- `entry_time < exit_time`.
- For double-TP, `points` is the summed net and may differ from the price-difference formula — the aggregated `Trade` is built by a dedicated close helper (`_close_double_trade`), not the single-lot `_close_trade`.

## Engine state — `_OpenPosition` (`api/services/backtest_service.py`) — extended

New optional fields on the existing class (all inert when `double=False`):

| Field | Type | Notes |
|---|---|---|
| `double` | `bool` | True for a GER40 position (from `definition.double_take_profit`). |
| `first_target_level` | `Optional[float]` | TP1 = H1 midpoint (long and short share the level). |
| `first_target_taken` | `bool` (default `False`) | Set when lot A exits at TP1; arms the runner's break-even (FR-G04). |
| `banked_points` | `float` (default `0.0`) | Lot-A realised points, added to the runner's points at close. |
| `initial_stop_price` | `float` | Absolute initial stop level. For GER40 = H1 low − 150 (long) / H1 high + 150 (short). For CAC40 the existing `stop_loss_points`-from-entry computation is kept (this field unused). |

`stop_level` property gains a reference-based branch: if `be_armed` → entry; elif `stop_from_reference_level` → `initial_stop_price`; else → `entry ± stop_loss_points` (unchanged CAC40 path).

## State transitions — double-TP position (GER40), within a single day

The **entry** machinery (breakout/reversal detection, entry validity, one-position-at-a-time) is identical to spec 021 (`_DirectionSearch`), judged against the full take-profit level (TP2) for validity (FR-G03 / spec 021 FR-006a). Only the **open-position** exit handling changes. Long shown; short is the mirror around the H1 high.

```
[entry confirmed] --> [open, 2 lots, stop = H1_low - 150, TP1 = midpoint, TP2 = H1_high - 10]

Both lots open (first_target_taken = False), per candle, in order:
  - candle low <= stop        --> [closed: STOP_LOSS (or BREAK_EVEN if +50 already armed)]
                                   net points = 2 * (stop - entry)            # "SL is x2"
  - candle high >= TP1         --> lot A exits at TP1 (gap-fill FR-010):
                                   banked_points = TP1 - entry
                                   first_target_taken = True; be_armed = True # FR-G04
                                   (if same candle high >= TP2, runner also exits at TP2 -> closed TAKE_PROFIT,
                                    net = (TP1-entry)+(TP2-entry))
  - candle high >= entry + 50  --> be_armed = True (shared stop -> entry, from next candle)  # FR-G06

Runner only (first_target_taken = True), stop at entry (break-even), per candle:
  - candle low <= entry        --> [closed: BREAK_EVEN] net = banked_points + (fill - entry)  # ~banked (net-positive)
  - candle high >= TP2         --> [closed: TAKE_PROFIT] net = banked_points + (TP2 - entry)

Any state:
  - session end                --> [closed: END_OF_DAY]
                                   both-lots open: net = 2 * (close - entry)
                                   runner only:   net = banked_points + (close - entry)
```

Same-candle precedence (extends spec 021 FR-009): while both lots are open, **stop beats TP1** on a candle that would reach both (conservative). Once only the runner remains, its break-even stop beats TP2 on a same-candle collision (unreachable in practice since TP2 > entry for a long). TP1-and-TP2 on the same candle fills lot A at TP1 and the runner at TP2.

## Response mapping — `BacktestDefinitionResponse` (`api/models/backtest.py`)

Extended so the frontend can pre-fill per-definition defaults (research §5):

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | existing |
| `display_name` | `str` | existing |
| `instrument` | `str` | existing |
| **`default_parameters`** | `BacktestParametersResponse` | echoes the definition's `default_parameters` (four floats) |
| **`double_take_profit`** | `bool` | lets the frontend label/hint the two-lot strategy (optional UI use) |

`TradeResponse`, `DayDetailResponse`, `DayResultSummaryResponse`, `BacktestSummaryResponse`, `BacktestRunResponse` are **unchanged** (FR-G10).

## Relationships

```
BacktestDefinition (3 hardcoded: B9H, B9HTC, G9H)
  ├─ default_parameters : BacktestParameters (per definition)
  ├─ double_take_profit / first_target_fraction / stop_from_reference_level (G9H only)
  └─> BacktestRunResult / DayResult (per request)
        └─ Trade (0..n; for G9H each is one aggregated 2-lot position)
```
