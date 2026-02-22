# Feature Specification: Workflow Order History Tracking

**Feature Branch**: `010-workflow-execution-tracking`
**Created**: 2026-02-22
**Status**: Draft
**Input**: User description: "Track when workflows place orders in DynamoDB with 7-day TTL to provide order history and monitoring capabilities in the UI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Workflow Order History (Priority: P1)

As a trader, I need to see when a workflow last placed an order so that I can verify my automated strategies are working and review recent trading activity.

**Why this priority**: This is the core value of the feature - users need visibility into what orders their workflows are actually placing. Currently, there's no way to see a workflow's order history without manually checking all orders.

**Independent Test**: Can be fully tested by triggering a workflow that places an order, then viewing the workflow detail page in the UI and verifying the order record appears with correct timestamp and details.

**Acceptance Scenarios**:

1. **Given** a workflow has placed 3 orders in the past day, **When** I view the workflow detail page, **Then** I see 3 order records with timestamps, prices, quantities, and directions
2. **Given** a workflow has not placed any orders in the past 7 days, **When** I view the workflow detail page, **Then** I see "No orders placed" or an empty order history
3. **Given** I am viewing order history for a workflow, **When** the orders are displayed, **Then** they are sorted by most recent first

---

### User Story 2 - Identify Active Workflows (Priority: P2)

As an operations user, I need to see when each workflow last placed an order so that I can identify which workflows are actively trading.

**Why this priority**: Helps users understand which of their workflows are producing results versus sitting idle. Less urgent than viewing individual order history but valuable for portfolio management.

**Independent Test**: Can be fully tested by having multiple workflows with different order histories, then viewing the workflows list page and verifying last order timestamps are displayed correctly for each.

**Acceptance Scenarios**:

1. **Given** I have 10 workflows with varying order histories, **When** I view the workflows list page, **Then** I see the last order timestamp for each workflow that has placed orders
2. **Given** a workflow placed an order 2 days ago, **When** I view the workflows list, **Then** I see "Last order: 2 days ago" for that workflow
3. **Given** a workflow has never placed an order, **When** I view the workflows list, **Then** I see "No orders yet" for that workflow

---

### Edge Cases

- What happens when an order record fails to save to DynamoDB (e.g., network error, throttling)?
- How does the system handle viewing order history for a workflow that has been deleted or disabled?
- What happens when TTL expires for order records while a user is viewing them in the UI?
- How does the system behave when DynamoDB is unavailable during order placement?
- What happens if order history is queried for a workflow that has never placed an order?
- How does the system handle duplicate order records (if the same order is recorded multiple times due to retries)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST record an order event every time a workflow successfully places an order, whether via Lambda scheduled execution or CLI invocation
- **FR-002**: System MUST store order metadata including: workflow_id (UUID), order placement timestamp, order price, quantity, direction (buy/sell), order type (LIMIT/OPEN_STOP), and asset details
- **FR-003**: System MUST automatically delete order records after 7 days using DynamoDB Time-To-Live (TTL) feature
- **FR-004**: System MUST provide API endpoint to retrieve order history for a specific workflow with pagination support
- **FR-005**: System MUST provide API endpoint to retrieve order details for a single order event
- **FR-006**: Users MUST be able to view workflow order history in the UI workflow detail page
- **FR-007**: Users MUST be able to see the most recent order timestamp in the workflows list view
- **FR-008**: System MUST handle DynamoDB write failures gracefully without disrupting order placement (order tracking should not block the actual order submission)
- **FR-009**: System MUST link order records to the workflow using the workflow UUID to maintain referential integrity
- **FR-010**: System MUST record only successful order placements, not failed attempts or conditions-not-met scenarios

### Key Entities

- **WorkflowOrder**: Represents a single order placed by a workflow
  - Unique identifier (order_id)
  - Reference to workflow (workflow_id UUID)
  - Order placement timestamp (placed_at)
  - Order price
  - Quantity
  - Direction (buy/sell)
  - Order type (LIMIT/OPEN_STOP)
  - Asset details (code, CFD, index)
  - Execution context (Lambda event ID, CLI user, trigger source)
  - TTL expiration timestamp (7 days from placement)

- **WorkflowOrderSummary**: Aggregated order statistics for a workflow
  - Workflow identifier
  - Total order count (last 7 days)
  - Last order timestamp
  - Last order price and direction

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view the complete order history (up to 7 days) for any workflow within 2 seconds of requesting it
- **SC-002**: System successfully records 100% of workflow order placements without disrupting the actual order submission
- **SC-003**: Order records are automatically deleted 7 days after creation with no manual intervention required
- **SC-004**: Users can determine when a workflow last placed an order by viewing the workflows list page
- **SC-005**: System handles DynamoDB unavailability gracefully - order placement continues even if tracking fails
- **SC-006**: Workflows list page displays last order timestamp for all workflows without performance degradation (< 1 second load time)
- **SC-007**: Users can review a workflow's recent trading activity (past 7 days) in under 10 seconds

## Assumptions

- Order history is only needed for the past 7 days; older order data provides diminishing value
- Users primarily need order tracking to monitor automated trading activity, not for compliance or long-term audit trails
- DynamoDB is the appropriate storage solution given existing infrastructure and 7-day TTL requirement
- Order tracking failures should not prevent the actual order from being placed
- The existing workflow UI (recently added in commit c896c7d) will be extended to display order history
- Order records will use the same DynamoDB table access patterns as the existing workflow management system
- Average order record size will be under 2KB (order details + metadata)
- Peak order volume will not exceed DynamoDB's default capacity limits (no need for reserved capacity)
- Users do not need to track failed executions or conditions-not-met scenarios - only successful order placements matter

## Dependencies

- Existing workflow engine (engines/workflow_engine.py) must be modified to record order placement events
- Existing DynamoDB infrastructure (already in use for workflows table)
- Existing workflow UI (frontend/src/pages/Workflows.tsx and related components)
- Existing API layer (api/routers/workflow.py) will need new endpoints for order history
- Lambda execution environment must have DynamoDB write permissions for the new workflow_orders table

## Out of Scope

- Long-term order analytics or reporting beyond 7 days (future enhancement)
- Real-time order monitoring or streaming updates (polling is acceptable for MVP)
- Tracking of failed workflow executions or conditions-not-met scenarios
- Tracking of manually placed orders (only workflow-generated orders)
- Comparison of order history across time periods or workflows
- Export of order history to external systems (CSV, reports)
- Alerting or notifications when workflows place orders (future enhancement)
- Performance profiling or detailed timing breakdown of workflow execution
- Modification of workflow configuration based on order history (manual tuning only)
- Integration with existing order management system or order reconciliation
