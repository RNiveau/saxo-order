# Phase 1 Data Model: MM50 Proximity Alert with Slope Filter

**Feature**: 019-mm50-slope-alert
**Date**: 2026-05-17

This feature is fully expressible within the existing data model. No new tables, no new dataclasses, no migration. The changes below are limited to:
1. One new enum member (`AlertType.MM50_TOUCH`).
2. One conventional structure for the alert's `data` payload (a `Dict[str, Any]`, which already accepts arbitrary shapes).

## 1. Enum: `AlertType` (model/enum.py)

**Change**: Add a new member.

```python
class AlertType(EnumWithGetValue):
    CONGESTION20 = "congestion20"
    CONGESTION100 = "congestion100"
    COMBO = "combo"
    DOUBLE_TOP = "double_top"
    DOUBLE_INSIDE_BAR = "double_inside_bar"
    CONTAINING_CANDLE = "containing_candle"
    MM50_TOUCH = "mm50_touch"  # NEW
```

**Validation**:
- The string value `"mm50_touch"` MUST be stable — it is persisted in DynamoDB, returned by the API, displayed in the UI, and used in Slack message keys. Renaming it later is a breaking change for stored alerts (their `alert_type` strings would no longer match the enum).
- Snake_case lowercase matches the convention of all existing members.

## 2. Entity: `Alert` (existing, in model/__init__.py)

**Change**: None to the dataclass. The new alert is just an `Alert` instance whose `alert_type` is `AlertType.MM50_TOUCH`.

```python
@dataclass
class Alert:
    alert_type: AlertType
    date: datetime.datetime
    data: Dict[str, Any]
    asset_code: str
    asset_description: str
    exchange: str = "saxo"
    country_code: Optional[str] = None
```

**Convention for `data` payload (new alert only)**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `close` | `float` | yes | The latest candle's close price (`candles[0].close`) at the moment the alert was emitted. |
| `ma50` | `float` | yes | The current MM50 value: `mobile_average(candles, 50)`. |
| `distance_pct` | `float` | yes | Signed percentage: `(close - ma50) / ma50 * 100`. Positive = close above MM50, negative = below. Helps the trader read the alert without recomputing. |
| `slope` | `float` | yes | MM50 slope on base 100 over the 10-candle window. Same value as `ma50_slope`. |
| `ma50_slope` | `float` | yes | Duplicate of `slope` under the existing field name so the frontend's MM50 Slope badge keeps working without code changes. |

**Why both `slope` and `ma50_slope`**: The `slope` field is the alert-defining slope (its presence in the payload makes the alert self-describing if the dedicated field name `slope` is ever read alone). The `ma50_slope` field is the per-asset slope already attached to every other alert type and consumed by the frontend's existing MM50 Slope badge. They will hold the same value here.

## 3. Storage: DynamoDB `alerts` table (existing, no change)

**Schema (unchanged)**:
- Partition key: `asset_code`
- Sort key: `country_code` (string `""` for assets without one — current behaviour)
- Attributes: `alerts` (list of alert dicts), `last_updated`, `last_run_at`, `ttl` (7-day expiration)

**Dedup rule (existing)**: When `store_alerts` is called and an alert of the same `alert_type` already exists with the same ISO-day date, the new one is discarded.

**Implication for this feature**: An asset that stays within 1% of MM50 with slope ≥ 3 for several days in a row will produce one `mm50_touch` alert per day. This is the same cadence as `combo`, `double_top`, etc.

## 4. API response shape (existing, no change)

The `AlertItemResponse` Pydantic model in `api/models/alerting.py`:
- `alert_type: str` — receives `"mm50_touch"`.
- `data: Dict[str, Any]` — receives the payload defined in §2.

No new Pydantic models are introduced; the existing free-form `data` dict carries the new fields.

## 5. Frontend type (existing, no change)

`AlertItem` in `frontend/src/services/api.ts` already types `alert_type: string` and `data: Record<string, any>`. No interface change required.

## State transitions

There are no state transitions in this feature. An alert is an instantaneous, idempotent observation: at detection time, the alert either exists for the asset/day or it does not. It expires automatically after 7 days via DynamoDB TTL.
