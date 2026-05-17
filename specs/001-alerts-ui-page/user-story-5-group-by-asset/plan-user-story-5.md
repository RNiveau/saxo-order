# Implementation Plan: Group Alerts by Asset (User Story 5)

**Branch**: `RNiveau/group-alerts-by-asset` | **Date**: 2026-05-16 | **Spec**: [../spec.md](../spec.md)
**Parent Plan**: [../plan.md](../plan.md) (User Stories 1–3)
**Sibling Plan**: [../user-story-4-asset-exclusion/plan-user-story-4.md](../user-story-4-asset-exclusion/plan-user-story-4.md) (User Story 4)

## Summary

Add a toggle to the Alerts page that switches the existing flat list into an **asset-grouped view**. When on, alerts for the same asset are clustered under a group header showing the asset identifier and alert count. The currently selected sort (MA50 slope or Recent) is preserved within each group, and groups themselves are ordered by their "top" alert's sort value. Filtering applies before grouping. The toggle preference is persisted in `localStorage` (matching the existing `nav_collapsed` pattern in `Sidebar.tsx`).

**Scope**: Frontend-only. No backend changes, no API contract changes, no new dependencies. Grouping is a pure client-side reorganization of alerts already loaded by the existing `GET /api/alerts` endpoint (FR-038).

## Technical Context

**Frontend:**
- **Language/Version**: TypeScript 5+, React 19+
- **Primary Dependencies**: existing (React, React Router DOM v7+) — no additions
- **State**: Local component state (`useState`) for toggle; `localStorage` for persistence
- **Testing**: None currently configured (matches existing convention in this codebase)
- **Target Platform**: Web browser (Vite dev server on port 5173; production via existing build)

**Backend:** No changes.

**Project Type**: Extension of existing alerts UI feature (purely additive in `Alerts.tsx`, with one new presentational component).

**Performance Goals:**
- Toggle interaction completes within 200ms for up to 500 alerts (SC-016) — achievable since grouping is an O(n) `reduce` over an already-loaded array
- No additional network requests (FR-038)

**Constraints:**
- Must not refetch alerts on toggle (FR-038)
- Must respect the currently active sort and filters (FR-034, FR-036)
- `localStorage` is the only persistence mechanism (consistent with `Sidebar.tsx:14,86`)
- Asset identity = `asset_code` + `country_code` (Assumptions section of spec)

**Scale/Scope:**
- Up to ~600 alerts simultaneously (per parent plan)
- Expected group count: 20–60 asset groups
- Single user (trader) access pattern

## Constitution Check

*GATE: Must pass before implementation.*

### I. Layered Architecture Discipline ✅

**Frontend:**
- ✅ Pages: Modify `frontend/src/pages/Alerts.tsx` — add toggle state and grouping logic
- ✅ Components: Add `frontend/src/components/AlertGroup.tsx` — presentational wrapper rendering a group header + a list of `AlertCard`s (props in, events out)
- ✅ Utils: Add a pure grouping function to `frontend/src/utils/alertFilters.ts` (or a new `alertGrouping.ts` peer) — no side effects
- ✅ Services: No API client changes
- ✅ No direct API calls from components; `AlertCard.onExclude` callback flow preserved

**Backend:** N/A.

**Verdict**: ✅ PASS — additive only, no layer crossings.

### II. Clean Code First ✅

- ✅ Self-documenting: A `groupAlertsByAsset(alerts, sortBy)` utility with a clear signature; toggle state named `groupByAsset`
- ✅ No hardcoded strings: `localStorage` key declared as a const (`ALERTS_GROUP_BY_ASSET_KEY`)
- ✅ No over-engineering: One `reduce` to build groups, one comparator for inter-group ordering; no class hierarchy, no context provider
- ✅ No unnecessary comments

**Verdict**: ✅ PASS.

### III. Configuration-Driven Design ✅

- ✅ No new environment variables
- ✅ No new API URLs or endpoints
- ✅ `localStorage` key follows existing snake_case convention (`alerts_group_by_asset`)

**Verdict**: ✅ PASS.

### IV. Safe Deployment Practices ✅

- ✅ No infrastructure changes
- ✅ No Lambda or backend changes
- ✅ Frontend ships through existing build (`npm run build`)
- ✅ Conventional commit (e.g., `feat: group alerts by asset toggle`)
- ✅ Zero risk to existing users with toggle off (default state)

