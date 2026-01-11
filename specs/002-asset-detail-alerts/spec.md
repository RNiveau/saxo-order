# Feature Specification: Asset Detail Alerts Display

**Feature Branch**: `002-asset-detail-alerts`
**Created**: 2026-01-11
**Status**: Draft
**Input**: User description: "I want to add the alerts in the asset detail view"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Alerts for Current Asset (Priority: P1)

As a trader viewing an asset's detail page, I want to see all active alerts for that specific asset so I can understand recent market signals without navigating to a separate alerts page.

**Why this priority**: This is the core value proposition - contextual alert display where traders are already analyzing an asset. Alerts become actionable when shown alongside indicators and workflows.

**Independent Test**: Navigate to any asset detail page (e.g., /asset/ITP:xpar) and verify that all alerts for that specific asset from the last 7 days are displayed in a dedicated section.

**Acceptance Scenarios**:

1. **Given** I am on the asset detail page for "ITP:xpar", **When** 3 alerts exist for this asset, **Then** I see all 3 alerts displayed in an "Alerts" section below the indicators
2. **Given** I am on the asset detail page for "BTCUSDT", **When** 2 alerts exist for this asset, **Then** I see both alerts displayed correctly
3. **Given** I am on the asset detail page for an asset with no alerts, **When** the page loads, **Then** I see an "Alerts" section with a message "No active alerts for this asset"
4. **Given** alerts for the current asset include different types (combo, congestion20, double_top), **When** I view the alerts section, **Then** each alert displays its type, timestamp, and alert-specific data in a readable format

---

### User Story 2 - Understand Alert Context (Priority: P2)

As a trader, I want to see alert details including timestamp and alert type so I can assess how recent and relevant each signal is for my trading decisions.

**Why this priority**: Alert context (age, type, details) is critical for making informed decisions. A 6-day-old congestion alert has different implications than a 2-hour-old combo signal.

**Independent Test**: View an asset with multiple alerts and verify each alert card shows: alert type, relative time (e.g., "2 hours ago"), absolute timestamp on hover, and alert-specific data fields formatted appropriately.

**Acceptance Scenarios**:

1. **Given** an alert was created 2 hours ago, **When** I view it on the asset detail page, **Then** I see "2 hours ago" displayed prominently
2. **Given** an alert shows "2 hours ago", **When** I hover over the timestamp, **Then** I see the absolute timestamp in ISO format (e.g., "2026-01-11T16:30:00")
3. **Given** a COMBO alert exists, **When** I view it, **Then** I see the alert type badge "COMBO" and key data fields (price, direction, strength)
4. **Given** a CONGESTION20 alert exists, **When** I view it, **Then** I see the alert type badge "CONGESTION20" and touch points data
5. **Given** multiple alerts of different types exist, **When** viewing them, **Then** each alert is visually distinct with type-specific badges and color coding

---

### User Story 3 - Navigate from Alert to Context (Priority: P3)

As a trader, I want alerts to be displayed near relevant indicators and workflows so I can correlate signals with technical analysis without scrolling or switching pages.

**Why this priority**: Improves workflow efficiency by keeping related information together. Traders can make faster decisions when alerts, indicators, and workflows are in the same viewport.

**Independent Test**: Navigate to an asset detail page with alerts, indicators, and workflows. Verify alerts section is positioned logically within the page layout and doesn't require excessive scrolling to correlate with indicators.

**Acceptance Scenarios**:

1. **Given** I am on an asset detail page, **When** the page loads, **Then** the alerts section appears between the indicators section and the workflows section
2. **Given** I am viewing daily/weekly indicators, **When** I scroll down to alerts, **Then** the alerts section is within one screen height of the indicators
3. **Given** I want to analyze a combo alert signal, **When** I look at the indicators above, **Then** I can correlate the alert price with current price and indicator values without losing context

---

### Edge Cases

- What happens when no alerts exist for the current asset? (Display empty state message: "No active alerts for this asset")
- What happens when the alerts API is unavailable? (Display error message: "Unable to load alerts. Please try refreshing the page.")
- What happens when an asset has no country_code? (Display alert normally, handle filtering with null or empty string country_code)
- What happens when alert data contains unexpected fields? (Display core fields (type, timestamp) and render additional data as JSON in expandable details)
- What happens when multiple alerts have the same timestamp? (Sort by alert type alphabetically as secondary sort)
- What happens when an alert's data field is empty or malformed? (Display alert with type and timestamp, show placeholder "No details available" for data section)
- What happens when viewing on mobile devices? (Alerts stack vertically with responsive card layout, touch-friendly interactions)

## Requirements *(mandatory)*

### Functional Requirements

**Data Retrieval:**
- **FR-001**: System MUST fetch alerts filtered by the current asset's code and country_code when the asset detail page loads
- **FR-002**: System MUST handle assets both with and without country_code when filtering alerts
- **FR-003**: System MUST calculate alert age in hours for display purposes based on alert creation timestamp
- **FR-004**: System MUST sort alerts by creation timestamp in descending order (newest first)

