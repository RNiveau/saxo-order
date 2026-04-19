# Feature Specification: Unified Candle Builder

**Feature Branch**: `018-candle-builder`
**Created**: 2026-04-19
**Status**: Draft
**Input**: User description: "Build a unified candle system that rebuilds any unit time from 30-minute Saxo API data, handling both US and EU markets"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build daily candles from 30-minute data (Priority: P1)

A trader wants daily candles for an asset. The system aggregates 30-minute candles into H1 candles, then H1 candles into a daily candle, respecting market open/close hours for both EU and US assets.

**Why this priority**: Daily candles are the most commonly used timeframe for indicators and workflows. This is the foundational aggregation mechanism that all other daily-related features depend on.

**Independent Test**: Provide a full trading session of 30m candles for both a EU and a US asset. Verify the resulting daily candle has correct OHLC values matching the session boundaries.

**Acceptance Scenarios**:

1. **Given** all 30-minute candles for a EU asset covering a full trading day (07:00 to 15:00 UTC), **When** a daily candle is built, **Then** the open equals the first H1 candle's open, the close equals the last H1 candle's close, and high/low are the extremes across all H1 candles of the session.
2. **Given** all 30-minute candles for a US asset covering a full trading day (13:30 to 20:00 UTC), **When** a daily candle is built, **Then** the open equals the first H1 candle's open, the close equals the last H1 candle's close, and high/low are the extremes across all H1 candles of the session.
3. **Given** 30-minute candles that fall outside market hours, **When** building the daily candle, **Then** those candles are excluded from the aggregation.

---

### User Story 2 - Rebuild the current daily candle during trading hours (Priority: P1)

A trader checks an asset's daily chart during the trading session. The data provider only returns completed days, so the current day is missing. The system uses the daily candle building mechanism (Story 1) to rebuild the current incomplete day from available 30-minute data.

**Why this priority**: Without the current day's candle, every indicator and workflow operates on yesterday's data during trading hours. This is the primary gap the feature solves.

**Independent Test**: During a trading session, request daily candles for both a EU and a US asset. Verify the most recent candle represents today's partial session with correct open/high/low/close values.

**Acceptance Scenarios**:

1. **Given** a rebuilt current-day candle and completed daily candles from the provider, **When** the full daily list is assembled, **Then** the rebuilt candle appears at index 0 (most recent) followed by completed days in reverse chronological order.
2. **Given** the market is closed (weekend or holiday), **When** daily candles are requested, **Then** no rebuilt candle is inserted and the list starts with the last completed day.

---

### User Story 3 - Build hourly candles from 30-minute data (Priority: P1)

A trader wants H1 candles. The system aggregates pairs of 30-minute candles into hourly candles, handling both EU (:00-aligned) and US (:30-aligned) boundaries.

**Why this priority**: H1 candles are the intermediate building block: 30m -> H1 -> H4/Daily. They are also used directly by several indicators and workflows.

**Independent Test**: Request H1 candles for a EU and a US asset during a trading session. Verify each H1 correctly aggregates its two 30m candles.

**Acceptance Scenarios**:

1. **Given** two consecutive 30-minute candles at 07:00 and 07:30 for a EU asset, **When** H1 candles are built, **Then** one H1 candle is produced with open from 07:00, close from 07:30, and high/low as the extremes of both.
2. **Given** two consecutive 30-minute candles at 13:30 and 14:00 for a US asset, **When** H1 candles are built, **Then** one H1 candle is produced with open from 13:30, close from 14:00, and high/low as the extremes of both.
3. **Given** 30-minute candles outside trading hours, **When** H1 candles are built, **Then** those candles are excluded.

---

### User Story 4 - Build H4 candles from H1 candles (Priority: P2)

A trader wants 4-hour candles for medium-term analysis. The system aggregates H1 candles into H4 candles following the two-step pipeline: 30m -> H1 -> H4.

H4 candle boundaries are irregular and differ between EU and US markets because trading sessions don't divide evenly into 4-hour blocks:

**EU market (open_hour=7, 9 H1 candles per day):**
- First H4: 3 H1 candles (07:00, 08:00, 09:00)
- Second H4: 4 H1 candles (10:00, 11:00, 12:00, 13:00)
- Third H4: 2 H1 candles (14:00, 15:00)

