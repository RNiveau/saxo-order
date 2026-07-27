# Feature Specification: Hardcoded "GER40 Bougie de 9h" Backtest (double take-profit)

**Feature Branch**: `claude/ger40-backtest-spec-025-k9togf`
**Created**: 2026-07-23
**Status**: Draft
**Input**: User description: "Let's create a new backtest (need a new spec 025). It's the same strategy as «CAC 40 bougie de 9h» but for the GER40.I index. Rules are: TP 10 points below the higher; SL 150 points below the lower; BE +50 pts; Max distance 40 pts. I want a double take profit: 50% of the h1 candle then 10 pts below the high. It means a position is 2 products, so SL is x2. When we take TP1, the rest is BE."

## Context

This backtest reuses, verbatim, the base strategy of "CAC40 Bougie de 9h" (spec 021): the 9:00–10:00 H1 reference range, the after-10:00 5-minute breakout/reversal detection on both directions, one-position-at-a-time, the gap-fill convention on price-level exits, the end-of-day fallback, and the range-run aggregate summary. It differs from "CAC40 Bougie de 9h" in exactly four ways:

1. **Instrument**: `GER40.I` (the DAX / German 40 index) instead of `FRA40.I`. GER40 trades the same 9:00–17:30 Central-European session as FRA40 (Xetra ≈ Euronext Paris), so the existing Paris-local reference window and session-end handling apply unchanged.
2. **Different default thresholds** (in points): take-profit offset **10**, break-even trigger **50**, max entry distance **40**, and a stop-loss of **150 measured from the H1 reference level** (see §Stop-loss placement below and FR-G05).
3. **Double take-profit / two-lot position**: every entry opens **two products (lots)** on the same signal. The first lot targets the 50% level of the H1 candle (its midpoint); the second lot targets the full take-profit (H1 high − 10 for a long / H1 low + 10 for a short). See FR-G02–FR-G04.
4. **Take-first-then-break-even**: once the first lot's take-profit (TP1) fills, the remaining lot's stop is immediately moved to break-even (entry), independently of the +50-point break-even trigger.

Everything else — breakout/reversal detection, entry validity, exit ordering (stop before take-profit within a candle), the gap-fill convention, the one-position-at-a-time rule across both directions, and the range/day/CSV outputs — is identical to "CAC40 Bougie de 9h" and is not re-specified here; the requirements below reference the spec 021 requirement they mirror.

## Clarifications

### Session 2026-07-23

- Q: What does "TP1 = 50% of the h1 candle" mean? → A: The midpoint of the H1 high–low range: `(h1_high + h1_low) / 2`. For a long the first lot exits at that midpoint; the short is the mirror. It is not tied to the entry price, the candle body, or the distance to TP2.
- Q: A position is "2 products". How should a position appear in the day result and the aggregate summary? → A: As **one aggregated trade** whose points result is the **sum of both lots'** points. The two lots are not listed as two separate trades. "SL is x2" falls out of this: if both lots stop out before any take-profit, the position's points is twice a single lot's loss.
- Q: Where is the stop-loss placed — 150 points below the entry (as CAC40 does with its 50-point stop) or 150 points below the H1 low? → A: Below the **H1 reference level** — 150 points below the H1 low for a long, 150 points above the H1 high for a short ("150 points below the lower"). This is a **deliberate difference** from "CAC40 Bougie de 9h", whose stop is measured from the entry price. Both lots share this same stop level.
- Q: "When we take TP1, the rest is BE" — does the runner's stop move to entry as soon as TP1 fills, even if price never reached the +50 break-even trigger? → A: Yes. TP1 filling is an independent trigger that arms break-even on the remaining lot; the +50-point favorable-move trigger (FR-G06) is the other, whichever happens first.
- Q: Are the double-take-profit fraction (50%) and the two-lot count tunable per run like the four numeric thresholds? → A: No. The 50% first-target fraction and the two-lot structure are fixed properties of this hardcoded backtest, like the time-cut variant's 30-minute / 5-point settings. The four numeric thresholds (stop-loss, take-profit offset, break-even trigger, max entry distance) remain tunable per run, with the GER40 defaults above.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the "GER40 Bougie de 9h" double-TP backtest for a single day (Priority: P1)

A trader selects the Backtest menu, picks the hardcoded "GER40 Bougie de 9h" backtest, chooses a past trading day, and sees whether the strategy would have entered, and for each entry: where the two lots entered, where each lot exited (first lot at the 50% level, runner at the full target / break-even / stop / end of day), and the position's net points result.

