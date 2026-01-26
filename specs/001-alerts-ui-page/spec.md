# Feature Specification: Alerts UI Page

**Feature Branch**: `001-alerts-ui-page`
**Created**: 2026-01-10
**Status**: ✅ Complete (Last Updated: 2026-01-26)
**Input**: User description: "Today the alerting system runs every days and send a slack message. That's useful but we can't see these alerts in the UI yet. I want to see in a new page all the alerts. The alerts can live 7 days. They disappear after that."

## Implementation Status

| User Story | Priority | Status | Documentation |
|------------|----------|--------|---------------|
| **US1**: View All Active Alerts | P1 | ✅ Complete | See plan.md |
| **US2**: Filter and Search Alerts | P2 | ✅ Complete | See plan.md |
| **US3**: Sort Alerts by MA50 Slope | P2 | ✅ Complete | See plan.md |
| **US4**: Exclude Assets from Alerting | P2 | ✅ Complete | [`user-story-4-asset-exclusion/`](./user-story-4-asset-exclusion/) |

**Overall Feature Status**: All user stories completed and production-ready.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View All Active Alerts (Priority: P1)

As a trader, I want to see all my active alerts in a dedicated page so I can quickly review market conditions and trading signals without checking Slack messages.

**Why this priority**: This is the core value proposition - providing visibility into alerts that currently only exist in Slack. Without this, the feature provides no value.

**Independent Test**: Navigate to the Alerts page and verify all alerts from the last 7 days are displayed with their key information (asset, condition, timestamp).

**Acceptance Scenarios**:

1. **Given** alerts exist in the system, **When** I navigate to the Alerts page, **Then** I see a list of all active alerts sorted by timestamp (newest first)
2. **Given** an alert was created 6 days ago, **When** I view the Alerts page, **Then** that alert is visible in the list
3. **Given** an alert was created 8 days ago, **When** I view the Alerts page, **Then** that alert is not visible (expired after 7 days)
4. **Given** multiple alerts exist, **When** I view the Alerts page, **Then** each alert displays: asset name, TradingView link (with consistent icon and custom link support), alert type, MA50 slope value, alert condition, and timestamp

---

### User Story 2 - Filter and Search Alerts (Priority: P2)

As a trader with many assets, I want to filter alerts by asset or alert type so I can focus on specific trading opportunities.

**Why this priority**: Filtering capabilities significantly improve usability for active traders monitoring multiple assets, making the feature more practical for real-world use.

**Independent Test**: Apply a filter for a specific asset, verify only alerts for that asset are displayed.

**Acceptance Scenarios**:

1. **Given** alerts for multiple assets exist, **When** I filter by a specific asset, **Then** only alerts for that asset are displayed
2. **Given** different types of alerts exist, **When** I filter by alert type, **Then** only alerts of that type are displayed
3. **Given** a filter is applied, **When** I clear the filter, **Then** all alerts are displayed again

---

### User Story 3 - Sort Alerts by MA50 Slope (Priority: P2)

As a trader, I want to sort all alerts by their MA50 slope (highest first) so I can prioritize assets with the strongest upward trends regardless of alert type.

**Why this priority**: MA50 slope indicates trend direction and strength - higher positive slopes show stronger upward momentum, while negative slopes show downward trends. This helps traders identify which assets have the strongest upward movements and should be prioritized, across all alert types.

**Independent Test**: Create multiple alerts of different types with different MA50 slope values. Select "MA50 Slope" in the sort dropdown. Verify alerts are sorted by MA50 slope value descending (highest first).

**Acceptance Scenarios**:

1. **Given** alerts exist with MA50 slopes of +15.2, -12.5, +8.3, -20.4, **When** I sort by MA50 slope, **Then** they display in order: +15.2, +8.3, -12.5, -20.4 (highest slope first)
2. **Given** I select "MA50 Slope" sorting, **When** alerts of different types exist (COMBO, CONGESTION, DOUBLE_TOP), **Then** all alerts are sorted by their MA50 slope values descending
3. **Given** alerts are sorted by MA50 slope, **When** I switch back to "Recent" sorting, **Then** alerts sort by date (newest first)
4. **Given** MA50 slope sorting is selected, **When** I filter by asset or type, **Then** filtered alerts remain sorted by MA50 slope
5. **Given** MA50 slope sorting is active, **When** the page refreshes, **Then** sorting preference persists (or resets to default - specify in implementation)

