# Feature Specification: Alert Triage & Synthesis Agent

**Feature Branch**: `023-alert-triage`
**Created**: 2026-07-16
**Status**: Draft
**Input**: User description: "Alert triage & synthesis agent (spec 023). After the daily French-stock alerting scan runs its deterministic pattern detectors and produces Alert objects, a new triage agent reasons over the day's collected alerts and produces a ranked 'daily brief': each asset assigned a conviction tier (high / watch / noise), a rank, and a one-line rationale, based on pattern confluence and ma50_slope trend alignment. The digest is persisted to a new no-TTL store so history is retained for later 'was the agent right?' review. Detection logic and the order/workflow path are untouched. On any reasoning failure the agent falls back to a deterministic ranking so the daily scan never breaks. The persisted digest is surfaced in the app and Slack is demoted to a short digest notification that links into the app."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive a ranked daily brief instead of a raw firehose (Priority: P1)

Today, after the daily French-stock scan, the trader receives a raw, per-indicator dump of every pattern that fired — dozens of lines across all scanned stocks — and must eyeball it to find what matters. With this feature, once the scan completes the trader instead receives a synthesized daily brief: the day's signals are grouped by conviction (high / watch / noise), each high- and watch-tier asset is ranked and accompanied by a one-line rationale explaining *why* it stands out (which patterns co-fired on the same asset and whether the medium-term trend agrees), and the low-value noise is summarized as a count rather than listed in full.

**Why this priority**: This is the core value of the feature — turning an unreadable firehose into a decision-ready brief. Everything else (persistence, history, UI) exists to support or extend this. A brief the trader trusts and can act on in seconds is the minimum viable product.

**Independent Test**: Run the daily scan against a set of assets that produce a known mix of alerts; verify a brief is produced that ranks assets with multiple co-firing patterns and trend agreement above isolated single-pattern hits, that each ranked asset carries a plain-language rationale, and that low-conviction hits are collapsed into a summary count.

**Acceptance Scenarios**:

1. **Given** the daily scan produced alerts across several stocks, some with multiple patterns firing on the same asset and some with a single pattern, **When** the triage step runs, **Then** assets with multiple co-firing patterns are ranked above assets with a single isolated pattern.
2. **Given** an asset has a bearish pattern and its medium-term trend is falling, **When** the brief is produced, **Then** that asset is rated higher conviction than an equivalent bearish pattern whose trend is rising.
3. **Given** the scan produced a large number of low-significance hits, **When** the brief is produced, **Then** those hits are represented as a summary count in a "noise" grouping rather than enumerated individually.
4. **Given** the brief is produced, **When** the trader reads any high- or watch-tier entry, **Then** it includes a one-line rationale referencing the specific patterns and trend context behind the ranking.

---

### User Story 2 - Never lose a scan to a reasoning failure (Priority: P1)

The daily scan is a critical, unattended background job. The trader must be able to rely on receiving *a* brief every day, even if the reasoning step is unavailable or misbehaves. When the synthesis step cannot produce a valid result, the system falls back to a deterministic ranking derived from the raw signals themselves (how many patterns fired on the asset and how strongly the trend is inclined), and clearly marks the brief as having used the fallback so the trader knows the reasoning quality is degraded.

**Why this priority**: A brief that occasionally silently disappears — or worse, breaks the whole scan and suppresses the raw alerts too — would destroy trust and remove a tool the trader depends on. Guaranteed delivery with graceful degradation is as important as the synthesis itself.

**Independent Test**: Force the reasoning step to fail (unavailable service or malformed output) and confirm the scan still completes, a brief is still produced from a deterministic ranking, the brief is flagged as fallback, and no raw alert data is lost.

**Acceptance Scenarios**:

1. **Given** the reasoning service is unavailable, **When** the triage step runs, **Then** the scan still completes and a brief is produced using the deterministic fallback ranking.
2. **Given** the reasoning step returns an unparseable or invalid result, **When** the triage step processes it, **Then** the system discards it and uses the deterministic fallback instead of failing.
3. **Given** a fallback brief was produced, **When** the trader views it, **Then** it is clearly marked as having used the fallback ranking.
4. **Given** any failure in the triage step, **When** the scan runs, **Then** the raw per-asset alerts are still stored exactly as they are today and the order/workflow path is unaffected.

