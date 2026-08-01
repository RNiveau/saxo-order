# Feature Specification: Workflow-Trigger Corroboration in the Alert Triage Agent

**Feature Branch**: `028-triage-workflow-trigger`
**Created**: 2026-08-01
**Status**: Draft
**Input**: User description: "Enrich the alert triage agent with same-day workflow trigger data. Workflow triggers (recorded in the workflow_orders DynamoDB table by WorkflowEngine) are pre-registered, explicitly directional, capital-committing signals produced by a different mechanism than the chart-pattern detectors. They should be attached to assets already present in the day's alert set as an additional independent convergence signal — they must never introduce new assets into the digest ranking. Join path: workflow_orders.order_code is the traded CFD, so resolve each order to its Workflow via workflow_id (get_workflow_by_id) and match on Workflow.index against the alert asset id. Filter to today's Paris session. Dry-run workflows must be distinguished (excluded or explicitly labelled). The TriageAgent LLM prompt gains guidance that a workflow trigger counts as one independent convergence point, carries directional bias at least as authoritative as the combo pattern, and a trigger contradicting the pattern read is a red flag. The deterministic fallback counts a trigger as an extra pattern family. TriagedAsset gains an optional workflow-trigger field surfaced in the API, frontend Daily Brief, and Slack digest. The whole enrichment must be failure-tolerant: any error reading or joining workflow data is logged and swallowed, leaving the digest exactly as it is today."

## Context

The daily brief currently ranks assets using a single family of evidence: chart-pattern detectors and the 50-period moving-average slope, all computed by the same end-of-day scan from the same candles. Because these inputs are not truly independent of one another, the triage reasoning has to spend most of its effort discounting false confluence.

Workflow triggers are a structurally different kind of evidence. A workflow is a rule the trader registered in advance; when it fires during the trading day it produces an explicitly directional order at a known price. It is the only signal in the system that is both pre-registered and directional, and it is produced by a mechanism entirely separate from the pattern detectors. When a workflow trigger lands on an asset that also fired patterns today, that is the strongest corroboration the system can produce — and today the brief is blind to it.

This feature makes the brief aware of that corroboration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Workflow-corroborated assets rise in the brief (Priority: P1)

The trader opens the daily brief after the close. An asset that fired chart patterns today *and* triggered one of their registered workflows in the same direction is ranked at the top, and its rationale explicitly says so — naming the workflow, its direction, and the fact that this is evidence from a separate mechanism rather than another chart pattern.

**Why this priority**: This is the entire value of the feature. Corroboration between two independent mechanisms is the signal the trader most wants surfaced, and ranking is what the brief exists to do. Everything else is presentation.

**Independent Test**: Run a triage over an alert set in which exactly one asset also has a same-day workflow trigger aligned with its patterns, and confirm that asset is ranked above otherwise comparable assets and that its rationale names the workflow trigger as a distinct source of evidence.

**Acceptance Scenarios**:

1. **Given** an asset with two independent bullish patterns and a rising 50-MA, **and** a same-day workflow trigger in the buy direction on that asset, **When** the brief is generated, **Then** the asset is ranked above an otherwise identical asset with no trigger, and its rationale names the workflow.
2. **Given** an asset whose patterns read bearish, **and** a same-day workflow trigger in the buy direction on that asset, **When** the brief is generated, **Then** the contradiction is treated as a red flag on the bearish read rather than as supporting evidence, and the rationale says so.
3. **Given** a workflow trigger on an asset that produced no alerts today, **When** the brief is generated, **Then** that asset does not appear in the brief at all.
4. **Given** an alert set where no asset has a same-day trigger, **When** the brief is generated, **Then** the ranking and rationales are indistinguishable from the current behaviour.

---

### User Story 2 - The trigger is visible wherever the brief is read (Priority: P2)

Having been told an asset is workflow-corroborated, the trader can see the specifics — which workflow, which direction, at what price, at what time of day — without leaving the brief, whether they are reading it in the app or glancing at the Slack notification.

**Why this priority**: The ranking is useful on its own (US1 ships without this), but a claim of corroboration that the trader cannot verify at a glance forces them back into the workflow orders page, undoing the brief's zero-click promise.

**Independent Test**: Generate a brief containing at least one corroborated asset, then confirm the trigger details are present in the brief data served to the app, rendered on the asset's entry in the Daily Brief, and reflected in the Slack message.

**Acceptance Scenarios**:

1. **Given** a brief containing a corroborated asset, **When** the trader views the Daily Brief in the app, **Then** the asset's entry shows the workflow name, the trigger direction, and the time of day the workflow fired.
2. **Given** a brief containing at least one corroborated asset, **When** the Slack digest is posted, **Then** the message distinguishes corroborated assets from the rest.
3. **Given** a brief with no corroborated assets, **When** the trader views the Daily Brief and the Slack digest, **Then** no empty trigger section, badge, or placeholder text appears anywhere.