---

### User Story 4 - Exclude Assets from Alerting (Priority: P2)

As a trader, I want to exclude specific assets from alert processing so I can prevent unwanted alerts from appearing in my alert view and reduce computational overhead during batch runs.

**Why this priority**: This improves system efficiency by skipping processing for assets I'm not interested in, and reduces noise in the alert view. It's particularly useful for assets that consistently generate false signals or are no longer relevant to my trading strategy.

**Independent Test**: Add an asset to the exclusion list, run the batch alerting process, verify that no alerts are generated for the excluded asset and it doesn't appear in the alert view.

**Acceptance Scenarios**:

1. **Given** an asset is added to the exclusion list, **When** the batch alerting runs, **Then** that asset is skipped during processing and no alerts are generated for it
2. **Given** an asset is in the exclusion list, **When** I view the Alerts page, **Then** any existing alerts for that asset are filtered out and not displayed
3. **Given** an asset is excluded, **When** I manually trigger alerting for that specific asset using `--code`, **Then** the system respects the exclusion and does not process or generate alerts for it
4. **Given** I have excluded assets, **When** I view the exclusion list, **Then** I see all currently excluded assets with their codes and country codes
5. **Given** an asset is excluded, **When** I remove it from the exclusion list, **Then** future batch runs will process that asset again and new alerts will appear in the alert view
6. **Given** multiple assets are excluded, **When** batch alerting builds the watchlist, **Then** all excluded assets are filtered out before processing begins, reducing total processing time

> **📁 Implementation Documentation**: User Story 4 has been implemented. For complete implementation details, see [`user-story-4-asset-exclusion/`](./user-story-4-asset-exclusion/) directory which contains:
> - Implementation plan and task breakdown
> - API specifications (OpenAPI 3.0)
> - Test results and testing guides
> - Performance validation methodology
> - Complete feature summary
>
> **Quick Start**: See [`user-story-4-asset-exclusion/README.md`](./user-story-4-asset-exclusion/README.md) for navigation guide.
>
> **Status**: ✅ Complete - Ready for Deployment (2026-01-26)

---

### Edge Cases

