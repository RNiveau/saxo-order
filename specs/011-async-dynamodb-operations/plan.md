# Implementation Plan: Async DynamoDB Operations

**Branch**: `011-async-dynamodb-operations` | **Date**: 2026-02-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-async-dynamodb-operations/spec.md`

## Summary

Migrate DynamoDB operations from synchronous boto3 to asynchronous aioboto3 to enable true concurrent request handling in FastAPI. Currently, async endpoints call synchronous boto3 methods which block the event loop and prevent parallel request processing. This refactor enables the API to handle multiple requests concurrently, improving throughput from sequential (10+ seconds for 10 requests) to parallel (2 seconds for 10 requests) execution.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI 0.121+, aioboto3 13.0+ (replacing boto3 1.40+), uvicorn 0.38+, pytest 9.0+
**Storage**: AWS DynamoDB (6 tables: indicators, watchlist, asset_details, alerts, workflows, workflow_orders)
**Testing**: pytest with pytest-asyncio for async test support, unittest.mock for mocking
**Target Platform**: AWS Lambda (Python 3.11 runtime, Docker containers) + local development environment
**Project Type**: Web application (backend at repository root, frontend in `frontend/` directory)
**Performance Goals**: 10x throughput improvement - 10 concurrent requests complete in ~2 seconds (vs 10+ seconds sequentially), <200ms p95 for simple operations
**Constraints**: 5 second timeout per DynamoDB operation, 10 concurrent connection pool size (default), graceful degradation on failures
**Scale/Scope**: 50 concurrent API requests, 20+ DynamoDB client methods to migrate, 3 service classes affected, 6 API routers to update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Layered Architecture Discipline

**Status**: ✅ PASS

- **Service Layer**: Will update to async methods with proper await syntax
- **Client Layer**: DynamoDBClient will be refactored to use aioboto3, maintaining same method signatures (async)
- **API Layer**: Routers will await service calls (already async, just need proper await chain)
- **No Layer Violations**: Services continue to call client methods (not direct Table() access)
- **Dependency Injection**: DynamoDBClient instance passed to services via constructor (existing pattern)

**Enforcement**:
- All service methods calling DynamoDB will have `async` keyword
- All client methods will use `async/await` with aioboto3
- No direct `dynamodb.Table()` access from service layer (already enforced per constitution 1.2.1)

### II. Clean Code First

**Status**: ✅ PASS

- **Self-Documenting**: Async/await syntax is clearer than thread pool executors or callbacks
- **No Over-Engineering**: Direct migration from boto3 to aioboto3 (same API surface)
- **Enum-Driven**: No changes to enum usage (orthogonal concern)
- **No Unnecessary Comments**: Code changes are mechanical (add async/await keywords)

### III. Configuration-Driven Design

**Status**: ✅ PASS (with note)

- **Connection Pool Size**: Will use default of 10, can add environment variable later if needed
- **Timeout Configuration**: 5-second timeout per operation (can be made configurable)
- **AWS Credentials**: Continue using boto3/aioboto3 credential chain (no changes)
- **No Hardcoding**: Session configuration will be in client initialization (not scattered)

**Note**: Starting with hardcoded defaults per spec's "Assumptions" section. Can add env var configuration in future if performance tuning needed.

### IV. Safe Deployment Practices

**Status**: ✅ PASS

- **Pulumi**: No infrastructure changes needed (IAM policies already exist)
- **Docker Lambda**: Dockerfile will add aioboto3 dependency (Poetry manages it)
- **Deployment Script**: Standard `./deploy.sh` workflow unchanged
- **Testing**: All existing tests will be updated to async mocking patterns

### V. Domain Model Integrity

**Status**: ✅ PASS (not applicable)

- **No Model Changes**: Domain models (Alert, Workflow, Candle, etc.) remain unchanged
- **No API Contract Changes**: DynamoDB operations return same data structures
- **No Business Logic Changes**: Only execution model changes (sync → async)

---

**Constitution Compliance Summary**: ✅ ALL GATES PASS

No constitution violations. This is a clean internal refactor that:
- Maintains existing architectural layers
- Improves code quality through proper async patterns
- Uses configuration-driven approach
- Follows safe deployment practices
- Preserves domain model integrity

**Pre-Design Check**: ✅ PROCEED TO PHASE 0 (Research)

## Project Structure

### Documentation (this feature)

```text
specs/011-async-dynamodb-operations/
├── plan.md              # This file (/speckit.plan output)
├── spec.md              # Feature specification (already complete)
├── checklists/          # Quality checklists (already complete)
├── research.md          # Phase 0 output (next step)
├── data-model.md        # Phase 1 output (N/A - no new entities)
├── quickstart.md        # Phase 1 output (testing guide)
└── contracts/           # Phase 1 output (N/A - no API contract changes)
```

### Source Code (repository root)

```text
# Backend (repository root)
client/
└── aws_client.py                  # 🔄 REFACTOR: DynamoDBClient to aioboto3

