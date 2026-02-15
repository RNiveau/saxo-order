# Implementation Plan: Workflow Management UI & Database Migration

**Branch**: `009-workflow-db-ui` | **Date**: 2026-02-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-workflow-db-ui/spec.md`

## Summary

Migrate workflow storage from workflows.yml to DynamoDB and create a web UI for viewing all workflows with filtering, sorting, and detail views. The Lambda function will load workflows from DynamoDB (with YAML fallback), and new API endpoints will support the frontend workflow management page. This enables traders to view and monitor all active trading strategies without needing CLI access or S3/YAML file knowledge.

**Technical Approach** (from research.md):
- DynamoDB with simple partition key (id) and nested JSON storage for conditions/trigger
- Scan with FilterExpression for queries (no GSI for MVP at 50-100 workflow scale)
- React custom table component with client-side pagination, filtering, and sorting
- Python migration script using boto3 batch_writer with UUID generation
- FastAPI endpoints for listing and detail retrieval
- Lambda fallback mechanism (DynamoDB → S3/YAML if unavailable)

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ (frontend)
**Primary Dependencies**:
- Backend: FastAPI, boto3 (DynamoDB client), Pydantic, PyYAML
- Frontend: React 19+, React Router DOM v7+, Axios, Vite 7+

**Storage**: AWS DynamoDB (PAY_PER_REQUEST billing mode), table: `workflows`, partition key: `id` (UUID v4)
**Testing**: pytest with moto (DynamoDB mocking) for backend, no frontend tests (framework not configured)
**Target Platform**: AWS Lambda (Python 3.11 runtime), web browser (modern browsers supporting ES2022)
**Project Type**: Web application (backend API + frontend SPA)
**Performance Goals**:
- Workflow list page load: <2 seconds
- Filter/sort response: <500ms (client-side)
- API response time: <2 seconds for 100 workflows
- Lambda workflow loading: <5 seconds

**Constraints**:
- Database migration must be idempotent and reversible
- Lambda must gracefully fall back to YAML if DynamoDB unavailable
- Client-side filtering/sorting suitable for 50-1000 workflows
- No workflow creation/editing UI (out of scope)

**Scale/Scope**:
- 50-100 workflows initially, support up to 1000 workflows
- 4 backend API endpoints (2 new: list, detail)
- 3 frontend pages/components (1 new: Workflows page)
- Single DynamoDB table with nested JSON structure

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Layered Architecture Discipline

**Backend Layers**:
- ✅ CLI Layer: No CLI commands added (out of scope)
- ✅ API Layer: New routers in `api/routers/` for `/api/workflows` and `/api/workflows/{id}`
- ✅ Service Layer: New `WorkflowService` in `services/` - orchestrates DynamoDBClient
- ✅ Client Layer: Extend existing `DynamoDBClient` in `client/dynamodb_client.py` with workflow methods
- ✅ Model Layer: New `WorkflowDetail`, `WorkflowListItem` models in `model/`

**Frontend Layers**:
- ✅ Pages: New `Workflows.tsx` in `frontend/src/pages/`
- ✅ Components: New `WorkflowTable.tsx`, `WorkflowDetailModal.tsx` in `frontend/src/components/`
- ✅ Services: Extend `frontend/src/services/api.ts` with workflow endpoints
- ✅ Utils: No new utils required

**Compliance**:
- ✅ Service receives DynamoDBClient via dependency injection
- ✅ Client methods return domain models (Workflow objects), not raw boto3 responses
- ✅ Frontend API calls only through services layer
- ✅ No client internals access (e.g., no `client.dynamodb.Table()` from service)
- ✅ Client exposes workflow CRUD methods - encapsulates boto3 operations

**PASS**: All architectural layers respected with proper separation of concerns.

### II. Clean Code First

**Compliance**:
- ✅ Use existing enums: `UnitTime`, `IndicatorType`, `Direction`, `OrderDirection`, `Signal`
- ✅ No unnecessary inline comments
- ✅ Self-documenting code with clear method names
- ✅ No premature abstractions (MVP scope only)

**PASS**: Feature follows clean code principles.

### III. Configuration-Driven Design

**Backend Configuration**:
- ✅ DynamoDB table name hardcoded as `"workflows"` (existing pattern - follows indicators, watchlist, asset_details, alerts)
- ✅ No hardcoded API endpoints or timeouts (constitution applies to external integrations, not infrastructure identifiers)
- ✅ Migration script uses hardcoded table name consistent with existing client code

**Frontend Configuration**:
- ✅ API URL via `VITE_API_URL` environment variable
- ✅ No hardcoded backend endpoints

**PASS**: Configuration externalized for external integrations per constitution standards. Infrastructure identifiers (table names) follow existing hardcoded pattern.

### IV. Safe Deployment Practices

**Compliance**:
- ✅ DynamoDB table creation via Pulumi (`pulumi/dynamodb.py`)
- ✅ Lambda deployment via Docker + `./deploy.sh`
- ✅ Conventional commit messages for all changes
- ✅ No manual AWS console changes

**PASS**: Infrastructure as code and safe deployment practices followed.

### V. Domain Model Integrity

**Compliance**:
- ✅ Workflow model reflects business reality (trading strategies)
- ✅ Indicator enums match existing domain model
- ✅ No `country_code` inference - workflows reference assets by index symbol only
- ✅ Model boundaries respected (Workflow objects used throughout, not raw DynamoDB items)

**PASS**: Domain model integrity maintained.

### Quality Gates

**Pre-Commit Gates**:
- ✅ Conventional commit format enforced
- ✅ Black + isort formatting required
- ✅ MyPy type checking required
- ✅ TypeScript compilation required
- ✅ No hardcoded API URLs in frontend

**Pre-Merge Gates**:
- ✅ pytest test suite passes
- ✅ Architecture layers respected
- ✅ No hardcoded strings where enums exist
- ✅ Vite build succeeds
- ✅ TypeScript interfaces match Pydantic models

**PASS**: All quality gates can be satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/009-workflow-db-ui/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Technical research (complete)
├── data-model.md        # Entity definitions (complete)
├── contracts/           # API contracts (complete)
│   └── workflows-api.yaml
├── checklists/          # Quality validation (complete)
│   └── requirements.md
└── tasks.md             # Implementation tasks (pending - /speckit.tasks)
```

