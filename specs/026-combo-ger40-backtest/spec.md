# Feature Specification: "GER40 Combo" Backtest (5m / 15m / H1)

**Feature Branch**: `claude/combo-indicator-ger40-backtest-klzp2d`
**Created**: 2026-07-30
**Status**: Draft
**Input**: User description: "I want us to create a new backtest based on the combo indicator and the ger40.i index. Let's focus on 5m 15m and h1 for now. Create a new spec 026"

## Context

Every backtest in the Backtest menu today (spec 021 "CAC40 Bougie de 9h" and the spec 025 GER40 variants) is a *session* strategy: a 9:00–10:00 H1 reference range fixes the levels, 5-minute candles are scanned after 10:00, and the day ends flat. This backtest is the first one built on an **indicator signal** instead of a reference range, and the first that **carries positions across days**.

It measures what the existing `combo` indicator — already used live by the workflow engine (`workflows.yml`: "combo h1 dax", "combo h4 dax") — would have produced on **GER40.I**, evaluated independently on three timeframes: **5 minutes, 15 minutes and 1 hour**. Each timeframe is a separate hardcoded backtest so the three can be run and compared side by side, exactly as the GER40 "bougie de 9h" variants are compared today.

What this backtest inherits unchanged from the existing ones: the Backtest menu selection, the single-day and date-range run modes, the aggregate summary (days, trades, wins/losses/BE, average win, average loss, final result), the per-day detail view, the CSV exports, the gap-fill convention on price-level exits, the one-position-at-a-time rule, and the two-lot "one aggregated trade" reporting convention introduced in spec 025 (FR-G07).

What is **new** and is the substance of this spec:

1. **Entry comes from the `combo` indicator**, not from a breakout of a reference range. There is no H1 reference candle, no max-entry-distance, no 10:00 start.
2. **The stop is derived from the signal candle** (50 points beyond its adverse extreme), not from a session level or the entry price.
3. **Both take-profits are indicator levels that move candle by candle**: TP1 at the MM20 (the Bollinger middle band), TP2 at the opposite Bollinger band. Every existing backtest uses a target fixed at entry time.
4. **Positions carry overnight**, held until an exit rule fires, however many days that takes. Every existing backtest is flat at the session close.

## Clarifications

### Session 2026-07-30

- Q: How are the three timeframes exposed? → A: **Three separate hardcoded backtests** (5m, 15m, H1), one per timeframe, sharing one rule set. Not a run-time timeframe parameter and not a multi-timeframe confluence strategy.
- Q: What triggers the entry, and which signal strengths are traded? → A: The `combo` signal's own price convention: when the signal is already triggered, the entry is the signal candle's close; otherwise the signal price is a **pending stop level** at the signal candle's extreme, filled when a later candle trades through it. **MEDIUM and STRONG signals are traded; WEAK signals (score 0) are ignored.**
- Q: Where is the stop-loss? → A: **50 points beyond the signal candle's adverse extreme** — 50 below the signal candle's low for a long, 50 above its high for a short. Measured from the *signal* candle, not the entry price and not the entry candle.
- Q: What closes a winning trade? → A: **Two take-profits.** TP1 when price reaches the **MM20** (the 20-period moving average, i.e. the Bollinger middle band); TP2 when price reaches the **opposite Bollinger band** (the upper band for a long, the lower band for a short). This makes the position a two-lot position, like the GER40 double-TP variants.
- Q: Is the position protected once it moves in favor? → A: **Break-even on TP1** — when the first lot fills at the MM20, the runner's stop moves to the entry price. There is no separate points-based break-even trigger.
- Q: How long can a position run and how many at a time? → A: **One position at a time, no time cap.** The position is held until an exit rule fires, carrying over nights, weekends and however many days that takes; signals arriving while a position is open are ignored.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a "GER40 Combo" backtest over a date range (Priority: P1)

A trader opens the Backtest menu, picks "GER40 Combo 15m" (or the 5m / H1 sibling), enters a start and end date, and sees every position the combo indicator would have opened over that range: direction, entry time and price, exit time, price and reason, and the net points of each position — plus the usual aggregate summary.

**Why this priority**: The date range *is* the deliverable. Unlike the session backtests, a single day of an indicator strategy tells a trader almost nothing — a 5m combo may fire twice a week, and a position opened Tuesday may still be open Friday. Without the range run the feature has no value.

