# Feature Specification: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

**Feature Branch**: `514-backtest-menu-hardcoded`
**Created**: 2026-07-14
**Status**: Draft
**Input**: User description: "I want a new menu «back test» which will run hardcoded back test. I don't want to create a back test engine. All of them will be hardcoded. First one is the following: on the FRA40.I index, take the h1 candle 9am-10am with high and low has limit. then we work with 5minutes candle. if after 10am, the price is going bellow low h1, then close above the low, then we have a breakout 5min, we take a position. we sell the position when we lost 50points, or at the end of the day or if the price is going to high h1 less 10 points"

## Clarifications

### Session 2026-07-14

- Q: In what timezone are the 9:00–10:00 H1 reference window and the 10:00 evaluation start point defined? → A: Paris exchange local time (Europe/Paris), DST-aware — 9:00 always means 9:00 at the exchange, year-round.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the "CAC40 Bougie de 9h" backtest for a single day (Priority: P1)

A trader wants to select the "Backtest" menu, pick the hardcoded "CAC40 Bougie de 9h" backtest, choose a past trading day, and see whether the strategy would have entered one or more trades that day, and for each, at what price it entered, exited, and with what result in points.

**Why this priority**: This is the core capability of the feature. Without a single-day run producing a correct trade (or correctly reporting no trade), the feature delivers no value.

**Independent Test**: Run the backtest against a known historical day for FRA40.I where the 9:00–10:00 H1 candle and subsequent 5-minute candles are known in advance. Verify the reported outcome (no trade / trade with entry, exit, and points result) matches manual calculation using the rules below.

**Acceptance Scenarios**:

1. **Given** a trading day where, after 10:00, FRA40.I trades below the 9:00–10:00 H1 candle's low and a later 5-minute candle closes back above that H1 low, **When** the backtest runs for that day, **Then** the system reports a long trade entered at the close price of the 5-minute candle that closed back above the H1 low.
2. **Given** an open trade from Scenario 1, **When** a subsequent 5-minute candle's price action reaches a loss of 50 points from the entry price before any other exit condition is met, **Then** the system reports the trade closed at that stop-loss level (or at the candle's open price if the candle gapped past the stop-loss level).
3. **Given** an open trade from Scenario 1, **When** price rises to reach the H1 candle's high minus 10 points before the stop-loss or end of day is reached, **Then** the system reports the trade closed at that take-profit level (or at the candle's open price if the candle gapped past it).
4. **Given** an open trade from Scenario 1 that hits neither the stop-loss nor the take-profit level, **When** the trading day ends, **Then** the system reports the trade closed at the closing price of the last 5-minute candle of the day, labeled as an end-of-day exit.
5. **Given** a trading day where price never trades below the 9:00–10:00 H1 low after 10:00, or trades below it but no subsequent 5-minute candle closes back above it, **When** the backtest runs for that day, **Then** the system reports no trade for that day.
6. **Given** a trading day where no 9:00–10:00 H1 candle data exists for FRA40.I (e.g., market holiday, missing data), **When** the backtest runs for that day, **Then** the system reports that day as having no data, without failing the run.
7. **Given** a first trade from Scenario 1 that has closed (stop-loss, break-even, take-profit, or a later re-entry closing before end of day), **When** price subsequently trades below the H1 low again and a later 5-minute candle closes back above it, **Then** the system reports a second trade entered on the same day, evaluated against the same H1 high/low reference levels and the same exit rules, independently of the first trade's outcome.
8. **Given** an open trade from Scenario 1, **When** a subsequent 5-minute candle's high reaches 20 points or more above the entry price, **Then** the system moves that trade's stop-loss up to the entry price (break-even) for evaluation of all following candles, and this adjustment happens at most once for that trade.
9. **Given** an open trade whose stop-loss has already been moved to break-even (Scenario 8), **When** a later 5-minute candle's low reaches the entry price or below, before the take-profit or end of day is reached, **Then** the system reports the trade closed at break-even (0 points), labeled as a "break-even" exit — distinct from a stop-loss, take-profit, or end-of-day exit.

---

### User Story 2 - Run the backtest over a UI-provided time range and see aggregate results (Priority: P2)

A trader wants to enter a start date and end date in the UI, run the "CAC40 Bougie de 9h" backtest across every trading day in that range, and see one summary result: number of days, number of trades, number of winning positions, number of losing positions, number of break-even positions, average win, average loss, and the final (net) result — to judge whether the strategy is worth trading live.

