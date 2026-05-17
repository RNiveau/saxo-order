# Implementation Plan: Group Alerts by Asset, Collapsible per Group (User Story 5)

**Branch**: `RNiveau/group-alerts-by-asset` | **Date**: 2026-05-17 | **Spec**: [../spec.md](../spec.md)
**Parent Plan**: [../plan.md](../plan.md) (User Stories 1–3)
**Sibling Plan**: [../user-story-4-asset-exclusion/plan-user-story-4.md](../user-story-4-asset-exclusion/plan-user-story-4.md) (User Story 4)

## Summary

Alerts on the Alerts page are **always** grouped by asset — there is no global on/off control. Each group renders a header with the asset name, the alert count, and a small arrow indicator. Clicking the arrow (or header) expands or collapses just that group's alerts; other groups are unaffected. Every group starts **expanded** on each page load (the trader's primary use case is to see signals at a glance). Collapse state is local component state and is **not** persisted across refreshes.

**Scope**: Frontend-only. No backend changes, no API contract changes, no new dependencies. Grouping is a pure client-side reorganization of alerts already loaded by the existing `GET /api/alerts` endpoint (FR-039).

## Technical Context

**Frontend:**
- **Language/Version**: TypeScript 5+, React 19+
- **Primary Dependencies**: existing (React, React Router DOM v7+) — no additions
- **State**: Per-component `useState` boolean for expanded/collapsed; no `localStorage`, no context, no reducer
- **Testing**: None currently configured (matches existing convention in this codebase)
- **Target Platform**: Web browser (Vite dev server on port 5173; production via existing build)

**Backend:** No changes.

**Project Type**: Extension of the existing alerts UI feature (one new presentational component + a one-line render change in `Alerts.tsx` + a pure grouping utility).

**Performance Goals:**
- Group expand/collapse completes within 100ms (SC-016) — trivial: one `setState` toggling a boolean
- Page render with grouping ≤ existing render time + O(n) grouping pass (n ≤ ~600 alerts)
- No additional network requests (FR-039)

**Constraints:**
- Grouping is always on (FR-031) — no toggle, no preference
- Asset identity = `asset_code` + `country_code` (Assumptions section of spec)
- Each `AlertGroup` owns its own expand/collapse state; siblings are independent (FR-035, SC-018)

**Scale/Scope:**
- Up to ~600 alerts simultaneously (per parent plan)
- Expected group count: 20–60 asset groups
- Single user (trader) access pattern

## Constitution Check

*GATE: Must pass before implementation.*

### I. Layered Architecture Discipline ✅

**Frontend:**
- ✅ Pages: Modify `frontend/src/pages/Alerts.tsx` — drop any flat-list branch, render groups
- ✅ Components: Add `frontend/src/components/AlertGroup.tsx` — owns its own `useState` for expansion, renders the existing `AlertCard` per alert
- ✅ Utils: `groupAlertsByAsset()` in `frontend/src/utils/alertFilters.ts` — pure function, no side effects
- ✅ Services: No API client changes
- ✅ `AlertCard.onExclude` callback flow preserved (`AlertGroup` forwards it)

**Backend:** N/A.

**Verdict**: ✅ PASS.

### II. Clean Code First ✅

- ✅ Self-documenting: `groupAlertsByAsset(alerts)` + `<AlertGroup>` with local `isExpanded` state
- ✅ No hardcoded strings beyond ARIA labels for the toggle button
- ✅ No over-engineering: no context, no reducer, no key-value persistence
- ✅ No unnecessary comments

**Verdict**: ✅ PASS.

### III. Configuration-Driven Design ✅

- ✅ No new environment variables
- ✅ No new API URLs or endpoints
- ✅ No `localStorage` keys (collapse state is per-session)

**Verdict**: ✅ PASS.

### IV. Safe Deployment Practices ✅

- ✅ No infrastructure changes
- ✅ No Lambda or backend changes
- ✅ Frontend ships through existing build (`npm run build`)
- ✅ Conventional commit (e.g., `feat: collapsible asset groups on alerts page`)

**Verdict**: ✅ PASS.

### V. Domain Model Integrity ✅

- ✅ Existing `AlertItem` TypeScript interface used unchanged
- ✅ `AssetAlertGroup` is a view-layer aggregation only (not persisted, not on the wire)
- ✅ Asset identity respects optional `country_code` (None-safe key construction)

**Verdict**: ✅ PASS.

---

