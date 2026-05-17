# Phase 0 Research: MM50 Proximity Alert with Slope Filter

**Feature**: 019-mm50-slope-alert
**Date**: 2026-05-17

The spec arrived with no `NEEDS CLARIFICATION` markers, and the implementation reuses well-established infrastructure. This document records the decisions made during planning and the alternatives considered, so reviewers can challenge them before implementation begins.

## 1. Where the detector lives

**Decision**: Add a new pure function `mm50_touch(candles: List[Candle]) -> Optional[Dict[str, float]]` to `services/indicator_service.py`. The function returns a dict with `close`, `ma50`, `distance_pct`, and `slope` when the conditions are met, or `None` otherwise.

**Rationale**:
- All existing indicators live in `services/indicator_service.py` (`mobile_average`, `slope_percentage`, `combo`, `containing_candle`, `double_top`, `double_inside_bar`, `bollinger_bands`, `macd0lag`, `average_true_range`). Keeping this one alongside them preserves architectural coherence.
- A pure function on `List[Candle]` is trivially unit-testable, mirrors the contract of every other detector, and respects Constitution principle I (no client/external calls in service layer).
- Returning a dict (rather than a bool or `Candle`) lets the caller embed the same fields in the Alert's `data` payload without recomputing them, and aligns with the existing pattern (`combo` returns `ComboSignal`, the congestion indicator returns tuples, etc.).

**Alternatives considered**:
- *Adding a method to `Candle` or `Alert`*: rejected — those are data classes, and putting business logic there would violate the model/service separation.
- *Extending `combo()`*: rejected — `combo` already does multi-factor scoring with BB/MACD/ATR. The new alert is a simpler standalone signal; conflating them would dilute both.
- *A separate file `services/mm50_touch_service.py`*: rejected — overkill for a ~10-line function.

## 2. Slope computation convention

**Decision**: Compute the slope identically to the existing `ma50_slope` field used by other alerts:

```python
ma50_last  = mobile_average(candles, 50)
ma50_first = mobile_average(candles[10:], 50)
slope      = slope_percentage(0, ma50_first, 10, ma50_last)
```

**Rationale**:
- The spec explicitly says "slope of a mobile average on a base 100" — `slope_percentage` returns the slope normalized to base 100 with `coefficient = 100.0 / y2`. Same scale.
- `run_detection_for_asset` already computes this exact value once per asset and stores it on every alert as `ma50_slope`. Reusing it (a) avoids drift between the new alert's slope and the existing `ma50_slope` field, and (b) saves one MM50 computation.
- The 10-candle window is the same window used by the `combo` detector (`candles[10:]`), so the resulting slope is interpretable in the same way as the slope already shown on the Alerts UI's MM50 Slope badge.

**Alternatives considered**:
- *Different window size (5 or 20 candles)*: rejected — would create a second, slightly-different "MM50 slope" number across the system, confusing for traders comparing the new alert to existing ones.
- *Linear regression slope*: rejected — `slope_percentage` is the project's canonical slope and trader-facing.

## 3. Proximity check

**Decision**: `abs(latest_close - ma50) / ma50 <= 0.01`, where `latest_close` is `candles[0].close` (newest candle per the Candle Ordering invariant). Boundary is inclusive.

**Rationale**:
- The user said "near (1%)". 1% is universally read as "within ±1%". Using the absolute relative distance handles both above and below the MM50 symmetrically, matching the trader's "rebond mm50" mental model where pullbacks can come from either side (especially during consolidation phases around the MM50).
- Using `close` (not high/low) matches how the `combo` detector tests price-vs-MM50.
- `mm50 > 0` is guaranteed for any real asset that produced 60 candles, so no division-by-zero guard is needed.

