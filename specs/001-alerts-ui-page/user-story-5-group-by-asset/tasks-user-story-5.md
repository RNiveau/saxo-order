# Tasks: Group Alerts by Asset (User Story 5)

**Feature**: Alerts UI Page — User Story 5
**Branch**: `RNiveau/group-alerts-by-asset`
**Plan**: [plan-user-story-5.md](./plan-user-story-5.md)
**Spec**: [../spec.md](../spec.md) (see User Story 5 and FR-031–FR-039)

---

## Scope Note

US5 is purely a **frontend, client-side** enhancement of the existing Alerts page. It adds a toggle that reorganizes the already-loaded alerts into asset groups, with persistence via `localStorage`. The flat list (toggle off) remains the default.

There is **no Phase 1 (Setup)** and **no Phase 2 (Foundational)** for this user story — the parent feature is already deployed, the Alerts page exists at `frontend/src/pages/Alerts.tsx`, and the `AlertCard` component is reused as-is. All work happens in Phase 3 (US5) and a small polish phase.

Tests are not generated (project does not maintain frontend tests — matches the parent plan convention).

---

## Phase 3: User Story 5 — Group Alerts by Asset (Priority: P2) 🆕

**Story goal**: Let traders toggle between a flat alert list and an asset-grouped view. Within each group, alerts retain the active sort (MA50 slope or Recent); groups themselves are ordered by their top alert's sort value. Filters apply before grouping. The toggle preference persists across refreshes via `localStorage`.

**Independent test criteria** (run all in a browser against a real or seeded backend):

1. With ≥3 distinct assets in the alerts list, enabling the toggle clusters alerts by asset, with each group showing the asset identifier and an alert count badge.
2. With "MA50 Slope" sort selected, the group whose top alert has the highest slope appears first; alerts inside a group descend by slope.
3. Switching to "Recent" sort reorders both groups and within-group alerts by date desc.
4. Applying an asset or type filter while grouping is on yields only matching groups; no empty groups render.
5. Disabling the toggle restores the flat list using the current sort.
6. Toggling on, refreshing the browser, and revisiting `/alerts` shows the toggle still on.
7. Excluding an asset from a grouped alert card removes the alert (and its group, if it was the last one) without a page reload.

### Tasks

- [ ] T001 [US5] Add `groupAlertsByAsset(alerts, sortBy)` pure utility to `frontend/src/utils/alertFilters.ts`. Returns an `AssetAlertGroup[]` built via a `Map<string, AssetAlertGroup>` keyed by `` `${asset_code}__${country_code ?? ''}` ``. Input is assumed already filtered and sorted; iterate once, preserving insertion order so groups appear in the order of their top-ranked alert (satisfies FR-035). Each `AssetAlertGroup` exposes `key`, `asset_code`, `country_code`, optional `asset_name` (taken from the first alert in the group), and `alerts: AlertItem[]`. Export the `AssetAlertGroup` interface from the same file. Use the existing `AlertItem` type from `frontend/src/services/api.ts`. No external dependencies.

- [ ] T002 [P] [US5] Create `frontend/src/components/AlertGroup.tsx` — a presentational component that receives `{ group: AssetAlertGroup; onAlertExcluded: () => void }`. Render a group header containing the asset display name (`group.asset_name ?? group.asset_code`) plus an alert count badge (`group.alerts.length`), followed by a list of `AlertCard`s. Each `AlertCard` uses the existing key formula `` `${alert.asset_code}_${alert.alert_type}_${alert.date}` `` and forwards `onAlertExcluded` as its `onExclude` prop. No state, no API calls.

- [ ] T003 [P] [US5] Create `frontend/src/components/AlertGroup.css` with a group header style (flex row: name on the left, small count badge on the right), a thin separator between groups, and consistent spacing with the existing `.alerts-list` layout from `frontend/src/pages/Alerts.css`. Match the visual language of existing card styling (no new color tokens).