**US market (open_hour=13, 7 H1 candles per day):**
- First H4: 4 H1 candles (13:30, 14:30, 15:30, 16:30)
- Second H4: 3 H1 candles (17:30, 18:30, 19:30)

**Why this priority**: H4 is used by workflow indicators for medium-term trend detection. Less critical than H1/Daily since fewer workflows rely on it directly.

**Independent Test**: Build H4 candles from H1 data for a full trading day on both US and EU assets and verify correct grouping.

**Acceptance Scenarios**:

1. **Given** a full EU trading day of H1 candles (9 candles from 07:00 to 15:00), **When** H4 candles are built, **Then** three H4 candles are produced with groups of 3, 4, and 2 H1 candles respectively.
2. **Given** a full US trading day of H1 candles (7 candles from 13:30 to 19:30), **When** H4 candles are built, **Then** two H4 candles are produced with groups of 4 and 3 H1 candles respectively.
3. **Given** an incomplete set of H1 candles that doesn't fill a complete H4 group, **When** H4 candles are built, **Then** the incomplete group is skipped.

---

### User Story 5 - Build weekly candles including current week (Priority: P2)

A trader wants weekly candles where the current incomplete week is rebuilt from daily candles. The daily candles themselves may include a rebuilt current day.

**Why this priority**: Weekly candles are used for long-term trend analysis but are less frequently queried than daily or hourly data.

**Independent Test**: On a mid-week trading day, request weekly candles and verify the current week's candle aggregates Monday through the current day.

**Acceptance Scenarios**:

1. **Given** completed weekly candles from the provider and daily candles for the current week, **When** weekly candles are assembled, **Then** the rebuilt current week appears at index 0 followed by completed weeks.
2. **Given** it is Monday and only one daily candle exists for the current week, **When** the weekly candle is built, **Then** it mirrors that single day's OHLC values.
3. **Given** today is a weekday and the current day's daily candle is itself rebuilt from 30m data, **When** the weekly candle is built, **Then** it correctly includes the rebuilt daily candle.

---

### User Story 6 - Unified candle building across US and EU markets (Priority: P1)

A trader has a mixed portfolio. The same candle-building logic works for both EU and US assets, parameterized by market session hours (open hour, open minutes, close hour).

**Why this priority**: A common system avoids duplicated logic and ensures consistent behavior. The 30-minute base unit naturally handles both :00 (EU) and :30 (US) boundaries.

**Independent Test**: Run the candle-building pipeline on both a EU asset (open_minutes=0) and a US asset (open_minutes=30) using the same code path and verify both produce correct results.

**Acceptance Scenarios**:

1. **Given** a market defined with open_hour=7, open_minutes=0, close_hour=15 (EU), **When** candles are built from 30m data, **Then** boundaries align to the :00/:30 marks within EU trading hours.
2. **Given** a market defined with open_hour=13, open_minutes=30, close_hour=20 (US), **When** candles are built from 30m data, **Then** boundaries align to the :30/:00 marks within US trading hours.
3. **Given** the same candle-building function called for both markets, **When** only market parameters differ, **Then** both produce correctly aggregated candles without market-specific branching logic in the H1 and daily builders.

**Note**: H4 candle grouping produces different group sizes per market because trading sessions don't divide evenly into 4-hour blocks (see Story 4). However, the grouping logic MUST be derived from Market parameters (open hour, close hour, open minutes), not from hardcoded identity checks on specific market values.

---

### User Story 7 - Remove CFD fallback mechanism (Priority: P2)

The existing CFD fallback in `build_hour_candles` fetches CFD data when the latest 30m candle is stale. This mechanism is misleading in practice and must be removed. The candle builder should only use data from the asset itself.

**Why this priority**: CFD data mixed into regular asset candles produces misleading results in the app. Removing it simplifies the pipeline and makes the data source trustworthy.

**Independent Test**: Build candles for an asset with stale 30m data. Verify no CFD data is fetched or inserted, and the `cfd_code` parameter is removed from the candle-building interface.

