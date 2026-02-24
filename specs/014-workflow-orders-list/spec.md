# Feature Specification: Workflow Orders List Page

**Feature Branch**: `014-workflow-orders-list`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "I want a page where I can list easily workflow orders"

## Context

Workflow order history is already recorded in storage (spec 010) and viewable inside the Workflow Detail modal — but only one workflow at a time. There is no way to see a cross-workflow view of recent orders in a single glance. This feature adds a dedicated page that surfaces all workflow orders in a flat, scannable list.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View All Workflow Orders at a Glance (Priority: P1)

As a trader, I want to see all orders placed by all my workflows on a single page so that I can quickly assess recent automated trading activity without opening each workflow individually.

**Why this priority**: This is the core value — a global view of what has been traded automatically. Currently, checking order activity requires opening each workflow's detail modal one by one.

**Independent Test**: Can be fully tested by navigating to the new "Workflow Orders" page and verifying that all orders from all workflows within the past 7 days are listed with their key fields (timestamp, workflow name, asset, direction, price, quantity).

**Acceptance Scenarios**:

1. **Given** multiple workflows have placed orders in the past 7 days, **When** I navigate to the Workflow Orders page, **Then** I see a flat list of all orders sorted by most recent first, each row showing: timestamp, workflow name, asset code, direction (BUY/SELL), price, and quantity
2. **Given** no workflows have placed any orders in the past 7 days, **When** I navigate to the page, **Then** I see an empty state message indicating no recent orders
3. **Given** I am on the page, **When** the list is loaded, **Then** orders from different workflows appear together in a single unified chronological list

---

### User Story 2 — Filter Orders by Workflow or Direction (Priority: P2)

As a trader, I want to filter the order list by workflow name or by order direction so that I can focus on a specific strategy or on buy/sell activity only.

**Why this priority**: With many workflows placing orders, the full list can become noisy. Filtering by workflow or direction lets users focus on what matters without leaving the page.

**Independent Test**: Can be fully tested by applying a workflow filter and verifying only orders from that workflow appear, then applying a BUY/SELL filter and verifying only matching orders appear, then clearing filters to restore the full list.

**Acceptance Scenarios**:

1. **Given** orders from several workflows are displayed, **When** I select a specific workflow in the filter, **Then** only orders from that workflow are shown and the count updates accordingly
2. **Given** orders from several workflows are displayed, **When** I select "BUY" in the direction filter, **Then** only buy orders are shown
3. **Given** I have applied filters, **When** I clear all filters, **Then** the full list of orders is restored

---

### Edge Cases

- When a workflow that placed orders has since been deleted or disabled, its orders still appear in the list using the workflow name stored at order placement time
- When an order record is deleted by the 7-day TTL while the user is on the page, it disappears on the next page load without an error
- When the list contains a large number of orders (50+), the page renders without visible performance degradation
- When all orders are from a single workflow, the workflow filter still displays and functions correctly

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated page listing all workflow orders from all workflows within the past 7 days
- **FR-002**: Each order row MUST display: placement timestamp (human-readable), workflow name, asset code, order direction (BUY/SELL), order price, and order quantity
- **FR-003**: Orders MUST be sorted by placement timestamp, most recent first, by default
- **FR-004**: Page MUST provide a filter to restrict the list to a single workflow (selected from a list populated with known workflow names from the order records)
- **FR-005**: Page MUST provide a filter to restrict the list to a specific order direction (BUY, SELL, or All)
- **FR-006**: Page MUST display an appropriate empty state when no orders match the active filters or when no orders exist in the past 7 days
- **FR-007**: The Workflow Orders page MUST be accessible from the sidebar navigation
- **FR-008**: System MUST provide a new API endpoint to retrieve orders across all workflows, sorted by placement timestamp descending
- **FR-009**: Orders from deleted or disabled workflows MUST still appear, using the workflow name captured at order placement time

### Key Entities

- **WorkflowOrder**: A single order placed by a workflow — identified by its order ID, linked to a workflow by stored name and ID, with placement timestamp, asset code, direction (BUY/SELL), price, and quantity
- **WorkflowOrdersPage**: A dedicated frontend page showing a filterable flat list of all `WorkflowOrder` records across all workflows

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can see all workflow orders from the past 7 days in a single view within 2 seconds of navigating to the page
- **SC-002**: Applying a workflow or direction filter updates the displayed list within 1 second without a page reload
- **SC-003**: The page is reachable within 2 clicks from any page via the sidebar
- **SC-004**: All orders from all workflows are shown — no orders silently omitted
- **SC-005**: The page renders without visible slowdown with up to 100 orders displayed

---

## Assumptions

- The 7-day TTL from spec 010 defines the maximum available history — no orders older than 7 days will be surfaced
- Workflow name is stored alongside each order record (as designed in spec 010), so orders from deleted workflows still display correctly
- The cross-workflow API endpoint will aggregate orders server-side and return a single flat list sorted by recency; the frontend does not need to merge per-workflow responses
- Pagination is not required for MVP given the 7-day retention window and typical order volume (up to 100 orders is the expected maximum)
- Filtering (FR-004, FR-005) is applied client-side on the already-loaded data set, given the bounded dataset size
- The page is added to the sidebar alongside the existing Workflows link

## Dependencies

- Spec 010 backend infrastructure (workflow_orders DynamoDB table, order recording, TTL) must be deployed before this feature can be tested end-to-end
- A new cross-workflow API endpoint is required (the existing per-workflow endpoint from spec 010 is insufficient)
- Existing sidebar navigation and routing will be extended (no new infra changes)