- [ ] T004 [US5] Modify `frontend/src/pages/Alerts.tsx` to add the group-by-asset toggle:
  - Declare a module-level constant `const ALERTS_GROUP_BY_ASSET_KEY = 'alerts_group_by_asset';` near the top of the file.
  - Add `const [groupByAsset, setGroupByAsset] = useState<boolean>(() => localStorage.getItem(ALERTS_GROUP_BY_ASSET_KEY) === 'true');`
  - Add a `useEffect` (or inline in the change handler) that persists the boolean: `localStorage.setItem(ALERTS_GROUP_BY_ASSET_KEY, String(groupByAsset));`.
  - In the filter-controls bar (after the existing Sort/Asset/Type selects, before the Clear-filters button), add a checkbox labeled "Group by asset" wired to `groupByAsset` / `setGroupByAsset`.
  - Below the existing `alerts-count` line, branch the render: when `groupByAsset` is `true`, call `groupAlertsByAsset(filteredAlerts, sortBy)` and render `<AlertGroup>` per group with `onAlertExcluded={loadAlerts}`. Otherwise keep the existing `filteredAlerts.map(...)` flat list. Import `AlertGroup` from `../components/AlertGroup` and `groupAlertsByAsset` from `../utils/alertFilters`.

- [ ] T005 [US5] Extend `frontend/src/pages/Alerts.css` with a `.toggle-group` style for the new checkbox label so it visually aligns with the existing `.filter-group` cluster in the controls bar. Do not introduce new colors; reuse existing variables.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [ ] T006 Manual browser verification of every acceptance scenario listed in the "Independent test criteria" block above. Run `npm run dev` from `frontend/`, log in to the local stack, navigate to `/alerts`, and walk through scenarios 1–7. Record any deviations as comments on the PR.

- [ ] T007 Run `npm run build` from `frontend/` to confirm the production build passes (no new TypeScript errors). Run `npm run lint` if a lint script is configured.

- [ ] T008 Write a conventional commit (`feat: group alerts by asset toggle`) referencing the spec sections US5 and FR-031–FR-039. Do not commit unless explicitly asked by the user.

---

## Dependencies

```
T001 ──┐
       │
T002 ──┤  (T002 and T003 can run in parallel with T001 — they don't import the utility)
T003 ──┤
       │
       └──► T004 (imports both the utility and the component)
                │
                ├──► T005 (CSS for the new toggle in the controls bar — depends on T004 markup)
                │
                └──► T006 (manual verification needs the full integration)
                        │
                        └──► T007 (build/lint after manual verification)
                                │
                                └──► T008 (commit message)
```

**Story dependencies**: US5 depends only on the already-shipped US1 page surface (`Alerts.tsx`, `AlertCard.tsx`). It does **not** depend on US2 (filtering), US3 (sorting), or US4 (exclusion) being present, but it composes cleanly with all three when they exist (which they do today).

---

## Parallel Execution Examples

After T001 starts (or in parallel with it), T002 and T003 can be picked up by separate workers — they touch entirely different files:

```
worker A: T001  frontend/src/utils/alertFilters.ts
worker B: T002  frontend/src/components/AlertGroup.tsx
worker C: T003  frontend/src/components/AlertGroup.css
```

T004 is the integration point and must wait for T001 and T002 to land. T005 follows T004 because it styles the markup T004 adds. T006–T008 are strictly sequential.

---

## Implementation Strategy

**MVP for US5 = T001 + T002 + T003 + T004.** That delivers the full toggle behavior described in the spec. T005 is visual polish on the new control; T006–T008 are verification, build validation, and commit hygiene.

**Incremental landing** (recommended):
1. Land T001 as a self-contained utility commit (no behavior change yet).
2. Land T002 + T003 together (component + styles, still no behavior change).
3. Land T004 + T005 together — this is the user-visible change.
4. Verify (T006), build (T007), commit/PR (T008).

**Why this slicing**: each commit compiles and ships cleanly. T001 alone is dead code (unused export) — acceptable for one commit but should be wired up promptly. If a single-commit PR is preferred, bundle T001–T005 together; the unit of behavior is too small to require multiple PRs.

---

## Task Count Summary

| Phase                    | Tasks | Parallel slots |
| ------------------------ | ----- | -------------- |
| Phase 3 — US5            | 5     | 3 (T001, T002, T003) |
| Phase 4 — Polish         | 3     | 0              |
| **Total**                | **8** | **3**          |

**Suggested MVP scope**: T001–T004 (the toggle works end-to-end). T005 (label polish), T006 (verification), T007 (build check), T008 (commit) follow.

---

## Format Validation

Every task above conforms to the required format:

- ✅ `- [ ]` checkbox prefix
- ✅ Sequential ID (T001…T008)
- ✅ `[P]` marker on T002 and T003 (independent files, no in-phase dependencies on T001)
- ✅ `[US5]` story label on every Phase 3 task; no story label on Phase 4 polish tasks
- ✅ Explicit file paths in every implementation task
