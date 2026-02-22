# Implementation Plan: Workflow Order History Tracking

**Branch**: `010-workflow-execution-tracking` | **Date**: 2026-02-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-workflow-execution-tracking/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Track when workflows place orders by recording order events to DynamoDB with 7-day TTL. Display order history in the workflow UI, showing last order timestamp in list view and full order history in detail view. Only successful order placements are tracked (not failed executions or conditions-not-met).

**Technical Approach**:
- Create new DynamoDB table `workflow_orders` with workflow_id as partition key, timestamp as sort key
- Modify `WorkflowEngine.run()` to record order events after successful order placement
- Add API endpoints for retrieving order history (list and detail)
- Extend existing workflow UI components to display order history
- Use DynamoDB TTL to auto-delete records after 7 days

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ (frontend)
**Primary Dependencies**:
  - Backend: FastAPI, boto3 (DynamoDB), Pydantic (data validation)
  - Frontend: React 19+, Vite 7+, Axios (HTTP client), React Router DOM v7+
**Storage**: AWS DynamoDB (workflow_orders table with TTL enabled)
**Testing**: pytest (backend with unittest.mock), no frontend testing currently configured
**Target Platform**: AWS Lambda (backend), Web browser (frontend)
**Project Type**: Web application (backend API + frontend SPA)
**Performance Goals**: <2 seconds for order history retrieval, <1 second for list view with last order timestamps
**Constraints**:
  - Order tracking must not block order placement (graceful degradation)
  - 7-day retention maximum (TTL enforced)
  - Workflow engine modifications must be backward compatible
**Scale/Scope**: ~10-50 workflows, <100 orders per day, <700 order records at any time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Layered Architecture Discipline

**Backend Layers:**
- ✅ **Service Layer**: Will modify `WorkflowEngine` (engines/workflow_engine.py) to call `DynamoDBClient.record_workflow_order()`
- ✅ **Client Layer**: Will add `record_workflow_order()` method to existing `DynamoDBClient` (client/dynamodb_client.py)
- ✅ **API Layer**: Will add new endpoints in `api/routers/workflow.py` to retrieve order history
- ✅ **Model Layer**: Will create new Pydantic models in `api/models/workflow.py` and domain models in `model/workflow_api.py`

**Frontend Layers:**
- ✅ **Services**: Will extend `workflowService` in `frontend/src/services/api.ts` with new order history methods
- ✅ **Components**: Will update `WorkflowTable.tsx` to display last order timestamp, `WorkflowDetailModal.tsx` to show order history
- ✅ **Pages**: `Workflows.tsx` will use service methods to fetch order data

**Compliance:**
- ✅ No direct DynamoDB access from service layer - using `DynamoDBClient` methods
- ✅ No business logic in API routers - thin orchestration only
- ✅ Frontend API calls through service layer only
- ✅ Using existing enums where applicable (OrderDirection, OrderType from model/)

### ✅ II. Clean Code First

- ✅ Using existing domain models (Workflow, WorkflowListItem from model/workflow_api.py)
- ✅ No speculative features - only tracking order placements as specified
- ✅ No unnecessary abstractions - extending existing WorkflowService and DynamoDBClient
- ✅ Enum-driven: Will use OrderDirection, OrderType enums from model/

### ✅ III. Configuration-Driven Design

- ✅ **Backend**: Table name will use existing config pattern (dynamodb_client already configured)
- ✅ **Frontend**: Will use existing `VITE_API_URL` for API endpoint
- ✅ **No Hardcoding**: TTL duration (7 days = 604800 seconds) will be in config or constant

### ✅ IV. Safe Deployment Practices

- ✅ **Infrastructure as Code**: Will add `workflow_orders` table in `pulumi/dynamodb.py`
- ✅ **Docker-Based Lambda**: Existing Lambda deployment process unchanged
- ✅ **Deployment Script**: Will use `./deploy.sh` for deployment
- ✅ **Conventional Commits**: Will follow `feat:` commit format

### ✅ V. Domain Model Integrity

- ✅ **Model Boundaries**: Using WorkflowOrder domain model, not raw DynamoDB responses
- ✅ **Explicit Exchange**: Not applicable - orders are placed through workflows (already know source)
- ✅ **Consistent Patterns**: Following existing workflow model patterns (UUID primary keys, timestamps)