---

### User Story 3 - Review the history of past briefs (Priority: P2)

Because each daily brief is persisted without expiry, the trader can look back at previous days' briefs to review what the agent flagged and judge, in hindsight, whether the high-conviction calls played out. The trader can open the most recent brief and step back through prior runs by date.

**Why this priority**: History is the payoff of persisting the digest and the basis for building trust in (or calibrating) the agent's judgment over time. It is highly valuable but not required for the first usable version — the brief delivers value on day one; history compounds it.

**Independent Test**: Produce briefs on multiple distinct run dates, then confirm they can be listed newest-first and any individual past brief can be retrieved and viewed by its run date.

**Acceptance Scenarios**:

1. **Given** briefs exist for several past run dates, **When** the trader opens the brief history, **Then** the briefs are listed newest-first.
2. **Given** the trader selects a past run date, **When** the brief is opened, **Then** the full ranked brief for that date is displayed.
3. **Given** briefs have accumulated over many days, **When** old alerts have expired from the raw alert store, **Then** the corresponding briefs remain available in history.

---

### User Story 4 - A concise notification that links to the full brief (Priority: P2)

Instead of blasting the raw per-indicator lists into the notification channel, the system posts a short, human-readable summary of the day's brief (headline counts and the top high-conviction names) with a link into the application where the full ranked brief lives. The application becomes the source of truth; the notification is a pointer.

**Why this priority**: This closes the loop on replacing the firehose and drives the trader to the richer, persisted view. It depends on the brief and its persisted, viewable form existing first, so it follows P1.

**Independent Test**: After a scan, confirm the notification channel receives a single concise message containing the headline counts and top names plus a link to the brief, and does not receive the old per-indicator raw dump.

**Acceptance Scenarios**:

1. **Given** a brief was produced, **When** the notification is sent, **Then** it contains a short summary (counts and top high-conviction names) and a link to the full brief in the app.
2. **Given** a brief was produced, **When** the notification is sent, **Then** the old raw per-indicator firehose is not sent to the primary channel.
3. **Given** no alerts were detected in the scan, **When** the notification is sent, **Then** it states that there were no signals for the day.

---

### Edge Cases

- **No alerts detected**: the scan finds nothing. A brief is still recorded (empty/zero-count) and the notification states there were no signals for the day.
- **Single alert / very small scan**: the brief still produces a valid ranking without over-editorializing; behavior degrades gracefully to essentially passing through the one signal.
- **Missing trend context**: an asset's trend-slope value is unavailable (insufficient history). The asset is still ranked using the available signals rather than being dropped.
- **Reasoning service slow or timing out**: treated as a failure and handled by the deterministic fallback within the scan's time budget.
- **Reasoning output references an asset not in the scan, or omits assets that were in the scan**: the system reconciles against the actual detected alerts; unknown assets are ignored and detected assets are never silently dropped.
- **Two runs on the same calendar date**: history retains each run distinctly (ordered by run time) rather than overwriting.
- **Duplicate/late notification**: a triage failure must never cause the raw alerts, their storage, or the order/workflow path to be skipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After the daily alerting scan completes its deterministic pattern detection, the system MUST collect the day's detected alerts and produce a single synthesized daily brief.
- **FR-002**: The brief MUST assign every asset that produced at least one alert to exactly one conviction tier: high, watch, or noise.
- **FR-003**: The brief MUST assign a rank ordering to the high- and watch-tier assets.
- **FR-004**: The brief MUST include a concise one-line rationale for each high- and watch-tier asset.
- **FR-005**: Ranking and tiering MUST take into account pattern confluence (multiple distinct patterns firing on the same asset) and alignment between the signal's direction and the asset's medium-term trend slope.
- **FR-006**: The system MUST NOT modify the existing pattern-detection logic; detection remains the deterministic source of truth.
- **FR-007**: The system MUST continue to store the raw per-asset alerts exactly as it does today, independently of the brief.
- **FR-008**: The system MUST NOT alter the order-placement / workflow execution path in any way.
- **FR-009**: The system MUST persist each produced brief durably and WITHOUT automatic expiry, so that historical briefs remain available indefinitely for later review.
- **FR-010**: Each persisted brief MUST be identifiable and retrievable by its run date, and multiple runs on the same date MUST be retained distinctly by run time.
- **FR-011**: On any failure of the reasoning step (service unavailable, timeout, or invalid/unparseable output), the system MUST fall back to a deterministic ranking derived from pattern count and trend-slope magnitude, and MUST still produce and persist a brief.
- **FR-012**: A brief produced via the fallback path MUST be flagged as such so consumers can distinguish reasoning-based from fallback briefs.
- **FR-013**: A failure in the triage or persistence step MUST NOT prevent the scan from completing, MUST NOT lose raw alert data, and MUST NOT affect the order/workflow path.
- **FR-014**: The system MUST expose the persisted briefs for consumption by the application, supporting (a) listing briefs newest-first and (b) retrieving a single brief by its run date.
- **FR-015**: The application MUST provide a view that displays a brief's ranked assets with their conviction tier indicated visually, and MUST allow the user to select and view briefs from prior run dates.
- **FR-016**: After a scan, the notification channel MUST receive a concise summary (headline counts and top high-conviction names) with a link into the application, and MUST NOT receive the previous raw per-indicator dump.
- **FR-017**: The reasoning model MUST be configurable and swappable without code changes, defaulting to a specified high-capability model.
- **FR-018**: The reasoning step MUST reconcile its output against the actually detected alerts: assets not present in the scan are ignored, and assets present in the scan are never silently dropped from the brief.
- **FR-019**: When no alerts are detected, the system MUST still record a brief for the run and the notification MUST communicate that there were no signals.