services/
├── workflow_service.py            # 🔄 UPDATE: add async/await
├── candles_service.py             # ✅ NO CHANGE: doesn't use DynamoDB
├── alerting_service.py            # 🔄 UPDATE: add async/await (if uses DynamoDB)
└── watchlist_service.py           # 🔄 UPDATE: add async/await (if uses DynamoDB)

api/
├── main.py                        # 🔄 UPDATE: lifespan for session init/cleanup
└── routers/
    ├── workflow.py                # 🔄 UPDATE: await service calls
    ├── watchlist.py               # 🔄 UPDATE: await service calls
    ├── indicator.py               # 🔄 UPDATE: await service calls
    └── order.py                   # 🔄 UPDATE: await service calls (if uses DynamoDB)

saxo_order/commands/
├── workflow.py                    # 🔄 UPDATE: asyncio.run() wrapper for CLI
└── alert.py                       # 🔄 UPDATE: asyncio.run() wrapper for CLI (if uses DynamoDB)

lambda_function.py                 # 🔄 UPDATE: async handler if needed

tests/
├── client/
│   └── test_aws_client.py         # 🔄 UPDATE: async test mocks
├── services/
│   └── test_workflow_service.py   # 🔄 UPDATE: pytest-asyncio fixtures
└── api/routers/
    └── test_workflow.py           # 🔄 UPDATE: httpx.AsyncClient for testing