### Source Code (repository root)

```text
# Web application structure (Option 2 from template)

backend/ (Python 3.11)
├── api/
│   ├── main.py                     # FastAPI app with CORS configuration
│   └── routers/
│       └── workflows.py            # NEW: /api/workflows endpoints
├── services/
│   └── workflow_service.py         # NEW: WorkflowService with business logic
├── client/
│   └── dynamodb_client.py          # EXISTING: Extend with workflow methods
├── model/
│   ├── workflow.py                 # EXISTING: Workflow domain model
│   ├── workflow_api.py             # NEW: WorkflowDetail, WorkflowListItem
│   └── indicator.py                # EXISTING: Indicator, Condition models
├── engines/
│   └── workflow.py                 # EXISTING: Update to load from DynamoDB
└── tests/
    ├── services/
    │   └── test_workflow_service.py   # NEW: Service unit tests
    └── integration/
        └── test_workflows_api.py      # NEW: API integration tests

frontend/ (TypeScript 5+, React 19+)
├── src/
│   ├── pages/
│   │   └── Workflows.tsx           # NEW: Workflow management page
│   ├── components/
│   │   ├── WorkflowTable.tsx       # NEW: Table with filtering/sorting
│   │   └── WorkflowDetailModal.tsx # NEW: Detail view modal
│   ├── services/
│   │   └── api.ts                  # EXISTING: Extend with workflow endpoints
│   └── utils/
│       └── workflowFormatters.ts   # NEW: Format workflow data for display
└── tests/
    └── (no tests - framework not configured)

pulumi/
└── dynamodb.py                      # EXISTING: Add workflows table definition

scripts/
└── migrate_workflows.py             # NEW: One-time YAML → DynamoDB migration

lambda/
└── lambda_function.py               # EXISTING: Update to load from DynamoDB
```

**Structure Decision**: Web application structure with existing backend/ and frontend/ separation. Feature adds new API router, service, and frontend page while extending existing DynamoDB client and Lambda function. Migration script lives in scripts/ for one-time execution.

## Complexity Tracking

> **No constitution violations - this section left empty per template guidance.**

## Phase 0: Research (COMPLETE)

**Status**: ✅ Complete - research.md generated with 10 technical decisions

**Key Decisions**:
1. DynamoDB simple partition key (id) with nested JSON - avoids complex joins
2. Scan with FilterExpression (no GSI) - suitable for 50-100 workflow scale
3. Migration with batch_writer - automatic batching and retry logic
4. Custom React table component - aligns with existing codebase patterns
5. Client-side pagination/filtering/sorting - instant UX, no API latency
6. React hooks + URL query parameters - shareable/bookmarkable state
7. Separate route for detail view - deep linking support
8. Visibility API + setInterval - efficient auto-refresh pattern
9. Lambda fallback to YAML - graceful degradation during migration rollout

**Artifacts**: [research.md](./research.md) with rationale, alternatives, and cost analysis.

## Phase 1: Design & Contracts (COMPLETE)

**Status**: ✅ Complete - data-model.md and contracts/workflows-api.yaml generated

**Data Model** ([data-model.md](./data-model.md)):
- **Workflow**: Main entity with id, name, index, cfd, enable, dry_run, is_us, end_date, conditions (array), trigger (object), timestamps
- **Condition**: Nested entity with indicator, close, element
- **Indicator**: Nested with name, ut, value, zone_value
- **Close**: Nested with direction, ut, spread
- **Trigger**: Nested with ut, signal, location, order_direction, quantity

**API Contracts** ([contracts/workflows-api.yaml](./contracts/workflows-api.yaml)):
- `GET /api/workflows` with query params: page, per_page, enabled, index, indicator_type, dry_run, sort_by, sort_order
- `GET /api/workflows/{id}` returns WorkflowDetail with complete configuration
- Response schemas: WorkflowListResponse, WorkflowSummary, WorkflowDetail, Error

**Quickstart**: Not yet generated - will create in next step.

## Phase 2: Quickstart Documentation

**Purpose**: Create developer onboarding guide showing how to run migration, start API, and test workflows UI.

**Status**: ⏳ Pending - will generate quickstart.md

## Post-Design Constitution Re-Check

**Status**: ✅ PASS - no violations introduced during design phase

- Architecture layers maintained (API → Service → Client → Model)
- No configuration hardcoding (table name from config)
- Domain model integrity preserved (Workflow objects throughout)
- Safe deployment via Pulumi (workflows table creation)
- Clean code principles followed (enum usage, no premature abstraction)

**Conclusion**: Design ready for task generation via `/speckit.tasks` command.

## Next Steps

1. ✅ Research complete (research.md)
2. ✅ Data model complete (data-model.md)
3. ✅ API contracts complete (contracts/workflows-api.yaml)
4. ⏳ **Generate quickstart.md** - developer onboarding guide
5. ⏳ **Run `/speckit.tasks`** - generate implementation task checklist
6. ⏳ **Implementation** - execute tasks in dependency order
7. ⏳ **Testing** - manual smoke tests (no test framework for frontend)
8. ⏳ **Deployment** - Pulumi update + Lambda redeploy

**Ready for**: `/speckit.tasks` command to generate tasks.md implementation checklist.
