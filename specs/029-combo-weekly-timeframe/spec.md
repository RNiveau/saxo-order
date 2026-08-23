# Feature Specification: Weekly-Timeframe Combo Detection

**Feature Branch**: `029-combo-weekly-timeframe`
**Created**: 2026-08-23
**Status**: Draft
**Input**: User description: "Weekly-timeframe combo detection: run the existing combo indicator on weekly candles in the daily alerting scan, alongside the current daily combo, so a weekly Buy/Sell combo is stored as its own alert and ranked in the LLM triage digest."

## Clarifications

### Session 2026-08-23

- Q: When should the weekly combo be evaluated — every daily scan on the in-progress week, or only on completed weeks? → A: Every daily scan, on the week currently forming, assembled from the sessions elapsed so far. The setup is seen days earlier; repeat suppression must therefore key on the weekly bar and direction, not on the scan date.
- Q: How much weekly history must an asset have to be eligible? → A: A reduced criteria set needing ~60 weekly bars (~1.2 years), dropping the single criterion that demands 235 bars. Coverage of the scanned universe matters more than criteria parity with the daily combo, and the strength bands are re-stated for the reduced set.
- Q: Do the trend/flatness thresholds that qualify a combo carry over unchanged to weekly? → A: No — weekly-specific thresholds are calibrated against historical weekly data before release. The daily values measure change over a fixed candle count, which on weekly spans roughly five times the calendar period, and would misfire.

### Session 2026-08-23 (review of PR #711)

