# Phase 1 Data Model: "GER40 Combo" Backtest

Nothing here is a new persisted entity. The feature adds two fields to an
existing dataclass, one enum value, three enum entries, one in-memory
value object, and one new cache item shape in an existing table.

---

## 1. `BacktestDefinition` (`model/backtest.py`) — EDIT

Two additive fields, both defaulting to today's behavior so all six
existing definitions are untouched.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `unit_time` | `Optional[UnitTime]` | `None` | The candle timeframe the strategy is evaluated on. `None` = the session-range strategy's implicit "H1 reference scanned with 5-minute candles". Set to `UnitTime.M5` / `M15` / `H1` on the combo definitions. |
| `combo_entry` | `bool` | `False` | Selects the combo strategy. When `True` the definition is driven by the indicator, not by a reference range. |

**`__post_init__` validation** (the class already rejects unhonorable
flag combinations at registration time; these follow the same pattern):

- `combo_entry` requires `unit_time` — the strategy has no timeframe to
  evaluate on otherwise.
- `combo_entry` is incompatible with every session-range flag:
  `min_h1_range_points`, `structural_stop`, `impulsive_candle_points`,
  `last_entry_time`, `max_daily_losses`, `time_cut_minutes`,
  `stop_from_reference_level`, `first_target_fraction`,
  `runner_extension_points`, `trail_to_first_target_points`. Each would
  be a silent no-op, which is exactly what this `__post_init__` exists to
  prevent.
- `combo_entry` requires `double_take_profit=True` — the two-lot
  accounting is FR-C05, and `build_lot_model` keys off that flag.
  Combined with the two bullets above, a combo definition uses a **new
  `ComboTwoLot`** lot model (§4) rather than `TwoLot`/`ExtendedTwoLot`,
  whose targets are H1-range-derived.

### The three registered definitions (`definitions.py`)

| code | `Strategy` | display_name | instrument | market | unit_time | default `stop_loss_points` |
|---|---|---|---|---|---|---|
| `C5M` | `Strategy.C5M` | GER40 Combo 5m | `GER40.I` | `EuCfdMarket` | `UnitTime.M5` | 50 |
| `C15M` | `Strategy.C15M` | GER40 Combo 15m | `GER40.I` | `EuCfdMarket` | `UnitTime.M15` | 50 |
| `C1H` | `Strategy.C1H` | GER40 Combo H1 | `GER40.I` | `EuCfdMarket` | `UnitTime.H1` | 50 |

All three set `combo_entry=True`, `double_take_profit=True`. The other
three `BacktestParameters` fields keep their dataclass defaults and are
never read (FR-C16).

---

## 2. Enums (`model/enum.py`) — EDIT

```python
class ExitReason(EnumWithGetValue):
    ...
    END_OF_RUN = "end_of_run"      # NEW - FR-C12
```

`END_OF_DAY` is unchanged and stays the session backtests' fallback.

```python
class Strategy(EnumWithGetValue):
    ...
    C5M = "Combo GER40 5m"         # NEW
    C15M = "Combo GER40 15m"       # NEW
    C1H = "Combo GER40 h1"         # NEW
```

`SignalStrength` (`WEAK` / `MEDIUM` / `STRONG`) and `UnitTime`
(`M5` / `M15` / `H1`) already carry everything needed — no change.

---

## 3. `Position` (`api/services/backtest/position.py`) — EDIT

| Change | Detail |
|---|---|
| `h1_high`, `h1_low` | `float` → `Optional[float] = None`. A combo position has no reference range. |
| `structural_level` | Raises `SaxoException` when either level is `None` instead of returning a wrong number. **Not `assert`** (constitution §II.5). Only `StructuralStop` / `ImpulsiveStop` read it, and neither is in the combo chain. |
| `retarget(first_target, take_profit)` | **NEW.** Sets `first_target_level` and `take_profit_level`. Called once per candle by `ComboStrategy` before `resolve_exit`, which is what makes FR-C07's targets move. Never called by the session-range strategy. |

Everything else is reused verbatim: `initial_stop_price` carries FR-C06,
`stop_level` returns `entry_price` once `be_armed` (FR-C08),
`banked_points` / `first_target_taken` carry the two-lot accounting, and
`close()` delegates points to the lot model.

---

## 4. `ComboTwoLot` (`api/services/backtest/lots.py`) — NEW

```python
@dataclass(frozen=True)
class ComboTwoLot(TwoLotAccounting):
    """Two lots whose targets come from the indicator, not the H1 range:
    the strategy retargets the position every candle, so `targets` has
    nothing to place at entry time."""

    def targets(self, side, h1_high, h1_low, take_profit_level) -> Targets:
        raise SaxoException(
            "combo targets are set per candle by Position.retarget"
        )
```

Inherits `total_points` (the "SL is x2" accounting, FR-C05) and
`classify` (by net-points sign, FR-C15) from `TwoLotAccounting`
unchanged. Its `targets` is unreachable because `ComboStrategy` never
calls it — raising states that as an invariant rather than returning a
meaningless level.

---

## 5. `BandLevels` (`api/services/backtest/bands.py`) — NEW, in-memory

```python
@dataclass(frozen=True)
class BandLevels:
    mm20: float          # bollinger_bands(window, 2.0).middle  -> TP1
    upper: float         # .up                                  -> TP2 long
    bottom: float        # .bottom                              -> TP2 short

    def opposite(self, side: Side) -> float:
        return self.upper if side.is_long else self.bottom
```

Computed per candle from the newest-first window. Not persisted, not
serialized.

---

## 6. `PendingEntry` (`api/services/backtest/signals.py`) — NEW, in-memory

The one-candle pending stop level of FR-C03/FR-C04.

| Field | Type | Meaning |
|---|---|---|
| `level` | `float` | `ComboSignal.price` — the signal candle's high (buy) / low (sell). |
| `side` | `Side` | From `ComboSignal.direction`. |
| `signal_candle` | `Candle` | The candle the indicator fired on — the reference for the 50-point stop (FR-C06), **not** the fill candle. |

Lives for exactly one candle: `ComboEntrySearch` fills it or drops it on
the next candle, before evaluating that candle's own signal.

---

## 7. Cache item — NEW shape, existing table

Written and read **only** through two new `DynamoDBClient` methods
(`store_backtest_series`, `get_cached_backtest_series`), never by
reaching into the client (constitution §I).

| Attribute | Type | Notes |
|---|---|---|
| hash key | String | `"{instrument}:{session_key(market)}:{ut.value}:v1"` — a new namespace; existing `"{instrument}:{session}:v2"` entries are untouched. |
| range key | String | `trading_date.isoformat()` — same granularity as today. |
| `has_data` | Bool | `False` records a genuine "Saxo has nothing for this day". |
| `candles` | List | Serialized `Candle` dicts for that trading day at that timeframe, chronological. |

Failure policy is inherited from `CandleSource` and re-stated because it
is a correctness rule, not an optimization: a genuine empty day is
cached; a `SaxoException` (token, rate limit, network) is **never**
cached; any cache failure in either direction degrades to going to Saxo.

---

## 8. Unchanged models

`BacktestParameters`, `Trade`, `DayResult`, `DayResultSummary`,
`BacktestSummary`, `BacktestRunResult`, `CachedDayCandles`, `Candle`,
`ComboSignal`, `Targets`, `Side` — all reused as-is.

`DayResultSummary.h1_high` / `h1_low` / `h1_open` are simply `None` on a
combo day; `mm50_slope`, `adx14` and `overnight_gap` are still populated
because they measure the instrument, not the strategy (research R8).