Running that same range on each of the three timeframes and comparing the summaries — which is the reason three were asked for rather than one — needs nothing beyond this story: the three are separate registered backtests evaluated on their own candle series, so the comparison falls out of the three definitions existing. It is measured by SC-C03 and SC-C04 rather than carried as a story of its own.

**Independent Test**: Run the 15m backtest over a known multi-week GER40.I range and verify each reported position's entry, exits and net points against a manual evaluation of the combo indicator and the Bollinger/MM20 levels on the same candles.

**Acceptance Scenarios**:

1. **Given** a GER40.I 15-minute candle on which `combo` returns a **buy** signal of MEDIUM or STRONG strength that is **already triggered** (the signal candle closed above the previous candle's high), **When** the backtest runs, **Then** a **long position of two lots** is opened at that candle's **close price** and close time.
2. **Given** a GER40.I candle on which `combo` returns a MEDIUM or STRONG **buy** signal that is **not yet triggered**, **When** a **later** candle trades at or above the signal candle's **high**, **Then** a long position of two lots is opened at that level (or the candle's open when it gapped through it — the conservative gap-fill of spec 021 FR-010).
3. **Given** a MEDIUM or STRONG signal that is not yet triggered, **When** the very next candle does **not** trade through the signal candle's extreme, **Then** **no position is opened from that signal** — the pending level expires and only a fresh signal on a later candle can open a trade.
4. **Given** a candle on which `combo` returns a **WEAK** signal (signal score 0), **When** the backtest runs, **Then** **no position is opened** and the signal is not reported as a trade.
5. **Given** an open two-lot long, **When** price reaches the **MM20** of the current candle, **Then** the **first lot** is closed there (TP1, a take-profit) and the **runner's stop moves to the entry price** (break-even) from the next candle onward.
6. **Given** the runner from Scenario 5, **When** price then reaches the **upper Bollinger band** of the current candle, **Then** the runner is closed there (TP2) and the position's net points is `(TP1 − entry) + (TP2 − entry)`.
7. **Given** the runner from Scenario 5, **When** price instead falls back to the entry price, **Then** the runner closes at break-even and the position's net points is the banked TP1 (a net-positive result).
8. **Given** an open two-lot long **before** TP1 has filled, **When** price falls to **the signal candle's low − 50 points**, **Then** **both lots** are closed at that stop level and the position's net points is twice a single lot's loss.
9. **Given** the mirror-image setup — a MEDIUM or STRONG **sell** signal — **When** it is entered, **Then** a two-lot **short** is opened with the stop at **the signal candle's high + 50**, TP1 at the MM20 and TP2 at the **lower** Bollinger band, and every rule above mirrored.
10. **Given** an open position, **When** the trading day ends, **Then** the position is **NOT** closed: it carries into the next trading day (and across weekends) until an exit rule fires.
11. **Given** an open position, **When** `combo` produces a further signal on a later candle — in either direction — **Then** that signal is **ignored**; only one position may be open at a time and a position is never reversed or added to.
12. **Given** a run range whose end date arrives with a position still open, **When** the run finishes, **Then** the still-open position is closed at the last available candle's close and reported with an **end-of-run** exit reason, so the range's points total is complete.

---

### User Story 2 - Only the parameters that do something are offered (Priority: P2)

A trader selecting a "GER40 Combo" backtest is offered exactly one tunable threshold — the stop distance — instead of the four the "bougie de 9h" backtests expose.

**Why this priority**: Three of the four existing thresholds (take-profit offset, break-even trigger, max entry distance) have **no meaning** for this strategy: its targets come from the Bollinger bands and its break-even from TP1, and there is no reference level to be too far from. Leaving them editable invites a trader to tune a number that does nothing, watch the result not move, and conclude the strategy is insensitive to it — a wrong conclusion produced by the UI, not by the market. It is not P1 because the strategy is fully measurable without it.

**Independent Test**: Select each combo backtest and confirm only the stop-distance input is offered, then select an existing "bougie de 9h" backtest and confirm all four are still offered.

**Acceptance Scenarios**:

1. **Given** the Backtest menu, **When** a trader selects any "GER40 Combo" backtest, **Then** only the stop-distance parameter is offered for editing, defaulted to 50 points.
2. **Given** the Backtest menu, **When** a trader selects any existing "bougie de 9h" backtest, **Then** all four thresholds are still offered, unchanged by this feature.

---

### User Story 3 - Inspect why a position was opened (Priority: P3)

A trader opens the detail of a run and, for a given position, sees the candle the signal fired on, the signal's strength, and the level each exit happened at, so the result can be audited against the chart.

**Why this priority**: Builds trust in an entry rule that — unlike a range breakout — is not obvious from looking at a chart. The strategy is measurable without it.

**Independent Test**: Open the detail for a day containing a position and confirm the signal candle, the strength, and the entry/exit levels are consistent with the summary and the underlying candles.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the trader opens a day that contains a position, **Then** the candles of the definition's timeframe are shown with the position's entry and exits marked.
2. **Given** a completed run, **When** the trader exports CSV, **Then** the export follows the existing format (one row per day: date, status, trade count, points), where a two-lot position counts as one trade contributing its net points.

---

### Edge Cases

- **Not enough history to evaluate the indicator**: `combo` needs a 50-period moving average measured 10 candles back, 20-period Bollinger bands and a MACD — at least **60 candles of the definition's timeframe** before the first candle it can be evaluated on. Candles inside that warm-up window produce no signal and are not an error (see FR-C13).
- **Signal fires on the same candle as an exit**: while a position is open, no signal is acted on at all (FR-C09), so this cannot open a position. A signal on the candle the position *closes* on is also ignored; the search resumes on the following candle.
- **TP1 (MM20) is already at or past the entry price**: for a long, the combo entry sits near the lower Bollinger band and the MM20 is normally above it, but a fast move can put the entry at or above the MM20. Such an entry is **rejected and no position is opened** — it would fire TP1 immediately, bank a loss as a "take-profit" and arm break-even before the stop could work. This mirrors the spec 025 FR-G02 guard.
- **TP1 and TP2 crossed by the same candle**: the first lot fills at TP1 and the runner at TP2 on that candle; net points is the sum of both.
- **Stop and TP1 reached by the same candle, before any scale-out**: the **stop wins** for both lots — the conservative same-candle rule of spec 021 FR-009.
- **The moving targets move against the position**: TP1 and TP2 are re-read on every candle, so a target can retreat (a rising MM20 in a falling market). This is intentional: the exit is "price reached the MM20 / the band", evaluated candle by candle, never a level frozen at entry.
- **The MM20 crosses to the wrong side of the entry while the position is open**: for a long, if the MM20 falls below the entry price after entry, TP1 is reached the moment price touches it and the first lot closes for a **loss**, banking it and arming break-even on the runner. That is the rule as specified, not a special case.
- **Gap through a level over a weekend or overnight**: the position carries across the gap and the exit fills at the candle's open, per the existing gap-fill convention — a stop can therefore fill materially worse than its level.
- **Both a stop and the start of a new signal in the same candle**: exits are always resolved before entries; the position closes first and the candle's signal is still ignored (it arrived while a position was open).
- **A position open at the end of the requested range**: it is force-closed at the last candle's close and reported as end-of-run (FR-C12), so a run's total is never missing an open trade. Re-running with a later end date can therefore change that position's result — expected, and worth surfacing in the exit reason.
- **A day with no candles** (holiday, missing data) inside the range: it is skipped, does not break an open position's continuity, and is excluded from the day count exactly as in the existing backtests.

## Requirements *(mandatory)*

### Functional Requirements

Requirements are numbered FR-C##. Where a rule is unchanged from the existing backtests, the spec 021 / spec 025 requirement it reuses is referenced rather than restated.

