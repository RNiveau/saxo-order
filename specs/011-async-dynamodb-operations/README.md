# Async DynamoDB Operations: Complete Research & Migration Documentation

**Date**: 2026-02-22
**Project**: saxo-order
**Phase**: Phase 0 Complete - Research Documentation
**Status**: Ready for Phase 1 Implementation

---

## Overview

This directory contains comprehensive research and migration guidance for converting the saxo-order project from synchronous `boto3` to asynchronous `aioboto3` for DynamoDB operations. The migration enables true concurrent request handling in FastAPI, improving throughput from sequential (10+ seconds for 10 requests) to parallel (2 seconds for 10 requests) execution.

---

## Documentation Files

### 1. **research.md** (39 KB - Primary Research Document)

**Purpose**: Complete Phase 0 research answering all 5 research questions

**Contents**:
- Executive Summary and Key Findings
- Research Topic 1: aioboto3 Session Lifecycle Management
  - Session creation and context manager requirements
  - Three implementation patterns (short-lived, long-lived with lifespan, AsyncExitStack)
  - FastAPI lifespan context manager details
  - Configuration recommendations

- Research Topic 2: Async/Await Migration Strategy
  - API differences table (boto3 vs aioboto3)
  - Side-by-side code patterns for all operations:
    - get_item (simple lookup)
    - put_item (insert/upsert)
    - query (with pagination)
    - scan (with pagination)
    - update_item (modify)
    - delete_item (remove)
    - batch_writer (bulk operations)
    - Pagination helper pattern
  - Error handling changes
  - Pagination details

- Research Topic 3: Testing Strategy
  - pytest-asyncio configuration
  - Async test function patterns
  - Mocking async context managers (3 approaches)
  - Complete testing examples
  - aiomoto for in-memory testing
  - Async fixture patterns

- Research Topic 4: Connection Pool & Performance
  - Pool sizing recommendations by environment
  - Timeout configuration
  - Performance under concurrent load
  - Lambda considerations
  - Local development performance

- Research Topic 5: CLI Compatibility
  - Four approaches evaluated
  - Recommended: asyncio.run() wrapper
  - Nested event loop handling
  - Alternative approaches with pros/cons

**Key Section**: Summary: Migration Patterns and Templates with complete checklist

**When to Use**: Read this first for comprehensive understanding of all aspects

---

### 2. **MIGRATION_GUIDE.md** (28 KB - Practical Reference)

**Purpose**: Side-by-side migration patterns and implementation reference

**Contents**:
- API Differences Quick Reference (table format)
- Method-by-Method Migration Templates (7 templates):
  1. get_item (simple key lookup)
  2. put_item (insert/upsert)
  3. query (filtered search with pagination)
  4. scan (full table scan with pagination)
  5. update_item (modify existing)
  6. delete_item (remove item)
  7. batch_writer (bulk with auto-batching)
  8. Pagination helper (reusable pattern)

- Each template includes:
  - Current boto3 code
  - Migrated aioboto3 code
  - Changes highlighted
  - Key concepts explained

- Error Handling Section:
  - DynamoDB exception types (same as boto3)
  - Automatic retry configuration
  - HTTP status code checking patterns
  - Exception-based vs status code handling

- Testing Guide:
  - Async test functions
  - Three mocking patterns
  - Complete examples
  - aiomoto alternative
  - Fixture patterns

- Configuration Reference:
  - Session initialization options
  - FastAPI lifespan integration
  - CLI integration pattern

- Troubleshooting:
  - 7 common issues with solutions
  - Debug checklist

**When to Use**: Keep open while coding for quick reference and copy/paste patterns

---

### 3. **CODE_TEMPLATES.md** (27 KB - Copy/Paste Ready Code)

**Purpose**: Production-ready code templates for immediate use

**Contents**:

#### FastAPI Application Setup
- `api/main.py`: Complete lifespan setup with aioboto3
- `api/dependencies.py`: Dependency injection pattern
- `api/routers/example.py`: Route handler with DynamoDB integration

