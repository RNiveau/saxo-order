# Feature Specification: Create & Edit Workflow

**Feature Branch**: `016-workflow-create`
**Created**: 2026-03-22
**Updated**: 2026-03-22
**Status**: In Progress
**Input**: User description: "Create new workflows from the Workflows view or Asset Detail page. Need to handle all different kinds of workflows that exist in the system. Add edit capability."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create a Workflow from the Workflows Page (Priority: P1)

A user on the Workflows page clicks a "New Workflow" button, fills in a form covering all required fields (asset, indicator type, timeframes, condition, trigger, quantity), and saves. The new workflow appears immediately in the workflows list.

**Why this priority**: The Workflows page is the natural home for workflow management. Creating from here is the most general-purpose entry point and covers 100% of use cases.

**Independent Test**: Navigate to `/workflows`, click "New Workflow", fill in the form for any indicator type, save, and verify the workflow appears in the list.

**Acceptance Scenarios**:

1. **Given** the user is on the Workflows page, **When** they click "New Workflow", **Then** a creation form opens with all fields empty and defaults applied (dry run = on, enabled = on).
2. **Given** the form is open, **When** the user selects an indicator type (MA50, BBB, BBH, POL, ZONE, COMBO), **Then** the form adapts to show only the fields relevant to that indicator (POL shows a "value" field; ZONE shows "value" and "zone value"; MA50/BBB/BBH/COMBO show neither).
3. **Given** all required fields are filled, **When** the user clicks "Save", **Then** the workflow is created, the form closes, and the new workflow is immediately visible in the list.
4. **Given** a required field is missing or invalid, **When** the user clicks "Save", **Then** the form highlights the problematic field and does not submit.
5. **Given** the form is open, **When** the user clicks "Cancel", **Then** the form closes without saving anything.

---

### User Story 2 — Create a Workflow from the Asset Detail Page (Priority: P2)

A user viewing the detail page of a specific asset can create a workflow directly from that context. The asset fields (index, CFD symbol) are pre-filled. The user only needs to configure the workflow logic.

**Why this priority**: Pre-filling asset data from context reduces friction and errors for the most common creation path.

**Independent Test**: Navigate to an asset detail page, click "Create Workflow", verify index and CFD are pre-filled, complete remaining fields, save, verify the workflow appears on the Workflows page.

**Acceptance Scenarios**:

1. **Given** the user is on an asset detail page, **When** they click "Create Workflow", **Then** the creation form opens with the asset's index and CFD pre-filled.
2. **Given** the form is pre-filled with asset data, **When** the user completes the remaining required fields and saves, **Then** the workflow is created and linked to that asset.
3. **Given** a successful save from the asset detail page, **Then** a success confirmation is shown and the form closes.

---

---

### User Story 3 — Edit an Existing Workflow (Priority: P2)

A user can edit an existing workflow's configuration. An "Edit" button is available in the workflow detail modal. Clicking it opens the same `WorkflowCreateModal` pre-filled with the workflow's current values. On save, the workflow is updated in place.

**Why this priority**: Creation alone is not enough for day-to-day management — users need to adjust names, spreads, quantities, and dates without deleting and recreating.

**Independent Test**: Open a workflow detail modal, click "Edit", change the spread value, save, and verify the workflow detail shows the updated spread.

**Acceptance Scenarios**:

1. **Given** the user is viewing a workflow in the detail modal, **When** they click "Edit", **Then** the modal switches to edit mode with all current values pre-filled.
2. **Given** the edit form is open with pre-filled values, **When** the user changes a field and clicks "Save", **Then** the workflow is updated and the updated values are visible in the detail view.
3. **Given** a required field is cleared, **When** the user clicks "Save", **Then** validation fires inline and the update is not submitted.
4. **Given** the backend update call fails, **When** the user tries to save, **Then** an error banner appears inside the modal, form input is preserved, and the user can retry.
5. **Given** the user clicks "Cancel" in edit mode, **Then** no changes are persisted and the modal returns to the detail view (or closes).

---

---

### User Story 4 — Delete a Workflow (Priority: P3)

A user can permanently delete a workflow. A "Delete" button is available in the workflow detail modal. Clicking it prompts for confirmation before proceeding. On confirmation, the workflow is deleted and the modal closes; the workflow disappears from the Workflows list.

**Why this priority**: Deletion completes the full CRUD lifecycle for workflow management.

**Independent Test**: Open a workflow detail modal, click "Delete", confirm the prompt, verify the modal closes and the workflow no longer appears in the Workflows list.

**Acceptance Scenarios**:

1. **Given** the user is viewing a workflow in the detail modal, **When** they click "Delete", **Then** a confirmation prompt appears (e.g., "Are you sure you want to delete this workflow? This action cannot be undone.").
2. **Given** the confirmation prompt is shown, **When** the user confirms, **Then** the workflow is deleted, the modal closes, and the workflow is removed from the Workflows list.
3. **Given** the confirmation prompt is shown, **When** the user cancels, **Then** no deletion occurs and the detail modal remains open.
4. **Given** the delete API call fails, **Then** an inline error message is shown inside the modal and the workflow is not removed.

---

### Edge Cases