**Alternatives considered**:
- *Use high or low to be more permissive*: rejected — would emit more alerts but make "near" harder to interpret (an asset with a wick touching MM50 but closing far from it isn't really "near").
- *One-sided (close above MM50 only)*: rejected — would exclude valid pullback-from-below setups (price re-testing MM50 from below after a breakout).

## 4. Insufficient-history handling

**Decision**: When `len(candles) < 60`, the detector returns `None` immediately (without raising). The caller does not emit an alert. This mirrors the existing handling in `run_detection_for_asset` where `len(candles) >= 60` gates the `ma50_slope` computation.

**Rationale**:
- 50-period MA needs at least 50 candles to compute; the existing code uses 60 (50 + 10-period slope window) as the safety threshold. Same threshold here keeps the system coherent.
- Returning `None` (rather than raising `SaxoException`) avoids polluting logs for the many small-cap French stocks that legitimately have short histories. The existing `ma50_slope` block already logs a single warning per asset when it can't compute; reusing that path means no new log lines.

**Alternatives considered**:
- *Raise an exception and let the caller catch it*: rejected — adds noise. The condition is expected, not exceptional.
- *Use a lower threshold like 50*: rejected — without the extra 10 candles, the slope cannot be computed, so the alert cannot fire anyway.

## 5. Slack message group

**Decision**: Add a new key `"mm50_touch"` to the `slack_messages` dict in `run_alerting()`, with a French label "Indicator mm50_touch" header (consistent with the existing `Indicator combo`, `Indicator double_top`, etc. headers). Each message line is formatted as:

```
<asset name>: <date> close=<close> mm50=<mm50> dist=<distance_pct>% slope=<slope>%
```

**Rationale**:
- The Slack rendering pipeline in `run_alerting()` is a simple per-AlertType `if/elif` chain that builds grouped messages. Adding a new branch is the established pattern.
- The line format reuses the same key/value style as other alert messages, which makes the message readable at a glance for the trader scanning the daily summary.
- Naming the dict key `mm50_touch` matches the enum value (`AlertType.MM50_TOUCH = "mm50_touch"`), so the Slack header reads exactly as the alert type, and `formatAlertType` on the frontend produces the matching "Mm50 Touch" badge.

**Alternatives considered**:
- *Group into "congestion" or "combo"*: rejected — these are distinct setups; conflating them would confuse the daily summary.
- *Use a French label string like "Rebond MM50"*: rejected for the Slack header — current headers all use the snake_case alert type name; introducing a French label there would break the convention. The frontend badge already displays a friendly label via `formatAlertType`.

## 6. Frontend changes

**Decision**: No frontend changes are required.

**Rationale**:
- `frontend/src/components/AlertCard.tsx` uses `formatAlertType(alert.alert_type)` to convert any snake_case alert type into title-case (`mm50_touch` → `Mm50 Touch`). This works generically for any new enum value.
- `available_filters` on the alerts list endpoint is computed dynamically from the alerts present in DynamoDB (`alert_types = sorted(set(alert.alert_type.value for alert in alerts))` in `alerting_service.py`). The filter dropdown will pick up the new value automatically once alerts of the new type exist.
- `MA50 Slope` is already displayed on every alert card from `alert.data.ma50_slope`. The new alert's slope field is named `slope` (the alert-defining slope), but it will coincide with the per-asset `ma50_slope` already attached by `run_detection_for_asset` since the same convention is used. To keep the card's existing MA50 Slope badge correct, the new alert's `data` payload MUST also include the `ma50_slope` key — same value as `slope`, just under both names so the existing UI doesn't show "N/A".
- `frontend/src/utils/alertFilters.ts` dedups by `alert_type` string — no allowlist to maintain.

**Alternatives considered**:
- *Add a custom icon/styling for the new alert type*: deferred — can be done in a follow-up if visual differentiation is desired. Not required by the spec.

## 7. DynamoDB storage

**Decision**: No schema change. The new alert is appended to the existing `alerts` list in the same item (partition `asset_code`, sort `country_code`). Dedup is handled by `DynamoDBClient.store_alerts`'s existing same-alert-type-same-date logic.

**Rationale**:
- The `Alert` dataclass already supports arbitrary `data: Dict[str, Any]`, the DynamoDB table already stores a 7-day-TTL `alerts` list, and the dedup rule is per-alert-type. Adding a new alert type is fully transparent to persistence.

**Alternatives considered**:
- *Separate table or item*: rejected — would fragment the data and break the existing alerts UI which assumes one item per asset.

## 8. On-demand API

**Decision**: No router or service change. The `POST /api/alerts/run` endpoint calls `run_detection_for_asset` (the same function used by the cron), which will now also emit the new alert when conditions hold.

**Rationale**:
- Single point of detection logic (DRY). Once the new alert is wired into `run_detection_for_asset`, both the scheduled run and the on-demand run produce it identically.

**Alternatives considered**:
- *Skip on-demand and only run from cron*: rejected — would create an inconsistent user experience where the UI's "Run Alerts" button doesn't show alerts the cron will show later.

## Open questions

None. All decisions above either have a single reasonable choice or have been validated against existing code conventions.