- **FR-C01**: System MUST provide **three new hardcoded backtests** — "GER40 Combo 5m", "GER40 Combo 15m" and "GER40 Combo H1" — selectable from the Backtest menu alongside the existing ones (extends spec 021 FR-001/FR-002). All three run on the **GER40.I** instrument and share one rule set, differing only in the candle timeframe (5 minutes / 15 minutes / 1 hour) they evaluate. Adding them does not make the menu a generic engine.
- **FR-C02**: For each candle of its timeframe, in chronological order, the system MUST evaluate the existing **`combo` indicator** on the series ending at that candle. A candle produces a **candidate signal** when the indicator returns a signal whose strength is **MEDIUM or STRONG**. A **WEAK** signal (signal score 0) MUST be ignored and MUST NOT open a position.
- **FR-C03**: A candidate signal MUST be converted into an entry as follows:
  - **Already triggered** (the signal candle closed beyond the previous candle's extreme in the signal's direction): the entry is at the **signal candle's close price**, at that candle's close time.
  - **Not yet triggered**: the signal's price — the signal candle's **high** for a buy, its **low** for a sell — becomes a **pending stop level**. The entry occurs on the **next candle** if that candle trades at or beyond the level, filled at the level, or at the candle's **open** when it gapped through it (spec 021 FR-010 gap-fill).
- **FR-C04**: A pending stop level MUST be valid for **the next candle only**. If that candle does not trade through it, the pending entry is discarded; a later candle can only open a position via its own fresh signal (which, if the setup persists, carries its own updated level).
- **FR-C05**: Every entry MUST open a position of **two lots** at the same price and time, managed together while both are open, and reported as **one aggregated trade** whose points is the sum of both lots (spec 025 FR-G07).
- **FR-C06**: The position's stop-loss MUST be placed **50 points beyond the signal candle's adverse extreme** — the **signal candle's low − 50** for a long, its **high + 50** for a short. The signal candle is the candle the indicator fired on, which for a pending entry is *not* the candle the position opened on. The stop is **shared by both lots**: a stop hit before any take-profit closes both lots at that level.
- **FR-C07**: The position MUST have two moving take-profit targets, both re-read from the **current candle** of the definition's timeframe on every candle the position is open:
  - **TP1 (first lot)** — the **MM20**: the 20-period moving average of the closes, i.e. the middle Bollinger band. When price reaches it, the **first lot only** is closed there (gap-fill per spec 021 FR-010).
  - **TP2 (runner)** — the **opposite Bollinger band**: the **upper** band for a long, the **lower** band for a short, at the same deviation the `combo` indicator uses for its inner band. When price reaches it, the runner is closed there.
- **FR-C08**: When **TP1 fills**, the runner's stop MUST move to the **entry price** (break-even) from the next candle onward. This is the **only** break-even mechanism: there is **no** points-based break-even trigger in this backtest (unlike spec 021 FR-008a and spec 025 FR-G06).
- **FR-C09**: **At most one position may be open at a time**, across both directions. While a position is open, every signal on every candle MUST be ignored — the strategy never reverses, never adds to a position, and never runs a long and a short concurrently. Signal evaluation resumes on the candle **after** the one the position closed on.
- **FR-C10**: An entry MUST be **rejected** when the current **TP1 (MM20) is not strictly on the favorable side of the entry price** — at or below the entry for a long, at or above it for a short. No position is opened and the strategy continues searching (see the "TP1 already at or past the entry" edge case).
- **FR-C11**: A position MUST be **held across day boundaries, weekends and non-trading days** until an exit rule fires. There is **no end-of-day close** (overriding spec 021 FR-011) and **no maximum holding duration**.
- **FR-C12**: When the requested date range ends with a position still open, the system MUST close it at the **last available candle's close** and report it with an **end-of-run** exit reason, distinguishable from a take-profit, stop-loss or break-even exit.
- **FR-C13**: Before evaluating the first candle of the requested range, the system MUST have at least **60 candles of the definition's timeframe preceding it**, so the indicator's moving average, Bollinger bands and MACD are all defined. Candles without sufficient history MUST produce no signal, silently — not an error and not a trade.
- **FR-C14**: Exit resolution within a single candle MUST follow the existing conservative ordering (spec 021 FR-009): the **stop is resolved before the take-profits**; a candle that reaches both the stop and TP1 while both lots are open closes the **whole position at the stop**.
- **FR-C15**: The run MUST report results using the **existing** day/summary/CSV shapes (spec 021 FR-013/FR-015/FR-017/FR-018): a summary of days, trades, winning/losing/BE positions, average win, average loss and final result, a per-day breakdown, and the CSV exports. A two-lot position counts as **one trade** and is classified by the **sign of its net points** (spec 025 FR-G08). A position is attributed to the day it **entered**, whatever day it exits on.
- **FR-C16**: The **stop distance (50 points)** MUST be tunable per run under the existing parameter-override mechanism (spec 021 FR-025–FR-027: strictly greater than 0, per-run only, never persisted). The **two-lot structure**, the **MM20 first target**, the **opposite-band second target**, the **strength filter** and the **one-candle pending-level validity** are **fixed properties** of these backtests, not tunable parameters. The three thresholds the existing backtests expose that have no meaning here — take-profit offset, break-even trigger, max entry distance — MUST NOT affect these definitions.

