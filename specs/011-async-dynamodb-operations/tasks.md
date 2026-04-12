# Tasks: Async DynamoDB Operations Migration

**Input**: Design documents from `/specs/011-async-dynamodb-operations/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: No dedicated test tasks - tests will be updated inline during implementation per research findings

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend at root**: `client/`, `services/`, `api/`, `saxo_order/commands/`, `tests/`
- **Frontend**: `frontend/src/` (no changes for this feature)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add aioboto3 dependency and configure async testing infrastructure

- [x] T001 Add aioboto3 = "^13.0.0" to [tool.poetry.dependencies] in pyproject.toml
- [x] T002 Add pytest-asyncio = "^1.0.0" to [tool.poetry.dev-dependencies] in pyproject.toml (^1.0.0 needed for pytest ^9 compat)
- [x] T003 [P] Add asyncio_mode = "auto" to [tool.pytest.ini_options] in pyproject.toml
- [x] T004 Run `poetry install` to install new dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migrate DynamoDBClient to aioboto3 - MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Core Client Migration

- [x] T005 [P] Create backup of client/aws_client.py before making changes
- [x] T006 Update DynamoDBClient.__init__() to store aioboto3 session in client/aws_client.py (lines 65-68)
- [x] T007 [P] Add async def to store_indicator() method signature in client/aws_client.py (line 107)
- [x] T008 [P] Add await for table access and operations in store_indicator() in client/aws_client.py (lines 116-124)
- [x] T009 [P] Add async def to get_indicator() method signature in client/aws_client.py (line 129)
- [x] T010 [P] Add await for table access and operations in get_indicator() in client/aws_client.py (lines 132-140)
- [x] T011 [P] Add async def to get_indicator_by_id() method signature in client/aws_client.py (line 142)
- [x] T012 [P] Add await for table access and operations in get_indicator_by_id() in client/aws_client.py (lines 143-149)
- [x] T013 [P] Add async def to add_to_watchlist() method signature in client/aws_client.py (line 151)
- [x] T014 [P] Add await for table access and operations in add_to_watchlist() in client/aws_client.py (lines 181-184)
- [x] T015 [P] Add async def to get_watchlist() method signature in client/aws_client.py (line 186)
- [x] T016 [P] Add await for table access and operations in get_watchlist() in client/aws_client.py (lines 188-192)
- [x] T017 [P] Add async def to remove_from_watchlist() method signature in client/aws_client.py (line 194)
- [x] T018 [P] Add await for table access and operations in remove_from_watchlist() in client/aws_client.py (lines 196-201)
- [x] T019 [P] Add async def to is_in_watchlist() method signature in client/aws_client.py (line 203)
- [x] T020 [P] Add await for table access and operations in is_in_watchlist() in client/aws_client.py (lines 205-208)
- [x] T021 [P] Add async def to get_watchlist_item() method signature in client/aws_client.py (line 210)
- [x] T022 [P] Add await for table access and operations in get_watchlist_item() in client/aws_client.py (lines 216-223)
- [x] T023 [P] Add async def to update_watchlist_labels() method signature in client/aws_client.py (line 225)
- [x] T024 [P] Add await for table access and operations in update_watchlist_labels() in client/aws_client.py (lines 229-237)
- [x] T025 [P] Add async def to set_asset_detail() method signature in client/aws_client.py (line 239)
- [x] T026 [P] Add await for table access and operations in set_asset_detail() in client/aws_client.py (lines 251-254)
- [x] T027 [P] Add async def to get_asset_detail() method signature in client/aws_client.py (line 256)
- [x] T028 [P] Add await for table access and operations in get_asset_detail() in client/aws_client.py (lines 258-264)
- [x] T029 [P] Add async def to get_tradingview_link() method signature in client/aws_client.py (line 266)
- [x] T030 [P] Add await for get_asset_detail() call in get_tradingview_link() in client/aws_client.py (line 268)
- [x] T031 Add async def to get_all_tradingview_links() method signature in client/aws_client.py (line 273)
- [x] T032 Add await for table access and all scan operations including pagination in get_all_tradingview_links() in client/aws_client.py (lines 282-298)
- [x] T033 Add async def to get_excluded_assets() method signature in client/aws_client.py (line 316)
- [x] T034 Add await for table access and all scan operations including pagination in get_excluded_assets() in client/aws_client.py (lines 324-342)
- [x] T035 Add async def to update_asset_exclusion() method signature in client/aws_client.py (line 352)
- [x] T036 Add await for table access and update_item operation in update_asset_exclusion() in client/aws_client.py (lines 370-380)
- [x] T037 Add async def to get_all_asset_details() method signature in client/aws_client.py (line 395)
- [x] T038 Add await for table access and all scan operations including pagination in get_all_asset_details() in client/aws_client.py
- [x] T039 Add async def to store_alerts() method signature in client/aws_client.py (line 430)
- [x] T040 Add await for table access and batch_writer context manager in store_alerts() in client/aws_client.py (change `with` to `async with` and await put_item)
- [x] T041 Add async def to get_alerts() method signature in client/aws_client.py (line 535)
- [x] T042 Add await for table access and get_item operation in get_alerts() in client/aws_client.py
- [x] T043 Add async def to get_all_alerts() method signature in client/aws_client.py (line 552)
- [x] T044 Add await for table access and all scan operations including pagination in get_all_alerts() in client/aws_client.py
- [x] T045 Add async def to get_last_run_at() method signature in client/aws_client.py (line 593)
- [x] T046 Add await for table access and scan operation in get_last_run_at() in client/aws_client.py
- [x] T047 Add async def to update_last_run_at() method signature in client/aws_client.py (line 632)
- [x] T048 Add await for table access and put_item operation in update_last_run_at() in client/aws_client.py
- [x] T049 Add async def to get_all_workflows() method signature in client/aws_client.py (line 655)
- [x] T050 Add await for table access and all scan operations including pagination in get_all_workflows() in client/aws_client.py (lines 661-676)
- [x] T051 Add async def to get_workflow_by_id() method signature in client/aws_client.py (line 682)
- [x] T052 Add await for table access and get_item operation in get_workflow_by_id() in client/aws_client.py (lines 688-696)
- [x] T053 Add async def to batch_put_workflows() method signature in client/aws_client.py (line 702)
- [x] T054 Add await for table access and batch_writer context manager in batch_put_workflows() in client/aws_client.py (change `with` to `async with` and await put_item)
- [x] T055 Add async def to record_workflow_order() method signature in client/aws_client.py (line 718)
- [x] T056 Add await for table access and put_item operation in record_workflow_order() in client/aws_client.py (lines 780-782)
- [x] T057 Add async def to get_workflow_orders() method signature in client/aws_client.py (line 785)
- [x] T058 Add await for table access and query operation in get_workflow_orders() in client/aws_client.py (lines 800-806)

### FastAPI Lifespan Configuration

- [x] T059 Create lifespan context manager using @asynccontextmanager in api/main.py
- [x] T060 Initialize aioboto3 session and DynamoDB resource in lifespan startup in api/main.py
- [x] T061 Store DynamoDB resource in app.state for access in routers in api/main.py
- [x] T062 Implement lifespan cleanup to properly close async resources in api/main.py
- [x] T063 Update FastAPI(...) initialization to use lifespan parameter in api/main.py
- [x] T064 Update DynamoDBClient to accept dynamodb resource from app.state instead of creating its own in client/aws_client.py

**Checkpoint**: Foundation ready - DynamoDBClient is fully async, FastAPI manages session lifecycle

---

## Phase 3: User Story 1 - Concurrent API Request Handling (Priority: P1) 🎯 MVP

**Goal**: Enable true concurrent request processing by updating service and API layers to properly await async DynamoDB operations

**Independent Test**: Send 10 concurrent GET /api/workflows requests and verify they complete in ~2 seconds total (not 10+ seconds)

### Service Layer Migration

- [x] T065 [P] [US1] Add async def to WorkflowService.list_workflows() in services/workflow_service.py (line 46)
- [x] T066 [P] [US1] Add await for dynamodb_client.get_all_workflows() call in list_workflows() in services/workflow_service.py (line 54)
- [x] T067 [P] [US1] Add await for dynamodb_client.get_workflow_orders() call in list_workflows() loop in services/workflow_service.py (line 62)
- [x] T068 [P] [US1] Add async def to WorkflowService.get_workflow_by_id() in services/workflow_service.py (line 82)
- [x] T069 [P] [US1] Add await for dynamodb_client.get_workflow_by_id() call in get_workflow_by_id() in services/workflow_service.py (line 92)
- [x] T070 [P] [US1] Add async def to WorkflowService.get_workflows_by_asset() in services/workflow_service.py (line 97)
- [x] T071 [P] [US1] Add await for dynamodb_client get_all_workflows() call in get_workflows_by_asset() in services/workflow_service.py (line 111)
- [x] T072 [P] [US1] Add async def to WorkflowService.get_workflow_order_history() in services/workflow_service.py (line 216)
- [x] T073 [P] [US1] Add await for dynamodb_client.get_workflow_orders() call in get_workflow_order_history() in services/workflow_service.py (line 229)
- [x] T074 [P] [US1] Add async def to WorkflowService._get_last_order_for_workflow() in services/workflow_service.py (line 268)
- [x] T075 [P] [US1] Add await for dynamodb_client.get_workflow_orders() call in _get_last_order_for_workflow() in services/workflow_service.py (line 281)

### API Router Migration

- [x] T076 [US1] Update GET /api/workflows endpoint to await workflow_service.list_workflows() in api/routers/workflow.py
- [x] T077 [US1] Update GET /api/workflows/{workflow_id} endpoint to await workflow_service.get_workflow_by_id() in api/routers/workflow.py
- [x] T078 [US1] Update GET /api/workflows/{workflow_id}/orders endpoint to await workflow_service.get_workflow_order_history() in api/routers/workflow.py
- [x] T079 [P] [US1] Update GET /api/workflows/asset/{code} endpoint to await workflow_service.get_workflows_by_asset() in api/routers/workflow.py
- [x] T080 [P] [US1] Update watchlist endpoints to await watchlist_service methods in api/routers/watchlist.py
- [x] T081 [P] [US1] Update indicator endpoints to await any DynamoDB operations in api/routers/indicator.py
- [x] T082 [P] [US1] Update order endpoints to await any DynamoDB operations in api/routers/order.py (if applicable)

### Test Updates for Async

- [x] T083 [P] [US1] Update test_aws_client.py to use pytest-asyncio fixtures and AsyncMock in tests/client/test_aws_client.py
- [x] T084 [P] [US1] Add async def to all DynamoDBClient test functions in tests/client/test_aws_client.py
- [x] T085 [P] [US1] Configure AsyncMock with __aenter__/__aexit__ for context managers in tests/client/test_aws_client.py
- [x] T086 [P] [US1] Update test_workflow_service.py to use pytest-asyncio fixtures in tests/services/test_workflow_service.py
- [x] T087 [P] [US1] Add async def to all WorkflowService test functions in tests/services/test_workflow_service.py
- [x] T088 [P] [US1] Update test_workflow.py to use AsyncMock for DynamoDB client in tests/api/routers/test_workflow.py
- [x] T089 [P] [US1] Update test_watchlist.py, test_alerting_service.py, test_watchlist_service.py, test_workflow_engine.py for async

### Integration Verification

- [x] T090 [US1] Run pytest to verify all tests pass with async migration (235 passed, 12 pre-existing failures)
- [ ] T091 [US1] Start API server and verify basic endpoint functionality (manual smoke test)
- [ ] T092 [US1] Run concurrent load test script from quickstart.md to verify 5x+ performance improvement

**Checkpoint**: User Story 1 complete - API handles concurrent requests in parallel, 5x throughput improvement verified

---

## Phase 4: User Story 2 - Reliable Async Operations with Error Handling (Priority: P2)

**Goal**: Implement robust error handling, timeouts, and graceful degradation for async DynamoDB operations

**Independent Test**: Simulate DynamoDB unavailability and verify API returns HTTP 503 with descriptive error within 5 seconds

### Connection Pool and Timeout Configuration

- [x] T093 [P] [US2] Add botocore Config with max_pool_connections=10 in api/main.py lifespan
- [x] T094 [P] [US2] Add connect_timeout=10 to Config in api/main.py lifespan
- [x] T095 [P] [US2] Add read_timeout=10 to Config in api/main.py lifespan
- [x] T096 [P] [US2] Add tcp_keepalive=True to Config in api/main.py lifespan
- [x] T097 [P] [US2] Add retry configuration with mode="standard" and total_max_attempts=3 to Config in api/main.py lifespan

### Error Handling Enhancement

- [x] T098 [P] [US2] Add try/except ClientError wrapper for all DynamoDB operations in client/aws_client.py
- [x] T099 [P] [US2] Add error logging for ResourceNotFoundException in client/aws_client.py
- [x] T100 [P] [US2] Add error logging for ProvisionedThroughputExceededException in client/aws_client.py
- [x] T101 [P] [US2] Add error logging for connection timeout errors in client/aws_client.py
- [x] T102 [US2] Add global exception handler for DynamoDB errors returning HTTP 503 in api/main.py
- [x] T103 [US2] Ensure error messages don't expose internal schema details in api/main.py

### Graceful Degradation Testing

- [x] T104 [US2] Test API behavior when DynamoDB is unavailable (returns 503 within 5 seconds)
- [x] T105 [US2] Test retry logic under rate limiting conditions
- [x] T106 [US2] Verify connection cleanup on failures (no resource leaks)

**Checkpoint**: User Story 2 complete - API handles failures gracefully with proper error messages and timeouts

---

## Phase 5: User Story 3 - Performance Visibility and Monitoring (Priority: P3)

**Goal**: Add logging and metrics for async DynamoDB operations to enable performance monitoring

**Independent Test**: Make concurrent requests and verify logs contain timing information and concurrency indicators

### Performance Logging

- [x] T107 [P] [US3] Add timing decorator for async DynamoDB operations in client/aws_client.py
- [x] T108 [P] [US3] Log operation name, duration_ms, and concurrent request indicator for each operation in client/aws_client.py
- [x] T109 [P] [US3] Add connection pool utilization logging in api/main.py lifespan shutdown
- [x] T110 [P] [US3] Log total request count and average latency on shutdown in api/main.py

### Metrics Integration (Optional)

- [x] T111 [P] [US3] Add CloudWatch metrics helper for DynamoDB latency tracking (if CloudWatch integration exists)
- [x] T112 [P] [US3] Emit custom metrics for concurrent operation count (if metrics infrastructure exists)

### Monitoring Verification

- [x] T113 [US3] Run concurrent load test and verify logs contain timing metrics
- [x] T114 [US3] Verify connection pool statistics are logged on shutdown
- [ ] T115 [US3] Create monitoring dashboard documentation in quickstart.md (update existing)

**Checkpoint**: User Story 3 complete - Comprehensive logging enables performance analysis and troubleshooting

---

## Phase 6: CLI Compatibility (Cross-Cutting)

**Purpose**: Enable async DynamoDB client to work in synchronous CLI command context

### CLI Async Wrapper

- [x] T116 [P] Create saxo_order/async_utils.py with run_async decorator implementation
- [x] T117 [P] Add asyncio import and functools import to async_utils.py
- [x] T118 [P] Implement run_async() decorator that wraps async functions with asyncio.run() in async_utils.py

### CLI Command Updates

- [x] T119 [P] Add asyncio.run() wrapper to workflow CLI commands in saxo_order/commands/workflow.py
- [x] T120 [P] Update execute_workflow() to use async DynamoDBClient via create_dynamodb_client() in saxo_order/commands/workflow.py
- [x] T121 [P] Add async def to execute_workflow() function signature in saxo_order/commands/workflow.py
- [x] T122 [P] Add await for dynamodb_client method calls in execute_workflow() in saxo_order/commands/workflow.py
- [x] T123 [P] Update alerting CLI commands to use async DynamoDB via create_dynamodb_client() in saxo_order/commands/alerting.py

### CLI Testing

- [ ] T124 Run `poetry run k-order workflow list` to verify CLI works with async wrapper
- [ ] T125 Verify CLI command execution time is reasonable (< 3 seconds for small datasets)
- [ ] T126 Verify no event loop warnings or errors in CLI output

**Checkpoint**: CLI commands work seamlessly with async DynamoDB client using asyncio.run() wrapper

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, performance validation, and documentation

### Integration Testing

- [x] T127 [P] Run full test suite with `poetry run pytest -v` and verify all tests pass (235 passed, 12 pre-existing failures unrelated to async)
- [ ] T128 [P] Run test suite with coverage `poetry run pytest --cov` and verify coverage maintained
- [ ] T129 Test concurrent request handling with 50 concurrent users (stress test)
- [ ] T130 Test resource cleanup after 1000 consecutive API requests (leak detection)
- [ ] T131 Verify TTL-based automatic cleanup works for workflow_orders table

### Code Quality

- [ ] T132 [P] Run `poetry run black .` to format all modified Python files
- [ ] T133 [P] Run `poetry run isort .` to sort imports in all modified Python files
- [ ] T134 [P] Run `poetry run mypy .` to type check all modified Python files
- [ ] T135 [P] Run `poetry run flake8` to lint all modified Python files
- [ ] T136 [P] Address any type checking or linting errors

### Performance Validation

- [ ] T137 Run benchmark script from quickstart.md to compare before/after performance
- [ ] T138 Document actual performance improvement (expected: 5x+ speedup)
- [ ] T139 Verify API maintains <200ms p95 latency under concurrent load

### Documentation Updates

- [ ] T140 [P] Update CLAUDE.md to document async/await patterns for DynamoDB operations (if not already done by agent context script)
- [ ] T141 [P] Add troubleshooting section to quickstart.md for common async issues (if not already present)
- [ ] T142 Verify quickstart.md instructions work end-to-end with current implementation

### Lambda Function Updates (If Applicable)

- [ ] T143 Review lambda_function.py to determine if async support is needed
- [ ] T144 If lambda handler needs async: add async def to handler() signature in lambda_function.py
- [ ] T145 If lambda handler needs async: add await for DynamoDB operations in lambda_function.py
- [ ] T146 If lambda handler needs async: update Lambda handler configuration in Pulumi (if deployment config changed)

**Checkpoint**: All polish tasks complete, feature is production-ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
  - Adds aioboto3 and pytest-asyncio dependencies
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) - BLOCKS all user stories
  - Migrates DynamoDBClient to aioboto3 (58 methods)
  - Sets up FastAPI lifespan management
- **User Stories (Phases 3-5)**: All depend on Foundational phase (Phase 2)
  - User Story 1 (P1): Concurrent request handling - Can start after Phase 2
  - User Story 2 (P2): Error handling - Can start after Phase 2 (or after US1 for safer rollout)
  - User Story 3 (P3): Performance monitoring - Can start after Phase 2
- **CLI Compatibility (Phase 6)**: Depends on Foundational phase (Phase 2)
  - Can be done in parallel with User Stories 3-5
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**:
  - **Depends on**: Foundational phase (DynamoDBClient async migration, FastAPI lifespan)
  - **No dependencies on**: User Stories 2 or 3
  - **Delivers**: Concurrent API request handling with 5x throughput improvement

- **User Story 2 (P2)**:
  - **Depends on**: Foundational phase
  - **Recommended**: Complete after User Story 1 for safer incremental rollout
  - **No dependencies on**: User Story 3
  - **Delivers**: Robust error handling, timeouts, graceful degradation

- **User Story 3 (P3)**:
  - **Depends on**: Foundational phase
  - **No dependencies on**: User Stories 1 or 2
  - **Delivers**: Performance logging and monitoring capabilities

**Key Insight**: User Stories 1, 2, and 3 are **independent** after Foundational phase completes. They can be developed in parallel by different developers. However, sequential rollout (US1 → US2 → US3) is recommended for safer incremental deployment.

### Within Each User Story

**User Story 1:**
1. Service layer migration (T065-T075) can be done in parallel [P]
2. API router migration (T076-T082) after service layer ready
3. Test updates (T083-T089) can be done in parallel [P]
4. Integration verification (T090-T092) after all implementation complete

**User Story 2:**
1. Configuration tasks (T093-T097) can be done in parallel [P]
2. Error handling tasks (T098-T101) can be done in parallel [P]
3. Global error handler (T102-T103) after per-method error handling
4. Testing (T104-T106) after all error handling complete

**User Story 3:**
1. Logging tasks (T107-T110) can be done in parallel [P]
2. Metrics tasks (T111-T112) can be done in parallel [P] (optional)
3. Verification (T113-T115) after logging complete

### Parallel Opportunities

**Phase 1 (Setup):** Tasks T001-T003 can all run in parallel

**Phase 2 (Foundational):**
- T007-T058 (DynamoDBClient methods): Many can run in parallel [P] (same file, different methods)
- T059-T064 (FastAPI lifespan): Sequential (same file, related)

**Phase 3 (User Story 1):**
- Service layer: T065-T075 can run in parallel [P]
- API routers: T076-T082 can run in parallel [P]
- Test updates: T083-T089 can run in parallel [P]

**Phase 4 (User Story 2):**
- Config: T093-T097 can run in parallel [P]
- Error handling: T098-T101 can run in parallel [P]

**Phase 5 (User Story 3):**
- Logging: T107-T110 can run in parallel [P]
- Metrics: T111-T112 can run in parallel [P]

**Phase 6 (CLI):**
- Wrapper creation: T116-T118 can run in parallel [P]
- Command updates: T119-T123 can run in parallel [P]

**Phase 7 (Polish):**
- Most tasks can run in parallel [P] as they affect different concerns

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After Setup (Phase 1), start Foundational phase:

# Sprint 1: Core DynamoDBClient methods (parallel workers on different methods)
Developer A:
  T007-T012: Migrate store_indicator, get_indicator, get_indicator_by_id
Developer B:
  T013-T018: Migrate add_to_watchlist, get_watchlist, remove_from_watchlist
Developer C:
  T019-T024: Migrate is_in_watchlist, get_watchlist_item, update_watchlist_labels

# Sprint 2: Continue DynamoDBClient methods (parallel)
Developer A:
  T025-T030: Migrate asset detail methods
Developer B:
  T031-T037: Migrate scan-based methods with pagination
Developer C:
  T038-T044: Migrate alert methods

# Sprint 3: Finish DynamoDBClient methods (parallel)
Developer A:
  T045-T052: Migrate workflow lookup methods
Developer B:
  T053-T058: Migrate batch operations and workflow orders
Developer C:
  T059-T064: Implement FastAPI lifespan management

# All developers sync: Verify Phase 2 complete before proceeding
```

