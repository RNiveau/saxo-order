# Feature Specification: Order Creation API

**Feature Branch**: `409-order-creation-api` (merged)
**Created**: 2026-01-09 (retroactive documentation)
**Status**: Implemented
**Input**: Reverse-engineered from commits 3b34c57, 48f45a1, 3720471, cd1ccee and plan file

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Programmatic Order Placement (Priority: P1)

As a developer building trading automation, I want to place orders via REST API so I can integrate saxo-order capabilities into my applications without using the CLI.

**Why this priority**: API enables automation, integration with other systems, and building custom UIs - critical for extensibility.

**Independent Test**: Send POST request to API endpoint, verify order is placed and logged identically to CLI.

**Acceptance Scenarios**:

1. **Given** valid order parameters, **When** I POST to `/api/orders`, **Then** order is placed and I receive success response with order ID
2. **Given** invalid parameters (insufficient funds), **When** I POST to API, **Then** I receive HTTP 400 with clear error message
3. **Given** API and CLI with same inputs, **When** both place orders, **Then** both produce identical validation and results

---

### User Story 2 - Web-Based Order Interface (Priority: P2)

As a trader, I want to create orders through a web interface so I can place trades without using the command line, with dropdown selectors for accounts, strategies, and signals.

**Why this priority**: Web UI improves accessibility and reduces errors through guided forms and validation.

**Independent Test**: Open Orders page, fill form, submit order, verify Google Sheets and Slack logging.

**Acceptance Scenarios**:

1. **Given** Orders page loaded, **When** I select account and fill order details, **Then** form validates inputs in real-time
2. **Given** valid order form, **When** I click "Place Order", **Then** order is submitted and success message displays
3. **Given** order placement, **When** I check Google Sheets, **Then** new row appears with order details
4. **Given** BUY order placement, **When** order succeeds, **Then** Slack notification appears in #execution-logs

---

### User Story 3 - Advanced Order Types (Priority: P2)

As a trader, I want to create OCO (One-Cancels-Other) and Stop-Limit orders via API and web UI so I can implement sophisticated risk management strategies.

**Why this priority**: Advanced order types enable professional trading strategies beyond simple limit/market orders.

**Independent Test**: Create OCO order with both limit and stop prices, verify both legs are placed correctly.

**Acceptance Scenarios**:

1. **Given** OCO order parameters, **When** I POST to `/api/orders/oco`, **Then** two linked orders are created
2. **Given** Stop-Limit parameters, **When** I POST to `/api/orders/stop-limit`, **Then** stop-limit order is created
3. **Given** web UI order type selector, **When** I switch between types, **Then** form adapts to show relevant fields

---

### User Story 4 - CLI Consistency (Priority: P3)

As a CLI power user, I want existing `k-order set` commands to continue working unchanged so my scripts don't break.

**Why this priority**: Backwards compatibility ensures existing workflows remain functional.

**Independent Test**: Run CLI command, verify it uses new OrderService internally but maintains same behavior.

**Acceptance Scenarios**:

1. **Given** existing CLI workflow, **When** I run `k-order set order`, **Then** interactive prompts work as before
2. **Given** CLI with automation flags, **When** I run with `--code --price` flags, **Then** order places without prompts
3. **Given** CLI and API, **When** both create orders, **Then** both use same validation logic (OrderService)

---

### Edge Cases