**Display Requirements:**
- **FR-005**: System MUST display alerts in a dedicated "Alerts" section on the asset detail page
- **FR-006**: System MUST show for each alert: alert type badge, relative timestamp (e.g., "2 hours ago"), and alert-specific data
- **FR-007**: System MUST provide absolute timestamp on hover or tap for each alert
- **FR-008**: System MUST format alert type as a readable badge (e.g., "COMBO", "CONGESTION20", "DOUBLE TOP")
- **FR-009**: System MUST render alert-specific data fields based on alert type (price/direction/strength for COMBO, touch points for CONGESTION, OHLC for candle patterns)
- **FR-010**: System MUST handle empty state when no alerts exist for the current asset
- **FR-011**: System MUST display error state when alerts cannot be loaded

**Layout Requirements:**
- **FR-012**: System MUST position the alerts section between the indicators section and the workflows section on the asset detail page
- **FR-013**: System MUST use a responsive layout that works on desktop, tablet, and mobile screens
- **FR-014**: System MUST limit the alerts section height to show the 3 most recent alerts, with an option to expand and see all if more than 3 exist

**Integration Requirements:**
- **FR-015**: System MUST use the existing alertService.getAll() API with asset_code and country_code filters
- **FR-016**: System MUST extract asset_code and country_code from the current asset symbol (e.g., "ITP:xpar" → code="ITP", country_code="xpar")
- **FR-017**: System MUST handle the case where country_code is empty string or null for any asset

### Key Entities

- **Alert Display Item**: Represents a single alert shown on the asset detail page
  - Alert Type: Category of alert (COMBO, CONGESTION20, DOUBLE_TOP, etc.)
  - Asset Code: The asset symbol (e.g., "ITP", "BTCUSDT")
  - Country Code: Exchange code (e.g., "xpar") or null when not applicable
  - Timestamp: When the alert was created (ISO 8601 format)
  - Age: Hours since alert creation (calculated for display)
  - Data: Alert-specific fields that vary by type (price/direction for COMBO, touch points for CONGESTION, etc.)

- **Alert Section State**: Represents the UI state of the alerts section
  - Loading: Whether alerts are being fetched
  - Error: Error message if fetch fails
  - Alerts: List of alert items for the current asset
  - Expanded: Whether the section shows all alerts or just the top 3

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Alerts for the current asset load and display within 1 second of page load
- **SC-002**: Each alert displays all required information (type badge, relative time, key data fields) in a scannable card format
- **SC-003**: Alerts section appears within one screen height (900px) of the indicators section on desktop
- **SC-004**: 100% of alerts shown match the current asset being viewed (no alerts from other assets)
- **SC-005**: Empty state displays correctly when asset has no alerts
- **SC-006**: Error state displays with actionable message when alerts cannot be loaded
- **SC-007**: Relative timestamps update correctly (e.g., "2 hours ago" vs "3 days ago") based on actual alert age
- **SC-008**: Alert section is fully responsive and usable on mobile devices (screens 375px and wider)
- **SC-009**: Users can view up to 50 alerts for an asset without performance degradation (scroll, not pagination)
- **SC-010**: Hover/tap on timestamp reveals absolute time within 100ms

### Assumptions

- Alerts API endpoint `/api/alerts` already exists and supports `asset_code` and `country_code` query parameters
- Alert data structure matches the AlertItem interface defined in frontend/src/services/api.ts
- alertService.getAll() function exists and is working correctly
- Asset detail page already loads asset symbol from URL parameters (/:symbol route parameter)
- Asset symbols follow the format "CODE:COUNTRY" for assets with country code and "SYMBOL" for assets without country code
- Alerts are automatically filtered to 7 days by the backend (TTL mechanism)
- Users are authenticated and authorized to view alerts (existing auth applies)
- Alert types have consistent enum values between backend and frontend
- The AssetDetail.tsx page already has patterns for displaying sections (indicators, workflows)
- CSS styling patterns exist in AssetDetail.css that can be extended for alerts

## Technical Constraints

- **TC-001**: Must integrate with existing alertService API client
- **TC-002**: Must use the same authentication mechanism as other asset detail sections
- **TC-003**: Must follow the existing AssetDetail page layout and styling patterns
- **TC-004**: Must handle asset identifier formats both with and without country code consistently
- **TC-005**: Must not block or delay the loading of indicators or workflows sections
- **TC-006**: Must respect existing asset detail page performance budget (<2s total page load)

## Non-Functional Requirements

- **NFR-001**: Alerts section load time must not increase total asset detail page load time by more than 500ms
- **NFR-002**: Alerts must be displayed in a scannable format that requires minimal cognitive effort
- **NFR-003**: UI must maintain visual consistency with existing indicators and workflows sections
- **NFR-004**: Timestamp display must be intuitive (relative time for recent alerts, absolute time on hover)
- **NFR-005**: Empty states and error states must provide clear, actionable guidance
- **NFR-006**: Alert cards must be touch-friendly on mobile (minimum 44px touch targets)
- **NFR-007**: Alert type badges must use distinct colors for quick visual identification
- **NFR-008**: Page must remain fully functional if alerts API fails (alerts section shows error, rest of page works)