---

### User Story 3 - Corroboration survives degraded reasoning (Priority: P3)

When the triage reasoning is unavailable and the brief falls back to deterministic ranking, an asset with a workflow trigger is still ranked above an equivalent asset without one.

**Why this priority**: The fallback path is rare, and the brief remains useful without this. But a fallback that silently discards the strongest available signal would make degraded days quietly worse than they need to be.

**Independent Test**: Force the reasoning step to fail over an alert set containing one corroborated asset, and confirm the fallback ranking places it above equivalent uncorroborated assets and that the brief is still flagged as a fallback.

**Acceptance Scenarios**:

1. **Given** reasoning is unavailable, **and** an asset has one pattern plus a same-day trigger, **When** the fallback ranking runs, **Then** the trigger counts toward that asset's confluence and lifts its conviction tier accordingly.
2. **Given** reasoning is unavailable, **When** the fallback ranking runs, **Then** the brief is still marked as a fallback and its templated rationales mention the trigger where one exists.

---

### Edge Cases

- **No triggers today**: the brief is byte-for-byte what it would have been before this feature.
- **Trigger on an asset outside the alert set** (index, CFD-only instrument, or a stock excluded from the scan): silently ignored; it never creates a brief entry.
- **Trigger whose workflow record can no longer be resolved** (deleted or renamed workflow): that trigger is dropped; the rest of the enrichment proceeds.
- **Several triggers on one asset in the same day**: all are attached; the brief still counts them as a single point of convergence, not one per trigger.
- **Triggers on one asset disagreeing with each other on direction**: treated as an internally inconsistent signal, not as amplified conviction.
- **Underlying identifier does not match the alert asset identifier** (formatting or market-suffix differences): the trigger is dropped rather than guessed at, and the mismatch is logged so the mapping can be corrected.
- **Workflow data unreadable** (storage error, timeout, permission failure): the brief is produced exactly as it is today, and the failure is recorded in operational logs only.
- **Manual or off-schedule triage run**: the session window is computed from the run's own date, not from the scheduled run time.
- **Trigger fired after the triage run**: not included in that day's brief; it is not retro-fitted into an already-stored brief.

## Requirements *(mandatory)*

### Functional Requirements

**Sourcing and scoping**

- **FR-001**: The system MUST read the workflow triggers recorded during the current Paris trading day and make them available to the triage step.
- **FR-002**: The system MUST attach a trigger only to an asset that already appears in the day's alert set. Triggers MUST NOT introduce assets into the brief.
- **FR-003**: The system MUST resolve each recorded trigger from the instrument actually traded (the CFD) to the underlying asset the workflow watches, and match that underlying against the alert asset identifier. A trigger whose underlying cannot be resolved or matched MUST be dropped, not approximated.
- **FR-004**: The system MUST bound the session window to the current run date in Paris local time, computed from the run itself rather than from an assumed schedule.
- **FR-005**: The system MUST record, for each trigger it attaches: the workflow name, the order direction, the order price, the market price at the moment the workflow fired, the time of day it fired, and whether the workflow was in dry-run mode.
- **FR-006**: The system MUST distinguish dry-run triggers from live ones everywhere a trigger is used — in reasoning, in fallback ranking, and in every display surface.

**Reasoning**

- **FR-007**: The triage reasoning MUST treat a workflow trigger as evidence produced by a mechanism independent of the chart-pattern detectors, and therefore as a genuine point of convergence — unlike two lookback windows of the same detector, which already count as one.
- **FR-008**: The triage reasoning MUST treat a trigger's direction as directional bias at least as authoritative as the strongest existing directional pattern.
- **FR-009**: The triage reasoning MUST treat a trigger whose direction contradicts the pattern-and-trend read as a red flag on that read, not as supporting confluence — consistent with how structurally impossible pattern combinations are already handled.
- **FR-010**: The triage reasoning MUST count multiple same-day triggers on one asset as a single point of convergence.
- **FR-011**: The triage reasoning MUST name the workflow trigger in the rationale of any asset whose ranking it influenced, so the trader can see why the asset rose.
- **FR-012**: The triage reasoning MUST weigh a dry-run trigger as directional evidence one step weaker than a live trigger, since no capital was committed.

**Degraded operation**

- **FR-013**: The deterministic fallback ranking MUST count an attached trigger as one additional independent point of confluence when tiering and ordering assets.
- **FR-014**: The deterministic fallback rationale MUST mention the trigger where one is attached.

