# Implementation Plan: Sidebar Navigation

**Branch**: `012-sidebar-navigation` | **Date**: 2026-02-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-sidebar-navigation/spec.md`

## Summary

Document the existing sidebar navigation and add a collapsible nav section that hides the 9 navigation links by default, giving the Live Watchlist more vertical room. The sidebar width (300 px) and `app-main` left margin are unchanged. Preference is persisted in `localStorage` under `nav_collapsed`. This is a **pure frontend change** — no backend, no API, no infrastructure changes.

## Technical Context

**Language/Version**: TypeScript 5+ / React 19+
**Primary Dependencies**: React Router DOM v7+, Vite 7+
**Storage**: `localStorage` (browser-native, no new dependency)
**Testing**: No frontend testing framework currently configured
**Target Platform**: Web — desktop (Chromium/WebKit)
**Project Type**: Web application — frontend-only
**Performance Goals**: CSS height transition ≤ 200 ms; no layout shift on toggle
**Constraints**: Sidebar width stays at 300 px / 250 px (mobile); `app-main` margin unchanged; no new npm packages
**Scale/Scope**: Two files touched — `Sidebar.tsx` and `Sidebar.css`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Layered Architecture | ✅ PASS | `localStorage` is UI-state, not an API call. No direct axios in component. All watchlist API calls remain through `services/api.ts`. |
| II | Clean Code First | ✅ PASS | Single state variable + conditional render. No abstraction needed for one-off localStorage toggle. |
| III | Configuration-Driven | ✅ PASS | No API URLs. No env vars required. localStorage key is a constant — acceptable inline. |
| IV | Safe Deployment | ✅ PASS | No infrastructure changes. Frontend build via Vite unchanged. |
| V | Domain Model Integrity | ✅ PASS | No domain models involved. |

**All gates pass. No violations. Complexity Tracking table not required.**

## Project Structure

### Documentation (this feature)

```text
specs/012-sidebar-navigation/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx      ← add navCollapsed state + toggle button + conditional render
│   │   └── Sidebar.css      ← add toggle button styles + nav collapse transition
│   └── (no other files changed)
└── (no new files)
```

**Structure Decision**: Frontend-only, single-component modification. Option 2 (web application) applies. No new files created. No backend, no API, no utils file (localStorage logic is 2 lines — no abstraction needed).

## Phase 0: Research

See [research.md](./research.md) — all decisions resolved.

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md).

### API Contracts

**None required.** This feature has no new API endpoints. The existing `watchlistService` in `frontend/src/services/api.ts` is unchanged.

### Quickstart

See [quickstart.md](./quickstart.md).

## Implementation Approach

### Sidebar.tsx changes

1. Read initial state from `localStorage`:
   ```ts
   const [navCollapsed, setNavCollapsed] = useState<boolean>(
     localStorage.getItem('nav_collapsed') !== 'false'  // default: true (collapsed)
   );
   ```

2. Toggle handler that persists to localStorage:
   ```ts
   const toggleNav = () => {
     setNavCollapsed(prev => {
       const next = !prev;
       localStorage.setItem('nav_collapsed', String(next));
       return next;
     });
   };
   ```

3. Replace the `<nav className="sidebar-nav">` block:
   - Add a clickable header row with a chevron icon and toggle handler
   - Conditionally render `<ul className="sidebar-menu">` based on `navCollapsed`

### Sidebar.css changes

1. Add `.sidebar-nav-header` styles (flex row, clickable cursor, chevron rotation via CSS class)
2. Add `.sidebar-menu` collapse transition (CSS `max-height` transition for smooth animation)

### No other files changed

The sidebar width stays at 300 px so `App.css` `.app-main { margin-left: 300px }` is unchanged.
