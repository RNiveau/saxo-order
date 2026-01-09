# Feature Specification: Homepage Dashboard

**Feature Branch**: `511-homepage-feature` (merged)
**Created**: 2026-01-09 (retroactive documentation)
**Status**: Implemented
**Input**: Reverse-engineered from commits 08a4191, b269568, 3627e4b

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quick Market Overview (Priority: P1)

As a trader, I want to see my most important assets at a glance on the homepage so I can quickly assess market conditions without navigating through multiple pages.

**Why this priority**: Homepage is the first touchpoint - critical for daily workflow

**Independent Test**: Navigate to homepage, verify 6 tagged assets display with live prices

**Acceptance Scenarios**:

1. **Given** I have assets tagged with "homepage" in my watchlist, **When** I load the homepage, **Then** I see up to 6 assets displayed
2. **Given** assets are displayed on homepage, **When** prices update, **Then** I see current price and variation percentage
3. **Given** assets with TradingView links, **When** I click an asset, **Then** I navigate to asset detail page

---

### User Story 2 - Moving Average Indicator (Priority: P2)

As a trader, I want to see MA50 (50-period moving average) for each homepage asset so I can identify trend direction at a glance.

**Why this priority**: MA50 is a key technical indicator for trend following

**Independent Test**: Verify MA50 value displays correctly and "above/below" indicator is accurate

**Acceptance Scenarios**:

1. **Given** homepage assets, **When** I view the display, **Then** I see MA50 value and whether price is above/below MA50
2. **Given** MA50 calculation, **When** price crosses MA50, **Then** indicator updates to reflect new status

---

### Edge Cases

- What happens when user has fewer than 6 assets tagged as "homepage"? (Display all available)
- What happens when user has no assets tagged? (Empty state message)
- What happens when price data is unavailable? (Show last known price or "N/A")
- What happens when MA50 cannot be calculated? (Insufficient historical data - show "N/A")

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch watchlist items from DynamoDB
- **FR-002**: System MUST filter items by "homepage" tag
- **FR-003**: System MUST limit display to maximum 6 assets
- **FR-004**: System MUST retrieve current price and variation % for each asset
- **FR-005**: System MUST calculate MA50 indicator (daily timeframe)
- **FR-006**: System MUST determine if current price is above/below MA50
- **FR-007**: Frontend MUST display assets in grid layout
- **FR-008**: Frontend MUST support click navigation to asset detail page
- **FR-009**: System MUST support both Saxo and Binance exchanges

### Key Entities

- **HomepageItem**: Asset data for homepage display
  - `id`: Asset identifier
  - `asset_symbol`: Ticker symbol
  - `description`: Asset name
  - `current_price`: Latest price
  - `variation_pct`: % change
  - `currency`: Price currency
  - `tradingview_url`: Chart link (optional)
  - `exchange`: "saxo" or "binance"
  - `ma50_value`: 50-period moving average
  - `is_above_ma50`: Boolean trend indicator

- **WatchlistTag**: Enum for categorization
  - `HOMEPAGE`: Tag for homepage display

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Homepage loads within 2 seconds with all asset data
- **SC-002**: MA50 calculation accurate compared to external sources (TradingView)
- **SC-003**: Price updates reflect real-time data (within exchange API refresh rate)
- **SC-004**: Users can navigate to asset detail page in single click
- **SC-005**: Homepage displays correctly on both desktop and mobile viewports
