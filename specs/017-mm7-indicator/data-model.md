# Data Model: MM7 Indicator & Workflow

## Changes to Existing Models

### `IndicatorType` (extends `model/workflow.py`)

New enum value added:

| Value | String key | Meaning |
|-------|-----------|---------|
| `MA7` | `"ma7"` | 7-period simple moving average workflow indicator |

Existing values unchanged. The string key `"ma7"` is used in `workflows.yml` configuration entries.

---

## New Engine Class

### `MA7Workflow` (in `engines/workflows.py`)

Parallel to `MA50Workflow`. Computes the 7-period simple moving average from the candle series and uses it as the reference level for proximity-based conditions.

| Attribute | Type | Description |
|-----------|------|-------------|
| `indicator_value` | `float` | The 7-period moving average computed at workflow initialization |
| `logger` | `Logger` | Logger instance tagged `"ma7-workflow"` |

**Methods** (same contract as `MA50Workflow`):

- `init_workflow(indicator, candles)` — computes `mobile_average(candles, 7)` and stores result
- `below_condition(candle, spread, element?)` — true if `candle.close` or `candle.higher` is within `[indicator_value - spread, indicator_value]`
- `above_condition(candle, spread, element?)` — true if `candle.close` or `candle.lower` is within `[indicator_value, indicator_value + spread]`

---

## Candle Count Requirements

The engine requests a fixed number of candles per indicator type to ensure enough history is available before computation.

| Indicator | Weekly candles | Hourly candles (× UnitTime multiplier) |
|-----------|---------------|---------------------------------------|
| MA50      | 55            | 55 × multiplier                       |
| **MA7**   | **12**        | **12 × multiplier**                   |
| BB (20)   | 21            | 21 × multiplier                       |

The buffer of 5 extra candles (7 + 5 = 12) matches the MA50 pattern (50 + 5 = 55).

---

## No Persistent Storage Changes

This feature introduces no new DynamoDB tables, no new fields on existing records, and no schema migrations. The `workflows.yml` configuration file is the only place an end-user references the new indicator, via `name: ma7`.