**Acceptance Scenarios**:

1. **Given** the most recent 30m candle is stale, **When** building candles, **Then** the system uses only the available data without fetching from any CFD source.
2. **Given** the candle-building entry point, **When** inspecting its interface, **Then** there is no `cfd_code` parameter.

---

### User Story 8 - Single candle-building entry point (Priority: P2)

The system exposes a single method for building candles at any unit time, replacing the current duplication between `get_candle_per_hour` (returns one candle) and `build_hour_candles` (returns a list). Callers request a list of candles at a given unit time; getting only the latest is just taking index 0.

**Why this priority**: Duplicated building methods lead to divergent behavior and maintenance burden. A single pipeline ensures consistency.

**Independent Test**: Request candles at H1, H4, and Daily unit times through the single entry point. Verify the result is a list with correct candles, and that taking index 0 gives the same result as the old `get_candle_per_hour`.

**Acceptance Scenarios**:

1. **Given** a request for H1 candles through the unified method, **When** the caller takes index 0, **Then** the result matches what `get_candle_per_hour` would have returned.
2. **Given** a request for Daily candles through the unified method, **When** the full list is returned, **Then** it matches what `build_hour_candles` would have returned.

---

### User Story 9 - Remove legacy `build_daily_candle_from_hours` (Priority: P3)

The legacy function `build_daily_candle_from_hours` in `utils/helper.py` is hardcoded to EU market hours (open at hour 7, close at hour 15) and is not parameterized. It should be removed and its callers migrated to the unified pipeline.

**Why this priority**: Cleanup task. The function is already superseded by `build_daily_candles_from_h1` but still exists in the codebase.

**Independent Test**: After removal, verify no code references the function and all tests pass.

**Acceptance Scenarios**:

1. **Given** the legacy function is removed, **When** all existing callers are identified, **Then** they are migrated to use the unified candle-building pipeline.
2. **Given** the migration is complete, **When** the full test suite runs, **Then** all tests pass without regressions.

---

### Edge Cases

- What happens when the market is closed (weekend/holiday)? No 30m candles exist for the current day; the system returns completed candles only, without inserting a rebuilt candle at index 0.
- What happens during daylight saving transitions? The system relies on UTC timestamps from the provider and the market configuration. Local time is never used.
- What if 30m data has gaps (timeout, missing candle)? The system builds from available data without interpolating missing candles. High/low/close are computed from what exists.
- What if a 30m candle falls exactly on market close time? It is included as the last candle of the session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use the 30-minute interval as the base unit for candle building, ensuring alignment with both EU (:00) and US (:30) market open times.
- **FR-002**: System MUST add M30 as a value in the UnitTime enum to represent 30-minute candles explicitly.
- **FR-003**: System MUST follow a two-step aggregation pipeline: 30m -> H1 -> H4/Daily. H4 and Daily candles are built from H1 candles, not directly from 30m.
- **FR-004**: System MUST build H1 candles by aggregating pairs of consecutive 30-minute candles, respecting market open/close boundaries.
- **FR-005**: System MUST build H4 candles from H1 candles with grouping rules derived from Market parameters (open hour, close hour, open minutes), not from hardcoded market identity checks. The grouping is irregular because trading sessions don't divide evenly into 4-hour blocks: EU produces groups of 3/4/2, US produces groups of 4/3.
- **FR-006**: System MUST build daily candles from H1 candles covering a full trading session, with the session length derived from Market parameters. EU = 9 H1 candles (07:00-15:00 UTC), US = 7 H1 candles (13:30-19:30 UTC).
- **FR-007**: System MUST rebuild the current (incomplete) daily candle from available 30m data when the trading day is still open.
- **FR-008**: System MUST rebuild the current (incomplete) weekly candle from daily candles.
- **FR-009**: System MUST always return candle lists with the most recent candle at index 0 (newest first).
- **FR-010**: System MUST only return complete candles. Incomplete periods (not enough 30m candles to form a full H1, or not enough H1s to form a full H4) are skipped. A future enhancement may add a parameter to include partial candles.
- **FR-011**: System MUST accept a Market object (open hour, open minutes, close hour) to determine candle boundaries. H4 and Daily builders MUST derive their grouping logic from these parameters, not from hardcoded checks like `open_hour == 7` or `open_hour == 13`. Adding a new market MUST only require defining a new Market instance, not modifying builder functions.
- **FR-012**: System MUST exclude 30-minute candles that fall outside the market's trading hours when building larger-timeframe candles.
- **FR-013**: When aggregating candles, open MUST come from the first (oldest) candle in the group, close from the last (newest), high from the maximum of all highs, and low from the minimum of all lows.
- **FR-014**: System MUST NOT use CFD data as a fallback. The existing CFD fallback mechanism and `cfd_code` parameter MUST be removed from the candle-building pipeline.
- **FR-015**: System MUST expose a single candle-building entry point, replacing the current duplication between `get_candle_per_hour` and `build_hour_candles`.
- **FR-016**: The legacy `build_daily_candle_from_hours` function MUST be removed after migrating its callers (production: `saxo_order/commands/alerting.py:663`) to the unified pipeline.
- **FR-017**: The Market model MUST be updated to use correct UTC close hours: `EUMarket.close_hour` from 17 to 15, `USMarket.close_hour` from 21 to 20. Currently `_build_h1_from_30m` accepts candles up to the wrong close_hour, producing H1 candles beyond the real session end that the daily builder then ignores.