**Why this priority**: A single day's result has little statistical value; traders need to see the strategy's behavior across a meaningful sample of days before trusting it. This builds directly on User Story 1's per-day logic.

**Independent Test**: Provide a known multi-week start/end date range with a mix of trade and no-trade days, run the backtest, and verify the eight summary figures (number of days, number of trades, number of winning positions, number of losing positions, number of break-even positions, average win, average loss, final result) match a manual computation from the individual per-day results.

**Acceptance Scenarios**:

1. **Given** a start date and end date entered in the UI, **When** the backtest runs, **Then** the system displays a single summary containing: number of days, number of trades, number of winning positions, number of losing positions, number of break-even (BE) positions, average win (in points), average loss (in points), and the final result (net points) for the range.
2. **Given** a date range that includes non-trading days (weekends, holidays) or days with missing H1 data, **When** the backtest runs, **Then** those days are excluded from the "number of days" count and from every other summary figure, and the run completes without error.
3. **Given** a date range where no trade signal ever occurs, **When** the backtest runs, **Then** the system displays number of trades as 0, number of winning, losing, and break-even positions as 0, average win and average loss as not applicable, and a final result of 0 points.
4. **Given** a date range containing at least one trade that closed via the break-even mechanism, **When** the backtest runs, **Then** that trade counts toward "number of BE" and toward "number of trades," but not toward "number of winning positions" or "number of losing positions," and its 0-point result is excluded from the average win and average loss calculations.

---

### User Story 3 - Inspect the reference levels and candles behind a day's result (Priority: P3)

A trader wants to see, for a given backtested day, the H1 opening-range high/low, the 5-minute candles used, and where the entry and exit fell, so they can visually verify the backtest matched the actual chart.

**Why this priority**: Builds trust in the hardcoded logic by letting a trader audit individual results, but the strategy is usable (Stories 1–2) without this inspection view.

**Independent Test**: Open the detail view for a day that produced a trade and confirm the displayed H1 high/low, the 5-minute candle sequence, and the marked entry/exit points are consistent with the values reported in the summary for that day.

**Acceptance Scenarios**:

1. **Given** a backtested day with a trade, **When** the trader opens that day's detail view, **Then** the system shows the 9:00–10:00 H1 high and low, the sequence of 5-minute candles from 10:00 onward, and the entry and exit points marked against that data.

---

### Edge Cases

