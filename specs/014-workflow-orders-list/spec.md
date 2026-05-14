# Feature Specification: Workflow Orders List Page

**Feature Branch**: `014-workflow-orders-list`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "I want a page where I can list easily workflow orders"

## Context

Workflow order history is already recorded in storage (spec 010) and viewable inside the Workflow Detail modal — but only one workflow at a time. There is no way to see at a glance, across all workflows, what each workflow most recently did. This feature adds a dedicated page that surfaces, for each workflow, its **single most recent order** — one row per workflow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View the Latest Order per Workflow at a Glance (Priority: P1)

As a trader, I want to see, for each of my workflows, only its most recent order on a single page so that I can quickly see what each workflow most recently traded without scrolling through duplicates or opening each workflow individually.

**Why this priority**: This is the core value — a global, deduplicated view of each workflow's latest activity. Currently, checking the last action of each workflow requires opening each workflow's detail modal one by one.

**Independent Test**: Can be fully tested by navigating to the new "Workflow Orders" page and verifying that exactly one row appears per workflow — the row corresponding to that workflow's most recent order — with its key fields (timestamp, workflow name, asset, direction, price, quantity).

**Acceptance Scenarios**:

1. **Given** multiple workflows have placed orders in the past 7 days, **When** I navigate to the Workflow Orders page, **Then** I see exactly one row per workflow showing only that workflow's most recent order, sorted by most recent first, each row showing: timestamp, workflow name, asset code, direction (BUY/SELL), price, and quantity
2. **Given** no workflows have placed any orders in the past 7 days, **When** I navigate to the page, **Then** I see an empty state message indicating no recent orders
3. **Given** a single workflow has placed multiple orders in the past 7 days, **When** I view the page, **Then** only its single most recent order appears — older orders for the same workflow are not shown

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

- When a workflow that placed orders has since been deleted or disabled, its latest order still appears in the list using the workflow name stored at order placement time
- When a workflow's most recent order is deleted by the 7-day TTL while the user is on the page, the next page load shows either the next-most-recent order for that workflow (if any survives) or no row for that workflow at all, without an error
- When the list contains many distinct workflows (50+), the page renders without visible performance degradation
- When all orders in the table belong to a single workflow, only one row is displayed and the workflow filter still functions correctly
- When two orders for the same workflow share the exact same `placed_at` timestamp, the system MUST keep exactly one row for that workflow (selection between same-timestamp ties is deterministic but the specific tiebreaker is implementation-defined)

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated page listing the most recent order per workflow, considering only orders placed within the past 7 days
- **FR-002**: Each order row MUST display: placement timestamp (human-readable), workflow name, asset code, order direction (BUY/SELL), order price, and order quantity
- **FR-003**: Rows MUST be sorted by placement timestamp, most recent first, by default
- **FR-004**: Page MUST provide a filter to restrict the list to a single workflow (selected from a list populated with known workflow names from the displayed rows)
- **FR-005**: Page MUST provide a filter to restrict the list to a specific order direction (BUY, SELL, or All) — the filter applies to the deduplicated (one-per-workflow) row set
- **FR-006**: Page MUST display an appropriate empty state when no rows match the active filters or when no orders exist in the past 7 days
- **FR-007**: The Workflow Orders page MUST be accessible from the sidebar navigation
- **FR-008**: System MUST provide an API endpoint that returns at most one order per `workflow_id` — the row with the largest `placed_at` for each workflow — sorted by `placed_at` descending
- **FR-009**: Rows for deleted or disabled workflows MUST still appear, using the workflow name captured at order placement time
- **FR-010**: System MUST deduplicate orders by `workflow_id`, keeping the row with the largest `placed_at` value for each workflow; deduplication MUST happen server-side before the response is returned to the frontend

### Key Entities

- **WorkflowOrder**: A single order placed by a workflow — identified by its order ID, linked to a workflow by stored name and ID, with placement timestamp, asset code, direction (BUY/SELL), price, and quantity
- **LatestWorkflowOrder**: The single `WorkflowOrder` record with the largest `placed_at` for a given `workflow_id` within the 7-day retention window — exactly one per workflow
- **WorkflowOrdersPage**: A dedicated frontend page showing a filterable list of `LatestWorkflowOrder` rows — one row per workflow

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can see the latest order for each workflow (one row per workflow) in a single view within 2 seconds of navigating to the page
- **SC-002**: Applying a workflow or direction filter updates the displayed list within 1 second without a page reload
- **SC-003**: The page is reachable within 2 clicks from any page via the sidebar
- **SC-004**: Every workflow that has placed at least one order within the past 7 days appears in the list exactly once — no workflow is silently omitted and no workflow appears more than once
- **SC-005**: The page renders without visible slowdown with up to 100 distinct workflows displayed

---

## Assumptions

- The 7-day TTL from spec 010 defines the maximum available history — no orders older than 7 days will be surfaced
- Workflow name is stored alongside each order record (as designed in spec 010), so rows for deleted workflows still display correctly
- The cross-workflow API endpoint will scan, deduplicate by `workflow_id` (keeping the row with the largest `placed_at`), and sort by recency server-side; the frontend does not need to merge or deduplicate per-workflow responses
- Pagination is not required for MVP given the 7-day retention window and the expected scale (up to 100 distinct workflows is the expected maximum)
- Filtering (FR-004, FR-005) is applied client-side on the already-deduplicated data set returned by the API, given the bounded size
- The page is added to the sidebar alongside the existing Workflows link

## Dependencies

- Spec 010 backend infrastructure (workflow_orders DynamoDB table, order recording, TTL) must be deployed before this feature can be tested end-to-end
- A new cross-workflow API endpoint is required (the existing per-workflow endpoint from spec 010 is insufficient)
- Existing sidebar navigation and routing will be extended (no new infra changes)
