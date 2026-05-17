# Feature Specification: MM50 Proximity Alert with Slope Filter

**Feature Branch**: `019-mm50-slope-alert`
**Created**: 2026-05-17
**Status**: Draft
**Input**: User description: "we know how to calculate a mobile average 50. We know how to calculate the slope of a mobile average on a base 100. with all of that, I want to create a new alert type when a asset is near (1%) average mobile 50 when the slope is 3 or above"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect assets approaching MM50 in an uptrend (Priority: P1)

A trader wants to be notified when a monitored asset's current price approaches the 50-period moving average (within 1%) while that moving average has a slope of 3 or above on the base-100 scale. This combination identifies pullback opportunities on assets in a confirmed uptrend, a standard "rebond mm50" setup.

**Why this priority**: This is the core capability of the feature. Without it, no trader sees the signal, and the feature has no value.

**Independent Test**: Run the alerting workflow against a known asset whose latest candle close is within 1% of its MM50 and whose MM50 slope (computed on the base-100 scale over the standard 10-period window) is ≥ 3. Verify that an alert of the new type is produced, stored, and surfaced.

**Acceptance Scenarios**:

1. **Given** an asset with at least 60 daily candles where the latest close is within 1% (absolute distance) of its MM50 and the MM50 slope is exactly 3, **When** the alerting workflow runs, **Then** an alert of the new "MM50 proximity" type is emitted for that asset.
2. **Given** an asset with at least 60 daily candles where the latest close is within 1% of its MM50 and the MM50 slope is 7.4, **When** the alerting workflow runs, **Then** an alert of the new type is emitted for that asset.
3. **Given** an asset where the latest close is within 1% of its MM50 but the MM50 slope is 2.9, **When** the alerting workflow runs, **Then** no alert of the new type is emitted (slope threshold not met).
4. **Given** an asset where the latest close is 1.5% away from its MM50 even with slope 5, **When** the alerting workflow runs, **Then** no alert of the new type is emitted (proximity threshold not met).
5. **Given** an asset with fewer than 60 candles, **When** the alerting workflow runs, **Then** no alert of the new type is emitted and the workflow continues processing the remaining assets without error.

---

### User Story 2 - View the new alert alongside existing alerts (Priority: P2)

The trader wants the new alert to show up in the same channels as existing alerts (Slack stock channel, alerts UI, alerts API response) so it does not require a separate workflow to monitor.

**Why this priority**: The detection alone is not useful if it isn't delivered through the trader's existing review channels. This is the visibility layer.

**Independent Test**: Trigger detection on an asset that meets the new alert's conditions, then verify the alert appears in the Slack grouped message, in the on-demand `POST /api/alerts/run` JSON response, and in the alerts UI list for that asset.

**Acceptance Scenarios**:

1. **Given** the scheduled alerting job has produced one or more alerts of the new type, **When** the Slack summary is posted, **Then** the new alert type is included in the message, grouped consistently with other alert types and labelled clearly (so a reader can tell it apart from CONGESTION, COMBO, DOUBLE_TOP, etc.).
2. **Given** the on-demand `POST /api/alerts/run` endpoint is called on an asset that meets the conditions, **When** the response is returned, **Then** the JSON includes the new alert with its associated data (current close, MM50 value, distance %, MM50 slope).
3. **Given** the alerts UI page is opened for an asset that has the new alert, **When** the page renders, **Then** the new alert type is displayed with a label and the same metadata layout as the other alert types.

---

### Edge Cases

- **Insufficient history**: When fewer than 60 candles are available for the asset, the MM50 cannot be computed reliably; the new alert MUST be silently skipped (consistent with the current `ma50_slope` handling in `run_detection_for_asset`).
- **Slope exactly at threshold**: A slope of exactly 3 satisfies the condition (the threshold is inclusive — "3 or above").
- **Close exactly at MM50**: A 0% distance satisfies the proximity condition (distance ≤ 1%).
- **Latest close below vs. above MM50**: Proximity is symmetric — the close may be above or below the MM50 as long as the absolute distance is within 1%. The asset is "near" the MM50 in either direction.
- **Duplicate detection**: If the asset already has an alert of the new type stored for the current date (ISO day), the alert MUST NOT be duplicated, consistent with the deduplication policy applied to other alert types.
- **Asset without country code**: A Binance asset (no country code) MUST still be eligible for this alert if its candles support a valid MM50 computation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize a new alert type representing "asset close near MM50 in confirmed uptrend" as a first-class member of the `AlertType` enum, with a stable string value usable across DynamoDB persistence, Slack output, and API responses.
- **FR-002**: System MUST detect this alert during the existing per-asset detection pipeline (`run_detection_for_asset`), reusing the candle series already loaded for that asset (no extra Saxo API calls).
- **FR-003**: System MUST compute the MM50 using the existing `mobile_average(candles, 50)` function and the MM50 slope using the existing `slope_percentage` function on a 10-candle base, matching the convention already applied for the `ma50_slope` field used by other alerts.
- **FR-004**: System MUST emit the new alert when **both** of the following hold:
  - The absolute percentage distance between the latest candle's close and the current MM50 value is **≤ 1%** (i.e., `abs(close - ma50) / ma50 ≤ 0.01`).
  - The MM50 slope is **≥ 3** on the base-100 scale.