- What happens if the user changes indicator type after filling in condition fields? → Indicator-specific value fields (value, zone_value) reset; other fields are preserved.
- What if an end date in the past is submitted? → Inline validation error; form does not submit.
- What if quantity is zero or negative? → Inline validation error; form does not submit.
- What if the CFD symbol is not known from the asset detail page? → The field is pre-filled with a best-effort value and remains editable.
- What if a workflow is edited while it is actively running? → The update is persisted; the engine picks up new values on the next evaluation cycle.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to open a workflow creation modal from both the Workflows page and the Asset Detail page. The modal overlays the current page (no navigation away).
- **FR-002**: The form MUST include all workflow fields: name, index, CFD symbol, enabled toggle, dry-run toggle, US market flag, optional end date, one condition (indicator type, indicator timeframe, condition direction, condition timeframe, spread, optional candle element), and a trigger (timeframe, order location, order direction, quantity). The name field MUST be pre-populated with an auto-suggested value following the pattern "{direction} {indicator} {timeframe} {asset}" (e.g., "Buy BBB H1 DAX") that updates as the user changes indicator type, timeframe, or direction, and is always freely editable.
- **FR-003**: The form MUST dynamically show or hide indicator-specific fields based on the selected indicator type:
  - **MA50, BBB, BBH, COMBO**: no extra value fields
  - **POL (Polarité)**: one numeric "value" field (the pivot level)
  - **ZONE**: two numeric fields — "value" (zone lower bound) and "zone value" (zone upper bound)
- **FR-004**: When opened from the Asset Detail page, the index and CFD fields MUST be pre-filled with the viewed asset's data.
- **FR-005**: The form MUST validate all required fields before submission and display inline errors for missing or invalid values. If the backend save call fails (server error, network timeout), an error banner MUST appear inside the modal; the form MUST remain open with all user input preserved so the user can retry.
- **FR-006**: On successful submission, the workflow MUST be persisted and appear in the Workflows list without requiring a manual page refresh.
- **FR-007**: The form MUST include a "Cancel" action that discards all input and closes the form without side effects.
- **FR-008**: The dry-run toggle MUST default to enabled (on) for all new workflows to prevent accidental live order placement.
- **FR-009**: The enabled toggle MUST default to on so the workflow is active immediately after creation.
- **FR-010**: The end date field is optional; if provided, it MUST be validated to be a future date.
- **FR-011**: The candle element field (close / high / low) is optional; if not specified, the workflow engine applies its default evaluation logic.
- **FR-012**: An "Edit" button MUST be available in the workflow detail modal (`WorkflowDetailModal`). Clicking it opens `WorkflowCreateModal` in edit mode with all current workflow values pre-filled.
- **FR-013**: The `WorkflowCreateModal` MUST support an optional `workflow` prop containing an existing `WorkflowDetail`. When provided, the modal is in edit mode: the title changes to "Edit Workflow", the form is pre-filled, and saving issues a `PUT /api/workflow/workflows/{id}` request instead of POST.
- **FR-014**: The `PUT` endpoint MUST accept the same `WorkflowCreateRequest` body and return the updated `WorkflowDetail` (200). The `id`, `created_at` fields are preserved; `updated_at` is refreshed.
- **FR-015**: After a successful edit, the workflow detail view MUST reflect the updated values immediately.
- **FR-016**: A "Delete" button MUST be available in the workflow detail modal. Clicking it MUST show an inline confirmation prompt before any deletion occurs.
- **FR-017**: On confirmation, the workflow MUST be permanently deleted via `DELETE /api/workflow/workflows/{id}`. The modal MUST close and the Workflows list MUST remove the deleted entry without a manual page refresh.
- **FR-018**: If the delete API call fails, an inline error message MUST appear inside the modal; the workflow MUST NOT be removed from the list.

### Key Entities

- **Workflow**: The persisted configuration unit that drives automated order placement. Identified by a UUID. Contains basic metadata, one condition, and a trigger.
- **Condition**: An evaluation rule — specifies which indicator to watch, on which timeframe, and whether the asset price must be above or below the indicator with a spread tolerance. Optionally checks a specific candle element.
- **Indicator**: The technical signal the condition evaluates. The type determines what extra configuration is required (none for MA50/BBB/BBH/COMBO; a pivot level for POL; lower and upper bounds for ZONE).
- **Trigger**: Defines how an order is placed once the condition is met — timeframe, price location relative to the indicator, order direction (buy/sell), and quantity.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a complete workflow of any indicator type in under 2 minutes.
- **SC-002**: The form prevents submission with missing or invalid required fields 100% of the time, with clear inline error messages pointing to the problematic field.
- **SC-003**: A newly created workflow appears in the Workflows list immediately after saving, with no manual refresh required.
- **SC-004**: When opening the form from an Asset Detail page, the asset index and CFD fields are pre-filled correctly 100% of the time.
- **SC-005**: The form correctly adapts to show only the relevant fields for each of the 6 indicator types — no wrong fields shown, no required fields missing.
- **SC-006**: A user can edit any field of an existing workflow and see the updated values reflected immediately after saving.
- **SC-007**: Editing a workflow preserves all fields not explicitly changed (id, created_at, conditions not modified, etc.).
- **SC-008**: A deleted workflow disappears from the Workflows list immediately after the user confirms deletion, with no manual refresh required.
- **SC-009**: Deletion always requires explicit user confirmation — no workflow can be deleted with a single click.

---

## Clarifications

### Session 2026-03-22

- Q: How is the creation form presented? → A: Modal overlay (consistent with WorkflowDetailModal pattern)
- Q: What happens when the backend save call fails? → A: Error banner inside the modal — form stays open, user can retry without losing input
- Q: Should the workflow name field be auto-suggested? → A: Yes — auto-suggest a name from order direction + indicator type + indicator timeframe + asset (e.g., "Buy BBB H1 DAX"), user can override freely

---

## Assumptions

- Only one condition per workflow is supported at creation time, matching the existing majority of workflows. Multiple conditions may be added in a future iteration.
- The signal type is always "breakout" (the only type currently supported by the execution engine); no selector is shown in the form.
- Workflows created via the form are stored directly in DynamoDB. The YAML file is used for seeding/migration only and is not involved here.
- Workflow editing (US3) and deletion (US4) are both in scope for this feature.
- The "is US market" flag defaults to off and is toggled manually by the user when needed.