#### DynamoDBClient Class (Complete)
- Full AsyncDynamoDBClient implementation with all methods:
  - Initialization and resource management
  - All 20+ CRUD operations
  - Helper methods for pagination
  - Error handling patterns
  - Float-to-Decimal conversion
  - Country code normalization

#### Service Layer Template
- WorkflowService example with async methods
- Proper error handling
- Dependency injection

#### CLI Command Template
- Async CLI commands with Click
- asyncio.run() wrapper pattern
- Multiple command examples

#### Testing Templates
- Async test function examples
- Mocking patterns (AsyncMock, context managers)
- Pagination testing
- Error handling tests
- Fixture examples (mock and real)

**When to Use**: Copy entire sections and customize for your use case

---

### 4. **plan.md** (14 KB - Project Planning)

**Status**: Already present from project initialization

**Contains**:
- Implementation Plan overview
- Constitution Check (passes all gates)
- Project Structure mapping
- Phase 0: Research topics definition
- Phase 1-2: Design and implementation planning
- Complexity tracking
- Timeline estimates

**When to Use**: Reference for understanding project scope and timeline

---

### 5. **spec.md** (12 KB - Feature Specification)

**Status**: Already present from project initialization

**Contains**:
- User scenarios and testing criteria (3 user stories)
- Functional requirements (10 FRs)
- Success criteria (6 measurable outcomes)
- Assumptions (8 key assumptions)
- Dependencies (internal and external)
- Scope boundaries (in/out of scope)
- Technical constraints
- Security considerations
- Open questions

**When to Use**: Reference for understanding requirements and acceptance criteria

---

## Key Findings Summary

### Recommended Architecture

```
FastAPI Application
    ├── Lifespan Context Manager
    │   ├── Startup: Initialize aioboto3 session
    │   └── Shutdown: Close resources
    │
    ├── API Routers (async endpoints)
    │   ├── Dependency: Get DynamoDBClient from app.state
    │   └── Operations: await service.async_method()
    │
    ├── Service Layer (async methods)
    │   └── Operations: await db_client.async_method()
    │
    └── DynamoDBClient (async operations)
        └── Operations: await table.get_item(), scan(), etc.

CLI Commands
    └── asyncio.run(service.async_method())
```

### Quick Reference Table

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Async Framework** | aioboto3 | Native async support, boto3 compatibility, proven in production |
| **Session Mgmt** | FastAPI lifespan | Proper resource cleanup, reuses session across requests |
| **Pool Size** | 10 (default, tunable) | Covers spec's 50 concurrent requests, can increase if needed |
| **Timeout** | 5 seconds per op | Matches spec requirement, prevents indefinite hangs |
| **Retry Strategy** | Exponential backoff, mode=adaptive, max 3 attempts | AWS recommended, handles throttling automatically |
| **CLI Pattern** | asyncio.run() wrapper | Minimal boilerplate, standard Python pattern |
| **Testing** | pytest-asyncio + AsyncMock | Parallel test execution, clean mocking approach |
| **Error Handling** | Try/except with ClientError | Same as boto3, botocore exceptions unchanged |

### Migration Effort Estimate

| Component | Effort | Notes |
|-----------|--------|-------|
| **Client Layer** | 4-6 hours | 20+ methods, straightforward async conversion |
| **Service Layer** | 1-2 hours | Add async/await keywords, await client calls |
| **API Layer** | 1-2 hours | await service calls (most routes already async) |
| **CLI Layer** | 30-60 min | asyncio.run() wrappers around async calls |
| **Testing** | 3-4 hours | Convert tests to async, update mocks |
| **Integration** | 2-3 hours | End-to-end testing, Lambda verification |
| **Total** | **12-18 hours** | Plus code review and optimization |

---

## How to Use This Documentation

### For Understanding the Migration
1. Start with **research.md** - Read Executive Summary and one research topic
2. Jump to **MIGRATION_GUIDE.md** - Review "API Differences Quick Reference" table
3. Find your operation in **CODE_TEMPLATES.md** - Copy the template

