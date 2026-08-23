# Data Model: Weekly-Timeframe Combo Detection

**Feature**: 029-combo-weekly-timeframe | **Date**: 2026-08-23

No new table, no schema migration, no Pulumi change. One new enum member, one new settings
structure, and two additional keys inside an existing free-form map.

---

## 1. `AlertType.COMBO_WEEKLY` (new enum member)

`model/enum.py`

| Field | Value |
|-------|-------|
| Member | `COMBO_WEEKLY` |
| Stored value | `"combo_weekly"` |

Joins the nine existing members. The stored value is what lands in DynamoDB, what the API's
`alert_type` filter accepts, and what the frontend label map keys on.

**Validation**: `EnumWithGetValue` already rejects unknown values on read, so a stored alert of this
type is only readable once the member exists — which is why no backfill is possible or intended.

---

## 2. `ComboSettings` (new frozen dataclass)

`services/indicator_service.py`

| Field | Type | Daily | Weekly | Meaning |
|-------|------|-------|--------|---------|
| `min_candles` | `int` | 235 | 60 | Bars required before the indicator will run |
| `ma50_slope_min` | `float` | 3.0 | *calibrated (R8)* | Slope floor that admits a direction |
| `ma50_slope_strong` | `float` | 10.0 | *calibrated (R8)* | Slope above which `strong_ma50` scores |
| `bb_flat_slope_max` | `float` | existing | *calibrated (R8)* | Ceiling under which a band counts as flat |
| `atr_bb_margin` | `float` | existing | existing | ATR multiple defining "near the band" |
| `atr_ma50_margin` | `float` | existing | existing | ATR multiple defining "near the MA50" |
| `strong_signal_min` | `int` | 4 | 3 | Criteria met before the signal is `STRONG` (R3) |
| `use_macd` | `bool` | `True` | `False` | Whether the `macd` criterion participates (R2) |

Exposed as `COMBO_SETTINGS: Dict[UnitTime, ComboSettings]` keyed by `UnitTime.D` / `UnitTime.W`.

**Invariants**:
- `strong_signal_min` ≤ number of active criteria (5 when `use_macd`, else 4). A settings object
  violating this makes `STRONG` unreachable or trivial; validated in tests, not by `assert`
  (Constitution II.5).
- `min_candles` ≥ 60 always; ≥ 235 whenever `use_macd` is `True`, since `macd0lag` raises below that.

**Relationships**: consumed by `combo()`, `_ComboContext`, `_combo_for_direction`. No persistence.

---

## 3. Weekly combo alert (existing `Alert`, new payload keys)

`model/__init__.py` — the dataclass is unchanged. The new alert differs only in its `alert_type`
and in two additional keys inside the existing free-form `data` map.

| Attribute | Source | Notes |
|-----------|--------|-------|
| `alert_type` | `AlertType.COMBO_WEEKLY` | — |
| `date` | scan timestamp | Unchanged convention; **not** the de-dup key for this type (R4) |
| `asset_code`, `country_code`, `asset_description`, `exchange` | scanned asset | `exchange` stays explicit (Constitution V.4) |
| `data.price` | `ComboSignal.price` | Trigger price, or the pending price when untriggered |
| `data.direction` | `Direction.value` | `"Buy"` / `"Sell"` — read unchanged by `_alert_direction` |
| `data.strength` | `SignalStrength.value` | Banded per the reduced set (R3) |
| `data.has_been_triggered` | `ComboSignal` | — |
| `data.details` | `ComboSignal.details` | Four criteria for weekly, five for daily |
| `data.ma50_slope` | scan | Same key the digest already reads |
| **`data.weekly_bar_date`** | **new** | ISO date of the weekly bar's first session — the de-dup dimension |
| **`data.timeframe`** | **new** | `UnitTime.W.value` — makes the timeframe explicit to consumers reading `data` |

**State**: alerts are append-only records inside one item per asset. A weekly alert is never
updated in place; a direction change on the same bar appends a second record.

**TTL**: the item's 7-day TTL is refreshed only when a write actually happens, so an asset whose
only alert is a persisting weekly combo stops refreshing for the rest of that week. A weekly bar
spans at most 5 scans, inside the window — the margin is adequate but now load-bearing (R4).

---

## 4. Alert de-duplication signature (new model-layer function)

`model/` — used by `DynamoDBClient.store_alerts` for both stored items and incoming alerts (R4).

| Alert type | Signature |
|------------|-----------|
| `COMBO_WEEKLY` | `(alert_type, data["weekly_bar_date"], data["direction"])` |
| every other type | `(alert_type, date.date().isoformat())` — byte-identical to today |

`weekly_bar_date` is itself normalised with `.date().isoformat()` when the alert is built, so the
two sides of the comparison cannot disagree over a time component (see R4).

**Validation / degradation**: a weekly alert whose `data` lacks either key falls back to the default
signature rather than raising, preserving the existing "malformed stored row is skipped, never
fatal" behaviour of `store_alerts`.

**Consequences**:
- Same bar, same direction, five consecutive scans → one record (SC-002).
- Same bar, direction flips → two records.
- New week → new record, whatever the direction.

---

## 5. Configuration

None. The feature introduces no configuration key — see research.md R10 for why the earlier
`weekly_combo_enabled` toggle was dropped, and R9 for why the calibrated thresholds stay in code.