# Frontend (no changes)
frontend/                          # ✅ NO CHANGE: API contracts unchanged
```

**Structure Decision**: Web application structure with backend at root, frontend in subdirectory. Backend follows layered architecture: CLI → API → Service → Client → External APIs (DynamoDB). This refactor affects Client layer (aioboto3 migration) and propagates async/await up through Service and API layers. CLI commands will wrap async operations with `asyncio.run()` for backward compatibility.

## Complexity Tracking

> **Empty - No Constitution Violations**

All constitution checks pass. This refactor:
- Maintains strict layered architecture (Service → Client → DynamoDB)
- Improves code clarity through proper async patterns
- Uses existing dependency injection (services receive DynamoDBClient)
- Preserves domain model integrity (no business logic changes)
- Follows safe deployment practices (Pulumi, Docker, testing)

No additional complexity introduced beyond inherent async programming model.

---

# PHASE 0: Research & Technical Decisions

## Research Topics

### 1. aioboto3 Session Lifecycle Management

**Question**: How should aioboto3 session be initialized, managed, and cleaned up in FastAPI application lifecycle?

**Research Areas**:
- FastAPI lifespan context manager for async resource initialization
- aioboto3.Session() vs aioboto3.Resource() patterns
- Connection pooling configuration (max_pool_connections)
- Graceful shutdown and resource cleanup

**Expected Output**: Best practice pattern for session initialization in `api/main.py` using FastAPI lifespan events.

### 2. Async/Await Migration Strategy for DynamoDB Operations

**Question**: What's the best approach to migrate 20+ synchronous DynamoDB methods to async while maintaining backward compatibility for tests?

**Research Areas**:
- boto3 → aioboto3 API differences (method names, parameters)
- Context manager usage (`async with` for resource management)
- Error handling differences between sync and async boto clients
- Pagination handling for scan/query operations in async context

**Expected Output**: Migration patterns and code templates for common operations (get_item, put_item, query, scan, update_item, delete_item).

### 3. Testing Strategy for Async Code

**Question**: How to test async DynamoDB operations with pytest and maintain test isolation?

**Research Areas**:
- pytest-asyncio plugin configuration and fixtures
- Mocking async context managers (`async with`)
- unittest.mock.AsyncMock vs unittest.mock.MagicMock
- Test isolation when using shared async session

**Expected Output**: Testing patterns and fixture examples for async DynamoDB operations.

### 4. Connection Pool Sizing and Performance Tuning

**Question**: What connection pool size and timeout values optimize for Lambda and local development environments?

**Research Areas**:
- AWS Lambda concurrency model and connection reuse
- aioboto3 max_pool_connections parameter tuning
- Timeout strategies (connect_timeout, read_timeout)
- Trade-offs between pool size and memory consumption

**Expected Output**: Recommended connection pool configuration with justification.

### 5. CLI Compatibility Pattern

**Question**: How to make async DynamoDB client work in synchronous CLI command context?

**Research Areas**:
- asyncio.run() wrapper pattern for CLI commands
- Event loop management in Click command decorators
- Trade-offs between sync wrapper vs fully async CLI
- Alternative: separate sync client for CLI vs async client for API

**Expected Output**: Decision on CLI approach (asyncio.run wrapper vs dual clients) with implementation pattern.

---

**Research Phase Status**: 🔄 PENDING - Run research agents in Phase 0

**Next Step**: Execute Phase 0 research to resolve all "Expected Output" items, document findings in `research.md`.

---

# PHASE 1: Design & Contracts

**Prerequisites**: ✅ Phase 0 (research.md) complete

## Design Artifacts

### data-model.md

**Status**: ✅ N/A - Not applicable for this feature

**Rationale**: This is a technical refactor that doesn't introduce new entities or modify existing domain models. All DynamoDB table schemas remain unchanged. The refactor only changes the execution model (sync → async) of existing operations.

### contracts/

**Status**: ✅ N/A - Not applicable for this feature

**Rationale**: No API contract changes. All FastAPI endpoints maintain the same request/response schemas. The change from sync to async is transparent to API consumers - same HTTP endpoints, same JSON payloads, same status codes. Only internal execution model changes.

### quickstart.md

**Status**: 🔄 PENDING Phase 1 generation

**Content**:
1. **Local Development Setup**:
   - Install dependencies (`poetry install`)
   - Configure DynamoDB Local for testing
   - Run async API server (`poetry run python run_api.py`)
   - Verify async behavior with concurrent requests

2. **Testing Async Operations**:
   - Run async tests (`poetry run pytest -v`)
   - Test concurrent API requests (script example)
   - Verify connection pool behavior
   - Check error handling under load

3. **Manual Verification**:
   - Load test script for 10 concurrent GET /api/workflows requests
   - Expected results: ~2 seconds total (not 10+ seconds)
   - Monitor logs for async operation timing
   - Verify connection pool statistics

**Next Step**: Generate `quickstart.md` after research phase completes.

---

**Design Phase Status**: 🔄 PENDING - Waiting for Phase 0 research

**Phase 1 Outputs**:
- ✅ data-model.md: N/A (no new entities)
- ✅ contracts/: N/A (no API changes)
- 🔄 quickstart.md: Pending generation

---

# PHASE 2: Agent Context Update

**Prerequisites**: Phase 1 complete (design artifacts generated)

**Action**: Run `.specify/scripts/bash/update-agent-context.sh claude`

**Changes**:
- Add `aioboto3` to active technologies
- Document async/await patterns for DynamoDB operations
- Note connection pool configuration approach

**Status**: 🔄 PENDING - Execute after Phase 1

---

**Post-Design Constitution Check**: 🔄 PENDING - Re-evaluate after Phase 1 complete

Expected result: All gates continue to pass (no design introduces new complexity or violations).

---

# Next Steps

1. **Execute Phase 0 Research** (next immediate step):
   - Research aioboto3 session lifecycle patterns
   - Research async migration strategies
   - Research testing patterns for async code
   - Research connection pool configuration
   - Research CLI compatibility approaches
   - Document all findings in `research.md`

2. **Generate Phase 1 Artifacts**:
   - Generate `quickstart.md` with testing scenarios
   - Skip data-model.md and contracts/ (not applicable)

3. **Update Agent Context**:
   - Run update script to add aioboto3 technology

4. **Ready for /speckit.tasks**:
   - After Phase 0 and Phase 1 complete, run `/speckit.tasks`
   - Task breakdown will reference research findings
   - Tasks will follow migration patterns documented in research

**Command Status**: ✅ PLAN TEMPLATE FILLED - Ready to proceed with Phase 0 research
