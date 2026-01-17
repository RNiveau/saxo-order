# Feature Specification: On-Demand Alerts Execution

**Feature Branch**: `003-on-demand-alerts`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: "In the asset detail view, I want to be able run the alerts system on demands for the asset"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Alerts on Demand (Priority: P1)

As a trader viewing an asset's detail page, I want to manually trigger the alerts system to check for new signals on the current asset so I can get immediate feedback without waiting for the scheduled alert generation.

**Why this priority**: This is the core value proposition - gives traders control to run analysis when they want it, especially useful when they spot interesting price action or before making trading decisions.

**Independent Test**: Navigate to any asset detail page (e.g., /asset/ITP:xpar), click a "Run Alerts" button, and verify that the system executes alert detection logic for that specific asset and displays any newly detected alerts.

**Acceptance Scenarios**:

1. **Given** I am on the asset detail page for "ITP:xpar", **When** I click the "Run Alerts" button, **Then** the system executes alert detection for this asset and displays a loading indicator
2. **Given** the alerts system is running, **When** new alerts are detected (e.g., combo, congestion), **Then** they appear in the alerts section immediately after execution completes
3. **Given** the alerts system completes execution, **When** no new alerts are found, **Then** I see a message "No new alerts detected" and existing alerts remain visible
4. **Given** I run alerts multiple times within 5 minutes, **When** I click "Run Alerts", **Then** I see a message "Alerts recently run. Please wait X minutes before running again" to prevent excessive API usage

---

### User Story 2 - Understand Execution Status (Priority: P2)

As a trader, I want to see clear feedback about the alert execution process (running, completed, failed) so I know when to check for results and understand if something went wrong.

**Why this priority**: User feedback is critical for manual actions - traders need to know the system is working and when results are ready.

**Independent Test**: Click "Run Alerts" button and verify: (1) button becomes disabled during execution, (2) loading indicator appears, (3) success or error message displays after completion, (4) button re-enables after cooldown period.

**Acceptance Scenarios**:

1. **Given** I click "Run Alerts", **When** execution starts, **Then** I see a loading spinner and the button becomes disabled with text "Running..."
2. **Given** alerts are being executed, **When** execution completes successfully, **Then** I see a success message "Alerts analysis completed" for 3 seconds
3. **Given** alerts execution encounters an error, **When** the error occurs, **Then** I see an error message explaining what went wrong (e.g., "Unable to run alerts. Please try again.")
4. **Given** execution completes, **When** 5 minutes have not passed, **Then** I see a countdown timer showing when I can run alerts again

---

### Edge Cases

- What happens when the backend alert detection service is unavailable? (Display error message: "Alert service is currently unavailable. Please try again later.")
- What happens when I trigger alerts during an already-running execution? (Button stays disabled, show message "Alert execution already in progress")
- What happens when alert detection takes longer than 30 seconds? (Show extended loading message: "Alert detection is taking longer than usual...", timeout after 60 seconds with error)
- What happens when network fails mid-execution? (Show error message: "Network error. Unable to complete alert execution.")
- What happens when I navigate away during execution? (Cancel the request, no alerts are saved)
- What happens when multiple browser tabs run alerts simultaneously for the same asset? (Backend handles deduplication, only one execution occurs)
- What happens when cooldown period expires while I'm on the page? (Button automatically re-enables, countdown timer disappears)

## Requirements *(mandatory)*

### Functional Requirements

**Execution Control:**
- **FR-001**: System MUST provide a "Run Alerts" button on the asset detail page
- **FR-002**: System MUST disable the "Run Alerts" button during execution and for 5 minutes after completion
- **FR-003**: System MUST execute alert detection logic only for the current asset (filtered by asset_code and country_code)
- **FR-004**: System MUST prevent concurrent executions for the same asset

**Status Feedback:**
- **FR-005**: System MUST display a loading indicator when alerts are being executed
- **FR-006**: System MUST show the button state as "Running..." with a spinner during execution
- **FR-007**: System MUST display a success message for 3 seconds when execution completes successfully
- **FR-008**: System MUST display an error message when execution fails, including a helpful description
- **FR-009**: System MUST show a countdown timer during the cooldown period indicating when alerts can be run again

**Results Display:**
- **FR-010**: System MUST refresh the alerts section automatically when new alerts are detected
- **FR-011**: System MUST preserve existing alerts when no new alerts are detected
- **FR-012**: System MUST display a "No new alerts detected" message when execution finds no signals
- **FR-013**: System MUST highlight newly detected alerts visually (e.g., with a "NEW" badge) for 60 seconds