- What happens when no alerts exist in the last 7 days? (Display empty state message: "No active alerts")
- What happens when the alerts data source is unavailable? (Display error message with retry option)
- What happens when an alert expires while the page is open? (Alert no longer appears on next page refresh as it's been automatically deleted from storage)
- What happens when there are hundreds of alerts? (Implement pagination with 50 alerts per page)
- What happens when the user first visits the page and no alerts have been generated yet? (Display informative message explaining the feature and when alerts will appear)
- What happens at exactly the 7-day boundary (168 hours)? (Alert is automatically deleted from storage by TTL mechanism)
- What happens with alerts generated across different time zones? (Display timestamps in user's local time with timezone indicator)
- What happens when sorting by MA50 slope and ma50_slope data is missing or null for some alerts? (Treat missing values as slope=0 and sort accordingly with other zero-slope alerts)
- What happens when two alerts have identical MA50 slope values? (Secondary sort by date, newest first)
- What happens when MA50 cannot be calculated for an asset due to insufficient historical data? (Store ma50_slope as null/0 in alert data)
- What happens when all alerts have negative MA50 slopes? (Sort descending by slope value: -5 appears before -10, -10 before -20)
- What happens when MA50 slope value is missing or null for display? (Display "N/A" or "--" instead of a percentage)
- What happens when an asset is added to the exclusion list but already has active alerts? (Existing alerts are hidden from view but remain in storage until TTL expires)
- What happens when trying to exclude an asset that doesn't exist in the watchlist? (System accepts the exclusion and will skip it if encountered in future)
- What happens when all assets in the watchlist are excluded? (Batch run completes quickly with "No alerts for today" message, no processing occurs)
- What happens when an excluded asset is removed from the exclusion list mid-batch run? (Change takes effect on next batch run, current run continues with original exclusion list)

## Requirements *(mandatory)*

### Functional Requirements

**Data Retrieval:**
- **FR-001**: System MUST retrieve all available alerts from storage (alerts older than 7 days are automatically removed by TTL)
- **FR-002**: System MUST calculate alert age based on creation timestamp and current time for display purposes
- **FR-003**: System MUST sort alerts by creation timestamp in descending order (newest first)

**Display Requirements:**
- **FR-004**: System MUST display for each alert: asset name, TradingView link, alert type, MA50 slope value, alert condition/message, and creation timestamp
- **FR-005**: System MUST format timestamps in a human-readable format (e.g., "2 hours ago", "3 days ago")
- **FR-006**: System MUST provide absolute timestamp on hover or in detail view
- **FR-007**: System MUST handle empty state when no alerts exist
- **FR-008**: System MUST paginate results when more than 50 alerts exist

**Navigation:**
- **FR-009**: System MUST provide a navigation link to the Alerts page from the main navigation menu
- **FR-010**: System MUST support deep linking to the Alerts page via URL

**Filtering (Priority P2):**
- **FR-011**: System MUST allow filtering alerts by asset identifier
- **FR-012**: System MUST allow filtering alerts by alert type
- **FR-013**: System MUST show alert count for each filter option
- **FR-014**: System MUST support clearing all active filters

**Sorting (Priority P2):**
- **FR-015**: System MUST provide a sort dropdown with options: "MA50 Slope", "Recent" (date)
- **FR-016**: System MUST sort by MA50 slope (highest first) by default
- **FR-017**: When sorting by MA50 Slope, System MUST sort alerts by ma50_slope value descending (highest slope first)
- **FR-018**: System MUST extract ma50_slope from alert data payload for all alert types
- **FR-019**: System MUST treat alerts without ma50_slope data as having slope = 0 for sorting purposes
- **FR-020**: System MUST preserve sort selection when filters are applied or changed
- **FR-021**: Alert detection MUST calculate and store ma50_slope in alert data payload for all alert types using slope_percentage() function
- **FR-022**: TradingView link MUST use the same icon used throughout the application and MUST respect the custom link feature (if configured for the asset)
- **FR-023**: MA50 slope value MUST be displayed as a formatted percentage (e.g., "+15.2%", "-8.3%") with appropriate visual styling (positive values in green, negative in red)

**Asset Exclusion (Priority P2):**
- **FR-024**: System MUST maintain a persistent list of excluded assets identified by asset code and country code
- **FR-025**: Batch alerting process MUST filter out excluded assets from the watchlist before processing begins
- **FR-026**: Alert retrieval API MUST filter out alerts for excluded assets before returning results to the UI
- **FR-027**: System MUST allow adding assets to the exclusion list via configuration file or database
- **FR-028**: System MUST allow removing assets from the exclusion list
- **FR-029**: Exclusion MUST apply to both automatic batch runs and manual single-asset alerting commands
- **FR-030**: System MUST log when assets are skipped due to exclusion for debugging purposes

### Key Entities

- **Alert**: Represents a single alert notification generated by the alerting system
  - Identifier: Unique alert ID
  - Asset: The trading asset this alert relates to (symbol, code)
  - Condition: The condition that triggered the alert (e.g., "MA50 crossover", "price threshold exceeded")
  - Message: Human-readable alert message
  - Type: Category of alert (e.g., "technical_indicator", "price_alert", "volume_alert")
  - Timestamp: When the alert was created (ISO 8601 format)
  - TTL: Expiration timestamp (creation timestamp + 7 days) for automatic deletion from storage
  - Data: Alert-specific payload (structure varies by type)
    - All alerts include: ma50_slope (float or null) - slope percentage of 50-period moving average for the asset, normalized to 100 (positive for upward trends, negative for downward trends)
    - COMBO alerts additionally include: price, direction, strength, has_been_triggered, details

- **AlertFilter**: Represents user's filter preferences
  - Asset filter: Selected asset or "all"
  - Type filter: Selected alert type or "all"

- **ExcludedAsset**: Represents an asset that should be excluded from alert processing
  - Asset Code: The unique identifier of the asset (e.g., "SAN", "AAPL")
  - Country Code: The market/country code for the asset (e.g., "xpar", "xnas")
  - Exclusion Reason: Optional note explaining why the asset is excluded
  - Added Date: When the exclusion was added (for audit purposes)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can access the Alerts page from the main navigation within 1 click
- **SC-002**: Alerts page loads and displays all active alerts within 2 seconds
- **SC-003**: Each alert displays all required information (asset, condition, timestamp, type) in a scannable format
- **SC-004**: Alerts automatically expire and disappear from the UI exactly 7 days (168 hours) after creation
- **SC-005**: Page correctly handles zero alerts, one alert, and hundreds of alerts without breaking
- **SC-006**: 100% of alerts shown in UI match alerts sent to Slack (no missing or extra alerts)
- **SC-007**: Alert timestamps are accurate within 1 minute of actual creation time
- **SC-008**: Page is accessible on both desktop and mobile devices with responsive design
- **SC-009**: Filtering reduces displayed alerts to only matching items with zero false positives
- **SC-010**: MA50 slope sorting correctly orders alerts by slope value descending (highest slope first, e.g., +15 before +5 before -5 before -15)
- **SC-011**: Sorting by MA50 slope completes within 500ms for up to 500 alerts
- **SC-012**: Sort selection persists or resets predictably across page operations (filter changes, pagination)
- **SC-013**: Excluded assets are never processed during batch runs, reducing total processing time proportionally to the number of excluded assets
- **SC-014**: Alerts for excluded assets never appear in the UI, even if they exist in storage from before exclusion
- **SC-015**: Adding or removing an asset from the exclusion list takes effect on the next batch run (within 24 hours maximum)

### Assumptions

- Alerts are already being generated by the existing alerting system
- Alerts are stored in a persistent data store with automatic expiration (not just sent to Slack)
- Alert data structure includes: asset identifier, message/condition, timestamp, type, and TTL attribute
- The alerting system runs on a daily schedule and generates alerts continuously
- Users are authenticated and authorized to view alerts (existing auth system applies)
- Slack remains the primary notification channel (UI is supplementary)
- Alert retention is exactly 7 days with automatic deletion from storage (no user configuration needed)
- Default time zone for display is user's browser time zone
- Pagination limit of 50 alerts per page is sufficient for typical usage
- Manual page refresh is acceptable for seeing new alerts (no auto-refresh requirement)
- MA50 slope calculation logic already exists in indicator_service.py and can be reused for all alert types
- MA50 slope is calculated at alert generation time and stored with the alert (not calculated on-demand in UI)
- Assets have sufficient historical data (50+ candles) to calculate MA50 slope for most alerts
- Asset exclusion list can be stored in a configuration file, DynamoDB table, or similar persistent storage
- Exclusion list is read at the start of each batch run (no runtime updates during processing)
- Excluded assets remain in their original data sources (e.g., Saxo API, followup-stocks.json) but are filtered out during watchlist construction

## Technical Constraints

- **TC-001**: Must integrate with existing alert data source
- **TC-002**: Must respect existing authentication and authorization mechanisms
- **TC-003**: Must follow the project's frontend design system and styling
- **TC-004**: Must be accessible via standard browser navigation
- **TC-005**: Must handle concurrent access from multiple users
- **TC-006**: Alerts must automatically expire from storage after 7 days using TTL mechanism (no manual deletion required)

## Non-Functional Requirements

- **NFR-001**: Page load time must be under 2 seconds for up to 500 alerts
- **NFR-002**: Alerts must be displayed in a scannable, easy-to-read format
- **NFR-003**: UI must be responsive and work on mobile, tablet, and desktop screens
- **NFR-004**: Timestamp display must be intuitive and require minimal cognitive effort to understand
- **NFR-005**: Empty states and error states must provide clear guidance to users
- **NFR-006**: Page refresh must preserve user's current filters when possible
- **NFR-007**: Page must maintain visual consistency with existing application design
- **NFR-008**: Sort operations must be performant and not cause UI lag or freezing
- **NFR-009**: Sort dropdown must be easily accessible and clearly indicate current sort selection
