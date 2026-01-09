# Feature Specification: Binance Order Reporting

**Feature Branch**: `471-binance-reporting` (merged)
**Created**: 2026-01-09 (retroactive documentation)
**Status**: Implemented
**Input**: Reverse-engineered from commits 28f9161, 644b19b and implementation summary

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Order Reporting Interface (Priority: P1)

As a trader using both Saxo Bank and Binance, I want to view my Binance orders in the same report interface as my Saxo orders so I can have a unified view of my trading activity across all platforms.

**Why this priority**: Traders using multiple platforms need consistent interfaces to reduce cognitive overhead and enable cross-platform analysis.

**Independent Test**: Select "Binance" from account dropdown, verify orders display with same format as Saxo orders.

**Acceptance Scenarios**:

1. **Given** I have Binance trading history, **When** I select "Binance" from the report account dropdown, **Then** I see my Binance orders listed
2. **Given** Binance orders in USD, **When** I view the report, **Then** I see prices converted to EUR at configured exchange rate
3. **Given** both Saxo and Binance accounts, **When** I switch between accounts, **Then** I see different order histories without page reload

---

### User Story 2 - Google Sheets Position Tracking (Priority: P2)

As a trader, I want to save my Binance positions to Google Sheets with stop-loss and target objectives so I can track my risk management across all platforms in one place.

**Why this priority**: Unified position tracking enables consistent risk management regardless of platform.

**Independent Test**: Create a Binance position in Google Sheets, verify it appears with same format as Saxo positions.

**Acceptance Scenarios**:

1. **Given** a Binance order in the report, **When** I click "Manage" and enter stop/objective, **Then** a new row is created in Google Sheets
2. **Given** an open Binance position in Google Sheets, **When** I update stop-loss or objective, **Then** the Google Sheets row updates
3. **Given** a closed Binance position, **When** I mark it as closed, **Then** Google Sheets reflects closure status

---

### User Story 3 - CLI Consistency (Priority: P3)

As a power user, I want the CLI command `k-order binance get-report` to continue working unchanged so my existing scripts and workflows don't break.

**Why this priority**: Backwards compatibility ensures existing automation remains functional.

**Independent Test**: Run CLI command, verify it produces same output format as before.

**Acceptance Scenarios**:

1. **Given** existing CLI usage, **When** I run `k-order binance get-report --from-date 2024/01/01`, **Then** I see Binance orders as before
2. **Given** CLI with `--update-gsheet` flag, **When** I run the command, **Then** orders are saved to Google Sheets as before
3. **Given** interactive CLI prompts, **When** I run the command, **Then** I can still enter stop/objective interactively

---

### Edge Cases

- What happens when Binance API is unavailable? (Return cached orders if within 5-min TTL, otherwise error)
- What happens when currency conversion rate is missing? (Fall back to default rate from config)
- What happens when Google Sheets write fails? (Return error, don't corrupt data)
- What happens when no orders exist for date range? (Return empty list with appropriate message)
- What happens when account_id doesn't match "binance_" prefix? (Route to Saxo service)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch Binance orders from Binance API for given date range
- **FR-002**: System MUST convert USD prices to EUR using configured exchange rate
- **FR-003**: System MUST cache Binance orders for 5 minutes to reduce API calls
- **FR-004**: System MUST support "binance_main" account ID in all report endpoints
- **FR-005**: System MUST route requests to BinanceReportService when account_id starts with "binance_"
- **FR-006**: System MUST route requests to SaxoReportService for all other account IDs
- **FR-007**: System MUST create Binance positions in Google Sheets with strategy/signal validation
- **FR-008**: System MUST update Binance positions in Google Sheets (stop, objective, closure status)
- **FR-009**: System MUST display Binance account in account selector dropdown
- **FR-010**: System MUST use BinanceReportService in CLI (no code duplication)
- **FR-011**: System MUST preserve CLI interactive prompts for backwards compatibility
- **FR-012**: System MUST calculate aggregated summary statistics (total orders, buy/sell volume)

### Key Entities

- **BinanceReportService**: Service layer for Binance order operations
  - `get_orders_report(account_id, from_date)`: Fetch orders with caching
  - `convert_order_to_eur(order)`: Currency conversion
  - `calculate_summary(orders)`: Aggregate statistics
  - `create_gsheet_order(...)`: Create position in Google Sheets
  - `update_gsheet_order(...)`: Update position in Google Sheets

- **ReportOrder**: Unified order model (shared between Saxo and Binance)
  - `code`: Asset symbol
  - `name`: Asset description
  - `date`: Order execution date
  - `direction`: BUY or SELL
  - `quantity`: Order size
  - `price`: Execution price (original currency)
  - `price_eur`: Execution price (EUR converted)
  - `total`: Total value (original currency)
  - `total_eur`: Total value (EUR converted)
  - `currency`: Original currency (USD for Binance)

- **Account Routing**: Prefix-based service selection
  - `binance_*`: Route to BinanceReportService
  - All others: Route to SaxoReportService

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Binance orders load within 2 seconds on first request, <500ms on cached requests
- **SC-002**: Currency conversion accuracy matches configured exchange rate (±0.01 EUR)
- **SC-003**: Google Sheets integration has 100% success rate (no data corruption)
- **SC-004**: CLI continues to work with zero breaking changes for existing users
- **SC-005**: Frontend requires zero code changes (validates generic design)
- **SC-006**: Code reuse achieves 80%+ (avoid duplication between Saxo and Binance services)
- **SC-007**: Unit test coverage 100% for BinanceReportService (all methods tested)
- **SC-008**: All 12 unit tests pass with 100% success rate

## Technical Constraints

- **TC-001**: CLI must remain the source of truth (no duplicate logic in API)
- **TC-002**: Binance account must appear in same UI section as Saxo accounts (no separate view)
- **TC-003**: Same Google Sheets structure for both platforms (unified position tracking)
- **TC-004**: Service layer extraction required (eliminate CLI code duplication)
