# Feature Specification: MM7 Break Alert

**Feature Branch**: `027-mm7-break-alert`
**Created**: 2026-08-01
**Status**: Implemented
**Input**: User description: "I want to improve the triage agent. Breaking a ma7 is a strong short term indicator. We should add it in the alerting system."

## Clarifications

### Session 2026-08-01

- Q: Which MA7 breaks should fire an alert? → A: Both directions (bullish reclaim and bearish breakdown), with the direction carried in the alert data.
- Q: How strict should the qualifier be, so MM7 does not flood the daily digest? → A: Distance **and** streak — the close must clear the MM7 by ~0.5% AND the previous 3 candles must all have closed on the other side.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect a short-term change of character (Priority: P1)

A trader wants to be notified when an asset's latest daily close crosses through its 7-period moving average, in either direction, after a run of candles held on the other side. Breaking the MM7 is the earliest structural sign that the short-term run has changed character — a breakdown warns that an advance is stalling, a reclaim marks a possible short-term entry.

**Why this priority**: This is the detection itself. Without it there is no signal, and the rest of the feature has nothing to deliver.

**Independent Test**: Run the alerting workflow against an asset whose latest close sits more than 0.5% below its MM7 while the three prior candles all closed at or above their own MM7. Verify an alert of the new type is produced with a bearish direction, stored, and surfaced.

**Acceptance Scenarios**:

1. **Given** an asset with at least 10 daily candles whose latest close is 4% below its MM7 and whose 3 prior candles each closed at or above their MM7, **When** the alerting workflow runs, **Then** an alert of the new "MM7 break" type is emitted with a bearish (Sell) direction.
2. **Given** the mirror situation — latest close 5% above its MM7, 3 prior candles each closed at or below their MM7 — **When** the alerting workflow runs, **Then** an alert of the new type is emitted with a bullish (Buy) direction.
3. **Given** an asset whose latest close is 0.4% below its MM7 (a graze, inside the distance threshold), **When** the alerting workflow runs, **Then** no alert of the new type is emitted.
4. **Given** an asset whose closes alternate above and below the MM7 (chop, so the prior run is shorter than 3 candles), **When** the alerting workflow runs, **Then** no alert of the new type is emitted even if the latest close clears the distance threshold.
5. **Given** an asset with fewer than 10 candles, **When** the alerting workflow runs, **Then** no alert of the new type is emitted and the workflow continues processing the remaining assets without error.

---

### User Story 2 - Triage weighs the break correctly (Priority: P1)

The trader wants the triage agent to treat an MM7 break as what it is — a short-term timing trigger — rather than promoting it to a standalone thesis. A break in the same direction as the medium-term trend is a continuation trigger; a break against it is an early warning on an intact trend, not a reversal call.

**Why this priority**: Equal to P1 detection. The stated motivation for the feature is improving the triage agent, and a directional pattern added to the payload without semantics would be mis-weighted — the existing prompt already documents the meaning of every other pattern for exactly this reason. Adding MM7 blind would degrade the digest rather than improve it.

**Independent Test**: Submit a triage payload containing an asset whose only pattern is an MM7 break, on a flat trend. Verify the agent does not return it as "high" conviction. Submit a second payload where the MM7 break direction agrees with a strongly-inclined MA50 slope alongside another directional pattern, and verify it ranks above the isolated case.

**Acceptance Scenarios**:

1. **Given** an asset whose only alert is an MM7 break, **When** the digest is produced, **Then** that asset is never assigned "high" conviction on the strength of the break alone.
2. **Given** an MM7 break whose direction agrees with the sign of the asset's MA50 slope, **When** the digest is produced, **Then** the rationale treats it as a continuation trigger and counts it as directional evidence.
3. **Given** an MM7 break whose direction opposes the sign of the asset's MA50 slope, **When** the digest is produced, **Then** the rationale treats it as an early warning on an intact trend and does not describe it as a confirmed reversal.

---

### User Story 3 - View the new alert alongside existing alerts (Priority: P2)

The trader wants the new alert delivered through the channels already in use — the Slack digest, the alerts API, and the alerts UI — so it needs no separate workflow to monitor.

**Why this priority**: Delivery layer. The detection is useless if it is not visible where the trader already looks, but it depends on P1 existing first.

**Independent Test**: Trigger detection on an asset meeting the conditions, then verify the alert appears in the alerts UI list with a readable label and in the on-demand `POST /api/alerts/run` JSON response.

**Acceptance Scenarios**:

1. **Given** an asset that produced an MM7 break, **When** the alerts UI page renders, **Then** the alert is displayed with a human-readable label rather than its raw type string.
2. **Given** the on-demand `POST /api/alerts/run` endpoint is called on a matching asset, **When** the response is returned, **Then** the JSON includes the new alert with its data payload, in the same shape as other alerts.

---

### Edge Cases