- **No H1 reference candle**: If the 9:00–10:00 H1 candle cannot be retrieved for a day (holiday, missing data, market closed), that day is skipped and reported as "no data," not as "no trade."
- **Breakdown without confirmed reversal**: Price trades below the H1 low after 10:00 but no later 5-minute candle closes back above it before the session ends — no trade is taken for that day.
- **Repeat breakdown after a closed trade**: Once a trade has closed for the day (stop-loss, take-profit, or end of day), the strategy re-arms and MUST take a new trade if price breaks below the H1 low again and a later 5-minute candle closes back above it before the session ends — there is no cap on the number of trades in a day, other than requiring the previous trade to be closed first (never more than one open position at a time).
- **Stop-loss (or break-even) and take-profit breached in the same 5-minute candle**: Whichever stop level is currently active (the original stop-loss, or break-even once armed) is assumed to trigger first (conservative outcome) when a single candle's range would have touched both it and the take-profit level.
- **Break-even arms in the same candle it would otherwise have exited on take-profit or the original stop-loss**: The exit (stop-loss or take-profit) is resolved first, using the stop-loss level in effect at the start of that candle; the break-even arming (based on the candle's high reaching entry + 20 points) only takes effect starting with the next candle, and is moot if the trade has already exited.
- **Break-even arms and is then breached in the same candle**: Since the stop only moves to break-even starting the next candle (see above), a single candle's high reaching entry + 20 points cannot, by itself, also trigger a break-even exit in that same candle — at least one further candle is required to break back down through the entry price.
- **Gap through the exit level**: If the 5-minute candle that breaches the stop-loss, break-even, or take-profit level opens beyond that level (a gap), the exit is recorded at that candle's open price rather than the exact threshold, to reflect realistic fill slippage.
- **End-of-day with no clear last candle**: The end-of-day exit uses the close of the final 5-minute candle of FRA40.I's regular trading session for that day.
- **Break-even state does not carry across trades**: Each trade (including a same-day re-entry per FR-011) starts with its own fresh stop-loss at entry-minus-50; the break-even arming from a previous, already-closed trade has no effect on a later trade that day.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "Backtest" menu, reachable from primary navigation, listing the available hardcoded backtests by name.
- **FR-002**: System MUST provide one hardcoded backtest, "CAC40 Bougie de 9h," selectable from the Backtest menu, implementing the rules in FR-003 through FR-011 (including FR-008a). This backtest's rules are fixed in code; the menu does not offer a generic engine for defining new strategies.
- **FR-003**: For a given trading day, system MUST derive the reference range from the FRA40.I 1-hour (H1) candle covering 9:00–10:00 Paris exchange local time (Europe/Paris, DST-aware), using its high as the upper reference level and its low as the lower reference level. These levels stay fixed for the rest of the day, across all trades taken that day.
- **FR-004**: If the 9:00–10:00 (Paris local time) H1 candle is not available for a given day, system MUST report that day as having no data and MUST continue processing any other requested days without failing the run.
- **FR-005**: For the period from 10:00 Paris local time to the end of the trading session, system MUST evaluate FRA40.I 5-minute candles in chronological order.
- **FR-006**: System MUST recognize a trade signal ("breakout reversal") each time, after 10:00, price trades below the H1 low and a later 5-minute candle closes at or above the H1 low, provided no trade is currently open. This allows multiple signals — and multiple trades — on the same day, as long as they occur sequentially rather than concurrently.
- **FR-007**: When a trade signal is recognized, system MUST record a long (buy) entry at the closing price of the 5-minute candle that closed at or above the H1 low.
- **FR-008**: System MUST evaluate, for each 5-minute candle after entry in chronological order, whether any of the following exit conditions is met, and MUST close the trade at the first one reached:
  - **Stop-loss**: price has fallen to or below the trade's currently active stop-loss level (starting at 50 points below the entry price; see FR-008a for how this level can move).
  - **Take-profit**: price has risen to reach the H1 high minus 10 points.
  - **End of day**: the trading session for that day ends with neither of the above reached.
- **FR-008a**: While a trade is open and its stop-loss has not yet been moved, system MUST move that trade's stop-loss up to the entry price ("break-even") the moment a 5-minute candle's high reaches the entry price plus 20 points or more. This move happens at most once per trade, only ever moves the stop-loss upward (never back down toward entry-minus-50), and takes effect starting with the next 5-minute candle evaluated (see the "break-even arms in the same candle" edge case for same-candle handling). A trade subsequently closed at this moved level is recorded with exit reason "break-even," not "stop-loss," and a points result of 0.
- **FR-009**: When both the currently active stop-loss level (original or break-even) and the take-profit level would be reached within the same 5-minute candle, system MUST resolve the exit using the stop-loss (or break-even) level.
- **FR-010**: When the 5-minute candle that triggers a stop-loss, break-even, or take-profit exit opens beyond that level (a gap), system MUST record the exit at that candle's open price; otherwise the exit MUST be recorded at the exact stop-loss, break-even, or take-profit price level.
- **FR-011**: System MUST allow multiple sequential trades per day for this backtest: once a trade has closed (stop-loss, break-even, take-profit, or end of day) and there is remaining time before end of day, system MUST resume evaluating 5-minute candles for a new trade signal per FR-006. At most one trade may be open at any given time, and each new trade starts with its own fresh (unmoved) stop-loss.
- **FR-012**: System MUST let a trader provide a start date and end date via the UI and run the backtest across every trading day in that range (a single-day run is the special case where start date equals end date); the system MUST retain a per-day result (no data / no trade / one or more trades, each in chronological order with entry, exit, exit reason — stop-loss, break-even, take-profit, or end of day — and points gained or lost) for each day in the range so it can be drilled into via the detail view (User Story 3).
- **FR-013**: For a range run, system MUST display a single aggregate summary with exactly these figures:
  - **Number of days**: count of trading days in the range that had usable H1 reference data (days reported as "no data" are excluded).
  - **Number of trades**: total count of trades taken across the range (equal to the sum of winning, losing, and break-even positions).
  - **Number of winning positions**: count of trades that closed with a positive points result.
  - **Number of losing positions**: count of trades that closed with a negative points result.
  - **Number of BE**: count of trades that closed via the break-even mechanism (FR-008a), each with a points result of exactly 0.
  - **Average win**: mean points gained across winning positions (not applicable when there are no winning positions).
  - **Average loss**: mean points lost across losing positions, expressed as a positive magnitude (not applicable when there are no losing positions). Break-even positions are excluded from this average.
  - **Final result**: net points gained or lost across every trade in the range (sum of all trades' points results).
- **FR-014**: Trade results MUST be expressed in index points (entry/exit price and points gained or lost), consistent with how the strategy's thresholds (50 points, 10 points) are defined.
- **FR-015**: System MUST let a trader open a detail view for any backtested day that produced at least one trade, showing the H1 high/low reference levels, the 5-minute candles used from 10:00 onward, and the entry/exit points for every trade taken that day.

### Key Entities

- **Backtest Definition**: A hardcoded strategy available in the Backtest menu (name, instrument, and fixed rule set). "CAC40 Bougie de 9h" is the first instance; the data model must not assume it is the only one.
- **Backtest Run**: The result of executing a Backtest Definition over a UI-provided date range (a single day is the range's degenerate case) — a list of per-day outcomes plus the aggregate summary: number of days, number of trades, number of winning positions, number of losing positions, number of BE, average win, average loss, and final result.
- **Day Result**: The outcome for a single trading day within a Backtest Run — either "no data," "no trade," or a chronological list of one or more trades, each with entry price/time, exit price/time, exit reason (stop-loss, break-even, take-profit, or end of day), and points gained or lost.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can select the Backtest menu, run the "CAC40 Bougie de 9h" backtest for a single past day, and see a correct result (no data / no trade / one or more trades, each with entry, exit, and points) within a few seconds of requesting it.
- **SC-002**: On a hand-verified set of at least 6 historical FRA40.I trading days covering all outcome types (no data, no trade, stop-loss exit, break-even exit, take-profit exit, end-of-day exit, and at least one day with more than one trade), the backtest's reported entry price, exit price, exit reason, and points result match manual calculation exactly for every trade on every day.
- **SC-003**: A trader can enter a start and end date in the UI, run the backtest over a multi-week range, and receive a summary (number of days, number of trades, number of winning positions, number of losing positions, number of BE, average win, average loss, final result) that matches a manual computation from the individual day results.
- **SC-004**: A trader can open the detail view for any day with a trade and visually confirm the H1 reference levels and the entry/exit points against the underlying 5-minute candles.
- **SC-005**: Days with missing or unavailable H1 reference data never interrupt a multi-day backtest run — the run always completes and reports results for every day that does have data.

## Assumptions

- "Points" refers to raw index price difference on FRA40.I (e.g., entry 8000.0 to exit 7950.0 is a 50-point loss), not currency P&L from a specific position size; no position sizing or account currency conversion is in scope.
- The FRA40.I H1 and 5-minute candle history needed for past (fully closed) trading days is obtainable through the existing Saxo historical-candle capability; no new market-data source is required.
- The backtest operates only on already-closed historical days; it does not run live or simulate intraday in real time.
- "End of day" means the close of FRA40.I's regular trading session for that day, using the last available 5-minute candle.
- All clock times in this spec (9:00, 10:00, end of day) are Paris exchange local time (Europe/Paris), which observes daylight saving time; on the rare day where DST transition affects candle availability for the reference window, the existing "no data" handling (FR-004) applies.
- Only one hardcoded backtest ("CAC40 Bougie de 9h") is in scope for this feature; the Backtest menu's list structure should not preclude adding further hardcoded backtests later, but no generic backtest-authoring capability is being built.
- There is no upper limit on how many trades can occur in a single day beyond the natural constraint that a new trade can only start once the previous one has closed (never more than one open position at a time).
- No order placement, paper-trading, or live-execution capability is implied — this is a historical, read-only analysis feature.
- A trade closed via the break-even mechanism (FR-008a) always has a points result of exactly 0 and is counted only in "number of BE" — never in winning or losing positions, and excluded from the average win/loss calculations. In the rare case a trade reaches exactly 0 points through a different exit (e.g., an end-of-day close that happens to land on the entry price without break-even ever arming), it is classified as a losing position, since only break-even-mechanism exits are labeled "BE".
- "Average loss" is reported as a positive magnitude (e.g., "42 pts") rather than a negative number, so the summary reads naturally; "final result" is the only figure in the summary that can be negative, since it is a net sum.
- "Number of days" in the range summary counts only trading days where the H1 reference candle was available (i.e., days actually evaluated); days reported as "no data" are not counted, consistent with how they are excluded from every other aggregate figure.
- The break-even arm threshold (entry + 20 points) and the resulting stop level (entry price) are evaluated using candle high/low, not tick-level data; when a candle's high would both arm the break-even stop and (in the same candle) its low would breach it, the arming is treated as taking effect only from the next candle onward, so such a same-candle round-trip cannot itself produce a break-even exit — this favors a conservative, implementable reading over assuming a specific intra-candle price path.
