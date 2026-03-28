# Implementation Plan: Create Workflow

**Branch**: `016-workflow-create` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-workflow-create/spec.md`

## Summary

Add a "Create Workflow" modal accessible from both the Workflows page and the Asset Detail page. The feature adds a `POST /api/workflow/workflows` backend endpoint (new Pydantic request models → new service method → new DynamoDB client method) and a `WorkflowCreateModal` frontend component that adapts dynamically to the 6 indicator types, auto-suggests a workflow name, and pre-fills asset fields when opened from the Asset Detail page.

No new DynamoDB tables, no new IAM policies, no infrastructure changes.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI + Pydantic v2 (backend), React Router DOM v7+, Vite 7+, Axios (frontend)
**Storage**: AWS DynamoDB `workflows` table — existing, unchanged schema
**Testing**: pytest (backend) — no frontend testing framework configured
**Target Platform**: Linux / AWS Lambda (backend), Web browser (frontend)
**Project Type**: Web application — backend API + frontend SPA
**Performance Goals**: Workflow creation completes in < 2 s end-to-end
**Constraints**: No new tables; no new packages; single condition at creation time; signal fixed to "breakout"
**Scale/Scope**: 4 backend file edits + 2 new frontend files + 2 existing frontend file edits

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Layered Architecture | ✅ PASS | Router → Service → Client chain preserved. New `put_workflow` on client; new `create_workflow` on service; new `POST` route. Frontend API call goes through `workflowService` in `services/api.ts`. Modal component receives data via props, emits events via callbacks. |
| II | Clean Code First | ✅ PASS | Reuses existing enum values (no hardcoded strings), mirrors WorkflowDetailModal pattern. |
| III | Configuration-Driven | ✅ PASS | No new env vars or config keys required. |
| IV | Safe Deployment | ✅ PASS | No infrastructure changes. Existing DynamoDB table and IAM policies cover the write operation. |
| V | Domain Model Integrity | ✅ PASS | Uses existing `IndicatorType`, `UnitTime`, `WorkflowDirection`, `WorkflowLocation`, `WorkflowElement` enums. No exchange-field assumptions. |

**All gates pass. Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/016-workflow-create/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   └── create-workflow-api.yaml
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
# Backend — existing files modified
model/workflow_api.py                    ← add WorkflowCreateRequest + input sub-models
client/aws_client.py                     ← add put_workflow()
services/workflow_service.py             ← add create_workflow()
api/routers/workflow.py                  ← add POST /api/workflow/workflows

# Frontend — new files
frontend/src/components/WorkflowCreateModal.tsx    ← creation form modal
frontend/src/components/WorkflowCreateModal.css    ← modal styles

# Frontend — existing files modified
frontend/src/services/api.ts             ← add WorkflowCreateRequest interfaces + createWorkflow()
frontend/src/pages/Workflows.tsx         ← add "New Workflow" button + modal state
frontend/src/pages/AssetDetail.tsx       ← add "Create Workflow" button + modal with pre-fill
```

**Structure Decision**: Web application (existing structure). Backend follows existing layered pattern. Frontend follows existing page + component pattern. No new directories created.

## Phase 0: Research

See [research.md](./research.md) — all decisions resolved.

Key decisions:
- Form presented as **modal overlay** (consistent with WorkflowDetailModal)
- `POST /api/workflow/workflows` returns full `WorkflowDetail` (201)
- `signal` hardcoded to `"breakout"` on backend — not in request body
- `put_workflow()` added to DynamoDB client (single-item put_item)
- Name auto-suggested from `{direction} {indicator} {timeframe} {asset}` — frontend only
- Asset Detail pre-fills both `index` and `cfd` with asset code; both editable

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md).

New Pydantic models (all in `model/workflow_api.py`):
- `WorkflowIndicatorInput`
- `WorkflowCloseInput`
- `WorkflowConditionInput`
- `WorkflowTriggerInput`
- `WorkflowCreateRequest`

New TypeScript interfaces (in `frontend/src/services/api.ts`):
- `WorkflowIndicatorInput`
- `WorkflowCloseInput`
- `WorkflowConditionInput`
- `WorkflowTriggerInput`
- `WorkflowCreateRequest`

### API Contracts

See [contracts/create-workflow-api.yaml](./contracts/create-workflow-api.yaml).

