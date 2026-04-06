# Feature Specification: MM7 Indicator & Workflow

**Feature Branch**: `017-mm7-indicator`
**Created**: 2026-03-30
**Status**: Draft
**Input**: User description: "based on the MM50 indicator, I want you to create the same indicator but based on the MM7"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure a workflow using the MM7 indicator (Priority: P1)

A trader wants to set up a workflow that monitors when price approaches or touches the 7-period moving average, mirroring the same behavior already available for the MM50 indicator.

**Why this priority**: This is the core capability. Without it, no workflow can use MM7 as a trigger, and the feature has no value.

**Independent Test**: Can be fully tested by defining a workflow with `mm7` as the indicator type and verifying the system correctly computes the 7-period moving average and evaluates price proximity conditions.

**Acceptance Scenarios**:

1. **Given** a workflow configuration specifies `mm7` as the indicator type, **When** the workflow engine initializes, **Then** the 7-period moving average is computed from the candle series and used as the reference value.
2. **Given** a configured MM7 workflow with a "below" direction, **When** the current candle's close or high is within the spread below the MM7 value, **Then** the below condition is satisfied and the workflow triggers accordingly.
3. **Given** a configured MM7 workflow with an "above" direction, **When** the current candle's close or low is within the spread above the MM7 value, **Then** the above condition is satisfied and the workflow triggers accordingly.

---

### User Story 2 - MM7 indicator recognized in workflow enum (Priority: P2)

The existing indicator type registry must recognize `mm7` as a valid indicator, so it can be referenced consistently in workflow definitions and persisted correctly.

**Why this priority**: Without a registered indicator type, workflows using MM7 cannot be created or stored reliably. This is a prerequisite for any UI or API integration.

**Independent Test**: Can be tested by attempting to create a workflow with `mm7` indicator type and confirming it is accepted and stored without error.

**Acceptance Scenarios**:

1. **Given** the indicator type registry, **When** `mm7` is provided as an indicator name, **Then** it is resolved to the correct enum value without error.
2. **Given** a workflow stored with indicator type `mm7`, **When** the workflow is loaded, **Then** the indicator type is correctly deserialized.

---

### Edge Cases

- What happens when fewer than 7 candles are available? The system returns `None` — no signal is emitted and the workflow skips the evaluation cycle.
- What happens when the spread is zero? The condition should still evaluate correctly (exact match).
- What if the MM7 value equals the candle price exactly? The boundary should be considered a match.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize `mm7` as a valid indicator type, equivalent in status to the existing `ma50` indicator type.
- **FR-002**: System MUST compute the 7-period moving average from the candle series when an MM7 workflow is initialized.
- **FR-003**: System MUST evaluate a "below" condition as true when the candle's close or high falls within the spread below the MM7 value.
- **FR-004**: System MUST evaluate an "above" condition as true when the candle's close or low falls within the spread above the MM7 value.
- **FR-005**: System MUST support providing a single price element (instead of a full candle) for condition evaluation, consistent with the MM50 behavior.
- **FR-006**: System MUST return `None` (no signal) when fewer than 7 candles are available, allowing the workflow engine to skip the evaluation cycle without error.

### Key Entities

- **MM7 Indicator**: A 7-period moving average computed from a series of candles. Used as a reference level for workflow entry/exit conditions. Equivalent in structure to MM50 but using a period of 7.
- **MM7 Workflow**: A workflow variant that uses the MM7 indicator value as its trigger reference, supporting the same "above" and "below" condition logic as the existing MM50 workflow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A workflow configured with the MM7 indicator type runs without error across all supported unit times (no unit time restriction; identical scope to MM50).
- **SC-002**: The MM7 below and above conditions produce results consistent with manually computed 7-period moving averages — 100% accuracy on a defined test dataset.
- **SC-003**: All existing MM50 workflow tests continue to pass after the MM7 indicator is added (no regressions).
- **SC-004**: A trader can define and execute an MM7-based workflow using the same configuration format as an MM50 workflow, with no additional setup steps.

## Clarifications

### Session 2026-03-30

- Q: What should happen when fewer than 7 candles are available? → A: Return `None` — no signal is emitted; workflow skips the evaluation cycle.
- Q: Should MM7 be available on all unit times or restricted to shorter-term ones? → A: All unit times — no restriction, identical to MM50.

## Assumptions

- The MM7 workflow follows the exact same structural pattern as the MM50 workflow — only the moving average period changes (7 instead of 50).
- The slope-based logic used in the `combo` indicator function is not in scope for this feature; only the workflow trigger (touch/bounce) behavior is replicated.
- The `mobile_average` utility function already handles variable periods and can compute a 7-period average without modification.
