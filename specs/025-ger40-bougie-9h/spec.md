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
- **FR-G17b**: The daily regime measures (`mm50_slope`, `adx14`, `overnight_gap`) MUST be computed on **cash-session daily candles for every definition**, including the ones trading the CFD session. They measure the instrument, not the strategy, and are only comparable across definitions if the same day scores identically on all of them — a day sized 9:00–17:30 for one backtest and 9:00–22:00 for another is not the same daily bar, and `overnight_gap` would measure from a different prior close.
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
- A definition's market governs **what it trades** (the 5-minute scan window, the session end, the "has today closed" check), never **how it is measured**. The regime columns stay on the cash session regardless (FR-G17b).
- The variant is expected to have a worse worst-case loss than `G9HSL` and a higher win rate; whether that trade is favorable is exactly what the backtest is being built to answer. No deployment decision is implied by adding it.

---

# Addendum 2: entry cut-off and daily loss cap for `G9HIC`

**Added**: 2026-07-27
**Input**: User description: "add a new condition I forgot. We don't take any new position after 4pm and we don't take any new position if we already had two lost."

## Context

Two **entry filters** on the existing `G9HIC` definition. Neither touches how an open position is managed: an impulsive candle, the take-profit, the armed break-even stop and the 22:00 end-of-day exit all behave exactly as specified in Addendum 1. These rules only decide whether the engine is allowed to *open* a new position.

They are a change to `G9HIC` **in place**, not a seventh definition (Clarifications below). The other five definitions are untouched.

Both address the same weakness of a variant with no fixed stop: its worst case is unbounded, so the cost of a bad afternoon compounds. The cut-off stops a position being opened so late that its only realistic exit is the 22:00 close, and the loss cap stops a day that is already going badly from paying for a third attempt.

## Clarifications

### Session 2026-07-27 (2)

- Q: What counts as one of the "two lost" trades? → A: Any trade that closed with **negative points**, whatever its exit reason — an impulse stop, a break-even exit whose gap-fill landed below entry, or an end-of-day close below entry. This is the same test the run summary already uses to count losing positions, so "2 losses" means the same thing in the day detail, the summary and this rule.
- Q: Should these rules change `G9HIC` in place or ship as a new definition? → A: **In place.** `G9HIC` has never been run for real or written up in `backtests/`, so no published result is invalidated, and the menu does not grow a near-duplicate. The `G9HIC` golden snapshot is expected to shift.
- Q: Does the 16:00 cut-off close an already-open position? → A: **No.** It is purely an entry filter. A position opened at 15:55 is managed to its normal exit and may well close at 22:00. Only *opening* is blocked.
- Q: Does the loss cap count across days? → A: **No — per trading day.** A backtest day is evaluated independently and no position spans days, so the counter starts at zero each day and resets with it.
- Q: Are the 16:00 cut-off and the 2-loss cap tunable per run? → A: **No.** Like the 70-point impulse threshold and the 25% close fraction, they are fixed properties of this backtest (FR-G18).

## User Scenarios & Testing

### User Story 5 - Stop opening positions late in the day or after a bad start (Priority: P1)

A trader running "GER40 Bougie de 9h (bougie impulsive)" sees no entries taken after 16:00 Paris, and none once the day has already produced two losing trades — while positions opened before either limit are managed to their normal exits.

**Why this priority**: Both rules bound a variant whose worst case is otherwise unbounded; without them the strategy's exposure is not what the trader intends.

**Independent Test**: Run a day whose candles would confirm a valid breakout at 16:05 and verify no position is opened; run a day with three consecutive losing setups and verify only the first two are taken.

**Acceptance Scenarios**:

1. **Given** a day where a valid breakout confirms on a 5-minute candle starting at **15:55 Paris**, **When** the backtest runs, **Then** the position **is** opened normally.
2. **Given** a day where a valid breakout confirms on a 5-minute candle starting at **16:00 Paris** or later, **When** the backtest runs, **Then** **no position is opened**, and none is opened by any later candle that day.
3. **Given** a position opened at 15:55 that has not hit a take-profit, an impulsive candle or a break-even stop, **When** the session reaches 22:00, **Then** it closes at end-of-day as usual — the 16:00 cut-off did not close it early.
4. **Given** a day where the first two positions both close with negative points, **When** a third valid breakout confirms before 16:00, **Then** **no position is opened**.
5. **Given** a day where the first two positions close one with negative points and one with positive points, **When** a third valid breakout confirms before 16:00, **Then** the position **is** opened — the cap counts losses, not trades.
6. **Given** a day whose second losing position is still open, **When** a candle would confirm another entry, **Then** the question does not arise: the one-position-at-a-time rule (FR-011) already blocks it, and the loss counter only increments when a position **closes**.
7. **Given** a day where two positions have closed at a loss, **When** the session ends with no position open, **Then** the day reports exactly those two trades and `TRADED` status.
8. **Given** a day whose losses come from mixed exit reasons — one impulse stop and one end-of-day close below entry — **When** a third breakout confirms, **Then** it is blocked: both count, because both closed with negative points.

---

### Edge Cases

- **A trade closing at exactly 0 points** (an end-of-day close landing on the entry price, or a clean break-even) is **not** a loss and does not count toward the cap. Only strictly negative points count.
- **Cut-off and cap are independent**: either one alone blocks an entry. A day can be stopped by the clock having taken no losses at all, or by two losses at 10:30.
- **The cut-off is measured on the candle's start time**, the same timestamp the entry is recorded at, so the last candle that can open a position is the one starting 15:55 and running to 16:00.
- **DST**: 16:00 is Paris local time, resolved the same DST-aware way as the 9:00 reference window and the 22:00 session end, so it is 14:00 UTC in summer and 15:00 UTC in winter.
- **A day with no data or an H1 range ≤ 70 points** is unaffected — it never reaches the entry search at all (FR-G17).
- **Interaction with the breakout search**: blocking an entry must not corrupt the direction searches. After the cut-off the search state is irrelevant because nothing can open; before it, a blocked entry behaves as the existing "confirmed but not valid" path already does.

## Requirements