**Verdict**: ✅ PASS.

### V. Domain Model Integrity ✅

- ✅ Existing `AlertItem` TypeScript interface used unchanged
- ✅ `AssetAlertGroup` is a view-layer aggregation only (not persisted, not on the wire) — matches the spec's Key Entities section
- ✅ Asset identity respects optional `country_code` (None-safe key construction)

**Verdict**: ✅ PASS.

---

**Overall Constitution Compliance**: ✅ **PASS** — all 5 principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-alerts-ui-page/user-story-5-group-by-asset/
├── plan-user-story-5.md     # This file
└── README.md                # (optional, created with /speckit.tasks)
```

No `contracts/`, `data-model.md`, `research.md`, or `quickstart.md` are needed:
- **contracts/**: No API surface added or changed (FR-038).
- **data-model.md**: No persisted data; `AssetAlertGroup` is documented in the spec's Key Entities.
- **research.md**: No unknowns — toggle UX is standard, `localStorage` pattern is already in `Sidebar.tsx`, grouping is a one-line `reduce`.
- **quickstart.md**: No new dev workflow — uses existing `npm run dev` for the Alerts page.

### Source Code (repository root)

```text
frontend/src/
├── pages/
│   └── Alerts.tsx                  # MODIFIED: add toggle state, localStorage I/O, render branch
├── components/
│   ├── AlertGroup.tsx              # NEW: header + AlertCard list for one asset
│   ├── AlertGroup.css              # NEW: group header styling
│   └── AlertCard.tsx               # UNCHANGED
├── utils/
│   └── alertFilters.ts             # MODIFIED: add groupAlertsByAsset() pure function
└── services/api.ts                 # UNCHANGED
```

**Structure Decision**: Single page mutation + one new presentational component + one new pure utility. No router changes, no service changes, no new types beyond a local `AssetAlertGroup` view model in the utility.

## Complexity Tracking

**No violations** — Constitution Check passed.

## Implementation Phases

### Phase 0: Research

**Status**: ✅ Skipped — no unknowns.

**Rationale**:
- `localStorage` toggle persistence pattern already exists at `frontend/src/components/Sidebar.tsx:14,86`
- The current Alerts page already does client-side filter + sort (`Alerts.tsx:75–96`) — grouping is an analogous client-side transform applied **after** filtering and sorting
- No backend or API work; no new dependencies

### Phase 1: Design

**Design summary** (no separate artifacts needed):

**1. View model (utility-local TypeScript type):**

```ts
interface AssetAlertGroup {
  key: string;              // `${asset_code}__${country_code ?? ''}`
  asset_code: string;
  country_code: string | null;
  asset_name?: string;      // taken from the first alert in the group
  alerts: AlertItem[];      // already in sort order
}
```

**2. Pure grouping function** (`frontend/src/utils/alertFilters.ts`):

```ts
export function groupAlertsByAsset(
  alerts: AlertItem[],            // assumed already filtered AND sorted
  sortBy: 'ma50_slope' | 'date',
): AssetAlertGroup[]
```

- Iterates the already-sorted, already-filtered list once
- Builds a `Map<string, AssetAlertGroup>` keyed by `asset_code__country_code`
- Within each group, alerts retain input order (sort already applied upstream — FR-034)
- Inter-group order = order of **first occurrence** in the input list, which equals the order of each group's top-ranked alert under the active sort (FR-035)
- Returns the values of the Map as an array

**3. Component: `AlertGroup.tsx`:**

Props:
```ts
interface AlertGroupProps {
  group: AssetAlertGroup;
  onAlertExcluded: () => void;     // forwarded to AlertCard.onExclude
}
```

Render:
- Header: `{asset_name ?? asset_code}` + badge with `group.alerts.length`
- Body: a `<div>` of `<AlertCard>`s reusing the existing component as-is

**4. `Alerts.tsx` changes:**

a. Add toggle state, initialized from `localStorage`:

```ts
const STORAGE_KEY = 'alerts_group_by_asset';
const [groupByAsset, setGroupByAsset] = useState<boolean>(
  () => localStorage.getItem(STORAGE_KEY) === 'true'
);
```

b. Write to `localStorage` on toggle change (effect or inline in the handler).

c. Render branch: when `groupByAsset` is true, call `groupAlertsByAsset(filteredAlerts, sortBy)` and render `<AlertGroup>`s; otherwise render the existing flat `<AlertCard>` list.

d. Add the toggle control to the existing filter bar (consistent visual placement next to "Sort By" / filters):

```tsx
<label className="toggle-group">
  <input
    type="checkbox"
    checked={groupByAsset}
    onChange={(e) => setGroupByAsset(e.target.checked)}
  />
  Group by asset