**Technical Requirements:**
- **FR-014**: System MUST timeout alert execution after 60 seconds to prevent indefinite waiting
- **FR-015**: System MUST handle cases where asset has no country_code (use empty string or null)
- **FR-016**: System MUST call backend alert detection endpoint with asset_code and country_code parameters

### Key Entities

**Alert Execution Request:**
- `asset_code` (string, required): The asset identifier code
- `country_code` (string, nullable): The asset country code (can be empty/null)
- `exchange` (string, required): Exchange identifier (e.g., "xpar", "binance")
- `requested_at` (datetime, required): Timestamp when execution was requested

**Alert Execution Response:**
- `status` (enum: "success", "no_alerts", "error", required): Execution outcome
- `alerts_detected` (integer, required): Count of new alerts found
- `alerts` (array of Alert objects, optional): Newly detected alerts
- `execution_time_ms` (integer, required): How long detection took
- `message` (string, optional): Success or error message
- `next_allowed_at` (datetime, required): When alerts can be run again

## Success Criteria *(mandatory)*

### Measurable Outcomes

1. **Immediate Feedback**: Traders see alert execution results within 10 seconds of clicking "Run Alerts" for 95% of requests
2. **Clear Status**: Loading, success, and error states are visually distinct and appear within 200ms of state changes
3. **Execution Reliability**: Alert detection completes successfully for 98% of on-demand requests under normal conditions
4. **Cooldown Effectiveness**: Traders cannot trigger more than 1 execution per asset per 5-minute window, preventing system overload

### User Experience Goals

5. **Intuitive Control**: Traders understand how to trigger alerts without documentation (button placement and labeling are self-explanatory)
6. **Frustration Prevention**: Error messages provide actionable guidance (e.g., "Try again in 3 minutes" vs generic "Error occurred")

## Assumptions *(optional)*

1. **Backend Support**: Assumes a backend API endpoint exists or can be created to run alert detection for a single asset on demand
2. **Alert Detection Logic**: Assumes the existing scheduled alert detection logic can be invoked programmatically for individual assets
3. **Cooldown Mechanism**: Assumes backend enforces cooldown to prevent abuse (frontend displays timer but backend validates)
4. **Authentication**: Assumes users are authenticated and execution is logged for audit purposes
5. **Data Retention**: Assumes newly detected alerts follow the same 7-day retention policy as scheduled alerts
6. **Exchange Handling**: Assumes both Saxo and Binance assets support on-demand alert execution

## Dependencies *(optional)*

### Internal Dependencies
- **Existing Alerts Section**: Requires the alerts display section from feature 002-asset-detail-alerts to be implemented
- **Alert Detection Engine**: Requires access to the backend alert detection logic (combo, congestion, candle pattern detection)
- **Asset Context**: Requires asset_code, country_code, and exchange information from the current asset detail page

### External Dependencies
- **Backend API**: Requires new or existing endpoint to trigger alert detection for a single asset
- **User Authentication**: Requires user session/token to track execution history and enforce rate limits

## Out of Scope *(optional)*

1. **Bulk Execution**: Running alerts for multiple assets at once (e.g., all watchlist items)
2. **Scheduled Overrides**: Stopping or modifying the scheduled alert detection system
3. **Alert Configuration**: Customizing which alert types to detect (uses default detection logic)
4. **Historical Re-runs**: Re-running alert detection for past dates (only detects signals based on current/recent data)
5. **Execution Priority**: Prioritizing manual executions over scheduled ones (both use same backend queue)
6. **Advanced Filtering**: Running alerts only for specific types (e.g., "only run congestion detection")

## Metrics & Validation *(optional)*

### Usage Metrics
- **Execution Rate**: Track daily/weekly count of on-demand alert executions per user
- **Detection Success Rate**: Percentage of executions that find at least one new alert
- **Average Execution Time**: Mean and P95 execution duration
- **Cooldown Violations**: Count of attempts during cooldown period (indicates user friction)

### Quality Metrics
- **Error Rate**: Percentage of executions that fail (target: <2%)
- **Timeout Rate**: Percentage of executions exceeding 60 seconds (target: <1%)
- **User Satisfaction**: Track feedback on "Was this helpful?" prompt after execution

### Technical Metrics
- **Backend Load**: Monitor impact on alert detection service (CPU, memory, queue depth)
- **Concurrent Executions**: Track simultaneous executions to inform scaling decisions