**Surfacing**

- **FR-015**: The stored brief MUST carry the attached trigger information alongside the asset it corroborates, so that a brief re-read later shows the same corroboration it was ranked on.
- **FR-016**: The brief data served to the app MUST expose the attached trigger information for each asset that has one, and omit it entirely for assets that do not.
- **FR-017**: The Daily Brief in the app MUST show, on a corroborated asset, the workflow name, the trigger direction, the time of day, and a clear dry-run indication when applicable.
- **FR-018**: The Slack digest MUST distinguish corroborated assets from the rest without growing into a per-trigger listing.

**Failure tolerance**

- **FR-019**: Any failure in reading, resolving, or attaching workflow trigger data MUST leave the brief exactly as it would have been without this feature — same assets, same ranking, same rationales, same delivery.
- **FR-020**: Such failures MUST be recorded in operational logs only, and MUST NOT reach the trader-facing brief, the Slack digest, or the alerting error channel.
- **FR-021**: The enrichment MUST NOT change alert detection, alert storage, or any part of the workflow and order path. It reads workflow data; it never writes it.

### Key Entities

- **Workflow Trigger (as consumed by triage)**: a same-day record that a registered workflow fired. Carries the workflow's name, the direction and price of the resulting order, the market price at firing, the time of day, and whether the workflow was live or dry-run. Belongs to exactly one underlying asset, reached by resolving the traded instrument back to the asset the workflow watches.
- **Triaged Asset**: unchanged in purpose — an asset in the day's brief with its conviction tier, rank, rationale, patterns, and trend slope. Gains an optional set of attached workflow triggers, absent on most assets.
- **Alert Digest**: unchanged in shape and lifecycle. Its assets may now carry trigger corroboration, which is stored with the brief and persists for later review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a day where an asset both fires patterns and triggers a workflow in the same direction, that asset appears in the brief's top tier, ranked above otherwise comparable uncorroborated assets.
- **SC-002**: Every asset whose ranking was influenced by a trigger has a rationale that names the workflow, so the trader never has to guess why an asset rose.
- **SC-003**: No asset appears in the brief solely because a workflow triggered on it — the set of assets in the brief is identical to what the alert scan produced.
- **SC-004**: On days with no same-day triggers, the brief is indistinguishable from the pre-feature brief.
- **SC-005**: When workflow data is unavailable, the brief is still produced and delivered in full, with no trader-visible sign of the failure.
- **SC-006**: A trader reading a corroborated asset in the app can identify the workflow, its direction, its timing, and whether it was live or dry-run without navigating away from the brief.
- **SC-007**: The triage step's contribution to the end-of-day scan grows by no more than a few seconds, and the scan continues to complete within its existing time budget.
- **SC-008**: A brief re-read weeks later still shows the trigger corroboration it was ranked on, outliving the short retention of the raw trigger records.

## Assumptions

- **A-001 — Universe overlap**: the trader has confirmed that most registered workflows watch individual assets rather than index CFDs, so the alert set and the workflow set overlap meaningfully. This feature's value depends on that overlap; it was accepted as given rather than measured.
- **A-002 — Session window**: "today" means the current calendar day in Paris local time, from midnight to the moment the brief is generated. Triggers firing after the brief is generated belong to the next day's brief, if any.
- **A-003 — Dry-run handling**: dry-run triggers are included and explicitly labelled rather than excluded, on the reasoning that the rule still fired and the analytical content is identical; only the capital commitment differs, which FR-012 accounts for by weighting them one step lower. If the trader would rather not see dry-run rules in the brief at all, this reverses to a filter and FR-012 falls away.
- **A-004 — Convergence weighting**: a trigger adds one point of convergence, matching how a distinct pattern family is counted today. It is deliberately not given a multiplier; the intent is to break ties toward corroborated assets, not to let a single trigger dominate the ranking.
- **A-005 — No backfill**: briefs generated before this feature are left as they are. Corroboration appears from the first run after deployment onward.
- **A-006 — Read-only join**: resolving a trigger to its underlying asset requires reading the workflow definitions that the triggers reference. These reads are few (one per triggering workflow per day) and add negligible cost to the scan.

## Out of Scope

- Measuring whether workflow-corroborated assets subsequently performed better; the brief records the corroboration, it does not evaluate it.
- Surfacing workflow triggers on assets outside the alert set, in the brief or anywhere else. Those remain visible on the existing workflow orders page.
- Any change to workflow definitions, workflow scheduling, order placement, or the workflow Slack channels.
- Triggers from earlier days, multi-day trigger history, or trends in triggering behaviour.
- Retro-fitting corroboration into a brief that has already been generated and stored.