- What happens when Saxo API is unavailable? (Return 503 Service Unavailable with retry guidance)
- What happens when validation fails (insufficient funds)? (Return 400 with human-readable error)
- What happens when Google Sheets write fails? (Order still places, log error, don't block user)
- What happens when Slack notification fails? (Order still places, log error silently)
- What happens when asset code not found? (Return 400 "Asset not found")
- What happens when account selection invalid? (Return 400 "Invalid account")
- What happens with missing required fields? (Pydantic validation returns 422 with field details)
- What happens when price/quantity are negative? (Pydantic validation rejects with clear error)

## Requirements *(mandatory)*

### Functional Requirements

**Backend Requirements:**
- **FR-001**: System MUST create OrderService to share business logic between CLI and API
- **FR-002**: System MUST provide POST /api/orders endpoint for regular orders (limit, stop, market, open_stop)
- **FR-003**: System MUST provide POST /api/orders/oco endpoint for OCO orders
- **FR-004**: System MUST provide POST /api/orders/stop-limit endpoint for stop-limit orders
- **FR-005**: System MUST validate requests with Pydantic models (same validation as CLI)
- **FR-006**: System MUST return HTTP 400 for validation errors with human-readable JSON messages
- **FR-007**: System MUST refactor CLI commands to use OrderService (no code duplication)
- **FR-008**: System MUST maintain CLI backwards compatibility (same commands, same behavior)
- **FR-009**: System MUST log BUY orders to Google Sheets (same as CLI)
- **FR-010**: System MUST send Slack notifications for BUY orders (same as CLI)

**Frontend Requirements:**
- **FR-011**: System MUST provide Orders page accessible from sidebar navigation
- **FR-012**: System MUST display order type selector (regular, OCO, stop-limit)
- **FR-013**: System MUST load account list from `/api/fund/accounts`
- **FR-014**: System MUST load strategy/signal enums from `/api/report/config`
- **FR-015**: System MUST validate form inputs before submission
- **FR-016**: System MUST display success/error messages after order placement
- **FR-017**: System MUST support URL prefilling from asset detail page (issue #513 integration)
- **FR-018**: System MUST match dark theme styling of existing application

**Integration Requirements:**
- **FR-019**: System MUST integrate with SaxoClient for order placement
- **FR-020**: System MUST integrate with GSheetClient for logging
- **FR-021**: System MUST integrate with Slack WebClient for notifications
- **FR-022**: System MUST apply same validation rules as CLI (apply_rules, validate_ratio, calculate_taxes)

### Key Entities

- **OrderService**: Shared business logic layer
  - `create_order(...)`: Place regular order
  - `create_oco_order(...)`: Place OCO order
  - `create_stop_limit_order(...)`: Place stop-limit order
  - `_get_account(account_key)`: Resolve account
  - `_validate_ratio(...)`: Validate order size
  - `_apply_rules(...)`: Apply trading rules

- **Pydantic Models** (`api/models/order.py`):
  - `OrderRequest`: Regular order parameters
  - `OcoOrderRequest`: OCO order parameters
  - `StopLimitOrderRequest`: Stop-limit parameters
  - `OrderResponse`: Success/error response

- **React Component** (`frontend/src/pages/Orders.tsx`):
  - State: orderType, forms (regular/oco/stop-limit), loading, error, success
  - Methods: loadAccounts(), loadConfig(), handleSubmit()
  - UI: Three form types with account/strategy/signal dropdowns

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: API uses identical code as CLI (100% shared via OrderService)
- **SC-002**: API accepts same inputs as CLI (validated by Pydantic matching Click types)
- **SC-003**: API uses same validation as CLI (shared apply_rules, validate_ratio functions)
- **SC-004**: Validation errors return HTTP 400 with human-readable messages (not technical stack traces)
- **SC-005**: CLI backwards compatibility maintained (zero breaking changes for existing users)
- **SC-006**: Test coverage 100% for OrderService (11 tests covering all methods)
- **SC-007**: Test coverage 100% for API endpoints (11 tests covering success/error cases)
- **SC-008**: All 22 tests pass with 100% success rate
- **SC-009**: Orders page loads within 2 seconds
- **SC-010**: Form submission completes within 3 seconds (includes Saxo API call)
- **SC-011**: Google Sheets logging success rate >95% (failures don't block order placement)
- **SC-012**: Frontend form validation prevents invalid submissions (client-side validation)

## Technical Constraints

- **TC-001**: API must use same code as CLI (no duplication, shared OrderService)
- **TC-002**: API must accept same inputs as CLI (parameter name/type matching)
- **TC-003**: API must use same validation as CLI (shared validation functions)
- **TC-004**: HTTP 400 for validation errors with clear JSON messages (not 500 with stack traces)
- **TC-005**: CLI commands maintain backwards compatibility (same arguments, same prompts)
- **TC-006**: Service layer extraction required (business logic separate from CLI interaction)
- **TC-007**: Google Sheets and Slack logging must mirror CLI behavior exactly
- **TC-008**: Frontend uses Strategy/Signal enums from backend (no hardcoding)

## Non-Functional Requirements

- **NFR-001**: API response time <3 seconds for order placement
- **NFR-002**: Frontend form validation provides immediate feedback (<100ms)
- **NFR-003**: Logging failures (Google Sheets, Slack) must not block order placement
- **NFR-004**: Error messages must be user-friendly (not technical exceptions)
- **NFR-005**: Frontend supports URL query parameters for prefilling (asset detail integration)
- **NFR-006**: Dark theme styling matches existing application design system
