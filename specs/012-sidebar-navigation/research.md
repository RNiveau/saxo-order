# Research: Sidebar Navigation

**Feature**: 012-sidebar-navigation
**Date**: 2026-02-23

## Decision 1: State persistence mechanism

**Decision**: `localStorage` directly in the component (no custom hook, no context)

**Rationale**: The nav-collapse preference is read once on mount and written on each toggle. It is consumed by a single component (`Sidebar.tsx`). Extracting a `useLocalStorage` hook would be premature abstraction for a one-off usage.

**Alternatives considered**:
- Custom `useLocalStorage<T>(key, default)` hook — rejected (would add a `hooks/` directory for a single call site; violates "No Over-Engineering" in Constitution §II)
- React context / Zustand — rejected (global state management for a single boolean is disproportionate)
- URL query parameter — rejected (pollutes the URL with UI preference, not shareable intent)

---

## Decision 2: Default state

**Decision**: Default to **collapsed** (`nav_collapsed` absent from localStorage = `true`)

**Rationale**: The spec explicitly states "nav collapsed by default is the preferred initial state to maximise watchlist visibility". Reading as `localStorage.getItem('nav_collapsed') !== 'false'` achieves this: absent key → `true` (collapsed); stored `'false'` → expanded.

**Alternatives considered**:
- Default expanded — rejected (contradicts spec intent)
- Store `'true'`/`'false'` and parse JSON — rejected (unnecessary `JSON.parse` for a boolean string; direct string comparison is clearer)

---

## Decision 3: Animation approach

**Decision**: CSS `max-height` transition on `.sidebar-menu`

**Rationale**: A `max-height` transition between `0` and a value large enough to contain all items (e.g., `500px`) provides a smooth collapse/expand without JavaScript measurement. The nav list has a bounded and predictable height (9 items × ~48 px = ~430 px).

**Alternatives considered**:
- `display: none` toggle — rejected (no animation, abrupt visual jump)
- JavaScript `getBoundingClientRect` + explicit height — rejected (layout thrash, requires ResizeObserver for robustness; over-engineered for a static list)
- CSS `grid-template-rows: 0fr / 1fr` — valid modern alternative; rejected only because `max-height` is already used elsewhere in the project styles and is universally supported in target browsers

---

## Decision 4: Toggle button placement and icon

**Decision**: A header row at the top of `.sidebar-nav` with a text label "Navigation" and a chevron (▲/▼) that rotates via CSS class

**Rationale**: Makes the collapsible section discoverable (users see a labelled, interactive header rather than guessing), consistent with the existing `.sidebar-section-header` pattern already used for the Live Watchlist section header.

**Alternatives considered**:
- Icon-only button floating at top of sidebar — rejected (poor discoverability, requires tooltip)
- Collapse arrow at the bottom of the nav list — rejected (hard to find when list is long)

---

## Decision 5: Scope of files changed

**Decision**: Only `Sidebar.tsx` and `Sidebar.css`. No other files.

**Rationale**: Sidebar width does not change → `App.css` margin unchanged. No new API endpoints → `services/api.ts` unchanged. No new utility needed → `utils/` unchanged.

**Confirmed unchanged files**: `App.tsx`, `App.css`, `frontend/src/services/api.ts`, all page components.