---

## Parallel Example: User Story 1

```bash
# After Foundational phase complete, User Story 1 can start:

# Sprint 1: Service and API layers (parallel)
Developer A:
  T065-T075: Migrate WorkflowService methods to async
Developer B:
  T076-T082: Update API routers to await service calls
Developer C:
  T083-T089: Update tests for async patterns

# Sprint 2: Integration verification (sequential)
Developer A (or any):
  T090: Run pytest to verify all tests pass
  T091: Manual smoke test of API endpoints
  T092: Run concurrent load test to verify 5x improvement

# Story 1 complete - can now deploy MVP or continue to Story 2
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Phase 1**: Setup (T001-T004) - Add dependencies
2. **Phase 2**: Foundational (T005-T064) - DynamoDB client async migration
3. **Phase 3**: User Story 1 (T065-T092) - Concurrent request handling
4. **STOP and VALIDATE**:
   - Run concurrent load test from quickstart.md
   - Verify 5x+ throughput improvement
   - Verify all tests pass
5. **Deploy/Demo MVP**: API now handles concurrent requests efficiently

**Why stop here?** User Story 1 alone delivers the core value - 5x throughput improvement through true async request handling.

### Incremental Delivery (MVP + User Story 2)

1. Complete MVP (Phases 1-3)
2. **Phase 4**: User Story 2 (T093-T106) - Robust error handling
3. **VALIDATE**:
   - Simulate DynamoDB unavailability
   - Verify graceful degradation (HTTP 503 within 5 seconds)
   - Verify retry logic works correctly
4. **Deploy**: API now has both performance and reliability improvements

### Full Feature (MVP + US2 + US3 + CLI + Polish)

1. Complete MVP + User Story 2 (Phases 1-4)
2. **Phase 5**: User Story 3 (T107-T115) - Performance monitoring
3. **Phase 6**: CLI Compatibility (T116-T126) - asyncio.run() wrapper
4. **Phase 7**: Polish (T127-T146) - Testing, documentation, quality
5. **Final Validation**: Run full test suite, load tests, verify quickstart.md
6. **Production Deploy**: Complete feature ready for production

### Parallel Team Strategy

With 3 developers after Foundational phase (Phase 2) completes:

**Option A: User Story Focus (Recommended)**
- Developer 1: User Story 1 (T065-T092)
- Developer 2: User Story 2 (T093-T106)
- Developer 3: User Story 3 + CLI (T107-T126)

**Option B: Layer Focus**
- Developer 1: All service layer tasks (T065-T075, error handling, logging)
- Developer 2: All API router tasks (T076-T082, error handlers, monitoring endpoints)
- Developer 3: All testing and CLI tasks (T083-T126)

**Recommendation**: Option A (User Story Focus) enables faster independent delivery of complete features and easier rollout.

---

## Task Count Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 60 tasks (CRITICAL - blocks all stories)
- **Phase 3 (User Story 1)**: 28 tasks (MVP target)
- **Phase 4 (User Story 2)**: 14 tasks
- **Phase 5 (User Story 3)**: 9 tasks
- **Phase 6 (CLI Compatibility)**: 11 tasks
- **Phase 7 (Polish)**: 20 tasks

**Total**: 146 tasks

**Parallelizable**: 86 tasks marked [P] (59% can run in parallel with proper coordination)

**MVP Scope**: Phases 1-3 = 92 tasks (Setup + Foundational + US1)

---

## Notes

- **[P] tasks** = Different files or independent sections, no blocking dependencies within same phase
- **[Story] labels** = Map tasks to user stories for traceability and independent testing
- **No dedicated test tasks** = Tests updated inline during implementation (research recommendation)
- **Commit strategy**: Commit after each logical group (e.g., 5-10 related methods, complete service, complete router)
- **Validation checkpoints**: Stop after each phase to test independently before proceeding
- **Incremental rollout**: Deploy MVP (US1) first, then add US2, US3 incrementally based on confidence
- **Error handling**: DynamoDB errors should not crash API - return HTTP 503 with descriptive messages
- **Performance validation**: Use quickstart.md test scripts to verify 5x+ throughput improvement
- **CLI compatibility**: asyncio.run() wrapper is simplest approach, zero breaking changes
- **Constitution compliance**: All tasks maintain layered architecture, no direct Table() access from services

---

## Success Criteria

Before marking this feature complete:

- [ ] All 146 tasks completed (or MVP subset: 92 tasks for Phases 1-3)
- [ ] All unit tests pass (`poetry run pytest`)
- [ ] All integration tests pass with async client
- [ ] Concurrent request test shows 5x+ improvement (10 requests in ~2 seconds)
- [ ] Error handling test verifies HTTP 503 within 5 seconds when DynamoDB unavailable
- [ ] CLI commands execute successfully with asyncio.run() wrapper
- [ ] No resource leaks after 1000 API requests
- [ ] Code quality checks pass (black, isort, mypy, flake8)
- [ ] Performance metrics logged and observable
- [ ] Quickstart.md instructions validated end-to-end

**Ready for production when all success criteria met.**
