# Feature Specification: Inclined Line Indicator (ROB/SOH)

**Feature Branch**: `512-inclined-line-indicator`
**Created**: 2026-04-12
**Status**: Draft
**Input**: User description: "Calculate ROB and SOH inclined lines for workflow monitoring (GitHub issue #231)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor price relative to an inclined support/resistance line (Priority: P1)

A trader draws an inclined line through two historical price points (e.g., two swing lows for a support line or two swing highs for a resistance line). They want the workflow engine to automatically calculate where that line is "today" and alert them when price approaches, touches, or crosses the line.

**Why this priority**: This is the core value of the feature. Without the ability to evaluate price position relative to a dynamically projected inclined line, there is no ROB or SOH detection.

**Independent Test**: Can be fully tested by defining a workflow with two reference points (date + price), running the workflow engine, and verifying it correctly computes the line value at the current date and evaluates whether the current candle is above or below that line within the specified spread.

**Acceptance Scenarios**:

1. **Given** a workflow configured with an inclined indicator defined by two points (date1, price1) and (date2, price2), **When** the workflow engine runs, **Then** it calculates the projected line value at the current date using business days (excluding weekends and market holidays) as the X axis.
2. **Given** the line value at the current date is 105 and the spread is 1, **When** the candle's close is 104.5, **Then** the "below" condition is satisfied (price is within spread below the line).
3. **Given** the line value at the current date is 105 and the spread is 1, **When** the candle's low is 105.8, **Then** the "above" condition is satisfied (price is within spread above the line).
4. **Given** an inclined indicator with two reference points on past dates, **When** the current date is a market holiday or weekend, **Then** the system does not count that day in the X-axis calculation, preserving line accuracy.

---

### User Story 2 - Configure an inclined line in a workflow definition (Priority: P1)

A trader wants to define an inclined line indicator within a workflow configuration by specifying two reference points (each with a date and a price), a unit time, a close direction (above/below), and a spread.

**Why this priority**: Without a configuration mechanism, the inclined line calculation cannot be triggered. This is a prerequisite for User Story 1.

**Independent Test**: Can be tested by writing a workflow definition with an inclined indicator, loading it, and verifying the system parses the two points and creates the correct indicator object.

**Acceptance Scenarios**:

1. **Given** a workflow definition contains an indicator of type "inclined" with x1 (date, price) and x2 (date, price), **When** the workflow is loaded, **Then** the system creates an inclined indicator with the two reference points correctly parsed.
2. **Given** a workflow definition with an inclined indicator, **When** the close direction is "above" and the spread is 1, **Then** the workflow evaluates the "above" condition using the projected line value and the specified spread.
3. **Given** a workflow definition with an inclined indicator where x1 date equals x2 date, **When** the workflow is loaded, **Then** the system rejects the configuration with an error (two identical X values cannot define a line).

---

### User Story 3 - Create inclined line workflows from the UI (Priority: P2)

A trader wants to create and manage inclined line workflows through the frontend interface, selecting "inclined" as the indicator type and providing two reference points.

**Why this priority**: The CLI/YAML workflow is sufficient for initial usage. UI integration adds convenience but is not required for the core capability.

**Independent Test**: Can be tested by opening the workflow creation form, selecting "inclined" as the indicator type, filling in two reference points, saving, and verifying the workflow appears correctly in the workflow list.

**Acceptance Scenarios**:

1. **Given** the workflow creation form is open, **When** the user selects "inclined" as the indicator type, **Then** the form displays two additional input groups for point 1 (date, price) and point 2 (date, price).
2. **Given** the user fills in both reference points and saves the workflow, **When** the workflow list is refreshed, **Then** the new inclined workflow appears with its configuration correctly displayed.

---

### Edge Cases

- What happens when the two reference points have the same date? The system must reject the configuration (division by zero in slope calculation).
- What happens when the projected line extends far into the future? The line should continue to be calculated; the user is responsible for disabling stale workflows.
- What happens when market data is unavailable to determine if a day was open? The system should fall back to a standard weekday-only calculation (exclude Saturday and Sunday).
- What if the current date is before the second reference point? The system should still interpolate correctly between the two points.
- What happens when the inclined line results in a negative projected price? The calculation should proceed normally; the workflow condition will simply not match if price cannot be negative.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST calculate the projected value of an inclined line at any given date using a linear equation (Y = aX + b) where X is measured in business days from the first reference point.
- **FR-002**: System MUST count only business days (excluding weekends and market-specific holidays) when computing the X-axis distance between dates.
- **FR-003**: System MUST support defining an inclined indicator with two reference points, each consisting of a date and a price.
- **FR-004**: System MUST evaluate a "below" condition as true when the candle's close or high falls within the spread below the projected line value.
- **FR-005**: System MUST evaluate an "above" condition as true when the candle's close or low falls within the spread above the projected line value.
- **FR-006**: System MUST reject an inclined indicator configuration where both reference points have the same date.
- **FR-007**: System MUST recognize "inclined" as a valid indicator type in workflow definitions, alongside existing types (ma50, combo, bbh, bbb, polarite, zone).
- **FR-008**: System MUST always use business days as the X-axis unit for line projection, regardless of the workflow's unit time. Intraday workflows (H1, H4) compare against the same projected daily level throughout the trading day.
- **FR-009**: Frontend workflow creation form MUST dynamically display reference point inputs when "inclined" is selected as the indicator type.

### Key Entities

- **Inclined Line**: A linear projection defined by two reference points (date + price). The line extends indefinitely from the first point through the second and beyond, with the X axis measured in business days.
- **Reference Point**: A coordinate consisting of a calendar date and a price level, used to anchor the inclined line. Two reference points are required to define the line.
- **Business Day Distance**: The number of trading days between two calendar dates, excluding weekends and market-specific holidays. Used as the X-axis unit for the linear equation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A workflow configured with an inclined line indicator runs without error and correctly projects the line value at the current date, matching a manual calculation within rounding tolerance.
- **SC-002**: The inclined line workflow correctly triggers above/below conditions when the candle price is within the specified spread of the projected line value, with 100% accuracy on a defined test dataset.
- **SC-003**: All existing workflow types (MA50, Combo, BB, Polarite, Zone) continue to pass their tests after the inclined indicator is added (no regressions).
- **SC-004**: A trader can define, save, and execute an inclined-line workflow using the same configuration format as other workflow types, with the addition of two reference point fields.
- **SC-005**: Business day calculation correctly excludes weekends and known market holidays, matching expected results for at least 3 representative date ranges.

## Clarifications

### Session 2026-04-12

- Q: Should the X axis always use business days regardless of the workflow's unit time, or should shorter unit times use their own granularity? → A: Always use business days. Intraday workflows compare against the same projected daily level throughout the trading day.

## Assumptions

- The inclined line follows a simple linear equation (Y = aX + b) with no curvature or weighting.
- The two reference points are manually chosen by the trader based on their technical analysis; the system does not auto-detect support/resistance levels.
- The existing `number_of_day_between_dates()` and `apply_linear_function()` utilities are correct and can be reused for the core calculation.
- The `is_day_open()` API check is the authoritative source for determining market holidays.
- Cross-timeframe support (line defined on daily, executed on H4) is deferred; the initial implementation uses the same unit time for definition and execution.
