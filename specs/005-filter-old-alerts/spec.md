# Feature Specification: Filter Old Alerts (5-Day Retention)

**Feature Branch**: `005-filter-old-alerts`
**Created**: 2026-01-18
**Status**: Draft
**Type**: Amendment to existing features
**Amends**:
- [001-alerts-ui-page](../001-alerts-ui-page/spec.md)
- [002-asset-detail-alerts](../002-asset-detail-alerts/spec.md)

**Input**: User description: "update the spec for the alert-ui and alert in asset detail. I want to filter out all alerts older than 5 days, ttl from dynamodb doesn't work as I thought"

## Change Summary

This spec amends the alert retention policy in features 001 (Alerts UI Page) and 002 (Asset Detail Alerts) from **7 days to 5 days**. The original implementation relied on DynamoDB TTL for automatic cleanup, but this approach doesn't work reliably for client-side filtering within the retention window. This amendment implements client-side filtering to show only alerts from the last 5 days.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Only Recent Alerts (Priority: P1)

As a trader, I want to see only alerts from the last 5 days (instead of 7 days) so I focus on the most recent and relevant market signals for active trading decisions.

**Why this priority**: This is the core requirement - reducing alert retention from 7 days to 5 days improves signal-to-noise ratio. Since DynamoDB TTL doesn't work as expected for client-side filtering, application-level filtering ensures traders see only actionable recent signals.

**Independent Test**: Create alerts with timestamps spanning 1 to 8 days ago. Navigate to Alerts page and Asset Detail page. Verify only alerts from the last 5 days (≤120 hours old) are displayed, and alerts older than 5 days are hidden.

**Acceptance Scenarios**:

1. **Given** alerts exist from 1, 3, 5, 6, and 8 days ago, **When** I view the Alerts page, **Then** I see only alerts from 1, 3, and 5 days ago
2. **Given** an alert was created exactly 5 days ago (120 hours), **When** I view the Alerts page, **Then** that alert is visible (included in the 5-day window)
3. **Given** an alert was created 5 days and 1 hour ago, **When** I view the Alerts page, **Then** that alert is NOT visible (outside the 5-day window)
4. **Given** I am viewing an asset detail page, **When** the page loads, **Then** only alerts for that asset from the last 5 days are displayed
5. **Given** all alerts for an asset are older than 5 days, **When** I view the asset detail page, **Then** I see "No active alerts for this asset" empty state

---

### User Story 2 - Consistent Filtering Across Views (Priority: P2)

As a trader, I want the 5-day filter to apply consistently across both the Alerts page and Asset Detail page so I see the same alert retention policy everywhere.

**Why this priority**: Consistency prevents confusion. If the Alerts page shows alerts from the last 5 days but Asset Detail shows 7 days, traders will question which view is correct and lose trust in the system.

**Independent Test**: Create the same test alerts, then verify the Alerts page and multiple Asset Detail pages all filter at exactly 5 days (120 hours) with no discrepancies.

**Acceptance Scenarios**:

1. **Given** an alert is 4.5 days old, **When** I view it on both the Alerts page and Asset Detail page, **Then** it appears in both locations
2. **Given** an alert is 5.5 days old, **When** I check both the Alerts page and Asset Detail page, **Then** it does NOT appear in either location
3. **Given** alerts for multiple assets exist with varying ages, **When** I navigate between Asset Detail pages, **Then** each page correctly filters alerts to show only those ≤5 days old for that specific asset

---

### User Story 3 - Deduplicate Alerts by Type (Priority: P2)

As a trader, when multiple alerts of the same type exist for an asset, I want to see only the most recent one so I'm not overwhelmed by duplicate signals and can focus on the latest information.

**Why this priority**: Deduplication improves signal clarity. If the system generates COMBO alerts at 2 hours ago, 1 day ago, and 3 days ago for the same asset, traders only need the most recent signal to make decisions.

**Independent Test**: Create 3 COMBO alerts for asset "ITP:xpar" at different times (2 hours, 1 day, 3 days ago). View the Alerts page and Asset Detail page. Verify only the most recent COMBO alert (2 hours ago) is displayed for that asset.

**Acceptance Scenarios**:

1. **Given** 3 COMBO alerts exist for "ITP:xpar" at 2h, 1d, and 3d ago, **When** I view the Alerts page, **Then** I see only the most recent COMBO alert (2h ago)
2. **Given** 2 CONGESTION20 alerts and 1 DOUBLE_TOP alert exist for the same asset, **When** I view alerts, **Then** I see the most recent CONGESTION20 and the DOUBLE_TOP (different types, both kept)
3. **Given** alerts of type COMBO exist for different assets, **When** I view the Alerts page, **Then** each asset shows its most recent COMBO alert (deduplication is per-asset, not global)
4. **Given** on Asset Detail page for "BTCUSDT" with 2 COMBO alerts, **When** the page loads, **Then** only the newest COMBO alert for BTCUSDT is displayed

---

### Edge Cases