- **Insufficient history**: Fewer than 10 candles (7 for the average plus the 3-candle streak) means the break cannot be established; the alert MUST be silently skipped and the scan MUST continue with the other assets.
- **Graze**: A close that crosses the MM7 but stays within the distance threshold is not a break. Crossing alone is too common to be evidence.
- **Chop**: Price oscillating around a flat MM7 produces crossings on most days. The streak requirement is what excludes them; without it the alert would fire on a large share of the universe daily and dilute the digest.
- **Streak counting runs out of history**: When counting the prior run reaches the point where a full MM7 can no longer be computed, counting stops there. An asset with exactly 10 candles can therefore reach — but not exceed — the minimum streak.
- **Both directions on the same asset**: Mutually exclusive by construction; a single close cannot be more than 0.5% above and below the same average.
- **Duplicate detection**: One alert of this type per asset per day, consistent with the deduplication policy applied to the other alert types.
- **Asset without country code**: A Binance asset (no country code) MUST be eligible for this alert like any other, as long as its candle history supports the computation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize a new alert type representing "the latest close broke through the 7-period moving average" as a first-class member of the `AlertType` enum, with a stable string value usable across DynamoDB persistence, Slack output, and API responses.
- **FR-002**: System MUST detect this alert during the existing per-asset detection pipeline (`run_detection_for_asset`), reusing the candle series already loaded for that asset — no extra Saxo API calls.
- **FR-003**: System MUST compute the 7-period average with the existing `mobile_average` function, evaluated at the offset of the candle being judged.
- **FR-004**: System MUST emit the alert when **both** of the following hold:
  - The latest close clears the current MM7 by **more than 0.5%** in absolute distance (below it for a bearish break, above it for a bullish one).
  - The **3 candles preceding it** each closed on the opposite side of their own MM7 (at or above for a bearish break, at or below for a bullish one).
- **FR-005**: System MUST assign each emitted alert a direction using the existing `Direction` enum — `Sell` for a breakdown from above, `Buy` for a reclaim from below — carried inside the alert data rather than split across two alert types.
- **FR-006**: System MUST NOT emit the alert when fewer than 10 candles are available; the asset MUST be skipped without aborting the scan, and a detector that cannot run MUST NOT prevent the other detectors' alerts from being stored.
- **FR-007**: Each emitted alert MUST carry, at minimum: latest close, current MM7 value, previous close, previous MM7 value, signed distance percentage, direction, the observed streak length, and the asset's MA50 slope (the field the alerts UI sorts on).
- **FR-008**: System MUST deduplicate emitted alerts of the new type using the existing same-alert-type-same-date rule.
- **FR-009**: The triage agent's pattern semantics MUST describe the new alert as a short-term timing trigger, read against the **sign** of the MA50 slope: agreeing = continuation trigger and genuine directional evidence; opposing = early warning on an intact trend, explicitly not a reversal thesis.
- **FR-010**: The triage agent MUST NOT assign "high" conviction to an asset whose only evidence is an MM7 break, however clean the break.
- **FR-011**: The alerts UI MUST render the new alert type with a human-readable label, without breaking the layout used by the other alert types. The label MUST be the same wherever the alert type is displayed — filter list and alert card alike.
- **FR-013**: The deterministic triage fallback MUST NOT let an MM7 break contribute to the confluence count that promotes an asset to "high". An asset that fired one structural pattern before MUST NOT change tier merely because it also broke its MM7.
- **FR-012**: The new alert MUST be eligible on all assets currently processed by the alerting pipeline (French stocks fetched from Saxo, follow-up stocks, and Binance assets).

### Key Entities

- **MM7 Break Alert**: A new member of the `AlertType` enum. Conceptually it represents "the latest close crossed decisively through the 7-period moving average, ending a run of at least 3 candles on the other side". It carries close, MM7, previous close, previous MM7, signed distance %, direction, streak length, and MA50 slope as its data payload, and lives alongside CONGESTION20, CONGESTION100, COMBO, DOUBLE_TOP, DOUBLE_BOTTOM, DOUBLE_INSIDE_BAR, CONTAINING_CANDLE, and MM50_TOUCH in the alerts table.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a hand-curated test set of assets that broke their MM7 decisively after a run on the other side, every one produces the alert with the correct direction — no false negatives.
- **SC-002**: On a hand-curated test set of assets that only grazed the MM7 or that chopped around it, none produces the alert — no false positives.
- **SC-003**: The share of scanned assets carrying an MM7 break on a normal trading day stays low enough that the alert reads as evidence rather than background — comparable in order of magnitude to the other detectors, not a large fraction of the universe. This is the criterion to re-check on the first live runs; the distance and streak thresholds are the levers if it is exceeded.
- **SC-004**: The daily alerting job shows no measurable regression in duration or error rate versus the previous run, since the detector reuses the already-loaded candles.
- **SC-005**: A reader of the Slack digest or the alerts UI can tell at a glance which direction the break went and how far price cleared the average — without expanding the raw data payload.

## Assumptions

- The 0.5% distance threshold is **exclusive** (a break must clear it, not merely equal it) and the 3-candle streak is **inclusive** (exactly 3 qualifying candles is enough).
- The "other side" test for the prior candles is inclusive of touching the average: a close exactly equal to its MM7 counts as being on that side and does not interrupt the streak. A candle sitting exactly on the average has not left the side it came from.
- Both thresholds are derived from the shape of the existing detectors rather than from measured hit rates on the live universe; they are expected to be re-tuned after the first live runs (see SC-003) and are therefore expressed as named constants.
- This alert applies to daily candles, consistent with every other alert type produced by the alerting job. Other unit times are out of scope.
- This is a detection + delivery feature. It does not place orders, create workflows, or modify any trading behavior.
- The feature reuses the existing alerting pipeline, DynamoDB `alerts` table, Slack delivery, alerts API, and alerts UI — no new infrastructure.
- `distance_pct` is measured against an MM7 that includes the breaking candle, so the breaking close drags the average ~1/7 of the way toward itself and the measured distance is systematically smaller than the distance from the pre-break average. This matches how `mm50_touch` measures proximity, and makes the 0.5% gate slightly stricter than the plain reading of "clear the average by 0.5%". It is a factor when re-tuning under SC-003; the payload carries `previous_mm7` for anyone who wants the other measure.
- The deterministic triage fallback treats MM7 as a timing trigger excluded from the confluence count (FR-013). A lone MM7 break therefore lands in "noise" on the fallback path — with reasoning unavailable, a bare timing trigger is not actionable — while the alert itself is still stored and shown in the UI.