**Pre-Design Gate Result**: ✅ **PASS** - No constitution violations

## Project Structure

### Documentation (this feature)

```text
specs/010-workflow-execution-tracking/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── workflow-orders-api.yaml  # OpenAPI spec for new endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Backend (Python)
engines/
└── workflow_engine.py           # MODIFY: Add order tracking after placement

client/
└── dynamodb_client.py           # MODIFY: Add record_workflow_order() method

services/
└── workflow_service.py          # MODIFY: Add get_workflow_orders() method

api/
├── routers/
│   └── workflow.py              # MODIFY: Add GET /workflow/workflows/{id}/orders endpoint
└── models/
    └── workflow.py              # MODIFY: Add WorkflowOrderResponse model

model/
├── workflow.py                  # NEW: WorkflowOrder domain model
└── workflow_api.py              # MODIFY: Add WorkflowOrderListItem for API responses

pulumi/
└── dynamodb.py                  # MODIFY: Add workflow_orders table definition

tests/
├── engines/
│   └── test_workflow_engine.py  # MODIFY: Test order tracking
├── client/
│   └── test_dynamodb_client.py  # NEW: Test record_workflow_order()
└── services/
    └── test_workflow_service.py # MODIFY: Test get_workflow_orders()

# Frontend (TypeScript/React)
frontend/src/
├── services/
│   └── api.ts                   # MODIFY: Add getWorkflowOrders() to workflowService
├── components/
│   ├── WorkflowTable.tsx        # MODIFY: Add last order timestamp column
│   └── WorkflowDetailModal.tsx  # MODIFY: Add order history section
└── pages/
    └── Workflows.tsx            # MODIFY: Fetch and pass order data to components
```

**Structure Decision**: Extends existing web application structure (backend API + frontend SPA). No new directories needed - modifications to existing workflow management system. Backend follows service → client layer pattern. Frontend follows pages → components → services pattern.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations to justify. Implementation follows existing architectural patterns and respects all constitution principles.

---

## Phase 0: Research & Discovery

### Research Questions

Based on Technical Context above, the following areas need research:

1. **DynamoDB TTL Configuration**: How to properly configure TTL attribute in Pulumi and ensure it's enabled at table creation
2. **Order Event Capture**: Where exactly in WorkflowEngine.run() should order tracking occur (after order placement success, error handling)
3. **Backward Compatibility**: How to ensure WorkflowEngine changes don't break existing workflows or CLI usage
4. **Query Patterns**: Optimal DynamoDB query pattern for "get all orders for workflow_id, sorted by timestamp DESC"
5. **Frontend State Management**: How to integrate order history into existing Workflows.tsx state without performance degradation

### Research Tasks

*These will be delegated to research agents and consolidated in research.md*

- Research DynamoDB TTL attribute configuration in Pulumi (boto3 table definition)
- Identify exact integration point in WorkflowEngine.run() for order tracking
- Research query patterns for partition key + sort key (workflow_id + timestamp)
- Review existing WorkflowDetailModal.tsx to determine best UX for order history section
- Investigate error handling patterns in existing DynamoDBClient methods

*Research output will be consolidated in `research.md` before proceeding to Phase 1*

---

## Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

### Data Model Design

*Output: `data-model.md`*

**Entities to model:**
1. **WorkflowOrder** (domain model in model/workflow.py)
   - From spec Key Entities: order_id, workflow_id, placed_at, price, quantity, direction, order_type, asset details, execution context, ttl
2. **WorkflowOrderListItem** (API response in model/workflow_api.py)
   - Simplified version for list views: order_id, workflow_id, placed_at, price, quantity, direction
3. **WorkflowOrderResponse** (Pydantic in api/models/workflow.py)
   - Full details for single order retrieval

### API Contract Generation

*Output: `contracts/workflow-orders-api.yaml`*

**Endpoints from Functional Requirements:**

From FR-004, FR-005:
- `GET /api/workflow/workflows/{workflow_id}/orders` - List order history for workflow (paginated)
  - Query params: page, per_page, sort (default: placed_at DESC)
  - Response: WorkflowOrderListResponse (orders[], total, page, per_page)

- `GET /api/workflow/orders/{order_id}` - Get single order details
  - Path param: order_id (UUID)
  - Response: WorkflowOrderResponse (full order details)

