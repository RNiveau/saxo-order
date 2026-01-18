# Feature Specification: Long-Term Positions Menu

**Feature Branch**: `004-watchlist-menu`
**Created**: 2026-01-18
**Status**: Draft
**Input**: User description: "I want a new menu to access directly to long term position saved in the watchlist"

## Clarifications

### Session 2026-01-18

- Q: When an asset in the long-term menu has no current price data (due to delisting, API outage, or market closure), how should the menu display it? → A: Show the asset with last known price and a "stale data" warning indicator
- Q: How should crypto assets (those with both "crypto" and "long-term" tags) be displayed in the long-term menu? → A: Show a "Crypto" badge or icon next to the asset name but keep in main list
- Q: When a user has 50+ long-term positions, how should the menu handle the large dataset? → A: Single scrollable list with all items loaded (no pagination)
- Q: When an asset has been in the watchlist for months but its "added_at" timestamp is missing or invalid, how should the system handle it? → A: Display the asset but show "Unknown" or "N/A" for the added date

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Long-Term Holdings at a Glance (Priority: P1)

As a portfolio manager, I want a dedicated menu to view only my long-term positions so that I can quickly monitor my strategic holdings without seeing short-term or untagged watchlist items.

**Why this priority**: This is the core value proposition and MVP - traders need quick access to segregated long-term positions for portfolio reviews. Currently, they must use the "All Watchlist" view and mentally filter, or rely on frontend tag filters which aren't persistent.

**Independent Test**: Can be fully tested by tagging 3 assets with "long-term" label, accessing the new menu, and verifying only those 3 assets appear with current prices and daily variation.

**Acceptance Scenarios**:

1. **Given** I have 5 assets in my watchlist (2 tagged "long-term", 2 tagged "short-term", 1 untagged), **When** I access the long-term positions menu, **Then** I see exactly 2 assets with current prices and variation percentages
2. **Given** I have no assets tagged as "long-term", **When** I access the menu, **Then** I see an empty state message indicating no long-term positions are saved
3. **Given** I have 1 asset tagged with both "long-term" and "short-term", **When** I access the menu, **Then** that asset appears in the long-term view (long-term classification takes precedence)

---

### User Story 2 - Remove or Reclassify Positions Inline (Priority: P2)

As a portfolio manager, I want to remove the "long-term" tag or delete positions entirely from the long-term menu so that I can manage position classifications without switching contexts.

**Why this priority**: Convenience feature for maintenance workflows. Users can currently manage tags via the All Watchlist view, so this is a nice-to-have for dedicated long-term portfolio management.

**Independent Test**: Can be tested by accessing the menu with existing long-term positions, removing the "long-term" tag from one asset, and verifying it disappears from the menu but remains in the All Watchlist view.

**Acceptance Scenarios**:

1. **Given** I have an asset tagged "long-term", **When** I select "Remove from Long-Term" in the menu, **Then** the "long-term" tag is removed and the asset disappears from the menu but remains in my full watchlist
2. **Given** I have an asset tagged both "long-term" and "homepage", **When** I remove the "long-term" tag, **Then** the asset retains the "homepage" tag and disappears from the long-term menu
3. **Given** I have an asset I want to permanently delete, **When** I select "Delete Asset", **Then** the asset is removed from the entire watchlist system (all views)

---

### Edge Cases

- When an asset has missing price data (delisted stock, API outage), the system displays the last known price with a visible "stale data" warning indicator to alert users the data may be outdated
- Crypto assets with both "crypto" and "long-term" tags display in the main alphabetical list with a visual "Crypto" badge or icon to distinguish them from traditional securities
- For large datasets (50+ positions), the menu displays all items in a single scrollable list without pagination to enable quick scanning of the entire portfolio
- Assets from both Saxo Bank and Binance exchanges display together in the unified alphabetical list, distinguishable by their exchange metadata
- Assets with missing or invalid "added_at" timestamps display normally in the menu but show "Unknown" or "N/A" for the addition date field to maintain data integrity

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST filter watchlist items to show only those with the "long-term" label in their tags
- **FR-002**: System MUST display each long-term position with current price, daily variation percentage, asset symbol, description, and currency
- **FR-003**: System MUST update prices and variations for long-term positions at the same refresh rate as the main watchlist (every 60 seconds when market is open)
- **FR-004**: System MUST allow users to remove the "long-term" tag from an asset without deleting the asset from the full watchlist
- **FR-005**: System MUST allow users to permanently delete an asset from the entire watchlist system
- **FR-006**: System MUST sort long-term positions alphabetically by asset symbol for consistent display
- **FR-007**: System MUST show an appropriate empty state when no positions are tagged as "long-term"
- **FR-008**: System MUST display both Saxo Bank and Binance assets if they have the "long-term" tag
- **FR-009**: System MUST preserve all other existing tags (e.g., "homepage", "crypto") when modifying the "long-term" tag
- **FR-010**: System MUST display assets with unavailable price data using the last known price with a visible warning indicator (e.g., icon, color, or text label) to inform users the data may be stale
- **FR-011**: System MUST display a "Crypto" badge or icon next to assets that have both "crypto" and "long-term" tags while maintaining their position in the main alphabetical list
- **FR-012**: System MUST render all long-term positions in a single scrollable list without pagination, regardless of the number of items
- **FR-013**: System MUST display assets with missing or invalid "added_at" timestamps in the menu but show "Unknown" or "N/A" for the addition date field

### Key Entities

- **Long-Term Position**: A watchlist item with the "long-term" label, including asset identifier, symbol, description, current price, daily variation, currency, exchange type (Saxo/Binance), and timestamp of addition
- **Watchlist Tag**: A classification label that can be applied to positions, with "long-term" being one of several predefined values (others include "short-term", "crypto", "homepage")

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can access long-term positions within 2 clicks from the main navigation
- **SC-002**: Long-term positions menu displays up-to-date prices within 60 seconds of market data changes
- **SC-003**: 100% of assets tagged "long-term" appear in the dedicated menu (no filtering errors)
- **SC-004**: Tag modifications (remove "long-term") reflect in the menu within 2 seconds without page refresh
- **SC-005**: Menu supports displaying at least 100 long-term positions without performance degradation (load time under 3 seconds)