### Key Entities

- **Backtest Definition** (extends spec 021 / 025): three new instances on `GER40.I`, each carrying its **timeframe** (5m / 15m / H1) and the combo rule set — a new kind of definition property, since every existing definition is implicitly a 5-minute-scan / H1-reference strategy.
- **Combo Signal** (existing): direction, price, already-triggered flag, strength and the per-criterion detail map produced by the existing indicator. Consumed as-is; this feature does **not** change the indicator.
- **Position (two lots)**: an entry opening two lots at one price and time, sharing one stop derived from the signal candle; the first lot exits at the moving MM20, the runner at the moving opposite band with its stop at break-even once TP1 fills. Surfaced as one aggregated Trade.
- **Backtest Parameters** (existing shape): only the stop distance is meaningful here, defaulting to 50 points (FR-C16).

## Success Criteria *(mandatory)*

- **SC-C01**: A trader can select any of the three "GER40 Combo" backtests from the Backtest menu, run a multi-week date range, and receive a complete summary and per-day breakdown.
- **SC-C02**: On a hand-verified set of at least 8 historical GER40.I signals across the three timeframes, covering every outcome type (WEAK signal skipped, pending level expired unfilled, entry rejected because TP1 was already past, stop-out before TP1, TP1 then TP2, TP1 then break-even, a position carried across at least one overnight, and a position open at the end of the range), the reported entry, exits, exit reason and net points match a manual calculation exactly.
- **SC-C03**: Running the same date range on all three timeframes produces three independent result sets, and running any of them leaves the existing CAC40 and GER40 "bougie de 9h" backtests bit-for-bit unchanged.
- **SC-C04**: A trader can tell, from the summary alone, which of the three timeframes was profitable over the range and at what trade count — the comparison this feature exists to enable.
- **SC-C05**: A trader can open a day's detail and reconcile a position's entry and exits against the displayed candles.

## Assumptions

- **"Points" is the raw GER40.I index price difference**; no position sizing, spread, funding or currency P&L is in scope. "Two lots" is a unit count for points accounting (net = sum of both lots), consistent with spec 025.
- **The 50-point stop is measured from the signal candle**, not the entry candle and not the entry price. On a pending entry these differ; the signal candle is the reference in both cases.
- **The MM20 is the middle Bollinger band** — the 20-period simple moving average of the closes — and **TP2 is the opposite band at the deviation the `combo` indicator already treats as its inner band**. Both are read on the definition's own timeframe. Flagged for validation: if the intent was the outer (wider) band for TP2, only FR-C07 changes.
- **A pending (untriggered) signal level lives for exactly one candle** (FR-C04). This follows from the indicator being re-evaluated on every candle: a setup that still holds emits a fresh signal with an updated level, so no separate expiry window is needed. Flagged for validation.
- **Candles are built over the GER40 CFD session (9:00–22:00 Paris, DST-aware)**, matching the impulsive GER40 variants, so afternoon and US-session signals are visible on all three timeframes. The 15-minute timeframe is not used by any existing backtest and may need to be assembled from smaller candles the same way the existing ones rebuild the current hour/day.
- **Positions carrying overnight are held at the last traded price across the gap**; no overnight financing, margin or gap-risk modelling is applied.
- **The backtest operates only on already-closed historical candles**, computed on demand and returned synchronously; nothing is persisted beyond the existing raw-candle cache.
- **A position is attributed to its entry day** in the per-day breakdown, so a day's points can include a trade that closed days later, and a day can show zero trades while a position is open through it.
- **Carrying positions across days is a structural change to the run engine**: the existing backtests evaluate each day independently. This spec requires the range run to see one continuous candle stream. The three new definitions must not change how the existing day-independent ones behave.
- **The existing backtests, the `combo` indicator itself and the live workflow engine are unchanged by this feature.** This is a measurement of the indicator, not a modification of it.

---