**OpenAPI schema will be generated with:**
- Request/response schemas matching Pydantic models
- Error responses (404 Not Found, 500 Internal Server Error)
- Authentication requirements (if applicable)

### Quickstart Document

*Output: `quickstart.md`*

Will include:
1. **Local Development Setup**
   - Create DynamoDB local table for testing
   - Run backend with workflow order tracking enabled
   - Run frontend with order history UI

2. **Testing the Feature**
   - Trigger a workflow that places an order (via CLI or Lambda)
   - View order history in UI
   - Verify TTL expiration (set to 1 hour for testing)

3. **Deployment**
   - Pulumi up to create workflow_orders table
   - Deploy backend via ./deploy.sh
   - Build and deploy frontend

### Agent Context Update

*Run: `.specify/scripts/bash/update-agent-context.sh claude`*

Will add to `.claude/CLAUDE.md`:
- DynamoDB workflow_orders table with TTL
- New WorkflowOrder domain model and API models
- New API endpoints for order history
- Frontend order history components

---

## Phase 2: Task Generation

**Status**: NOT EXECUTED BY THIS COMMAND

Tasks will be generated by running `/speckit.tasks` after this plan is approved. That command will:
1. Read this plan.md and spec.md
2. Generate dependency-ordered tasks in tasks.md
3. Create executable implementation steps

---

## Post-Design Constitution Check

*Re-evaluate after Phase 1 design artifacts are complete*

### Artifacts Generated:
- ✅ `research.md` - Technical research findings consolidated
- ✅ `data-model.md` - Domain models and entity definitions
- ✅ `contracts/workflow-orders-api.yaml` - OpenAPI 3.0 specification
- ✅ `quickstart.md` - Development and testing guide
- ✅ Agent context updated in `CLAUDE.md`

### Constitution Compliance Review:

#### ✅ I. Layered Architecture Discipline
- **Service Layer**: WorkflowService.get_workflow_order_history() - business logic only
- **Client Layer**: DynamoDBClient.record_workflow_order() and get_workflow_orders() - encapsulates DynamoDB access
- **API Layer**: GET /workflow/workflows/{id}/orders - thin orchestration
- **Model Layer**: WorkflowOrder domain model, WorkflowOrderListItem API model - proper separation
- **Frontend Services**: workflowService.getWorkflowOrderHistory() - single API interaction point
- **No client internals accessed**: All DynamoDB operations through client methods, never direct Table() access

#### ✅ II. Clean Code First
- **Self-Documenting**: Method names clearly indicate purpose (record_workflow_order, get_workflow_orders)
- **No Over-Engineering**: Minimal abstractions - extends existing patterns only
- **Enum-Driven**: Uses existing Direction, OrderType, AssetType enums
- **No Unnecessary Comments**: Code examples in quickstart are clear without inline comments

#### ✅ III. Configuration-Driven Design
- **Backend**: TTL duration (7 days) will be constant, table names in config
- **Frontend**: Uses VITE_API_URL for API endpoint configuration
- **No Hardcoding**: All endpoints, timeouts, TTL values configurable

#### ✅ IV. Safe Deployment Practices
- **Infrastructure as Code**: workflow_orders table defined in pulumi/dynamodb.py
- **Docker-Based Lambda**: Existing deployment process unchanged
- **Deployment Script**: Uses ./deploy.sh (documented in quickstart.md)
- **Conventional Commits**: Feature follows `feat:` format

#### ✅ V. Domain Model Integrity
- **Model Boundaries**: WorkflowOrder domain model separate from API models
- **Existing Patterns**: Follows WorkflowListItem extension pattern
- **Immutable Records**: Orders are write-once (no updates)
- **Explicit Types**: Uses enums for direction, order_type, asset_type

### Verification:

| Constitution Principle | Compliant | Evidence |
|------------------------|-----------|----------|
| Layered Architecture | ✅ | data-model.md shows clear layer separation |
| Clean Code First | ✅ | No over-engineering, uses existing patterns |
| Configuration-Driven | ✅ | TTL constant, API URL from env vars |
| Safe Deployment | ✅ | Pulumi for infrastructure, ./deploy.sh |
| Domain Model Integrity | ✅ | WorkflowOrder follows existing conventions |

**Status**: ✅ **PASS** - All constitution principles respected in design phase

No violations introduced. Design follows existing architectural patterns and extends them appropriately.