</label>
```

**5. Empty / single-asset states:**
- Empty state message reused from existing `no-items` branch (works regardless of toggle).
- Single-asset case: one `AlertGroup` is rendered — same component path, no special handling.

**6. Pagination (FR-039):**
The current page does **not** implement pagination — spec lists pagination as a feature, but it is not in code. We do not add pagination as part of US5. If/when pagination is later added, FR-039 dictates that pagination operates on groups when the toggle is on; that work is **out of scope** for US5 and should be tracked as a follow-up under whichever ticket adds pagination.

### Phase 2: Tasks Generation

**Status**: ⏭️ Ready for `/speckit.tasks`.

**Expected task list (US5 only):**

1. **Utility**: Add `groupAlertsByAsset()` to `frontend/src/utils/alertFilters.ts` with the signature above. ~20 LOC.
2. **Component**: Add `AlertGroup.tsx` + `AlertGroup.css` — presentational, uses `AlertCard`. ~40 LOC.
3. **Page**: Modify `Alerts.tsx` — toggle state, `localStorage` read/write, render branch, toggle UI control in filter bar. ~25 LOC delta.
4. **Manual verification**: Exercise the acceptance scenarios in the browser (multiple assets, filter interaction, sort interaction, refresh persistence, single-asset, empty state).

**Total**: 3 implementation tasks + 1 verification task. No test tasks (project does not run frontend tests; matches the existing convention noted in the parent plan).

## Architecture Decisions

### Decision 1: Client-side grouping, no backend changes

**Context**: Spec FR-038 explicitly requires that toggling does not trigger a data fetch; the data needed for grouping is already present in `AlertItem.asset_code` / `country_code`.

**Decision**: Implement entirely in the frontend.

**Rationale**:
- Zero coupling to API contract — backwards compatible
- No deploy of backend or Lambda
- Trivial to roll back (remove the toggle render)
- Performance is fine: O(n) over <1000 alerts

**Alternatives considered**:
- A new `GET /api/alerts/grouped` endpoint — rejected: extra surface area, redundant data, more deploy risk

### Decision 2: `localStorage` for toggle persistence

**Context**: The spec requires preference to be preserved across page refreshes (FR-037).

**Decision**: Mirror the `Sidebar.tsx` pattern — single `localStorage` key (`alerts_group_by_asset`), read on mount, written on change.

**Rationale**:
- Consistent with the existing codebase convention
- No user accounts on the frontend → no server-side preference store needed
- Single-user app, single browser per user is the common case

**Alternatives considered**:
- URL query parameter (`?group=1`) — rejected: spec wants persistence without sharing-by-URL; also pollutes deep links
- `sessionStorage` — rejected: would not survive a full close/reopen, contradicting FR-037

### Decision 3: Group ordering derives from input order, not a separate comparator

**Context**: FR-035 requires groups to be ordered by their highest-priority alert under the active sort.

**Decision**: Build groups from the already-sorted, already-filtered list using a `Map` that preserves insertion order. The first time each `asset_code__country_code` is seen, its group is created — which by construction means the group containing the top-ranked alert appears first.

**Rationale**:
- One pass, no secondary sort
- Group order automatically follows whatever sort the user picked — no special-casing per sort mode

**Alternatives considered**:
- Compute a per-group "priority value", then sort groups — rejected as redundant given the input is already sorted

---

## Out of Scope (US5)

- Pagination of groups (FR-039) — current page has no pagination; ticket would be paired with future pagination work
- Server-side persistence of toggle preference across devices — no user-account system exists
- Collapsible/expandable groups — spec asks for grouping, not folding; can be a follow-up if requested
- Sticky group headers on scroll — purely cosmetic, not in spec
- Group-level actions (e.g., exclude all alerts of an asset from the group header) — adjacent to US4 exclusion flow but not specified