**Overall Constitution Compliance**: ✅ **PASS** — all 5 principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-alerts-ui-page/user-story-5-group-by-asset/
├── plan-user-story-5.md     # This file
└── tasks-user-story-5.md    # Companion task list
```

### Source Code (repository root)

```text
frontend/src/
├── pages/
│   └── Alerts.tsx                  # MODIFIED: render groups unconditionally (no toggle)
├── components/
│   ├── AlertGroup.tsx              # NEW: header + collapsible body of AlertCards
│   ├── AlertGroup.css              # NEW: header / arrow / collapsed state styling
│   └── AlertCard.tsx               # UNCHANGED
├── utils/
│   └── alertFilters.ts             # MODIFIED: add groupAlertsByAsset() pure function
└── services/api.ts                 # UNCHANGED
```

**Structure Decision**: Single page mutation + one new presentational component + one new pure utility. No router changes, no service changes, no new types beyond `AssetAlertGroup` in the utility.

## Complexity Tracking

**No violations** — Constitution Check passed.

## Implementation Phases

### Phase 0: Research

**Status**: ✅ Skipped — no unknowns.

**Rationale**:
- Accordion / collapsible pattern is standard React; per-component `useState` covers it
- No backend or API work; no new dependencies
- The current Alerts page already does client-side filter + sort (`Alerts.tsx:75–96`); grouping is an analogous client-side transform applied **after** filtering and sorting

### Phase 1: Design

**1. View model** (utility-local TypeScript type):

```ts
export interface AssetAlertGroup {
  key: string;                    // `${asset_code}__${country_code ?? ''}`
  asset_code: string;
  country_code: string | null;
  asset_description: string;      // taken from the first alert in the group
  alerts: AlertItem[];            // already in sort order
}
```

**2. Pure grouping function** (`frontend/src/utils/alertFilters.ts`):

```ts
export function groupAlertsByAsset(alerts: AlertItem[]): AssetAlertGroup[]
```

- Input: filtered + sorted alerts
- Iterates once over a `Map<string, AssetAlertGroup>` keyed by `asset_code__country_code`
- Within each group, alerts retain input order (sort already applied upstream — FR-036)
- Inter-group order = first occurrence in the input list = top-ranked alert's group first (FR-037)

**3. Component: `AlertGroup.tsx`:**

Props:
```ts
interface AlertGroupProps {
  group: AssetAlertGroup;
  onAlertExcluded?: () => void;
}
```

Local state:
```ts
const [isExpanded, setIsExpanded] = useState<boolean>(true);  // FR-034: default expanded
```

Render:
- Clickable header: arrow icon (▼ when expanded, ▶ when collapsed) + asset name + count badge
- Body: only rendered when `isExpanded` is true (or always rendered with CSS hide — TBD in implementation; `null` body is simpler and avoids paying React reconciliation cost)
- Clicking anywhere on the header (or just the arrow — implementation detail, full-header is more discoverable) toggles `isExpanded`
- ARIA: `aria-expanded`, `aria-controls`, `role="button"` on the header so screen readers can navigate

**4. `Alerts.tsx` changes:**

- Remove the `groupByAsset` state, the `localStorage` effect, the checkbox in the filter bar, and the flat-list render branch from the previous implementation
- Always render `groupAlertsByAsset(filteredAlerts).map((group) => <AlertGroup ... />)`

**5. Empty / single-asset / filter / sort behaviors:**
- Empty state: existing `no-items` branch fires before grouping; no group rendering
- Single-asset case: one `AlertGroup` is rendered — same component path
- Filter: applied before grouping (already the case in `Alerts.tsx:75–84`); empty groups never materialise
- Sort change: rebuilds groups on next render; each group's `isExpanded` is preserved because the component keyed by `group.key` is **not** unmounted (FR-040)

### Phase 2: Tasks Generation

**Status**: ⏭️ See [tasks-user-story-5.md](./tasks-user-story-5.md).

## Architecture Decisions

### Decision 1: Grouping is always on, no toggle

**Context**: Initial design had a "Group by asset" checkbox with `localStorage` persistence. User feedback: the flat-list view is not desired — grouping is the right default presentation. The per-asset collapse arrow is what supplies the "hide / show" affordance.

**Decision**: Remove the global toggle entirely. Grouping is unconditional. Each group has its own expand/collapse state.

**Rationale**:
- Reduces UX surface area: one less control to discover
- Removes a global preference (no `localStorage`, no migration concerns later)
- Per-group collapse is the trader's actual need — hide assets already reviewed without losing the rest
- Simpler implementation: no state lifted to the page; each `AlertGroup` owns its own state

**Alternatives considered**:
- Keep the global toggle and add per-group collapse — rejected: redundant, two different ways to hide the same thing

### Decision 2: Default expanded, no persistence

**Context**: A collapsed-by-default view would be more compact for 50+ groups, but hides the data the user came to see.

**Decision**: Every group starts expanded on every page load. Collapse state is per-session, per-component, not persisted.

**Rationale**:
- Aligns with the "glance at signals" workflow
- Refresh resets state — predictable, no surprise about hidden alerts
- Avoids `localStorage` schema (would need to track per-asset keys, handle stale entries when assets are excluded, etc.)

**Alternatives considered**:
- Persist per-group state in `localStorage` — rejected: schema/cleanup overhead for a low-value feature
- Default collapsed — rejected: hides primary data

### Decision 3: Click the entire header, not just the arrow

**Context**: Some accordions only respond to an explicit arrow click.

**Decision**: The full group header is the click target; the arrow is a visual indicator only.

**Rationale**:
- Larger hit area = better UX on touch and pointer devices
- Single, obvious affordance; no "did I click the wrong pixel?" friction
- Still accessible via keyboard with `role="button"` + Enter/Space handling

**Alternatives considered**:
- Arrow-only target — rejected: smaller hit area, less discoverable

### Decision 4: Group order driven by input order

(unchanged from previous plan iteration)

The grouping `Map` is insertion-ordered, so the first occurrence of each asset defines that group's position. Because input is already sorted, the group containing the top-ranked alert always appears first under any active sort. One pass, no secondary sort.

---

## Out of Scope (US5)

- Pagination of groups (FR-041) — current page has no pagination; ticket would pair with future pagination work
- Persistence of collapse state across refreshes — explicitly out per Decision 2
- Server-side grouping or a new grouped endpoint — see [PR discussion](https://github.com/RNiveau/saxo-order/pull/590) (current dataset and UX don't justify it)
- "Collapse all" / "Expand all" header action — easy to add later if asked; not in current spec
- Smooth animation on expand/collapse — purely cosmetic; can be a follow-up
- Group-level actions (e.g., exclude all alerts of an asset from the group header) — adjacent to US4 but not specified
