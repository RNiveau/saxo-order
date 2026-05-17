# Contract: MM50 Touch Alert

**Feature**: 019-mm50-slope-alert
**Date**: 2026-05-17

This feature does not introduce a new HTTP endpoint. It adds a new alert type that flows through three existing contracts. This document specifies the new behavior at each surface.

## 1. Detector contract (internal — `services/indicator_service.py`)

### Function signature

```python
def mm50_touch(candles: List[Candle]) -> Optional[Dict[str, float]]:
    """
    Detect whether the latest candle is within 1% of its MM50 while the
    MM50 slope (base-100, 10-candle window) is >= 3.

    Returns a dict {close, ma50, distance_pct, slope} when both conditions
    hold, or None otherwise (including when there are fewer than 60 candles).
    """
```

### Behavioral guarantees

| Input | Output |
|-------|--------|
| `len(candles) < 60` | `None` (no exception raised). |
| `len(candles) >= 60`, `abs(close - ma50) / ma50 > 0.01` | `None`. |
| `len(candles) >= 60`, distance ≤ 1%, slope < 3 | `None`. |
| `len(candles) >= 60`, distance ≤ 1%, slope ≥ 3 | `{"close": float, "ma50": float, "distance_pct": float, "slope": float}` with `distance_pct = (close - ma50) / ma50 * 100`. |
| Boundary: `distance == 0.01 * ma50` (exactly 1%) | Match — returns dict. |
| Boundary: `slope == 3.0` (exactly) | Match — returns dict. |
| `candles[0].close == ma50` | Match — returns dict with `distance_pct == 0.0`. |
| `close < ma50` (close below MM50, within 1%, slope ≥ 3) | Match — returns dict with negative `distance_pct`. |

### Purity guarantees

- No I/O.
- No mutation of `candles` or its elements.
- Determined entirely by the candle series.

## 2. Pipeline contract (internal — `saxo_order/commands/alerting.py::run_detection_for_asset`)

After existing CONGESTION/COMBO/DOUBLE_TOP/etc. detection blocks, add a new block:

```python
mm50_touch_result = indicator_service.mm50_touch(candles)
if mm50_touch_result is not None:
    asset_alerts.append(
        Alert(
            alert_type=AlertType.MM50_TOUCH,
            date=datetime.datetime.now(),
            data={
                **mm50_touch_result,
                "ma50_slope": ma50_slope,
            },
            asset_code=asset_code,
            asset_description=asset_description,
            exchange=exchange,
            country_code=country_code,
        )
    )
```

The `data` payload merges the detector's output (`close`, `ma50`, `distance_pct`, `slope`) with `ma50_slope` (the value already computed at the top of `run_detection_for_asset` — equal to `slope` here, but added under both names so the existing frontend MM50 Slope badge keeps working).

### Guarantees

- Reuses the candle series already loaded — no extra Saxo API calls.
- Reuses the `ma50_slope` already computed at the top of the function — no duplicate MM50 work.
- Dedup is handled by `DynamoDBClient.store_alerts` (same-alert-type-same-date rule).
- Failure to detect (returns `None`) is silent; the workflow continues to other detectors and other assets.

## 3. Slack output contract (internal — `run_alerting`)

The `slack_messages` dict gains a new key:

```python
slack_messages: Dict[str, List[str]] = {
    "double_top": [],
    "container_candle": [],
    "combo": [],
    "double_inside_bar": [],
    "congestion": [],
    "mm50_touch": [],   # NEW
}
```

And a new `elif` branch in the per-alert dispatch:

```python
elif alert.alert_type == AlertType.MM50_TOUCH:
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    close = alert.data.get("close")
    ma50 = alert.data.get("ma50")
    dist = alert.data.get("distance_pct")
    slope = alert.data.get("slope")
    slack_messages["mm50_touch"].append(
        f"{asset['name']}: {date} close={close} ma50={ma50} "
        f"dist={dist:.2f}% slope={slope:.2f}%"
    )
```

When at least one `mm50_touch` alert is collected, the Slack summary will include an `Indicator mm50_touch` block alongside the existing `Indicator combo`, `Indicator double_top`, etc.

## 4. API contract (existing — `POST /api/alerts/run` and `GET /api/alerts`)

**No change to request/response schemas.** The new alert flows through the existing `AlertItemResponse`:

```json
{
  "id": "SAN_xpar",
  "alert_type": "mm50_touch",
  "asset_code": "SAN",
  "asset_description": "Sanofi SA",
  "exchange": "saxo",
  "country_code": "xpar",
  "date": "2026-05-17T18:15:00+02:00",
  "data": {
    "close": 92.18,
    "ma50": 91.55,
    "distance_pct": 0.688,
    "slope": 4.21,
    "ma50_slope": 4.21
  },
  "age_hours": 0,
  "tradingview_url": null
}
```

`GET /api/alerts` will also surface `"mm50_touch"` automatically in `available_filters.alert_types` once at least one such alert exists, because the filter list is computed dynamically from the stored alerts.

## 5. DynamoDB contract (existing — `alerts` table)

**No change to schema.** A new entry of shape:

```json
{
  "alert_type": "mm50_touch",
  "date": "<ISO 8601>",
  "data": { "close": ..., "ma50": ..., "distance_pct": ..., "slope": ..., "ma50_slope": ... }
}
```

is appended to the asset's `alerts` list, deduplicated by (`alert_type`, ISO-day-of-`date`).

## 6. Frontend contract (existing — `AlertCard.tsx`)

**No change to component code.**

- Type badge: `formatAlertType("mm50_touch")` → `"Mm50 Touch"`.
- MA50 Slope badge: reads `alert.data?.ma50_slope` — works because the pipeline writes `ma50_slope` into the payload.
- Data section: expanded JSON view shows all fields verbatim.

## 7. Constants

| Constant | Value | Scope |
|----------|-------|-------|
| MM50 period | 50 | `mobile_average(candles, 50)` — already a constant in the codebase. |
| Slope window | 10 candles | Matches `combo()` and existing `ma50_slope` computation. |
| Proximity threshold | 1% (`0.01`) | Feature-defining constant. Live as a module-level constant `MM50_TOUCH_PROXIMITY = 0.01` in `services/indicator_service.py` for testability and self-documentation. |
| Slope threshold | 3 | Feature-defining constant. Live as `MM50_TOUCH_SLOPE_MIN = 3.0` in `services/indicator_service.py`. |
| Minimum candles | 60 | Same threshold the existing pipeline uses for `ma50_slope`. |