- Q: The spec forbids a daily repeat, but the existing repeat suppression keys on (alert type, scan date) and the combo alert is dated with the scan date — neither a daily repeat nor a mid-week direction flip is expressible. → A: Weekly-combo suppression keys on the weekly bar plus the direction. This diverges from the shared scan-date rule, so the change must be demonstrably inert for every other alert type.
- Q: At which layer does suppression apply — detection or recording? The digest is built from what each scan detects, not from what is stored. → A: At the recording layer only. Every scan re-evaluates the weekly combo, so the digest always reflects the current state of the forming bar; only the stored record is suppressed.
- Q: US2 was written before the triage brief became long-only. → A: US2 and FR-009 are restated in long-only terms: a Buy weekly combo is the strongest reason to surface an asset; a Sell weekly combo disqualifies it as a long and can never reach the highest conviction band.
- Q: Where does the historical data for threshold calibration and the labelled validation sample come from? → A: Calibration fetches weekly history for a sample of the scanned universe, once, outside the scheduled scan; the labelled sample of historical setups is produced by the trader before release. Both are release prerequisites, recorded under Dependencies. (Amended after review: the existing backtest candle store was considered and rejected — it holds intraday bars for two index instruments, not weekly bars for the scanned equities.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect a combo on the weekly timeframe (Priority: P1)

A trader wants the daily scan to also test each asset for a combo on its weekly bars. A weekly combo describes the same setup as the daily one — a trending 50-period average, quiet volatility bands, price pressing a trigger level — but over a horizon of months rather than days, so it identifies positions worth holding for weeks instead of a swing lasting days.

**Why this priority**: This is the detection itself. Nothing else in the feature has anything to deliver without it.

**Independent Test**: Run the alerting workflow against an asset whose weekly bars satisfy the combo conditions and verify a weekly combo alert is produced with a direction, a strength, a trigger price, and the per-criterion breakdown, stored for that asset.

**Acceptance Scenarios**:

1. **Given** an asset whose weekly bars form a bullish combo, **When** the alerting workflow runs, **Then** a weekly combo alert is emitted carrying a Buy direction, a strength, a trigger/pending price, and the per-criterion detail, identical in shape to the daily combo alert.
2. **Given** the mirror bearish case on weekly bars, **When** the workflow runs, **Then** a weekly combo alert is emitted with a Sell direction.
3. **Given** an asset that forms a combo on both its daily and its weekly bars on the same scan, **When** the workflow runs, **Then** both alerts are stored and neither suppresses the other.
4. **Given** an asset with fewer than the minimum weekly bars the reduced criteria set requires, **When** the workflow runs, **Then** no weekly combo alert is emitted, the omission is logged as routine, and every other detector for that asset still runs and stores its results.
5. **Given** an asset whose weekly bars do not satisfy the combo conditions, **When** the workflow runs, **Then** no weekly combo alert is emitted and the daily combo behaviour for that asset is unchanged.

---

### User Story 2 - Triage ranks the weekly combo as higher-timeframe evidence (Priority: P1)

The trader wants the daily triage digest to treat a weekly combo as the strongest directional evidence available for an asset — stronger than the same combo on daily bars — and to say so in its rationale. The desk is long-only, so this is asymmetric: a Buy weekly combo is the single best reason to surface an asset, while a Sell weekly combo is a reason not to buy it, never a tradable setup of its own. When a daily and a weekly combo agree, that agreement should lift the asset; when they disagree, the bearish leg counts against the long thesis and the digest must say so rather than presenting one unqualified direction.

**Why this priority**: Equal to detection. The digest already documents the meaning and rank of every pattern it receives; a new directional pattern delivered without semantics would be mis-weighted and would degrade the digest instead of improving it.

**Independent Test**: Submit a triage payload for an asset whose only pattern is a Buy weekly combo and verify it is ranked at least as high as an equivalent Buy-daily-combo-only asset. Submit a second payload where daily and weekly combos point in opposite directions and verify the rationale names the disagreement and does not present the asset as a clean long.

**Acceptance Scenarios**:

1. **Given** an asset whose only pattern is a **Buy** weekly combo, **When** the digest is produced, **Then** the asset is eligible for the highest conviction band, and the rationale identifies the signal as being on the weekly timeframe.
2. **Given** an asset whose only pattern is a **Sell** weekly combo, **When** the digest is produced, **Then** the asset is disqualified as a long exactly as a Sell daily combo disqualifies it — it can never reach the highest conviction band, and it is surfaced at all only as a warning on a name the trader may already hold.
3. **Given** two assets, one with a Buy weekly combo and one with a Buy daily combo and no other patterns, **When** the digest is produced, **Then** the weekly one is ranked at or above the daily one.
4. **Given** an asset with a Buy weekly combo and a Sell daily combo, **When** the digest is produced, **Then** the rationale reports the timeframe disagreement and treats the bearish leg as counting against the long thesis, not as a symmetric conflict to be averaged.
5. **Given** an asset with a Buy weekly combo and a Buy daily combo, **When** the digest is produced, **Then** the rationale treats the agreement as reinforcing evidence.

---

### User Story 3 - See the weekly combo where alerts are already consumed (Priority: P2)

The trader wants the weekly combo delivered through the channels already in use — the Slack digest, the alerts API, and the alerts UI — labelled so it is never confused with the daily combo at a glance.

**Why this priority**: Delivery layer. The detection is worthless if invisible where the trader already looks, but it depends on P1 existing first.

**Independent Test**: Trigger detection on an asset that qualifies, then confirm the alert appears in the alerts list with its own readable label and its direction badge, and in the on-demand alert-run response.

**Acceptance Scenarios**:

1. **Given** a stored weekly combo alert, **When** the trader opens the alerts view, **Then** it is displayed with a label that distinguishes it from the daily combo and shows its Buy/Sell direction the way other directional alerts do.
2. **Given** a stored weekly combo alert, **When** the alerts are requested through the API, **Then** the weekly combo is returned alongside the other alert types with its full detail payload.

---

### User Story 4 - Keep the scan within its operating budget (Priority: P2)

The trader depends on the daily scan finishing inside its scheduled execution window and within the market data provider's request budget. The weekly bars cannot be re-cut from the history the scan already fetches — that history is roughly one trading year, far short of the 60 weeks required — so weekly detection adds at least one further provider request per asset per scan, and more if the forming week is assembled from a separate daily fetch. The scan must absorb that roughly doubled request count without putting its schedule at risk.

**Why this priority**: An unreliable scan costs more than the new signal is worth, but this is a constraint on P1 rather than value delivered on its own.

**Independent Test**: Run a full scan of the production universe with weekly detection enabled and compare total duration and provider request count against the same scan with it disabled; confirm the request count grows by no more than one additional request per asset per timeframe fetched.

**Acceptance Scenarios**:

1. **Given** a full scan of the production universe with weekly detection enabled, **When** it runs, **Then** it completes within its scheduled execution window with margin to spare.
2. **Given** the market data provider rejects or fails a weekly history request for one asset, **When** the scan runs, **Then** that asset's other detectors still run and the scan continues over the remaining assets.

---

### Edge Cases

- **Asset newly listed**: fewer weekly bars exist than the minimum. No weekly combo, no error, other detectors unaffected.
- **In-progress week**: the market data provider does not return the week currently trading, so the current week's bar must be assembled from the sessions elapsed so far (FR-003).
- **Monday before the open / weekend scan**: the current week has no completed session yet, so no partial bar can be assembled. Detection falls back to the last completed week.
- **Holiday-shortened week**: a week with fewer than five sessions is still one weekly bar, built from the sessions that traded.
- **Same asset, same day, both timeframes**: the two combos must remain independently stored and independently visible; storing one must never cause the other to be discarded as a repeat.
- **Repeat of the same weekly combo on consecutive days**: a setup that persists across several daily scans must not produce a new alert every day for the same weekly bar.
- **Direction flips mid-week**: the forming week's bar changes direction between two daily scans. The digest must reflect the latest state rather than the first one recorded, and the change must survive repeat suppression.
- **Setup vanishes mid-week**: a combo present on Tuesday's forming bar no longer qualifies on Thursday. The already-issued alert stands as a record; no retraction is expected.
- **Weekly detection unavailable for an entire scan**: if weekly history cannot be fetched at all, the scan still delivers the full daily alert set and the digest is produced without weekly evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The scan MUST evaluate the combo setup on each asset's weekly bars, producing the same signal shape as the existing daily combo (direction, strength, trigger/pending price, per-criterion breakdown), scored on the reduced criteria set defined in FR-004.
- **FR-002**: A weekly combo MUST be recorded as a distinct alert, separable from a daily combo by every consumer, so that both can coexist for the same asset on the same day without either being treated as a repeat of the other.
- **FR-003**: The weekly bar series MUST cover completed weeks and MUST include the week currently trading, assembled from the sessions elapsed so far, so a forming setup is reported before the week closes.
- **FR-004**: The weekly combo MUST be scored on a reduced criteria set requiring roughly 60 weekly bars. Its strength bands MUST be redefined for that reduced set: the set loses one of its criteria, so the band boundaries inherited from the daily combo would make the top band mean a perfect score.
- **FR-005**: The scan MUST skip weekly detection for any asset holding less than the required weekly history, record the skip as a routine event rather than a failure, and continue with all other detectors for that asset.
- **FR-006**: A failure to obtain or evaluate weekly data for one asset MUST NOT abort the scan, discard alerts already found for that asset, or prevent other assets from being scanned.
- **FR-007**: Repeat suppression for the weekly combo MUST key on the weekly bar and the direction rather than on the scan date: while the same setup persists on the same bar in the same direction, no further alert is recorded, and a direction change on that bar MUST be recorded as a new alert. This differs from the scan-date suppression governing every other alert type, so the change MUST be demonstrably inert for those types (see FR-012 and SC-007).
- **FR-008**: The triage digest MUST rank a weekly combo as directional evidence at least as strong as a daily combo, and MUST state the timeframe of the signal in its rationale.
- **FR-009**: When daily and weekly combos for one asset disagree in direction, the digest's reasoned rationale MUST report the disagreement explicitly rather than emitting a single unqualified direction, and MUST resolve it under the long-only mandate: the bearish leg counts against the long thesis and caps the asset's conviction, whichever timeframe it sits on. This governs the reasoned path; the degraded fallback path is governed by FR-014.
- **FR-015**: A weekly combo that met none of its scoring criteria MUST NOT be emitted. It cleared the structural gates and nothing more, and every alert emitted costs an entry in the reasoning payload — one which the pattern ranking would present as the strongest signal available. The asset is still scanned and its other detectors still record what they find.
- **FR-014**: In the degraded fallback ranking, a daily and a weekly combo on one asset MUST count as a single point of evidence, not two. They are one detector at two timeframes, and their agreement is reinforcement of one signal rather than two independent mechanisms; counting them separately would promote an asset to the highest conviction band on the strength of one detector, in a path that does not read direction at all.
- **FR-010**: The weekly combo MUST be registered as a directional alert everywhere a directional alert type is enumerated — the alerts view, the alerts API, and the triage inputs alike — and MUST carry a label distinct from the daily combo wherever it is displayed.
- **FR-011**: The qualifying thresholds used for weekly evaluation MUST be calibrated against historical weekly data before release, and MUST be adjustable independently of the daily ones so tuning one timeframe never changes the behaviour of the other.
- **FR-012**: Existing alerts stored before this feature MUST remain readable and displayable unchanged.
- **FR-013**: Repeat suppression MUST apply to what is recorded, never to what is detected. Every scan MUST evaluate the weekly combo afresh, so the digest always reflects the state of the forming bar on the day it runs — including a direction that has changed since the alert was first recorded.

### Key Entities

- **Weekly bar**: one trading week condensed into a single open/high/low/close observation, dated by the week's first session. Built either by the market data provider for completed weeks or assembled from the elapsed sessions for the week currently trading.
- **Weekly combo alert**: the record produced when an asset's weekly bars satisfy the combo conditions. Carries direction (Buy/Sell), strength, the trigger or pending price, the per-criterion breakdown that produced the strength, the trend slope, and its timeframe. Belongs to one asset and one weekly bar.
- **Triage digest entry**: the per-asset ranking and rationale the digest produces. Gains the weekly combo as an input, with its timeframe and its relation to the asset's daily evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every asset with sufficient weekly history, a weekly combo present in its weekly bars is reported by the scan — verified with no misses against the labelled sample of at least 20 historical setups named under Dependencies.
- **SC-002**: No asset receives more than one recorded weekly combo alert for the same weekly bar and direction, measured over a five-consecutive-day scan window; a direction that flips on that bar does produce a second record.
- **SC-003**: A full production scan with weekly detection enabled finishes inside its scheduled execution window, with at least 25% of that window unused.
- **SC-004**: At least 80% of the scanned universe holds enough weekly history to be eligible for weekly detection, measured and reported before release.
- **SC-005**: Across a two-week trial, weekly combos account for no more than 15% of the asset-days surfaced in the daily digest — counted per digest, so one setup persisting all week counts once for each day it is surfaced — confirming the signal narrows attention instead of flooding it.
- **SC-006**: In every reasoned digest entry where an asset carries a weekly combo, the rationale names the timeframe, and where daily and weekly disagree, it names the conflict — verified on a sample of 20 entries. The degraded fallback rationale is out of this criterion's scope: it lists pattern names without interpretation by design, and its wording is constrained to stay unchanged for assets this feature does not touch.
- **SC-009**: No weekly combo alert is recorded for an asset whose weekly signal met none of its criteria, verified over a full scan — the reasoning payload carries no entry that says nothing.
- **SC-008**: An asset carrying both a daily and a weekly combo and nothing else reaches the same conviction band in the degraded fallback as an asset carrying the daily combo alone — confirming the new type adds no unearned promotion (FR-014).
- **SC-007**: With the weekly detection code reverted, the scan reproduces the current daily-only alert set exactly, on the same assets and the same date — verified once before release, so the de-duplication change is shown to be inert for every pre-existing alert type.

## Dependencies

- **Historical weekly data for calibration**: the threshold calibration required by FR-011 is a one-off developer task that fetches weekly history for a sample of the scanned universe. It cannot reuse the existing backtest candle store, which holds intraday bars for two index instruments rather than weekly bars for the scanned equities — thresholds fitted on those would not transfer. The fetch happens outside the scheduled scan and is paid once; it is a release prerequisite.
- **Labelled validation sample**: SC-001 is verified against a sample of at least 20 historical weekly combo setups, labelled by the trader before release. No such sample exists today and backfill is out of scope, so producing it gates release rather than following it.

## Assumptions

- The weekly combo answers the same question as the daily one over a longer horizon; no new criterion is invented for it.
- Weekly bars follow the ISO week (Monday-dated) convention already used elsewhere in the product for weekly aggregation.
- The universe scanned is unchanged: this feature adds a timeframe, not assets.
- Weekly detection runs inside the existing daily scan rather than as a separate scheduled job.
- Historical alerts are not backfilled; the weekly combo starts producing alerts from its first scan onward.
- Calibrating the weekly thresholds requires a measurement pass over historical weekly data, sized to produce defensible values rather than an exhaustive optimisation.
- The digest continues to be synthesised from what each scan detects rather than from stored history, so a persisting weekly setup remains visible in the digest for as long as it holds even though it is recorded only once (FR-013).
- The reduced criteria set changes the composition of the strength score on weekly; "strong" on weekly is not numerically comparable to "strong" on daily and is re-stated for the reduced set.

## Out of Scope

- Extending any other detector (congestion, double top/bottom, inside bar, containing candle, MA touch, MM7 break) to the weekly timeframe.
- Monthly or intraday combo detection.
- Redesigning the combo criteria themselves. The weekly variant reuses them minus one, with re-stated strength bands (FR-004); the daily combo's criteria, scoring and bands are untouched.
- Backfilling weekly combo alerts for historical dates.
- Any change to how alerts are retained or expired.
- Automatic order placement or workflow triggering from a weekly combo.