New endpoint: `POST /api/workflow/workflows`

Request: `WorkflowCreateRequest` (JSON body)
Response: `WorkflowDetail` (201 Created) — reuses existing response model

Validation rules enforced by backend:
- `name`, `index`, `cfd` non-empty
- `conditions` min length 1
- `indicator.value` non-null when `name = "polarite"` or `name = "zone"`
- `indicator.zone_value` non-null when `name = "zone"`
- `close.spread > 0`, `trigger.quantity > 0`
- `end_date` must be a future date if provided

### Quickstart

See [quickstart.md](./quickstart.md).

9 acceptance scenarios covering: MA50 creation, POL/ZONE dynamic fields, asset detail pre-fill, validation (missing field, past date), name auto-suggestion, cancel, and save failure.

## Implementation Approach

### Backend

**`model/workflow_api.py`** — add input models:
```python
class WorkflowIndicatorInput(BaseModel):
    name: str
    ut: str
    value: Optional[float] = None
    zone_value: Optional[float] = None

class WorkflowCloseInput(BaseModel):
    direction: str
    ut: str
    spread: float = Field(..., gt=0)

class WorkflowConditionInput(BaseModel):
    indicator: WorkflowIndicatorInput
    close: WorkflowCloseInput
    element: Optional[str] = None

class WorkflowTriggerInput(BaseModel):
    ut: str
    location: str
    order_direction: str
    quantity: float = Field(..., gt=0)

class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    index: str = Field(..., min_length=1)
    cfd: str = Field(..., min_length=1)
    enable: bool = True
    dry_run: bool = True
    is_us: bool = False
    end_date: Optional[str] = None
    conditions: List[WorkflowConditionInput] = Field(..., min_length=1)
    trigger: WorkflowTriggerInput
```

**`client/aws_client.py`** — add `put_workflow()`:
```python
def put_workflow(self, workflow: Dict[str, Any]) -> None:
    response = self.dynamodb.Table("workflows").put_item(Item=workflow)
    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB put_item error: {response}")
        raise RuntimeError("Failed to persist workflow")
```

**`services/workflow_service.py`** — add `create_workflow()`:
```python
def create_workflow(self, data: WorkflowCreateRequest) -> WorkflowDetail:
    # validate enum values, end_date, indicator-specific fields
    # build dict with generated id, created_at, updated_at, signal="breakout"
    # call self.dynamodb_client.put_workflow(workflow_dict)
    # return WorkflowDetail built from the saved dict
```

**`api/routers/workflow.py`** — add POST route:
```python
@router.post("/workflows", response_model=WorkflowDetail, status_code=201)
async def create_workflow(
    data: WorkflowCreateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
```

### Frontend

**`services/api.ts`** — new interfaces + service method:
- `WorkflowIndicatorInput`, `WorkflowCloseInput`, `WorkflowConditionInput`, `WorkflowTriggerInput`, `WorkflowCreateRequest`
- `workflowService.createWorkflow(data: WorkflowCreateRequest): Promise<WorkflowDetail>`
  → `POST /api/workflow/workflows` with JSON body

**`WorkflowCreateModal.tsx`** — key behaviors:
- Controlled form state for all fields
- Indicator type selector drives conditional rendering: show `value` for POL; show `value` + `zone_value` for ZONE; show neither for MA50/BBB/BBH/COMBO
- Name field: auto-suggested from `{ORDER_DIRECTION} {INDICATOR_TYPE} {INDICATOR_UT} {ASSET}`, updates as fields change, user can override (tracked as "dirty")
- On save: client-side validation → `workflowService.createWorkflow()` → on success: call `onSuccess(newWorkflow)` callback + close; on failure: show error banner, preserve form
- On cancel / backdrop click: call `onClose()` with no side effects
- Props: `onClose: () => void`, `onSuccess: (workflow: WorkflowDetail) => void`, `prefill?: { index: string; cfd: string }`

**`Workflows.tsx`** — changes:
- Add "New Workflow" button in the page header
- Add `selectedWorkflowId` / `showCreateModal` state
- On create success: prepend new workflow to the list (or refresh) + show confirmation

**`AssetDetail.tsx`** — changes:
- Add "Create Workflow" button
- On click: open `WorkflowCreateModal` with `prefill={{ index: code, cfd: code }}`