**Why this priority**: This is the core capability — a correct single-day, two-lot, double-take-profit result. Without it the feature delivers nothing.

**Independent Test**: Run the backtest against a known historical GER40.I day where the 9:00–10:00 H1 candle and the subsequent 5-minute candles are known, and verify the reported entry, per-lot exits, and net points match a manual calculation using the rules below.

**Acceptance Scenarios**:

1. **Given** a GER40.I day where, after 10:00, price breaks below the H1 low, a 5-minute candle closes back above it, and a later candle's high confirms the breakout (mirroring CAC40 FR-006/FR-006b/FR-007), **When** the backtest runs, **Then** the system reports a long position of **two lots** entered at the same confirmed entry price.
2. **Given** the open two-lot long from Scenario 1, **When** price rises to reach the **50% level of the H1 candle** (`(h1_high + h1_low) / 2`) before the stop, **Then** the **first lot** is closed at that level (TP1, take-profit), the **remaining lot's stop is moved to entry** (break-even), and the second lot stays open.
3. **Given** the runner from Scenario 2, **When** price then rises to reach **H1 high − 10 points** before its break-even stop or end of day, **Then** the runner is closed at that take-profit level (TP2), and the position's net points is `(TP1 − entry) + (TP2 − entry)`.
4. **Given** the runner from Scenario 2, **When** price instead falls back to the entry price before reaching TP2, **Then** the runner is closed at break-even (≈0 points, gap-fill per CAC40 FR-010 applying to the exact fill), and the position's net points is `(TP1 − entry) + ≈0`.
5. **Given** the open two-lot long from Scenario 1 **before** TP1 has filled, **When** price falls to the stop-loss level (**H1 low − 150 points**) before reaching the 50% level, **Then** **both lots** are closed at that stop level and the position's net points is twice a single lot's loss (`2 × (stop − entry)`, a negative number).
6. **Given** the open two-lot long from Scenario 1 **before** TP1 has filled, **When** a candle's high reaches **entry + 50 points** (the break-even trigger) without TP1 having filled, **Then** the shared stop of **both** still-open lots is moved to entry (break-even) from the next candle onward — the standard CAC40 FR-008a arming, at the GER40 default of 50 points.
7. **Given** an open two-lot long that reaches neither a take-profit nor its stop, **When** the session ends, **Then** every lot still open is closed at the last 5-minute candle's close (end-of-day), and the position's net points sums whatever each lot realised.
8. **Given** the mirror-image setup off the H1 high, **When** a valid short breakdown confirms, **Then** a two-lot **short** is entered, with TP1 at the same 50% midpoint level, TP2 at **H1 low + 10**, the shared stop at **H1 high + 150**, and the +50-point break-even trigger and take-first-then-break-even rules mirrored — exactly the CAC40 short-side mirror (FR-020–FR-023) with the GER40 thresholds and the double-TP overlay.
9. **Given** a day with no 9:00–10:00 H1 candle for GER40.I (holiday, missing data), **When** the backtest runs, **Then** the day is reported as "no data" without failing the run (CAC40 FR-004).

---

### User Story 2 - Run the double-TP backtest over a date range and see aggregate results (Priority: P2)

A trader enters a start and end date, runs "GER40 Bougie de 9h" across every trading day in the range, and sees the same aggregate summary the other backtests produce (number of days, number of trades, winning/losing/BE positions, average win, average loss, final result), where each **position** (not each lot) counts as one trade and contributes its net points.

**Why this priority**: A single day has little statistical value; the range summary is what lets a trader judge the strategy. It builds on User Story 1.

**Independent Test**: Run a known multi-week range with a mix of outcomes and verify the summary figures match a manual computation from the per-day net-points results, counting each two-lot position once.

**Acceptance Scenarios**:

1. **Given** a start and end date, **When** the backtest runs, **Then** the system displays one summary with number of days, number of trades (one per position), number of winning positions, number of losing positions, number of BE positions, average win, average loss, and final result — computed on each position's **net** points (both lots summed), consistent with CAC40 FR-013.
2. **Given** a position where TP1 filled and the runner returned to break-even, **When** the summary is computed, **Then** the position is classified by the **sign of its net points** — a net gain from the banked TP1 makes it a winning position (see §Summary classification and FR-G08).
3. **Given** a range with non-trading days or missing-data days, **When** the backtest runs, **Then** those days are excluded from "number of days" and every other figure and the run completes without error (CAC40 FR-013 scenario 2).
4. **Given** a completed range run, **When** the trader exports CSV, **Then** the download has one row per day (date, status, trade count, points) exactly as CAC40 FR-017, where a two-lot position counts as one trade and contributes its net points.

