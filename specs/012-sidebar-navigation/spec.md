# Feature Specification: Sidebar Navigation

**Feature Branch**: `012-sidebar-navigation`
**Created**: 2026-02-23
**Status**: Retro
**Input**: Retrospective specification documenting the existing left sidebar component with a new collapsible behaviour user story.

---

## Context

The sidebar is a fixed left-panel present on every page of the application. It was introduced alongside the main frontend shell and extended over several features (watchlist live data in 004, slwin dividers in 007). This retro spec documents its current state and introduces the collapsible sidebar enhancement.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Navigate Between Pages (Priority: P1) *(existing)*

As a trader, I want a persistent navigation menu so that I can switch between any section of the application from any page without losing my current context.

**Why this priority**: Core navigation — the application is unusable without it.

**Independent Test**: Load the app, confirm all 9 nav links are visible in the sidebar, click each one and verify the correct page renders and the active link is highlighted.

**Acceptance Scenarios**:

1. **Given** I am on any page, **When** I look at the sidebar, **Then** I see links to Home, Available Funds, Create Order, Watchlist, Workflows, Long-Term Positions, Alerts, Asset Exclusions, and Trading Report
2. **Given** I am on the Watchlist page, **When** I look at the sidebar, **Then** the Watchlist nav link is visually highlighted (blue left border, blue text)
3. **Given** I click a nav link, **When** the route changes, **Then** the sidebar remains visible and the previously active link loses its highlight

---

### User Story 2 — Monitor Live Watchlist Prices (Priority: P1) *(existing)*

As a trader, I want to see my watchlist prices in the sidebar so that I can monitor market movements without leaving the page I am working on.

**Why this priority**: Persistent price visibility is the main reason the sidebar is wider than a typical icon-only nav.

**Independent Test**: Add at least 2 items to the watchlist (one short-term, one slwin), open any page, and verify prices auto-refresh every 60 seconds while the browser tab is visible.

**Acceptance Scenarios**:

1. **Given** the watchlist contains items, **When** the sidebar loads, **Then** each item displays its description, symbol (monospace), current price, and daily variation percentage (green for positive, red for negative)
2. **Given** short-term and slwin items are both present, **When** the list is rendered, **Then** a horizontal divider separates short-term items from slwin items
3. **Given** the market is open and the tab is visible, **When** 60 seconds elapse, **Then** the watchlist data is refreshed automatically without user interaction
4. **Given** the browser tab is hidden, **When** the auto-refresh interval fires, **Then** no API call is made until the tab becomes visible again
5. **Given** data was loaded more than 1 minute ago, **When** an item is displayed, **Then** a stale indicator (⏰) appears next to the item name

---

### User Story 3 — Collapse the Navigation Section (Priority: P2) *(new)*

As a trader, I want to collapse the navigation links so that the live watchlist gets more vertical space in the sidebar.

**Why this priority**: The 9 nav links occupy a large chunk of the sidebar's fixed height. Users who primarily use the sidebar for price monitoring rarely need all links visible at once and would benefit from a taller watchlist panel.

**Independent Test**: Click the nav collapse toggle, verify the navigation list is hidden and the live watchlist section expands to fill the freed space, reload the page and confirm the collapsed state is restored from localStorage.

**Acceptance Scenarios**:

1. **Given** the nav section is expanded (default), **When** I click the collapse toggle, **Then** the nav link list is hidden and the live watchlist section fills the additional vertical space
2. **Given** the nav section is collapsed, **When** I click the toggle again, **Then** the nav link list is shown and the live watchlist section returns to its previous size
3. **Given** I collapse the nav section, **When** I reload or navigate to another page, **Then** the nav section remains collapsed (preference persisted in localStorage under key `nav_collapsed`)
4. **Given** the nav section is collapsed, **When** I need to navigate, **Then** a visible toggle/header remains so I can expand the nav section again at any time
5. **Given** the nav section is collapsed or expanded, **When** the live watchlist renders, **Then** the sidebar width (300 px) and the main content area margin remain unchanged

---

### Edge Cases

- The sidebar width and the main content area margin are unaffected by the nav collapse state
- Live Watchlist auto-refresh continues normally regardless of the nav section state
- If localStorage is unavailable (private browsing, storage quota exceeded), the nav section defaults to expanded on every load without throwing an error
- The collapse toggle button must remain accessible via keyboard (Tab + Enter/Space)

---

## Requirements *(mandatory)*

### Functional Requirements — Existing Behaviour

- **FR-001**: Sidebar MUST render a fixed left panel on every page at 300 px width (250 px on screens ≤ 768 px)
- **FR-002**: Sidebar MUST display navigation links: Home, Available Funds, Create Order, Watchlist, Workflows, Long-Term Positions, Alerts, Asset Exclusions, Trading Report
- **FR-003**: The active route's nav link MUST be visually differentiated (blue `#58a6ff` left border and text colour)
- **FR-004**: Sidebar MUST display a Live Watchlist section below the nav links showing each item's description, symbol, price, and daily variation
- **FR-005**: Live Watchlist MUST auto-refresh every 60 seconds when the market is open and the browser tab is visible; refresh MUST pause when the tab is hidden
- **FR-006**: Watchlist items with the `short-term` label MUST appear above a divider that separates them from `slwin` items and other items
- **FR-007**: Items loaded more than 60 seconds ago MUST display a stale indicator (⏰) next to their name

### Functional Requirements — New: Collapsible Navigation Section

- **FR-008**: The navigation section MUST provide a visible toggle button (e.g. chevron or arrow) to collapse/expand the nav link list
- **FR-009**: In collapsed state the nav link list MUST be hidden; the Live Watchlist section MUST expand to fill the freed vertical space
- **FR-010**: The sidebar width (300 px / 250 px on mobile) and the `app-main` left margin MUST remain unchanged in both nav states
- **FR-011**: The collapsed/expanded preference MUST be persisted in `localStorage` under the key `nav_collapsed` and restored on page load
- **FR-012**: The Live Watchlist auto-refresh MUST continue unaffected regardless of the nav section state
- **FR-013**: If `localStorage` is unavailable, the nav section MUST default to expanded without throwing an error

### Key Entities

- **Sidebar**: Fixed left panel composed of two sections — navigation menu and live watchlist
- **Nav Link**: A React Router `NavLink` with an icon and a text label; in collapsed mode only the icon is shown
- **Live Watchlist Section**: Displays `WatchlistItem` records fetched from the watchlist API with auto-refresh logic
- **Nav Collapse State**: Boolean preference (`true` = collapsed) stored in `localStorage` under `nav_collapsed`

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 9 nav links are reachable and correctly highlighted from any route
- **SC-002**: Live watchlist prices refresh within 60 seconds of a market data change while the tab is active
- **SC-003**: Collapsing the nav section and reloading the page restores the collapsed state in 100% of localStorage-available environments
- **SC-004**: In collapsed nav state the live watchlist section visibly fills the additional vertical space with no layout gaps or overflow
- **SC-005**: The sidebar width and main content area margin are identical in both nav states (no layout shift)
- **SC-006**: The nav collapse toggle is operable via keyboard alone (Tab focus + Enter/Space activation)

---

## Assumptions

- The sidebar overall width stays fixed; only the nav section's visibility toggles
- `localStorage` is the appropriate persistence mechanism given the app is a single-user internal tool
- The nav section collapsed by default is the preferred initial state to maximise watchlist visibility

## Out of Scope

- Mobile drawer / overlay sidebar pattern (future spec)
- Resizable sidebar via drag handle
- Collapsing the Live Watchlist section independently
- Animation beyond a simple CSS height/opacity transition
