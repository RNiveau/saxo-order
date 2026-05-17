# Quickstart: MM50 Proximity Alert with Slope Filter

**Feature**: 019-mm50-slope-alert
**Date**: 2026-05-17

This walks a developer through verifying the feature end-to-end after implementation. It assumes the changes described in plan.md, data-model.md, and contracts/mm50-touch-alert.md have been merged.

## 1. Unit-test the detector

```bash
poetry run pytest tests/services/test_indicator_service.py -k mm50_touch -v
```

Expected: passes for the boundary cases listed in `contracts/mm50-touch-alert.md` §1 — matching when distance ≤ 1% and slope ≥ 3, not matching otherwise, returning `None` (no exception) when fewer than 60 candles are available.

## 2. Unit-test the pipeline wiring

```bash
poetry run pytest tests/saxo_order/commands/test_alerting.py -k mm50_touch -v
```

Expected: when `run_detection_for_asset` is fed a candle series that satisfies the detector, the returned `asset_alerts` list contains an `Alert` with `alert_type == AlertType.MM50_TOUCH` and the `data` payload includes `close`, `ma50`, `distance_pct`, `slope`, and `ma50_slope`.

## 3. Run the daily alerting cron locally (single asset)

```bash
poetry run k-order alerting --asset SAN:xpar
```

(Adapt the CLI command to the project's actual flag if `--asset` isn't the right name — the goal is the existing single-asset code path.) Check the output:

- Logs include `scan Sanofi SA`.
- If Sanofi's daily close is within 1% of its MM50 and the MM50 slope is ≥ 3, the asset's stored alerts now contain a `mm50_touch` entry.
- The Slack `#stock` test channel receives an `Indicator mm50_touch` block.

## 4. Verify the API surface

```bash
poetry run python run_api.py &
curl -s -X POST http://localhost:8000/api/alerts/run \
  -H 'Content-Type: application/json' \
  -d '{"asset_code": "SAN", "country_code": "xpar", "exchange": "saxo"}' | jq
```

Expected: if the conditions are met, the JSON response's `alerts` array contains an entry with `alert_type: "mm50_touch"` and the `data` payload defined in §2 of `data-model.md`.

```bash
curl -s 'http://localhost:8000/api/alerts' | jq '.available_filters.alert_types'
```

Expected: the array now includes `"mm50_touch"` (once at least one such alert has been stored).

## 5. Verify the frontend rendering

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173/alerts` and confirm:

- An alert card with the badge `Mm50 Touch` appears for any asset that produced the alert.
- The MM50 Slope badge reads correctly (`+X.X%` in green for the trader's upward trend).
- Expanding the `Data` section shows the full JSON payload (`close`, `ma50`, `distance_pct`, `slope`, `ma50_slope`).
- The alert-type filter dropdown now lists `mm50_touch` (or its formatted variant) as a selectable filter.

## 6. Confirm dedup

Run the cron twice on the same asset on the same day:

```bash
poetry run k-order alerting --asset SAN:xpar
poetry run k-order alerting --asset SAN:xpar
```

Expected: the stored alert count for `mm50_touch` does not double. A single alert per asset-day per type is preserved (same as the other alert types).

## 7. Confirm graceful handling of short history

Pick a recently-listed stock with fewer than 60 daily candles (or temporarily reduce the fetch count in a test).

Expected: the asset is processed without raising; no `mm50_touch` alert is emitted; a warning may be logged consistent with the existing `ma50_slope` warning path.

## 8. Deploy

```bash
./deploy.sh
```

After deploy, the next scheduled run (6:15 PM Paris) will emit the new alert type wherever applicable. Monitor the Slack `#stock` channel — the new `Indicator mm50_touch` block should appear if any of the ~330 scanned French stocks satisfy the conditions.

## Rollback

The feature is enum-additive. To roll back:
1. Revert the code changes (one commit).
2. Stored alerts with `alert_type: "mm50_touch"` will TTL out within 7 days.
3. No DynamoDB schema migration is required either way.