### Key Entities

- **Candle**: Open, High, Low, Close prices with a unit time (M30, H1, H4, D, W) and a timestamp. The unit time indicates the granularity of the candle.
- **Market**: Defines a trading session with open hour, open minutes, and close hour (all in UTC). EU: open_hour=7, open_minutes=0, close_hour=15. US: open_hour=13, open_minutes=30, close_hour=20.
- **UnitTime**: The granularity of a candle. Values: M30, H1, H4, D (daily), W (weekly), M (monthly), M15 (15 minutes, existing).

### Aggregation Pipeline

```
Saxo API (horizon=30)
       |
       v
  30-min candles (raw, newest first)
       |
       +---> filter by market hours
       |
       +---> aggregate 2x 30m --> H1 candles
       |         |
       |         +---> aggregate H1s --> H4 candles (market-specific grouping)
       |         +---> aggregate H1s --> Daily candle (full session)
       |
       v
  Combine with Saxo API completed candles (horizon=1440, 10080)
       |
       +---> insert rebuilt current-day at index 0 of daily list
       +---> insert rebuilt current-week at index 0 of weekly list
       |
       v
  Final candle list (newest first) --> indicators, workflows, UI
```

### H4 Grouping Reference

| Market | H4 Block 1 | H4 Block 2 | H4 Block 3 |
|--------|-----------|-----------|-----------|
| EU (open_hour=7) | 07:00, 08:00, 09:00 (3 H1s) | 10:00, 11:00, 12:00, 13:00 (4 H1s) | 14:00, 15:00 (2 H1s) |
| US (open_hour=13) | 13:30, 14:30, 15:30, 16:30 (4 H1s) | 17:30, 18:30, 19:30 (3 H1s) | - |

### Assumptions

- The data provider always returns 30-minute candles with consistent timestamps aligned to :00 and :30 marks.
- All market hours are in UTC. EU: 07:00-15:00 (09:00-17:00 UTC+2). US: 13:30-20:00.
- Market hours are static per market definition. Daylight saving adjustments are reflected in the market configuration, not computed dynamically.
- Monthly candles are not rebuilt from 30m data (the provider's monthly candles are sufficient since the current month lag is acceptable for long-term analysis).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any unit time (H1, H4, Daily, Weekly) can be correctly rebuilt from 30-minute candles for both US and EU assets.
- **SC-002**: During trading hours, the current incomplete day is available as the first candle (index 0) in the daily list.
- **SC-003**: When a period completes, the rebuilt candle's OHLC values match the provider's completed candle for the same period (validated by comparing rebuilt vs. provider data over at least 5 trading days).
- **SC-004**: H1 and Daily candle building use a single parameterized code path for both markets. H4 uses market-specific grouping definitions but shared aggregation logic.
- **SC-005**: A single entry point replaces the current dual methods, with no behavioral regressions in workflows or indicators.