- **FR-005**: System MUST NOT emit the alert when fewer than 60 candles are available for the asset; the failure MUST be logged at warning level (consistent with the existing MA50-slope handling) and the workflow MUST continue with other assets.
- **FR-006**: Each emitted alert MUST carry, at minimum, the following data fields: latest close price, current MM50 value, distance percentage between close and MM50 (signed or absolute — chosen for readability), MM50 slope value, and the alert date (ISO day). These fields MUST be persisted in DynamoDB and exposed in API responses.
- **FR-007**: System MUST deduplicate emitted alerts of the new type using the existing same-alert-type-same-date rule (one alert of this type per asset per day).
- **FR-008**: System MUST include the new alert type in the Slack `#stock` grouped message produced by the daily alerting cron, with a French label consistent with existing labels (e.g., a "Rebond MM50" / "Touchette MM50" style label) so traders can recognize it at a glance.
- **FR-009**: The on-demand `POST /api/alerts/run` endpoint MUST return the new alert type alongside other detected alerts for a single asset, using the same JSON shape as other alerts.
- **FR-010**: The alerts UI page MUST render the new alert type with a label and the metadata fields defined in FR-006, without breaking the existing layout for other alert types.
- **FR-011**: The new alert MUST be eligible on all assets currently processed by the alerting pipeline (French stocks fetched dynamically from Saxo, follow-up stocks from `followup-stocks.json`, and Binance assets — wherever MM50 can be computed).

### Key Entities

- **MM50 Proximity Alert**: A new member of the `AlertType` enum. Conceptually it represents "the asset's latest close is within 1% of its 50-period moving average, and that moving average is trending upward with slope ≥ 3". It carries the close price, MM50 value, distance %, slope, and date as its data payload, and lives alongside CONGESTION20, CONGESTION100, COMBO, DOUBLE_TOP, DOUBLE_INSIDE_BAR, and CONTAINING_CANDLE in the alerts table.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can run the daily alerting job and receive Slack notifications for every monitored asset whose latest close is within 1% of its MM50 AND whose MM50 slope is ≥ 3 — no false negatives on a hand-curated test set of 5 known matching assets.
- **SC-002**: A trader can run the daily alerting job and observe zero false positives on a hand-curated test set of 5 assets that fail at least one of the two conditions (close > 1% from MM50, or slope < 3).
- **SC-003**: The new alert is emitted, stored, deduplicated, and surfaced through all three existing delivery channels (Slack, alerts API, alerts UI) without any change in latency or error rate for the alerting job (no measurable regression in job duration vs. the previous run).
- **SC-004**: Assets with insufficient candle history (< 60 candles) do not block the alerting job — the job completes for all other assets, and a warning is logged for each skipped asset.
- **SC-005**: A specification reviewer (non-developer) can read the alert in Slack or the UI and immediately know what the alert means — the label and metadata clearly communicate "asset is near MM50 in an uptrend".

## Assumptions

- The 1% proximity threshold and the slope ≥ 3 threshold are both inclusive (≤ 1%, ≥ 3) — these are conventional treatments for boundary values and match the user's natural-language phrasing ("near (1%)", "3 or above").
- "Near MM50" is symmetric — the close may be above or below the MM50 (this matches the trader's "rebond mm50" mental model where a pullback can come from either side, though in practice the slope ≥ 3 filter biases toward pullbacks from above in an uptrend).
- The MM50 slope is computed on the existing convention used by `ma50_slope` elsewhere in the alerting code: `slope_percentage(0, mobile_average(candles[10:], 50), 10, mobile_average(candles, 50))` — i.e., the slope between the MM50 of 10 candles ago and the MM50 of today, expressed on the base-100 scale.
- This alert applies to daily candles, consistent with all other alert types currently produced by the alerting job. Other unit times are out of scope for this feature.
- This is an alert (notification-only) — it does not place orders, create workflows, or modify any trading behavior. It is detection + delivery only.
- The feature reuses the existing alerting pipeline, DynamoDB `alerts` table (with 7-day TTL), Slack delivery, alerts API, and alerts UI — no new infrastructure is required.