---

### User Story 3 - Inspect a day's reference levels, candles and trades (Priority: P3)

A trader opens a day's detail view and sees the H1 high/low, the 5-minute candles, and where each position entered and exited, so they can audit the two-lot result against the chart.

**Why this priority**: Builds trust in the hardcoded logic; the strategy is usable without it.

**Independent Test**: Open the detail view for a day with a two-lot position and confirm the H1 levels, 5-minute candles, and the position's entry/exit(s) are consistent with the summary and the underlying chart.

**Acceptance Scenarios**:

1. **Given** a backtested day with a position, **When** the trader opens the detail view, **Then** the system shows the H1 high/low, the 5-minute candles from 10:00 onward, and the position's entry and exit marked against that data (CAC40 FR-015).
2. **Given** a day's detail view, **When** the trader exports CSV, **Then** the download contains the H1 high/low, the 5-minute candle sequence, and the day's trades (CAC40 FR-018).

---

### Edge Cases

- **All CAC40 edge cases carry over**: breach-without-reversal, reversal-without-confirmation, candidate roll-forward, candidate discarded by a fresh close past the H1 level, repeat entry after a closed position, same-candle stop-vs-take-profit priority, break-even arm/breach timing, gap-through exits, confirmed-breakout-too-far-from-the-level, the short-side mirror, and one-position-at-a-time across both directions — all apply here with the GER40 thresholds. Read them from spec 021; only the double-TP-specific additions are listed below.
- **TP1 and the stop breached in the same pre-TP1 candle**: while both lots are still open, if a single candle would reach both the stop (H1 low − 150 for a long) and the 50% level, the **stop wins** for **both lots** (the conservative CAC40 FR-009 rule, applied to the whole position before any scale-out).
- **TP1 and TP2 in the same candle**: if a single candle reaches both the 50% level and the full target (H1 high − 10) while both lots are open, the first lot fills at TP1 and the runner fills at TP2 on that same candle (both are favorable price-level exits; the runner's break-even arming from the TP1 fill is moot because TP2 is reached). Net points is `(TP1 − entry) + (TP2 − entry)`.
- **Break-even trigger and TP1 on the same candle**: if a candle's high both reaches entry + 50 and reaches the 50% level, TP1 fills (a take-profit) and the runner's stop is at break-even either way; the two triggers agree on the outcome.
- **Runner stops at break-even after TP1, with a gap**: if the candle that takes the runner out at break-even opens beyond the entry price, the runner fills at that open (CAC40 FR-010 gap-fill), so the runner's points can be a small non-zero value; the position is still net-positive by the banked TP1.
- **Entry validity uses both targets (TP1 and TP2)**: a confirmed breakout is a valid entry only if it is within the max entry distance (40 points) of the H1 reference level **and** strictly on the favorable side of **both** take-profit levels — strictly below TP1 (the H1 midpoint) and TP2 (H1 high − 10) for a long, strictly above both for a short. Since TP1 sits between the reference level and TP2, requiring `entry < TP1` (long) is the binding constraint and implies `entry < TP2`. This extends the CAC40 FR-006a/FR-020a rule (which checks only the single take-profit) so that a valid double-TP entry always leaves room for **the first lot** to reach a genuine profit at TP1.
- **Narrow H1 range where the midpoint is at/below the entry (rejected)**: for an entry within 40 points of the H1 low, the midpoint `(h1_high + h1_low)/2` is above the entry only when the H1 range exceeds twice the entry-above-low distance. On a narrow H1 range (GER40's 9:00–10:00 range is frequently 50–80 points), an otherwise-valid entry (within the max entry distance) can land **at or past** the midpoint. Such an entry is **not valid and no trade is opened** — the strategy resumes searching for a fresh breakout. This is deliberate: opening it would fire TP1 on the very next candle, bank a loss as a "take-profit," arm the runner to break-even, and discard the 150-point structural stop before it could work — defeating the whole point of the GER40 variant. (Revised after PR review; the earlier draft treated this as a rare fire-immediately boundary case.)
- **"SL is x2" is an accounting consequence, not a second stop**: there is one stop **level** shared by both lots; the doubled loss simply reflects that two lots exit at it. Once TP1 has filled, only the runner remains, so a subsequent stop (now at break-even) affects one lot.

## Requirements *(mandatory)*

### Functional Requirements

Requirements below are numbered FR-G## and are additive/override requirements on top of "CAC40 Bougie de 9h" (spec 021, FR-001–FR-031). Every spec 021 requirement not overridden here applies unchanged, with the GER40 instrument and default thresholds substituted.

- **FR-G01**: System MUST provide a third hardcoded backtest, **"GER40 Bougie de 9h"**, selectable from the Backtest menu alongside "CAC40 Bougie de 9h" and its time-cut variant (extends CAC40 FR-001/FR-002). It runs on the **GER40.I** instrument and applies the base "CAC40 Bougie de 9h" rule set (reference range, both-direction breakout/reversal detection, entry validity, exit ordering, one-position-at-a-time, gap-fill, end-of-day, range/day/CSV outputs) with the GER40 defaults (FR-G05) and the double-take-profit overlay (FR-G02–FR-G04, FR-G07). Adding it does not make the menu a generic engine — it is a third fixed strategy.
- **FR-G02**: Every valid entry (long or short) MUST open a position of **two lots** at the confirmed entry price and time. The two lots are managed together while both are open and share one stop level (FR-G05). Entry validity extends the base FR-006a/FR-020a check: in addition to the max-entry-distance and full-take-profit (TP2) bounds, the entry MUST be strictly on the favorable side of the **first target (TP1, the H1 midpoint)** — below TP1 for a long, above it for a short. An entry at or past TP1 is rejected (it would otherwise fire TP1 immediately and discard the structural stop — see the "narrow H1 range" edge case).
- **FR-G03**: The position MUST have two take-profit targets:
  - **TP1 (first lot)** — the **50% level of the H1 candle**: `(h1_high + h1_low) / 2`, the same level for a long and a short. When price reaches TP1, the **first lot only** is closed at TP1 (a take-profit exit, gap-fill per CAC40 FR-010).
  - **TP2 (runner)** — the **full take-profit level**: H1 high − take-profit offset for a long, H1 low + take-profit offset for a short (offset default 10, CAC40 FR-008/FR-022). When price reaches TP2, the runner is closed at TP2.
- **FR-G04**: When **TP1 fills** (FR-G03), the remaining (runner) lot's stop MUST be moved to the entry price (**break-even**) immediately, from the next candle onward, independently of whether the +50-point break-even trigger (FR-G06) has fired. This is a second, TP1-driven path to arming break-even, in addition to the favorable-move trigger.
- **FR-G05**: The stop-loss for the position MUST be placed **150 points beyond the H1 reference level** — **150 points below the H1 low for a long**, **150 points above the H1 high for a short** — and is **shared by both lots** while both are open. This is a deliberate difference from "CAC40 Bougie de 9h", whose stop is measured from the entry price; here the 150-point default is measured from the H1 reference level. While both lots are open, a stop hit closes **both** lots at that level; after TP1 has filled and moved the runner to break-even (FR-G04), only the runner remains and its stop is the entry price.
- **FR-G06**: While a lot's stop has not yet been moved, the base break-even arming (CAC40 FR-008a/FR-022) applies at the GER40 default of **50 points**: the moment a candle's high reaches entry + 50 (long) / low reaches entry − 50 (short), the still-open lots' shared stop moves to the entry price, at most once, from the next candle onward. FR-G04 (TP1-driven) and FR-G06 (favorable-move-driven) are the two ways the runner reaches break-even, whichever occurs first.
- **FR-G07**: A position MUST be reported to the day result and the aggregate summary as **one aggregated trade**, whose **points result is the sum of both lots'** realised points. The two lots MUST NOT be listed as two separate trades. The aggregated trade's exit reason reflects how the **position finally closed** (the runner's exit): take-profit when the runner reached TP2, break-even when the runner closed at its moved (entry) stop, stop-loss when both lots stopped out before any take-profit, or end-of-day. A position where the first lot took TP1 and the runner then stopped at break-even is a take-first-then-break-even outcome recorded as a break-even exit with a net-positive points result (the banked TP1).
- **FR-G08**: In the aggregate summary (CAC40 FR-013), a two-lot position MUST be counted as **one trade** and classified by the **sign of its net points** (both lots summed): net > 0 is a winning position, net < 0 is a losing position, and a position that closed flat with no take-profit filled (both lots at break-even or a net of exactly 0) counts toward "number of BE". Average win and average loss use each position's net points; break-even positions are excluded from both, consistent with CAC40 FR-013. (This mirrors how the time-cut variant classifies by points sign rather than forcing a mechanism-only bucket.)
- **FR-G09**: The four numeric thresholds MUST remain **tunable per run** exactly as in CAC40 FR-025–FR-027 (validated strictly greater than 0, per-run only, not persisted), with these **GER40 defaults**: stop-loss **150** (measured from the H1 level, FR-G05), take-profit offset **10**, break-even trigger **50**, max entry distance **40**. The **50% first-target fraction** and the **two-lot** structure are **fixed properties** of this backtest, NOT tunable parameters (like the time-cut variant's 30-minute / 5-point settings, CAC40 FR-031).
- **FR-G10**: The per-day detail (CAC40 FR-015), the day/summary responses, and the CSV exports (CAC40 FR-017/FR-018) MUST include this backtest's positions using the existing trade fields (direction, entry time/price, exit time/price, exit reason, points), where a position is one aggregated trade (FR-G07). No new response shape is required beyond the existing Trade representation; the double-TP detail is summarised into the single aggregated trade.

### Key Entities

- **Backtest Definition** (extends spec 021): "GER40 Bougie de 9h" is a third instance — instrument `GER40.I`, the base "CAC40 Bougie de 9h" rule set, plus the fixed double-take-profit properties (two lots, 50% first-target fraction) and the GER40 default thresholds. The data model must continue not to assume a single definition.
- **Backtest Parameters** (unchanged shape): the four tunable thresholds (stop-loss distance, take-profit offset, break-even trigger, max entry distance), here defaulting to the GER40 values (FR-G09). The stop-loss distance is reinterpreted for this definition as a distance from the H1 reference level rather than from entry (FR-G05).
- **Position (two lots)**: an entry opens two lots at one price/time, sharing one stop level; the first lot targets the 50% midpoint (TP1), the runner targets the full take-profit (TP2) with a stop moved to break-even once TP1 fills. Surfaced to all outputs as **one aggregated Trade** whose points is the sum of both lots (FR-G07).

## Success Criteria *(mandatory)*

- **SC-G01**: A trader can select the Backtest menu, run "GER40 Bougie de 9h" for a single past day, and within a few seconds see a correct result (no data / no trade / one or more two-lot positions, each with entry, per-position net points, and exit reason).
- **SC-G02**: On a hand-verified set of at least 6 historical GER40.I days covering all outcome types (no data, no trade, both-lots stop-out, +50 break-even, TP1-then-break-even, TP1-then-TP2 full winner, end-of-day, and a day with more than one position), the reported entry, per-lot exits, net points, and exit reason match manual calculation exactly.
- **SC-G03**: A trader can run a multi-week range and receive a summary (days, trades counted one-per-position, winning/losing/BE positions, average win, average loss, final result) that matches a manual computation from the per-day net-points results.
- **SC-G04**: A trader can open a day's detail view and confirm the H1 levels and the position's entry/exit against the underlying 5-minute candles.
- **SC-G05**: Running the same range on "GER40 Bougie de 9h" versus "CAC40 Bougie de 9h" (on their respective instruments) shows the GER40 backtest using the GER40 defaults and the double-take-profit two-lot behavior, while "CAC40 Bougie de 9h" is entirely unaffected by this feature.

## Assumptions

- "Points" is the raw index price difference on GER40.I; no position sizing or currency P&L is in scope. "Two lots" is a **unit** count for points accounting (net = sum of both lots), not a monetary position size.
- GER40.I H1 and 5-minute candle history for past, fully-closed days is obtainable through the existing Saxo historical-candle capability, the same as FRA40.I; no new market-data source is required. GER40 trades the same 9:00–17:30 Central-European session, so the existing Paris-local (Europe/Paris, DST-aware) reference-window and session-end handling apply unchanged.
- The backtest operates only on already-closed historical days (CAC40 assumption), computed on demand and returned synchronously; nothing is persisted.
- The **stop-loss is measured from the H1 reference level** (150 points beyond it), a deliberate difference from "CAC40 Bougie de 9h" — surfaced explicitly for validation (Clarifications, 2026-07-23). The other three thresholds (take-profit offset, break-even trigger, max entry distance) keep the CAC40 entry-/level-relative meaning.
- **TP1 is the H1 midpoint** `(h1_high + h1_low)/2`, the same level for both directions (Clarifications, 2026-07-23). The 50% fraction and the two-lot count are fixed strategy properties, not tunable parameters.
- A position is surfaced as **one aggregated trade** (net points = both lots summed); the two lots are an internal mechanic, not two separate trades in any output (Clarifications, 2026-07-23). Its exit reason reflects the runner's final exit; its summary classification is by net-points sign (FR-G08).
- "CAC40 Bougie de 9h" and its time-cut variant are unchanged by this feature; the Backtest menu now lists three hardcoded backtests. No generic backtest-authoring capability is being built.

---

# Addendum: "GER40 Bougie de 9h (bougie impulsive)" variant

**Added**: 2026-07-27
**Input**: User description: "Let's introduce the concept of impulsive candle: it's a very biggest candle than the other one. To simplify for now, let's say 70 pts for a dax 5 min candle. For the SL we don't close the position except if we have a impulsive candle or end of day. It's a new backtest definition. We don't trade range smaller than 70 pts. Create also a new market: EuCfdMarket, open at 9 am and close 10 pm, we trade over this market."

## Context

This addendum defines a **fourth GER40 backtest**, `G9HIC` — "GER40 Bougie de 9h (bougie impulsive)". It is a **new definition**, not a change to `G9H` or `G9HSL`, both of which stay byte-for-byte unchanged.

It takes the **single-lot** GER40 setup (`G9HSL`) and replaces the fixed 150-point stop-loss with an **impulse stop**: the position is never closed by price merely trading through a level. It is closed only by an **impulsive candle** moving against it, by its take-profit, by its break-even stop once armed, or by end of day. Two further differences: days whose 9:00–10:00 H1 range is too narrow are not traded at all, and the session runs on a new **CFD market window** (9:00–22:00 Paris) rather than the 17:30 cash close.

## Clarifications

### Session 2026-07-27

- Q: How is an "impulsive candle" measured on a 5-minute DAX candle? → A: On the **full range including wicks**: `high − low ≥ 70` points. Not the body.
- Q: Does an impulsive candle alone close the position? → A: No. Three conditions must hold together: (1) impulsive amplitude, (2) the candle **closes near the extreme that hurts the position** — within 25% of its own range from that extreme, so a long wick that came back does not count, and (3) the candle **closes beyond the H1 reference level** on the losing side (the same confirmed-break condition the wide-range structural variant uses). The exit is a market exit at that candle's **close**.
- Q: Which side counts as "near the low (or high depending on the direction)"? → A: The side that hurts the open position. For a **long**, the adverse extreme is the candle's **low**, so `(close − low) / (high − low) ≤ 0.25`. For a **short** it is the **high**, so `(high − close) / (high − low) ≤ 0.25`. The shape test therefore carries the "against us" direction intrinsically — a 70-point candle closing near its high can never stop a long.
- Q: Is the fixed stop-loss distance still applied at all? → A: No. There is **no fixed stop distance** while break-even is unarmed. Once the +50-point break-even trigger fires, the break-even stop at the entry price becomes an ordinary intrabar stop, exactly as in the wide-range structural variant.
- Q: Single lot or the double take-profit? → A: **Single lot**, with the take-profit (H1 far level − 10) and the +50-point break-even arming kept. This isolates what the impulse stop itself changes relative to `G9HSL`.
- Q: "We don't trade range smaller than 70 pts" — which range? → A: The **day's 9:00–10:00 H1 reference range** (`h1_high − h1_low`), reusing the existing minimum-range filter (`min_h1_range_points`), whose established semantics reject a range that is **not strictly greater** than the threshold — a range of exactly 70.0 is therefore not traded. Reused as-is rather than introducing a second convention.
- Q: What are the `EuCfdMarket` hours, and what does the backtest use them for? → A: **09:00–22:00 Europe/Paris**, DST-aware like every other market. The backtest uses it for the **session end** — 5-minute candles are scanned from 10:00 to 22:00 instead of to the 17:30 Euronext cash close — and therefore for where an end-of-day exit lands. The 9:00–10:00 H1 reference window is unchanged (`EuCfdMarket` also opens at 9:00).

## User Scenarios & Testing

### User Story 4 - Run the impulsive-candle backtest (Priority: P1)

A trader selects the Backtest menu, picks "GER40 Bougie de 9h (bougie impulsive)", chooses a past trading day or a date range, and sees a strategy that holds through ordinary adverse moves and only gives up when a genuinely violent 5-minute candle breaks the H1 level against it.

**Why this priority**: It is the whole point of the variant — testing whether surviving noise, at the cost of an unbounded worst case, beats a fixed 150-point stop.

**Independent Test**: Run the backtest against a historical GER40.I day whose 9:00–10:00 range exceeds 70 points and whose afternoon contains a known 70-point 5-minute candle, and verify the position survives every smaller adverse candle and closes at the impulsive candle's close.

**Acceptance Scenarios**:

1. **Given** a day whose H1 range (`h1_high − h1_low`) is not strictly greater than 70 points, **When** the backtest runs, **Then** the day is reported as **no trade**, no 5-minute candles are fetched, and no position is opened.
2. **Given** an open long from a confirmed breakout, **When** price falls far below the entry — past where a 150-point stop would have sat — but no 5-minute candle satisfies all three impulse conditions, **Then** the position **stays open**.
3. **Given** an open long, **When** a 5-minute candle has a range of at least 70 points, closes within the bottom 25% of its own range, and closes below the H1 low, **Then** the position is closed at **that candle's close** with exit reason `stop_loss`, with no gap-fill adjustment (it is a market exit).
4. **Given** an open long, **When** a 5-minute candle spans 70 points but closes mid-range (a long lower wick that came back), **Then** the position **stays open** — the candle is not impulsive against it.
5. **Given** an open long, **When** a 5-minute candle closes in the bottom 25% of its range and below the H1 low but spans only 69 points, **Then** the position **stays open**.
6. **Given** an open long, **When** a candle satisfies all three impulse conditions **and** the same candle also reaches the take-profit level, **Then** the **take-profit wins** — a target is touched intrabar while the impulse stop is measured on the close.
7. **Given** an open long whose break-even has been armed by the +50-point trigger, **When** price returns to the entry price, **Then** the position closes at break-even as an ordinary intrabar stop (with the FR-010 gap-fill), and the impulse rule no longer applies.
8. **Given** an open position that meets no take-profit, no armed break-even stop and no impulsive candle, **When** the session ends at **22:00 Paris**, **Then** it is closed at the last 5-minute candle's close with exit reason `end_of_day`.
9. **Given** the mirror-image setup off the H1 high, **When** a valid short confirms, **Then** the impulse stop fires only on a candle spanning at least 70 points that closes within the **top** 25% of its range and **above** the H1 high.

---

### Edge Cases

- **Zero-range candle**: a candle with `high == low` cannot reach 70 points, so the amplitude test rejects it before the shape test is consulted; no division by zero is possible (the shape test is expressed multiplicatively).
- **Impulse and armed break-even on the same candle**: once break-even is armed, the break-even stop leads the chain and closes the position at the entry price; the impulse rule is not reached. This is deliberate — an armed position has a real stop again and no longer needs the impulse fallback.
- **Impulsive candle in our favor**: never closes the position. A 70-point candle closing near its high is, for a long, a large favorable move; it can only trigger the take-profit or arm break-even.
- **Unbounded loss on a gap**: with no fixed stop, a single 5-minute candle can carry the position far past where a 150-point stop would have exited before the impulse rule fires on its close. This is inherent to the variant and is what the backtest is meant to measure — the loss column, not just the win rate, is the result of interest.
- **Longer session, more candles**: extending the scan to 22:00 roughly doubles the 5-minute candles per day versus the 17:30 cash close, so a position can survive far longer, and end-of-day exits land at the 21:55 candle's close. Days already cached under other definitions are unaffected — this definition has its own cache key.

## Requirements

Requirements below are numbered FR-G1## and are additive on top of spec 021 and the FR-G0## requirements above. Every requirement not overridden here applies unchanged.

- **FR-G11**: System MUST provide a hardcoded backtest **"GER40 Bougie de 9h (bougie impulsive)"** (code `G9HIC`, `Strategy.G9HIC`), selectable from the Backtest menu alongside the existing definitions. It runs on `GER40.I`, single lot, with the GER40 default thresholds (FR-G09). Registering it MUST NOT change the behavior of any existing definition.
- **FR-G12**: System MUST define a new market, **`EuCfdMarket`** — Europe/Paris, open **09:00**, close **22:00**, DST-aware like the existing markets — and `G9HIC` MUST run its session against it. The 5-minute scan window is 10:00 → 22:00 Paris local, and an end-of-day exit is the close of the last 5-minute candle in that window. The 9:00–10:00 H1 reference window is unchanged.
- **FR-G13**: A `BacktestDefinition` MUST carry the market its session is derived from, defaulting to `EUMarket` so every existing definition keeps the 9:00–17:30 window it runs today. The reference-window, session-end and "today's session has not closed yet" calculations MUST all use the definition's market rather than a hardcoded one.
- **FR-G14**: A 5-minute candle is **impulsive against an open position** when all three hold: (a) `high − low ≥ 70` points (the definition's `impulsive_candle_points`); (b) the candle closes within **25%** of its range (`impulsive_close_fraction`) of the extreme adverse to the position — `(close − low) ≤ 0.25 × (high − low)` for a long, `(high − close) ≤ 0.25 × (high − low)` for a short; (c) the candle **closes beyond the H1 reference level** on the position's losing side (below the H1 low for a long, above the H1 high for a short).
- **FR-G15**: For `G9HIC`, an open position MUST NOT be closed by any fixed stop-loss distance. While break-even is unarmed, the only stop is FR-G14's impulse stop, which closes the position at **that candle's close** with exit reason `stop_loss` (a market exit — the FR-010 gap-fill does not apply). The `stop_loss_points` threshold is unused by this definition.
- **FR-G16**: The take-profit (FR-008, H1 far level − offset) and the break-even arming (FR-008a, at the GER40 default of 50 points) MUST apply unchanged. Once armed, the break-even stop at the entry price is an ordinary intrabar stop with the FR-010 gap-fill, and it takes precedence over the impulse rule. A take-profit reached on the same candle as an impulse MUST resolve as the take-profit, since a target is touched intrabar while the impulse stop is measured on the close.
- **FR-G17**: `G9HIC` MUST NOT trade a day whose H1 range is not strictly greater than **70 points**, reusing the existing minimum-range filter: such a day is reported as `no_trade` and its 5-minute candles are not fetched.
- **FR-G18**: The impulse threshold (70 points), the close fraction (25%), the minimum H1 range (70 points) and the single-lot structure are **fixed properties** of this backtest, NOT per-run tunable parameters — like the time-cut variant's 30-minute / 5-point settings (FR-031) and the double-TP fraction (FR-G09). The four numeric thresholds remain tunable per run, with the GER40 defaults, though `stop_loss_points` has no effect here (FR-G15).

### Key Entities

- **Market** (extended): `EuCfdMarket` joins `EUMarket`/`USMarket` as a session definition (09:00–22:00 Europe/Paris). `BacktestDefinition` gains a `market` field so each backtest states which session it runs on.
- **Backtest Definition** (extended): gains `impulsive_candle_points` and `impulsive_close_fraction`. When the former is set, the exit chain swaps its fixed stop for the impulse stop. Both default to "off" so existing definitions are unaffected.

## Success Criteria

- **SC-G06**: A trader can select "GER40 Bougie de 9h (bougie impulsive)" and run a single day and a multi-week range, receiving the same outputs (day detail, summary, CSVs) as every other definition, with no frontend change required.
- **SC-G07**: On hand-built candle days covering every FR-G14 boundary — impulsive-and-adverse-and-beyond-level, impulsive but closing mid-range, adverse-and-beyond-level but only 69 points, impulsive in our favor, impulse-vs-take-profit on one candle, armed-break-even-beats-impulse, and end-of-day at 22:00 — the reported exits and points match manual calculation exactly.
- **SC-G08**: A day whose H1 range is ≤ 70 points reports `no_trade` and performs no 5-minute fetch.
- **SC-G09**: `B9H`, `B9HTC`, `G9H`, `G9HSL` and `B9HWS` produce byte-for-byte identical results before and after this change, and continue to use the 9:00–17:30 `EUMarket` window.

## Assumptions

- 70 points is a placeholder calibrated by eye for a 5-minute DAX candle ("to simplify for now"), not a statistically derived threshold; it is a fixed property of the definition, so changing it means editing the definition (or registering another one), which is deliberate — it keeps the run parameters honest about what was actually tested.
- The 25% close fraction is likewise fixed. It exists to exclude long-wick reversal candles that spanned 70 points but closed back inside the range.
- GER40.I is quoted as a CFD outside the Xetra cash session, so 5-minute candles are expected to exist between 17:30 and 22:00. A day where Saxo returns nothing after 17:30 simply behaves as it does today (the scan ends with the last candle available).
- The variant is expected to have a worse worst-case loss than `G9HSL` and a higher win rate; whether that trade is favorable is exactly what the backtest is being built to answer. No deployment decision is implied by adding it.
