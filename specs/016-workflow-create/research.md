# Research: Create Workflow

**Feature**: 016-workflow-create
**Date**: 2026-03-22

---

## Decision 1: Backend Endpoint Design

**Decision**: `POST /api/workflow/workflows` returns the full `WorkflowDetail` response (201 Created).

**Rationale**: Mirrors the existing `GET /api/workflow/workflows/{id}` contract. The frontend can immediately display the created workflow's detail without a follow-up fetch. Consistent REST semantics.

**Alternatives considered**: Returning only the new `id` (202 Accepted) — rejected because it requires a second round-trip to refresh the list.

---

## Decision 2: Signal Field

**Decision**: The `signal` field is **not included** in the `WorkflowCreateRequest`. The backend hardcodes `signal = "breakout"`.

**Rationale**: "breakout" is the only signal type supported by the execution engine. Exposing it in the form would confuse users and create invalid states. Aligns with the spec assumption.

**Alternatives considered**: Accepting `signal` as an optional field — rejected because it adds complexity with no current benefit.

---

## Decision 3: Single `put_workflow()` vs. Reusing `batch_put_workflows()`

**Decision**: Add a dedicated `put_workflow(workflow_dict)` method to `DynamoDBClient`.

**Rationale**: `batch_put_workflows()` is designed for migration (accepts a list, calls `batch_writer`). A single-item `put_item` is the correct DynamoDB operation for creating one record at a time. Follows the constitution's encapsulation requirement (clients must expose methods for all operations).

**Alternatives considered**: Calling `batch_put_workflows([item])` — rejected because it wraps single-item creation in a batch operation designed for bulk use, obscuring intent.

---

## Decision 4: Name Auto-suggestion — Frontend Only

**Decision**: The workflow name is auto-suggested in the frontend from `{direction} {indicator} {timeframe} {asset}` (e.g., "Buy BBB H1 DAX"). The backend treats it as a plain required string.

**Rationale**: Name suggestion is a UX convenience, not a business rule. The backend has no knowledge of the user's chosen label format. Keeps the backend clean.

**Alternatives considered**: Backend-generated name — rejected because the user controls the name and the pattern depends on form fields chosen in the UI.

---

## Decision 5: Asset Detail Pre-fill

**Decision**: When opening the creation modal from the Asset Detail page, pre-fill both `cfd` and `index` with the asset's code (e.g., `"GER40.I"`). Both fields remain editable.

**Rationale**: The Asset Detail page gives us the CFD code directly. The `index` field (the underlying index symbol, e.g., `"DAX.I"`) is typically different, but since no reliable mapping from CFD to index exists at runtime, pre-filling with the same value and letting the user correct it is the least-surprising behavior.

**Alternatives considered**: Pre-filling CFD only and leaving index blank — rejected because a blank required field is confusing; pre-filling with a potentially-correct value is more helpful.

---

## Decision 6: `WorkflowCreateRequest` vs. Reusing Domain Enums

**Decision**: Accept raw strings for enum fields (`indicator.name`, `indicator.ut`, `close.direction`, etc.) in the Pydantic request model, with `Literal` constraints where practical. Validate against enum values inside the service layer.

**Rationale**: The existing `WorkflowDetail` already uses string fields (not enum types) in its Pydantic models for API serialization. Consistency is more valuable here than strict enum typing on the boundary model.

**Alternatives considered**: Using `IndicatorType`, `UnitTime`, etc. directly as Pydantic field types — evaluated but not adopted because it complicates JSON deserialization for string-valued enums without additional config.

---

## Decision 7: `end_date` Storage Format

**Decision**: Store `end_date` as `"YYYY-MM-DD"` string (ISO date, not datetime). Validate on the backend that the date is ≥ today.

**Rationale**: Matches the existing workflow storage format observed in `workflows.yml` and migration scripts. The execution engine compares dates using `datetime.strptime(end_date, "%Y/%m/%d")`, so the stored value must be parseable. Both `YYYY-MM-DD` and `YYYY/MM/DD` are accepted by the loader; we standardize on the hyphen form (ISO 8601).

---

## Decision 8: UUID generation

**Decision**: The backend generates the workflow `id` as a `uuid4` string. The frontend never sends an `id` in the create request.

**Rationale**: IDs are server-generated to prevent client-side collisions. Matches the migration script pattern.

---

## Existing Enum Values Reference

| Enum | Values (stored as) |
|------|-------------------|
| `IndicatorType` | `ma50`, `combo`, `bbb`, `bbh`, `polarite`, `zone` |
| `UnitTime` | `daily`, `15m`, `h1`, `h4`, `weekly`, `monthly` |
| `WorkflowDirection` | `above`, `below` |
| `WorkflowLocation` | `higher`, `lower` |
| `WorkflowElement` | `close`, `high`, `low` |
| `Direction` (order) | `buy`, `sell` |

---

## Existing Files That Need Modification

| File | Change |
|------|--------|
| `model/workflow_api.py` | Add `WorkflowCreateRequest`, `WorkflowConditionInput`, `WorkflowTriggerInput`, `WorkflowIndicatorInput`, `WorkflowCloseInput` Pydantic models |
| `client/aws_client.py` | Add `put_workflow(workflow_dict)` method |
| `services/workflow_service.py` | Add `create_workflow(data)` method |
| `api/routers/workflow.py` | Add `POST /api/workflow/workflows` endpoint |
| `frontend/src/services/api.ts` | Add `WorkflowCreateRequest` TS interface + `workflowService.createWorkflow()` |
| `frontend/src/components/WorkflowCreateModal.tsx` | New modal component |
| `frontend/src/components/WorkflowCreateModal.css` | New styles (reuse `.modal-*` class patterns) |
| `frontend/src/pages/Workflows.tsx` | Add "New Workflow" button + modal state |
| `frontend/src/pages/AssetDetail.tsx` | Add "Create Workflow" button + modal with pre-fill |