- **FR-G19**: `G9HIC` MUST NOT open a new position on any 5-minute candle whose start time is **at or after 16:00 Paris local time** (DST-aware, derived from the definition's market timezone). The last candle that can open a position is the one starting at 15:55. This filter applies to both directions.
- **FR-G20**: `G9HIC` MUST NOT open a new position once **two positions have already closed with negative points on that trading day**. A trade's points being strictly less than 0 is the test, whatever its exit reason; a trade closing at exactly 0 points does not count. The counter is per trading day and starts at zero each day.
- **FR-G21**: Neither filter MUST affect an already-open position. Exit handling — the impulse stop (FR-G14/FR-G15), the take-profit and break-even arming (FR-G16), and the 22:00 end-of-day close (FR-G12) — is unchanged, including for a position opened at 15:55 and for the second losing position while it is still open.
- **FR-G22**: Both filters MUST be **fixed properties** of `G9HIC`, not per-run tunable parameters (extending FR-G18). The four numeric thresholds remain tunable, with `stop_loss_points` still unused (FR-G15).
- **FR-G23**: The filters MUST leave every other definition unchanged: `B9H`, `B9HTC`, `G9H`, `G9HSL` and `B9HWS` take entries at any hour of their session and are not subject to a loss cap.

### Key Entities

- **Backtest Definition** (extended): gains a last-entry cut-off time and a maximum-losses-per-day count. Both default to "off" (None) so a definition without them behaves exactly as it does today.

## Success Criteria

- **SC-G10**: On a hand-built day where a valid breakout confirms at 16:00, no position is opened; on the same setup shifted to 15:55, one is.
- **SC-G11**: On a hand-built day with three losing setups, exactly two trades are reported; with a loss/win/loss sequence, three are.
- **SC-G12**: A position opened at 15:55 still closes at 22:00 end-of-day, proving the cut-off is an entry filter only.
- **SC-G13**: `B9H`, `B9HTC`, `G9H`, `G9HSL` and `B9HWS` produce byte-for-byte identical golden results before and after this change; only `G9HIC`'s rows move.

## Assumptions

- 16:00 and "two losses" are, like the 70-point threshold, judgement calls stated to be tested rather than derived — fixed on the definition so a run's results always correspond to the rules as shipped.
- The loss cap is evaluated when a position **closes**, so the third entry of a day is blocked only if both prior positions have already resolved as losses; this falls out of the one-position-at-a-time rule and needs no separate ordering rule.
- Both filters reduce the number of trades and are expected to reduce the number of days that end deeply negative. Whether they improve the strategy overall is what the run is for; adding them implies no deployment decision.

---

# Addendum 3: two-lot impulsive variant (`G9HICD`)

**Added**: 2026-07-27
**Input**: User description: "I want to do a last test: do the same impulsive strategy with two lots. tp1 as of today. tp2 is 100 pts above (if long). As usual we close everything end of day."

## Context

A **seventh definition**, `G9HICD` — "GER40 Bougie de 9h (bougie impulsive, 2 lots)". It is `G9HIC` with a two-lot / double-take-profit overlay, and inherits every other rule of that variant unchanged: the impulse stop with no fixed stop distance (FR-G14/FR-G15), the 70-point minimum H1 range (FR-G17), the 9:00–22:00 CFD session (FR-G12), the 16:00 entry cut-off and the two-loss daily cap (FR-G19/FR-G20).

`G9HIC` is deliberately left as-is so it remains the single-lot control this variant is measured against — the same relationship `G9HSL` has to `G9H`.

The difference from the existing double-TP variant (`G9H`) is where the two targets sit. `G9H` splits *inside* the H1 range: TP1 at the midpoint, TP2 just short of the far end. `G9HICD` puts TP1 where the single-lot variant already takes profit and sends the runner **beyond the H1 range entirely**, 100 points further. It is a test of whether the impulse stop's willingness to sit through noise is worth a target the range-bound variants can never reach.

## Clarifications

### Session 2026-07-27 (3)

- Q: "TP1 as of today" — which level is that? → A: The take-profit `G9HIC` uses now: the **H1 far level minus the take-profit offset** (H1 high − 10 for a long, H1 low + 10 for a short, at the GER40 default offset). Not the H1 midpoint that `G9H` uses for its first lot.
- Q: TP2 is "100 pts above" — above what? → A: **100 points beyond TP1**, in the position's favorable direction: `TP1 + 100` for a long, `TP1 − 100` for a short. So for a long, TP2 = H1 high + 90 — outside the H1 range. Measuring from TP1 rather than from the entry keeps TP2 strictly beyond TP1 whatever the H1 range and whatever the entry price.
- Q: When TP1 fills, does the runner get a break-even stop, or does it keep running under the impulse rule alone? → A: **Break-even**, exactly as `G9H` does (FR-G04). Once the first lot is banked the runner's stop moves to the entry price, and from then on it is an ordinary intrabar stop that takes precedence over the impulse rule.
- Q: Does this replace `G9HIC` or ship alongside? → A: **Alongside**, as a new definition. `G9HIC` stays the single-lot control.
- Q: Are the 100-point runner extension and the two-lot structure tunable per run? → A: **No** — fixed properties of the definition, like the 70-point impulse threshold and the 25% close fraction (FR-G18/FR-G22).

## User Scenarios & Testing

### User Story 6 - Run the two-lot impulsive backtest (Priority: P1)

A trader selects "GER40 Bougie de 9h (bougie impulsive, 2 lots)", runs a day or a range, and sees positions that bank the first lot at the usual target and let the second run 100 points past it, with the runner protected at break-even once the first is banked.

**Why this priority**: It is the whole variant.

**Independent Test**: Run a hand-built day where price reaches TP1 and then TP2, and one where it reaches TP1 and falls back, verifying the net points of each.

**Acceptance Scenarios**:

1. **Given** a valid long entry, **When** the position opens, **Then** it opens **two lots** at the same price, with TP1 at H1 high − 10 and TP2 at H1 high + 90.
2. **Given** that open position, **When** price reaches **TP1** before any impulsive candle, **Then** the first lot closes at TP1 and the runner's stop moves to **break-even** (entry).
3. **Given** the runner from Scenario 2, **When** price reaches **TP2**, **Then** the runner closes there and the position's net points is `(TP1 − entry) + (TP2 − entry)`.
4. **Given** the runner from Scenario 2, **When** price falls back to the entry price instead, **Then** the runner closes at break-even and the position's net points is the banked TP1 alone.
5. **Given** the runner from Scenario 2, **When** an impulsive candle occurs after TP1 filled, **Then** the **break-even stop wins** — the runner is already protected at entry, and an armed stop takes precedence over the impulse rule (FR-G16).
6. **Given** an open two-lot position **before** TP1 fills, **When** an impulsive candle closes beyond the H1 level against it, **Then** **both lots** close at that candle's close and the net points is twice a single lot's loss.
7. **Given** an open two-lot position before TP1 fills, **When** a candle reaches the +50 break-even trigger, **Then** the shared stop moves to entry as usual (FR-G06), and the impulse rule no longer applies.
8. **Given** any position still open at the session end, **When** 22:00 is reached, **Then** **every lot still open** closes at the last 5-minute candle's close, whether that is both lots or the runner alone.
9. **Given** the mirror short setup, **When** it confirms, **Then** TP1 is H1 low + 10 and TP2 is H1 low − 90, with everything else mirrored.

---

### Edge Cases

- **TP1 and TP2 on the same candle**: both fill on it, as in `G9H` — net points is `(TP1 − entry) + (TP2 − entry)`. They are 100 points apart, so this needs a candle spanning at least that.
- **An impulsive candle that also reaches TP1**: the take-profit wins, since a target is touched intrabar and the impulse is measured on the close (FR-G16). The first lot banks and the runner arms break-even; whether the runner then survives depends on later candles.
- **Entry validity**: unchanged in effect. The double-TP rule requires the entry to sit strictly on the favorable side of **both** targets (FR-G02); since TP1 is the nearer of the two here, TP1 is the binding constraint — which is exactly the single-lot check `G9HIC` already applies. Given the same state, both variants therefore accept and reject exactly the same breakouts.
- **But the two variants do not take the same *set* of trades over a day.** The runner holds the single position slot until TP2, break-even or the session end, while `G9HIC` exits outright at that same level and is immediately free to search again. On a day with several setups the single-lot variant can therefore take entries the two-lot variant is still holding through (FR-011, one position at a time). On the 42-day synthetic golden market this affects 4 days, where `G9HIC` takes 3 trades to `G9HICD`'s 2, and once 6 to 4. The daily loss cap (FR-G20) can compound the divergence, since the two variants may classify the same setup differently and so reach two losses at different points.
- The comparison is therefore **not** a pure position-management A/B, and should not be read as one. It is closer than `G9HSL` vs `G9H` — those differ in entry *validity* — but "same entries, different management" holds only while both variants are flat at the same moment.
- **TP2 is outside the H1 range by construction** (H1 high + 90 for a long). No H1-range check limits it, and the 70-point minimum range does not interact with it.
- **The daily loss cap counts positions, not lots**: a two-lot position closing net-negative is one loss (FR-G20 counts a closed trade's net points, and a position is one aggregated trade per FR-G07).

## Requirements

- **FR-G24**: System MUST provide a hardcoded backtest **"GER40 Bougie de 9h (bougie impulsive, 2 lots)"** (code `G9HICD`, `Strategy.G9HICD`), running `GER40.I` on the CFD session with the GER40 default thresholds, and inheriting `G9HIC`'s impulse stop, minimum H1 range, entry cut-off and daily loss cap unchanged. Adding it MUST NOT change any existing definition, `G9HIC` included.
- **FR-G25**: Every valid entry MUST open **two lots** at the confirmed entry price, managed together while both are open and sharing the same stop, exactly as FR-G02 specifies for `G9H`.
- **FR-G26**: The first lot's target (TP1) MUST be the **standard take-profit level** — the H1 far level minus the take-profit offset (FR-008), the same level the single-lot `G9HIC` exits at. The runner's target (TP2) MUST be **`runner_extension_points` beyond TP1 in the favorable direction**, defaulting to **100**: `TP1 + 100` for a long, `TP1 − 100` for a short.
- **FR-G27**: When TP1 fills, the runner's stop MUST move to the entry price (break-even) immediately, as FR-G04 specifies for `G9H`, independently of the +50-point trigger. From that point the runner has an ordinary intrabar stop, which takes precedence over the impulse rule (FR-G16).
- **FR-G28**: While both lots are open the impulse stop (FR-G14) applies to the position as a whole: an impulsive candle closes **both** lots at its close, and the net points is twice a single lot's loss (FR-G07's aggregation).
- **FR-G29**: At the session end every lot still open MUST close at the last 5-minute candle's close, whether that is both lots or the runner alone (FR-G12/FR-G07).
- **FR-G30**: A position MUST be surfaced as **one aggregated trade** with the net points of both lots and classified by the sign of that net, exactly as FR-G07/FR-G08 specify for `G9H`. No new response shape is introduced.
- **FR-G31**: The two-lot structure and the 100-point runner extension MUST be **fixed properties** of the definition, not per-run tunable parameters (extending FR-G18/FR-G22).

### Key Entities

- **Backtest Definition** (extended): gains `runner_extension_points`. When set alongside `double_take_profit`, it selects the "TP1 at the standard take-profit, TP2 beyond it" lot model instead of the fraction-of-the-range model `first_target_fraction` selects. Exactly one of the two MUST be set on a double-take-profit definition.

## Success Criteria

- **SC-G14**: On hand-built days covering every FR-G26/FR-G27 boundary — TP1 then TP2, TP1 then break-even, an impulse before TP1 closing both lots, an impulse after TP1 losing to the break-even stop, the +50 trigger before TP1, end of day with both lots and with the runner alone, and the short mirror — reported exits and net points match manual calculation exactly.
- **SC-G15**: Given the same state, `G9HICD` accepts and rejects exactly the same breakouts as `G9HIC` — the two-lot entry filter (FR-G02) adds no constraint here, because TP1 is the ordinary take-profit the single-lot variant already checks. Over a whole day the trade *sets* may still differ, because the runner occupies the one-position-at-a-time slot for longer; that divergence is expected and must be visible in the results rather than assumed away.
- **SC-G16**: `B9H`, `B9HTC`, `G9H`, `G9HSL`, `B9HWS` and `G9HIC` produce byte-for-byte identical golden results; only the new `G9HICD` rows are added.

## Assumptions

- 100 points is a judgement call to be tested, like the 70-point impulse threshold — fixed on the definition so a run's results always correspond to the rules as shipped.
- Because the runner holds the position slot longer, `G9HICD` will generally take **fewer** trades per day than `G9HIC`. When reading the pair, compare points per day rather than per trade — the trade counts are not like-for-like.
- Sending the runner beyond the H1 range is the point of the variant: the range-bound variants cap their upside at the far end of the 9h candle, and the impulse stop is what makes holding for more than that plausible. Whether it pays is what the run answers.
- Because TP1 fills arm break-even, the runner's realistic outcomes are TP2, break-even, or end of day — an impulsive candle can only take the runner out in the window between TP1 filling and break-even being consulted on the next candle, which does not exist. The impulse stop therefore protects the **pre-TP1** position only, and that is intended (Clarifications, 2026-07-27 (3)).

---

# Addendum 4: trail the runner's stop to TP1 (`G9HICD`)

**Added**: 2026-07-27
**Input**: User description: "After 50 pts, raise the BE to TP1."

## Context

One rule added to `G9HICD` **in place**: once the runner has gained 50 points beyond TP1, its stop moves up from break-even (the entry price) to **TP1**. A one-step trail that guarantees the runner at least matches what the first lot banked, at the cost of giving up the break-even-or-better outcomes where price stalls between entry and TP1 after having poked past TP1 + 50.

It only exists after TP1 has filled. Before that the position has no TP1 to trail to, and its stop is whatever FR-G15/FR-G27 make it.

## Clarifications

### Session 2026-07-27 (4)

- Q: 50 points measured from where? → A: **Beyond TP1**, in the position's favorable direction: `TP1 + 50` for a long, `TP1 − 50` for a short. On an 8000–8100 range that is 8140 — halfway from TP1 (8090) to TP2 (8190). It is the only anchor where TP1 sits *below* the price when the rule fires; measured from the entry (8065) TP1 would still be above the market and the stop would fill instantly.
- Q: Does this replace the break-even stop or come after it? → A: **After it.** TP1 filling still moves the runner to break-even (FR-G27); the trail then raises that stop a second time when the trigger is reached.
- Q: What exit reason does a trailed stop report? → A: A new **`trailing_stop`**. Reporting `break_even` would be wrong — the trade closes with the runner in profit, not flat — and `take_profit` would be wrong too, since no target was reached.
- Q: Is the 50-point trail trigger tunable per run? → A: **No** — a fixed property of the definition, like the 100-point runner extension.

## User Scenarios & Testing

### User Story 7 - Lock the runner in at TP1 (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a runner whose TP1 has filled and whose stop is at entry, **When** a candle reaches **TP1 + 50**, **Then** the runner's stop moves to **TP1**, from the next candle onward.
2. **Given** that trailed runner, **When** price falls back to TP1, **Then** the runner closes at TP1 with exit reason **`trailing_stop`**, and the position's net points is `2 × (TP1 − entry)` — the banked first lot plus the runner matching it.
3. **Given** that trailed runner, **When** price instead reaches TP2, **Then** it closes at TP2 as usual; the trail never prevents the target.
4. **Given** a runner whose TP1 has filled but which has **not** reached TP1 + 50, **When** price falls back to entry, **Then** it closes at break-even as before (FR-G27) — the trail has not armed.
5. **Given** a position where TP1 has **not** filled, **When** price moves 50 points past anything, **Then** no trail arms: there is nothing to trail to.
6. **Given** a candle that both reaches TP1 + 50 and falls back below TP1, **When** it is evaluated, **Then** the trail arms but does **not** close the position on that candle — like break-even arming, it takes effect from the next candle (FR-008a).
7. **Given** the short mirror, **When** the runner reaches TP1 − 50, **Then** its stop moves down to TP1 and the same rules mirror.

### Edge Cases

- **The trail supersedes break-even, never the reverse**: once armed it is the runner's stop, and it can only ever be better than entry (TP1 is in profit by construction, since a valid entry sits strictly on the favorable side of TP1 per FR-G02).
- **Arming and closing on the same candle are separate events**, so a spike to TP1 + 50 that closes back below TP1 arms the trail and leaves the position open until a *later* candle trades back to TP1.
- **Nothing changes before TP1**, so the impulse stop's role (FR-G28) is untouched.

## Requirements

- **FR-G32**: On `G9HICD`, once the first lot has filled, the runner's stop MUST move to **TP1** the first time a candle reaches `TP1 + trail_to_first_target_points` in the favorable direction (default **50**), taking effect from the next candle, at most once.
- **FR-G33**: A stop that fires at the trailed level MUST report the exit reason **`trailing_stop`**, distinct from `break_even` (flat) and `stop_loss`. The FR-010 gap-fill applies as to any price-level stop.
- **FR-G34**: The trail MUST NOT arm before the first lot has filled, and MUST NOT apply to definitions without `trail_to_first_target_points`. `G9HIC` and every other definition are unchanged.
- **FR-G35**: The trail trigger MUST be a fixed property of the definition, not a per-run tunable parameter.

## Success Criteria

- **SC-G17**: On hand-built days, a runner that reaches TP1 + 50 and falls back closes at TP1 as `trailing_stop` with net `2 × (TP1 − entry)`; one that does not reach it still closes at break-even with the banked TP1 alone.
- **SC-G18**: Every definition other than `G9HICD` produces byte-for-byte identical golden results.