### Key Entities *(include if feature involves data)*

- **Daily Brief (Digest)**: The synthesized output of one scan run. Attributes: run date, run timestamp, overall summary text, tier counts (high/watch/noise), the ordered list of triaged assets, an indicator of whether the reasoning-based or fallback path produced it, and a record of which reasoning model was used. Retained indefinitely.
- **Triaged Asset**: One asset's entry within a brief. Attributes: asset identifier and human-readable name, conviction tier, rank, one-line rationale, the set of patterns that fired on it, and the trend-slope context used in ranking.
- **Alert** (existing, unchanged): A single detected pattern for an asset produced by the deterministic detectors; the raw input to triage. Continues to be stored as-is with its existing expiry behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The primary notification for a daily scan is reduced from the full per-indicator listing to a single concise message, regardless of how many raw alerts fired.
- **SC-002**: The trader can identify the day's top opportunities from the brief in under 30 seconds, without scrolling through per-indicator raw lists.
- **SC-003**: 100% of scan runs produce and persist a brief — including runs where the reasoning step fails (via fallback) and runs where no alerts are detected.
- **SC-004**: In 100% of reasoning-failure cases, the scan still completes, the raw alerts are still stored, and the order/workflow path is unaffected.
- **SC-005**: Every high- and watch-tier entry in a brief carries a rank and a one-line rationale.
- **SC-006**: Briefs remain retrievable in history beyond the point at which their underlying raw alerts have expired (i.e., history outlives the raw-alert retention window).
- **SC-007**: An asset with multiple co-firing patterns and trend agreement is ranked above an otherwise-comparable asset with a single pattern in 100% of cases where that comparison applies.

## Assumptions

- The medium-term trend-slope value used for ranking is already computed and attached to each alert by the existing scan and does not need to be recomputed by this feature.
- "Daily brief" corresponds to one scan run; the run date is the natural key and multiple same-day runs are rare but retained distinctly.
- Conviction tiers are exactly three (high / watch / noise); "noise" is summarized rather than enumerated in notifications.
- The concise notification targets the same primary channel used today for stock alerts; error/operational channels are unchanged.
- Historical briefs are retained indefinitely (no automatic expiry); any future pruning is out of scope for this feature.
- The application already surfaces raw alerts, so the daily-brief view is an addition alongside the existing alerts experience rather than a replacement of it.
- Access control for the new view follows the same model as the rest of the application (no new authentication requirements introduced by this feature).

## Out of Scope

- Any change to how patterns are detected or which patterns exist.
- Any automated order placement or change to the workflow/execution path.
- Backfilling briefs for historical scans that ran before this feature existed.
- Trader feedback/labeling of whether a call was "right" (the history view enables manual review; capturing structured outcomes is a potential future feature).
- Multi-channel or per-user notification routing beyond the single existing primary channel.