- What happens when all alerts are older than 5 days? (Display empty state: "No active alerts" on Alerts page, "No active alerts for this asset" on Asset Detail)
- What happens at exactly the 5-day boundary (120 hours)? (Alert is still visible at 120.0 hours, hidden at 120.1 hours)
- What happens when alerts are created in different time zones? (Use server-side UTC timestamps for age calculation, display in user's local time zone for readability)
- What happens when the system clock is incorrect? (Age calculation uses alert timestamp vs current server time, so system clock issues affect all time-based features equally)
- What happens when new alerts arrive while viewing the page? (New alerts appear on page refresh; existing alerts correctly disappear when they exceed 5 days)
- What happens when an alert is exactly at the 5-day mark during page render? (Alert is included if created_at timestamp is within 120 hours from current time)
- What happens with alerts that have missing or malformed timestamps? (Skip alerts with invalid timestamps; log error for debugging; show remaining valid alerts)
- What happens when multiple alerts of the same type have the exact same timestamp? (Keep the first one encountered in the API response; order is deterministic based on alert ID as tiebreaker)
- What happens when deduplicating alerts across different assets? (Deduplication is per-asset: each asset can have one alert per type, not globally unique)
- What happens when an alert type field is missing or null? (Treat it as a distinct "unknown" type; group all null-type alerts together and keep most recent)
- What happens if all duplicate alerts are older than 5 days? (All are filtered out by the 5-day rule first; deduplication applies to remaining alerts)

## Requirements *(mandatory)*

### Functional Requirements

**Filtering Logic:**
- **FR-001**: System MUST filter alerts to show only those created within the last 5 days (120 hours) from current time
- **FR-002**: System MUST calculate alert age as: (current_time - alert_created_at) in hours
- **FR-003**: System MUST exclude alerts where age > 120 hours from all displays
- **FR-004**: System MUST use server-side UTC timestamps for age calculation to ensure consistency
- **FR-005**: System MUST apply the 5-day filter on the client side for both Alerts page and Asset Detail page

**Alerts Page Updates:**
- **FR-006**: Alerts page MUST apply 5-day filter after fetching all alerts from the API
- **FR-007**: Alerts page MUST display empty state when no alerts exist within the 5-day window
- **FR-008**: Alerts page MUST show the total count of filtered alerts (e.g., "Showing 12 alerts from the last 5 days")

**Asset Detail Page Updates:**
- **FR-009**: Asset Detail page MUST apply 5-day filter to alerts for the current asset
- **FR-010**: Asset Detail page MUST display empty state when no alerts within 5 days exist for the asset
- **FR-011**: Asset Detail page alerts section MUST show age indicator (e.g., "2 hours ago", "4 days ago") for remaining alerts

**Deduplication Logic:**
- **FR-015**: System MUST deduplicate alerts by keeping only the most recent alert for each combination of (asset_code, country_code, alert_type)
- **FR-016**: System MUST apply deduplication AFTER the 5-day age filter (deduplicate only alerts within 5 days)
- **FR-017**: System MUST determine "most recent" by comparing created_at timestamps (newest = highest timestamp)
- **FR-018**: System MUST treat alerts with different types as distinct (COMBO vs CONGESTION20 both kept)
- **FR-019**: System MUST apply deduplication separately for each asset (each asset can have one alert per type)
- **FR-020**: System MUST handle null or missing alert types by treating them as a distinct "unknown" type group

**Data Handling:**
- **FR-021**: System MUST handle alerts with missing or invalid timestamps by excluding them from the filtered list
- **FR-022**: System MUST log warnings when alerts have invalid timestamps for debugging purposes
- **FR-023**: System MUST maintain existing sort order (newest first) after filtering and deduplication

### Key Entities

- **Alert with Age Calculation**: Represents an alert with computed age
  - Alert ID: Unique identifier
  - Asset Code: Asset symbol (e.g., "ITP", "BTCUSDT")
  - Country Code: Exchange code or null
  - Created At: ISO 8601 timestamp when alert was created
  - Age Hours: Calculated as (now - created_at) in hours
  - Is Within 5 Days: Boolean flag (age_hours <= 120)
  - Alert Type: Category (COMBO, CONGESTION20, etc.)
  - Alert Data: Type-specific data fields

- **Filter Configuration**: Represents the 5-day retention policy
  - Retention Days: 5 days
  - Retention Hours: 120 hours (5 * 24)
  - Filter Location: Client-side (both Alerts page and Asset Detail page)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of alerts older than 5 days (>120 hours) are hidden from both Alerts page and Asset Detail page
- **SC-002**: Alerts exactly at 5 days (120 hours) are displayed correctly
- **SC-003**: Filtering logic is consistent across Alerts page and Asset Detail page (same alerts visible/hidden)
- **SC-004**: Empty state displays correctly when all alerts are filtered out (no alerts ≤5 days)
- **SC-005**: Age calculation uses UTC timestamps and is accurate within 1 minute
- **SC-006**: Filtering does not increase page load time by more than 50ms (client-side operation)
- **SC-007**: Alert counts reflect filtered results (e.g., "Showing 8 alerts from the last 5 days")
- **SC-008**: Alerts with invalid timestamps are excluded without breaking the page
- **SC-009**: When multiple alerts of the same type exist for an asset, 100% of duplicates are removed (only most recent kept)
- **SC-010**: Deduplication is applied per-asset (Asset A with 2 COMBO alerts and Asset B with 2 COMBO alerts each show 1 COMBO)
- **SC-011**: Alerts of different types are NOT deduplicated (COMBO + CONGESTION20 for same asset both display)

### Assumptions

- Alerts API continues to return all alerts regardless of age (backend does not filter)
- DynamoDB TTL exists but is not reliable for application-level filtering within the 5-day window
- Client-side filtering is acceptable for performance (alerts volume is reasonable, <1000 alerts expected)
- Alert timestamps are stored in ISO 8601 format in UTC
- Frontend has access to current server time or uses browser time with acceptable accuracy
- Existing alert data structure includes a `created_at` or `timestamp` field
- No backend API changes are required (filtering happens entirely in the frontend)
- The 5-day retention policy applies to all alert types equally
- Alerts older than 5 days remain in DynamoDB but are hidden from the UI (eventual TTL cleanup can happen later)
- The change from 7 days to 5 days affects both new and existing alerts immediately upon deployment
- Multiple alerts of the same type for the same asset can exist in the API response (deduplication happens client-side)
- Alert deduplication is deterministic based on created_at timestamp (newest wins)
- Each asset can have multiple alert types simultaneously (one COMBO + one CONGESTION20, for example)

## Technical Constraints

- **TC-001**: Must work with existing alerts API that returns all alerts
- **TC-002**: Must not require backend API modifications
- **TC-003**: Must use client-side filtering in both Alerts page and Asset Detail page components
- **TC-004**: Must handle timezone differences correctly (use UTC for calculations)
- **TC-005**: Must maintain existing performance benchmarks (<2s page load)
- **TC-006**: Must not break existing filter/search functionality on Alerts page

## Non-Functional Requirements

- **NFR-001**: Filtering and deduplication operations combined must complete in under 50ms for up to 500 alerts
- **NFR-002**: Age calculation must be accurate and consistent across all page views
- **NFR-008**: Deduplication must be deterministic (same input always produces same output)
- **NFR-003**: Empty state messages must clearly indicate the 5-day retention policy
- **NFR-004**: Code changes must be localized to alert display components (minimal ripple effects)
- **NFR-005**: Filtering logic must be testable with unit tests covering edge cases
- **NFR-006**: Alert age display must remain human-readable (e.g., "2 hours ago", "4 days ago")
- **NFR-007**: Console warnings for invalid timestamps must be clear and actionable for debugging

## Changes to Original Specs

### Updates to 001-alerts-ui-page

**Modified Requirements**:
- FR-001: Change from "7 days" to "5 days" - System retrieves alerts and filters to last 5 days on client side
- FR-002: Update age calculation to filter at 120 hours (5 days) instead of 168 hours (7 days)
- SC-004: Update success criteria from "7 days (168 hours)" to "5 days (120 hours)"

**Added Requirements**:
- FR-015: System MUST apply 5-day filter (120 hours) on client side after API fetch
- FR-016: System MUST handle DynamoDB TTL separately from display filtering
- FR-024: System MUST deduplicate alerts by keeping only the most recent alert per (asset, alert_type) combination
- FR-025: System MUST apply deduplication after 5-day filtering

**Assumptions Updated**:
- Add: "DynamoDB TTL may retain alerts beyond 5 days, but client filters ensure only 5-day-old alerts display"
- Add: "Client-side filtering is acceptable for volumes under 1000 alerts"

### Updates to 002-asset-detail-alerts

**Modified Requirements**:
- FR-003: Update to calculate age and filter at 120 hours (5 days) instead of 168 hours
- SC-007: Update relative timestamps to reflect 5-day maximum ("4 days ago" instead of "6 days ago")

**Added Requirements**:
- FR-018: Asset Detail page MUST apply 5-day client-side filter after fetching alerts
- FR-019: Asset Detail page MUST exclude alerts where (now - created_at) > 120 hours
- FR-026: Asset Detail page MUST deduplicate alerts by alert_type, keeping only the most recent for each type
- FR-027: Asset Detail page MUST apply deduplication after 5-day filtering

**Assumptions Updated**:
- Update: "Alerts are automatically filtered to 5 days by client-side logic (not backend TTL)"

## Implementation Notes

- Both Alerts page (`frontend/src/pages/Alerts.tsx`) and Asset Detail page (`frontend/src/pages/AssetDetail.tsx`) need the same filtering and deduplication logic
- Consider creating shared utility functions:
  - `filterRecentAlerts(alerts, maxAgeHours = 120)` - filters by age
  - `deduplicateAlertsByType(alerts)` - keeps most recent per (asset, type) combination
  - `processAlerts(alerts)` - combines both operations in correct order (filter first, then deduplicate)
- Deduplication key should be: `${alert.asset_code}:${alert.country_code || 'null'}:${alert.alert_type}`
- DynamoDB TTL can remain at 7 days for storage cleanup; client filters at 5 days for display
- No backend API changes required - all filtering and deduplication happens in frontend
- Deduplication logic: Group alerts by (asset + type), sort by timestamp desc, take first (most recent) from each group
