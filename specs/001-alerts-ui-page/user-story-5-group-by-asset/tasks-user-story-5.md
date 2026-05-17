# Tasks: Group Alerts by Asset, Collapsible per Group (User Story 5)

**Feature**: Alerts UI Page — User Story 5
**Branch**: `RNiveau/group-alerts-by-asset`
**Plan**: [plan-user-story-5.md](./plan-user-story-5.md)
**Spec**: [../spec.md](../spec.md) (User Story 5 and FR-031–FR-041)

---

## Scope Note

US5 is a **frontend, client-side** enhancement of the existing Alerts page. Alerts are always grouped by asset (no on/off toggle). Each group has its own expand/collapse arrow and starts expanded on every page load. Collapse state lives in local component state — no `localStorage`.

There is **no Phase 1 (Setup)** and **no Phase 2 (Foundational)**: the parent feature is already deployed, `Alerts.tsx` exists, and `AlertCard.tsx` is reused as-is. Work happens in Phase 3 (US5) and a small polish phase.

Tests are not generated (project does not maintain frontend tests — matches the parent plan convention).

---

## Phase 3: User Story 5 — Group Alerts by Asset, Collapsible (Priority: P2) 🆕

**Story goal**: Always render alerts grouped by asset, with each group showing an expand/collapse arrow that toggles only that group's visibility. Groups start expanded; collapse state is per-session and not persisted.

**Independent test criteria** (run all in a browser against a real or seeded backend):

1. With ≥3 distinct assets in the alerts list, the page renders one group per asset; each group header shows the asset name, an alert count, and an arrow indicator.
2. All groups are expanded on initial page load.
3. Clicking one group's header collapses just that group (arrow flips, alerts hide); other groups remain unchanged.
4. Clicking the collapsed group again expands it, restoring its alerts and the arrow indicator.
5. Switching sort between "MA50 Slope" and "Recent" reorders both groups and within-group alerts; previously-collapsed groups remain collapsed across the sort change.
6. Applying or clearing an asset/type filter never produces empty groups.
7. Refreshing the page returns all groups to the expanded state (no persistence).
8. Excluding an alert from inside an expanded group (🚫 button) removes the alert; if it was the last alert of that asset, the entire group disappears.

### Tasks

- [ ] T001 [US5] Confirm `groupAlertsByAsset(alerts)` and the `AssetAlertGroup` interface in `frontend/src/utils/alertFilters.ts` match the signatures in the plan (no `sortBy` parameter; input is assumed already filtered and sorted; insertion-ordered `Map` keyed by `` `${asset_code}__${country_code ?? ''}` ``). Adjust if the existing implementation drifts from the spec.

- [ ] T002 [US5] Modify `frontend/src/components/AlertGroup.tsx` to make the group collapsible:
  - Add `const [isExpanded, setIsExpanded] = useState<boolean>(true);`
  - Wrap the header in a clickable element (button or div with `role="button"`, `tabIndex={0}`, `aria-expanded={isExpanded}`); clicking or pressing Enter/Space toggles `isExpanded`
  - Prepend an arrow indicator inside the header: `▼` when `isExpanded`, `▶` when collapsed
  - Conditionally render the `.alert-group-body` (the list of `AlertCard`s): show only when `isExpanded === true`
  - Keep the existing `onAlertExcluded` forwarding

- [ ] T003 [P] [US5] Update `frontend/src/components/AlertGroup.css`:
  - Add `.alert-group-arrow` style (fixed width, monospace-aligned, color matching `--text-muted` tone of the header)
  - Add `cursor: pointer` and a subtle `:hover` background on the header
  - Ensure the arrow renders inline before the asset name with consistent spacing
  - Keep the collapsed body invisible by not rendering it (no CSS hiding needed since T002 returns `null` for the body when collapsed)

- [ ] T004 [US5] Modify `frontend/src/pages/Alerts.tsx`:
  - Remove the `groupByAsset` state, the `useEffect` that syncs it to `localStorage`, and the `ALERTS_GROUP_BY_ASSET_KEY` constant
  - Remove the "Group by asset" checkbox from the filter bar
  - Remove the unused `AlertCard` import if no longer referenced from this file
  - Replace the conditional render (grouped vs. flat) with an unconditional grouped render: `groupAlertsByAsset(filteredAlerts).map((group) => <AlertGroup key={group.key} group={group} onAlertExcluded={loadAlerts} />)`

- [ ] T005 [P] [US5] Remove the `.toggle-group` style from `frontend/src/pages/Alerts.css` (it is no longer used after T004).

---

## Phase 4: Polish & Cross-Cutting Concerns

- [ ] T006 Manual browser verification of every acceptance scenario listed in the "Independent test criteria" block above. Run `npm run dev` from `frontend/`, navigate to `/alerts`, and walk scenarios 1–8.

- [ ] T007 Run `npm --prefix frontend run build` to confirm no new TypeScript errors are introduced (pre-existing errors in unrelated files are out of scope).

- [ ] T008 Write a conventional commit (`feat: collapsible asset groups on alerts page`) referencing US5 and FR-031–FR-041. Do not commit unless explicitly asked by the user.

---

## Dependencies

```
T001 ──► T002 ──┐
                │
                ├──► T004 ──► T006 ──► T007 ──► T008
                │
T003 ───────────┤
T005 ───────────┘
```

T003 (group CSS) and T005 (remove `.toggle-group` style) can run in parallel with T002/T004 since they touch different files. T001 is a verification step that may be a no-op if the utility from the previous iteration is already correct.

**Story dependencies**: US5 depends only on the already-shipped US1 page surface. It composes cleanly with US2 (filter), US3 (sort), and US4 (exclusion) flows.

---

## Parallel Execution Examples

After T001 lands (or in parallel with it if no changes are needed), two workers can split:

```
worker A: T002  frontend/src/components/AlertGroup.tsx
worker B: T003  frontend/src/components/AlertGroup.css
worker C: T005  frontend/src/pages/Alerts.css   (and T004 once A finishes)
```

T004 is the integration point and must wait for T002.

---

## Implementation Strategy

**MVP for US5 = T001 + T002 + T003 + T004 + T005.** That is the full feature; there is no smaller increment that ships behavior without breaking the page (T004 removes the previous toggle UI in the same commit that switches to unconditional grouping).

**Single-commit landing recommended**: the changes are too tightly coupled to split. T001–T005 in one commit, T006–T007 as verification, T008 as the commit step.

---

## Task Count Summary

| Phase                    | Tasks | Parallel slots |
| ------------------------ | ----- | -------------- |
| Phase 3 — US5            | 5     | 2 (T003, T005) |
| Phase 4 — Polish         | 3     | 0              |
| **Total**                | **8** | **2**          |

**Suggested MVP scope**: all of T001–T005 (the feature is atomic).

---

## Format Validation

Every task above conforms to the required format:

- ✅ `- [ ]` checkbox prefix
- ✅ Sequential ID (T001…T008)
- ✅ `[P]` marker on T003 and T005 (independent files, no in-phase dependencies blocking them)
- ✅ `[US5]` story label on every Phase 3 task; no story label on Phase 4 polish tasks
- ✅ Explicit file paths in every implementation task