### For Implementation
1. Open **CODE_TEMPLATES.md**
2. Find the operation you're implementing (get_item, put_item, etc.)
3. Copy the template
4. Customize for your use case
5. Refer to **MIGRATION_GUIDE.md** for details on that operation

### For Testing
1. See "Testing Guide" section in **MIGRATION_GUIDE.md**
2. Copy test template from **CODE_TEMPLATES.md**
3. Customize for your test cases
4. Run with: `pytest --asyncio-mode=auto`

### For Troubleshooting
1. Check "Troubleshooting" section in **MIGRATION_GUIDE.md**
2. Find your issue in the 7 common problems
3. Review the solution and debug checklist

---

## Important Implementation Notes

### Session Management (Critical)
- ✅ **DO**: Use `async with session.resource('dynamodb')` for resource access
- ❌ **DON'T**: Use `session.resource()` without context manager (breaks resource cleanup)
- ✅ **DO**: Store session in FastAPI app.state for reuse across requests
- ❌ **DON'T**: Create new session per request (inefficient)

### Error Handling (Important)
- All exceptions remain from botocore (same as boto3)
- ResponseMetadata checking works identically
- Retry logic is automatic via botocore config
- Handle `ClientError` for specific error codes
- Handle `BotoCoreError` for network issues

### Testing (Important)
- Use `AsyncMock` for async operations
- Mock `__aenter__` and `__aexit__` for context managers
- Use `aiomoto` for integration tests if needed
- Add `@pytest.mark.asyncio` to async test functions
- Set `asyncio_mode = auto` in pytest.ini

### CLI Commands (Important)
- Wrap async calls with `asyncio.run()` at command entry point
- Initialize async resources inside the asyncio.run() context
- Clean up resources in finally block
- Don't nest `asyncio.run()` calls

---

## Phase 1 Readiness Checklist

Before moving to Phase 1 (Design & Implementation), verify:

- [ ] All research documents reviewed and understood
- [ ] Team familiar with async/await patterns
- [ ] Development environment supports pytest-asyncio
- [ ] DynamoDB Local or AWS access confirmed
- [ ] Code templates reviewed and customized examples created
- [ ] Timeline estimates accepted (12-18 hours)
- [ ] Acceptance criteria from spec understood

---

## Related Documents

- **plan.md**: Project planning and phasing
- **spec.md**: Feature requirements and acceptance criteria
- **checklists/requirements.md**: Quality requirements checklist

---

## Quick Links to Source Code

Current boto3 Usage:
- `/Users/kiva/codes/saxo-order/client/aws_client.py` (DynamoDBClient - to be refactored)

Related Files:
- `/Users/kiva/codes/saxo-order/api/main.py` (FastAPI app - will add lifespan)
- `/Users/kiva/codes/saxo-order/services/workflow_service.py` (Service layer - will make async)
- `/Users/kiva/codes/saxo-order/tests/client/test_aws_client.py` (Tests - will update)

---

## External References

### Official Documentation
- [aioboto3 GitHub](https://github.com/terricain/aioboto3)
- [aioboto3 ReadTheDocs](https://aioboto3.readthedocs.io/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [boto3 DynamoDB Docs](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/)
- [AWS DynamoDB Error Handling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html)

### Testing Resources
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [aiomoto GitHub](https://github.com/getmoto/moto)

### Community Guides
- [How to Access DynamoDB in FastAPI](https://retz.dev/blog/how-to-access-dynamodb-in-fastapi/)
- [FastAPI Discussion: Long-lived Client](https://github.com/fastapi/fastapi/discussions/6068)

---

## Document Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-22 | 1.0 | Initial complete research and documentation |

---

## Support & Questions

For questions about this migration:
1. Check the relevant documentation file (see "How to Use" section above)
2. Review troubleshooting section in MIGRATION_GUIDE.md
3. Check research.md for detailed explanations
4. Refer to external documentation links above

---

**Status**: Phase 0 Complete - Ready for Phase 1 Implementation Planning

**Next Step**: Run Phase 1 design and implementation planning based on findings documented here.
