# Tasks: Sidebar Navigation

**Input**: Design documents from `/specs/012-sidebar-navigation/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ quickstart.md ✅

**Tests**: No test tasks — no frontend testing framework is configured (per constitution & plan.md).

**Scope note**: User Stories 1 & 2 document existing behaviour (retro spec). No implementation tasks are needed for them. All implementation work is for **US3 only** (collapsible nav section).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks (different files)
- **[US3]**: Belongs to User Story 3 — Collapse the Navigation Section

---

## Phase 1: Setup

**Purpose**: Confirm dev environment is running before making changes.

- [x] T001 Start Vite dev server (`npm run dev` in `frontend/`) and verify `Sidebar` renders at `http://localhost:5173` with nav links and live watchlist visible

---

## Phase 2: Foundational

**Purpose**: No new dependencies, no infrastructure changes, no new files.

> No foundational tasks required. `Sidebar.tsx` and `Sidebar.css` already exist. `localStorage` is browser-native. Proceed directly to US3.

---

## Phase 3: User Story 3 — Collapse the Navigation Section (Priority: P2)

**Goal**: The nav link list collapses by default. Users can toggle it with a labelled header row. Preference persists across page loads via `localStorage`. Sidebar width and watchlist are unaffected.

**Independent Test**: Open app in private window (no localStorage), confirm nav links are hidden and watchlist fills the sidebar. Click the "Navigation" header, confirm links appear. Reload — confirm expanded state persists. See `quickstart.md` for full checklist.

### Implementation

- [x] T002 [US3] Add `navCollapsed` boolean state (default `true` when `localStorage.getItem('nav_collapsed')` is absent) and `toggleNav` handler that flips state and persists to `localStorage` under key `nav_collapsed` in `frontend/src/components/Sidebar.tsx`
- [x] T003 [P] [US3] Add `.sidebar-nav-header` CSS rule: flex row, `justify-content: space-between`, `cursor: pointer`, `padding: 0.75rem 1.5rem`, `color: #8b949e`, hover colour `#e6edf3` in `frontend/src/components/Sidebar.css`
- [x] T004 [US3] Replace the bare `<nav className="sidebar-nav">` opening with a clickable header row (`<button>` or `<div role="button">`) labelled "Navigation" + chevron character (▲/▼) that calls `toggleNav`; wire `navCollapsed` as a CSS class on the wrapper (e.g. `sidebar-nav--collapsed`) in `frontend/src/components/Sidebar.tsx` (depends on T002)
- [x] T005 [US3] Wrap `<ul className="sidebar-menu">` in `{!navCollapsed && (...)}` conditional render so the list is hidden when `navCollapsed` is `true` in `frontend/src/components/Sidebar.tsx` (depends on T004)
- [x] T006 [US3] Add chevron rotation CSS — `.sidebar-nav-header .chevron` default `transform: rotate(0deg)` and `.sidebar-nav--collapsed .sidebar-nav-header .chevron { transform: rotate(180deg) }` with `transition: transform 0.2s ease` in `frontend/src/components/Sidebar.css` (depends on T003)

**Checkpoint**: Nav section collapses/expands on click, persists across reloads, watchlist height grows when nav is collapsed, sidebar width unchanged.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Build validation and manual acceptance testing.

- [x] T007 [P] Run `npm run lint` in `frontend/` and fix any ESLint errors introduced by T002–T006
- [x] T008 [P] Run `npm run build` in `frontend/` and confirm TypeScript compiles without errors
- [ ] T009 Run all acceptance scenarios from `specs/012-sidebar-navigation/quickstart.md` manually (default state, toggle, persistence, watchlist unaffected, layout unchanged, keyboard access)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Skipped — no infrastructure work needed
- **Phase 3 (US3)**: Can start after T001 verification
- **Phase 4 (Polish)**: Depends on all Phase 3 tasks complete

### User Story 3 Internal Order

```
T001 (verify env)
  └─> T002 (state + handler)  ─┐
  └─> T003 [P] (header CSS)   ─┤
        T004 (header JSX)  ◄───┘ (after T002)
          T005 (conditional render) (after T004)
        T006 (chevron CSS) (after T003)
  └─> T007 [P] (lint)       ─┐
  └─> T008 [P] (build)      ─┤ (after T002–T006)
        T009 (manual test)  ◄─┘
```

### Parallel Opportunities

```bash
# T002 (Sidebar.tsx) and T003 (Sidebar.css) touch different files — launch together:
Task: "Add navCollapsed state + toggleNav in Sidebar.tsx"         # T002
Task: "Add .sidebar-nav-header CSS in Sidebar.css"               # T003

# T007 and T008 are independent lint/build checks — launch together:
Task: "Run npm run lint in frontend/"                             # T007
Task: "Run npm run build in frontend/"                           # T008
```

---

## Implementation Strategy

### MVP (US3 only)

1. Complete Phase 1 (T001) — verify environment
2. Complete Phase 3 (T002 → T003+T002 parallel → T004 → T005 → T006)
3. Complete Phase 4 (T007, T008, T009)
4. **Done** — feature is complete, no incremental delivery needed (single user story)

### Commit strategy

```
feat: add collapsible navigation section to sidebar
```

---

## Notes

- `[P]` tasks = different files or independent operations, no shared state
- `[US3]` maps every task to User Story 3 for traceability
- No test tasks — no frontend testing framework configured
- No backend, no API, no infra changes — frontend-only
- `App.css` is **not modified** (sidebar width unchanged, `app-main` margin unchanged)
