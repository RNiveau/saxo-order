# Research: Migration from boto3 to aioboto3 for DynamoDB Async Operations

**Date**: 2026-02-22
**Status**: Complete
**Researcher**: Claude Code Agent
**Input**: Phase 0 Research Topics from plan.md

---

## Executive Summary

This research document addresses the migration from synchronous boto3 to asynchronous aioboto3 for DynamoDB operations in the saxo-order FastAPI backend. The investigation covers five core research areas: session lifecycle management, async/await migration patterns, testing strategies, connection pool configuration, and CLI compatibility approaches.

**Key Finding**: aioboto3 is the appropriate choice for FastAPI async DynamoDB operations, with clear migration patterns established. However, boto3 remains viable if wrapped in thread pool executors (FastAPI's default behavior for blocking calls), though aioboto3 provides better performance under concurrent load.

---

## RESEARCH TOPIC 1: aioboto3 Session Lifecycle Management

### Question
How should aioboto3 session be initialized, managed, and cleaned up in FastAPI application lifecycle?

### Investigation

#### Session Creation and Context Manager Requirements
aioboto3 requires a **mandatory async context manager pattern** for resource initialization:

**Changes from boto3**:
- **boto3 (sync)**: `dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")`
- **aioboto3 (async)**: Must use `async with session.resource('dynamodb')` pattern

**Breaking Change (v9+)**: Module-level functions were removed:
- ❌ `aioboto3.resource()` (no longer exists)
- ❌ `aioboto3.client()` (no longer exists)
- ✅ `session = aioboto3.Session()` then `async with session.resource()`

#### Session Initialization Patterns

**Pattern 1: Short-lived Operations (Per-Request)**
```python
async def get_workflow(workflow_id: str):
    session = aioboto3.Session()
    async with session.resource('dynamodb', region_name='eu-west-1') as dynamo:
        table = await dynamo.Table('workflows')
        response = await table.get_item(Key={'id': workflow_id})
        return response.get('Item')
```

**Pros**: Guarantees resource cleanup per request
**Cons**: Creates new session/connection per request (inefficient)

**Pattern 2: Long-lived Session (FastAPI Lifespan)** ⭐ RECOMMENDED
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aioboto3

class DynamoDBSession:
    def __init__(self):
        self.session = None
        self.dynamodb = None

    async def initialize(self):
        self.session = aioboto3.Session()
        # Resource stays open via __aenter__
        self.dynamodb = self.session.resource('dynamodb', region_name='eu-west-1')

    async def close(self):
        if self.dynamodb:
            await self.dynamodb.__aexit__(None, None, None)
        if self.session:
            self.session = None

db_session = DynamoDBSession()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_session.initialize()
    yield
    # Shutdown
    await db_session.close()

app = FastAPI(lifespan=lifespan)

# In routes: use db_session.dynamodb directly
```

**Pros**: Reuses single session across requests, efficient
**Cons**: Requires proper state management

**Pattern 3: AsyncExitStack (For Multiple Async Contexts)**
```python
from contextlib import AsyncExitStack
import aioboto3

dynamodb_resource = None
s3_resource = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global dynamodb_resource, s3_resource
    async with AsyncExitStack() as stack:
        session = aioboto3.Session()
        dynamodb_resource = await stack.enter_async_context(
            session.resource('dynamodb', region_name='eu-west-1')
        )
        s3_resource = await stack.enter_async_context(
            session.resource('s3')
        )
        yield
        # Resources auto-cleanup when exiting context
```

**Pros**: Handles multiple AWS services cleanly
**Cons**: Slightly more complexity

### Resource and Table Access Pattern

**Critical**: Table objects must be awaited:
```python
# ❌ WRONG - synchronous access pattern
table = dynamo_resource.Table('workflows')

# ✅ CORRECT - async pattern
async with session.resource('dynamodb') as dynamo_resource:
    table = await dynamo_resource.Table('workflows')
```

### FastAPI Lifespan Context Manager Details

The recommended FastAPI lifespan pattern (Python 3.7+):

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code before yield: runs at startup
    print("Starting up")
    # Initialize resources here
    yield
    # Code after yield: runs at shutdown
    print("Shutting down")
    # Cleanup resources here

app = FastAPI(lifespan=lifespan)
```

**Execution Timing**:
- Startup code runs once before serving any requests
- Shutdown code runs after all requests have been handled
- Preferred over deprecated `@app.on_event("startup")` decorators

### Configuration Recommendations

**Connection Pool Configuration**:
- aioboto3 uses `max_pool_connections` parameter from aiobotocore
- Default: not explicitly set (uses system default)
- For DynamoDB: reasonable values are 10-50 depending on concurrency

```python
# In session initialization:
session = aioboto3.Session(
    botocore_session=AioSession(max_pool_connections=10)
)
```

### References
- [aioboto3 Usage Documentation](https://aioboto3.readthedocs.io/en/latest/usage.html)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [GitHub - aioboto3 Session](https://github.com/terricain/aioboto3/blob/main/aioboto3/session.py)

---

## RESEARCH TOPIC 2: Async/Await Migration Strategy for DynamoDB Operations

### Question
What's the best approach to migrate 20+ synchronous DynamoDB methods to async while maintaining backward compatibility for tests?

### Investigation

#### API Differences: boto3 vs aioboto3

| Operation | boto3 (Sync) | aioboto3 (Async) | Notes |
|-----------|--------------|------------------|-------|
| **Session** | N/A | `session = aioboto3.Session()` | Must create session first |
| **Resource** | `boto3.resource('dynamodb')` | `async with session.resource('dynamodb') as dynamo:` | Must use context manager |
| **Table Access** | `dynamo.Table('name')` | `table = await dynamo.Table('name')` | Table access is awaitable |
| **get_item** | `table.get_item(Key={...})` | `await table.get_item(Key={...})` | Add await keyword |
| **put_item** | `table.put_item(Item={...})` | `await table.put_item(Item={...})` | Add await keyword |
| **query** | `table.query(...)` | `await table.query(...)` | Add await keyword |
| **scan** | `table.scan()` | `await table.scan()` | Add await keyword |
| **update_item** | `table.update_item(...)` | `await table.update_item(...)` | Add await keyword |
| **delete_item** | `table.delete_item(...)` | `await table.delete_item(...)` | Add await keyword |
| **batch_writer** | `with table.batch_writer():` | `async with table.batch_writer():` | Context manager becomes async |

#### Side-by-Side Code Patterns

**PATTERN 1: get_item**

**boto3 (sync)**:
```python
def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
    response = self.dynamodb.Table("workflows").get_item(
        Key={"id": workflow_id}
    )
    return response.get("Item")
```

**aioboto3 (async)**:
```python
async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
    table = await self.dynamodb_resource.Table("workflows")
    response = await table.get_item(Key={"id": workflow_id})
    return response.get("Item")
```

**Key Changes**:
1. Method is now `async def`
2. `await` for Table access
3. `await` for DynamoDB operation

---

**PATTERN 2: put_item**

**boto3 (sync)**:
```python
def add_to_watchlist(self, asset_id: str, asset_symbol: str) -> Dict[str, Any]:
    response = self.dynamodb.Table("watchlist").put_item(
        Item={
            "id": asset_id,
            "asset_symbol": asset_symbol,
            "added_at": datetime.datetime.now().isoformat(),
        }
    )
    return response
```

**aioboto3 (async)**:
```python
async def add_to_watchlist(self, asset_id: str, asset_symbol: str) -> Dict[str, Any]:
    table = await self.dynamodb_resource.Table("watchlist")
    response = await table.put_item(
        Item={
            "id": asset_id,
            "asset_symbol": asset_symbol,
            "added_at": datetime.datetime.now().isoformat(),
        }
    )
    return response
```

---

**PATTERN 3: query with Pagination**

**boto3 (sync)**:
```python
def get_workflow_orders(self, workflow_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    items = []
    response = self.dynamodb.Table("workflow_orders").query(
        KeyConditionExpression="workflow_id = :wf_id",
        ExpressionAttributeValues={":wf_id": workflow_id},
        ScanIndexForward=False,
    )
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = self.dynamodb.Table("workflow_orders").query(
            KeyConditionExpression="workflow_id = :wf_id",
            ExpressionAttributeValues={":wf_id": workflow_id},
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return items
```

**aioboto3 (async)**:
```python
async def get_workflow_orders(self, workflow_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    items = []
    table = await self.dynamodb_resource.Table("workflow_orders")

    query_params = {
        "KeyConditionExpression": "workflow_id = :wf_id",
        "ExpressionAttributeValues": {":wf_id": workflow_id},
        "ScanIndexForward": False,
    }

    response = await table.query(**query_params)
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = await table.query(**query_params)
        items.extend(response.get("Items", []))

    return items
```

---

**PATTERN 4: scan with Pagination**

**boto3 (sync)**:
```python
def get_all_tradingview_links(self) -> Dict[str, str]:
    response = self.dynamodb.Table("asset_details").scan(
        ProjectionExpression="asset_id, tradingview_url"
    )
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = self.dynamodb.Table("asset_details").scan(
            ProjectionExpression="asset_id, tradingview_url",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return {item["asset_id"]: item["tradingview_url"] for item in items}
```

**aioboto3 (async)**:
```python
async def get_all_tradingview_links(self) -> Dict[str, str]:
    table = await self.dynamodb_resource.Table("asset_details")
    response = await table.scan(
        ProjectionExpression="asset_id, tradingview_url"
    )
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = await table.scan(
            ProjectionExpression="asset_id, tradingview_url",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return {item["asset_id"]: item["tradingview_url"] for item in items}
```

---

**PATTERN 5: update_item**

**boto3 (sync)**:
```python
def update_watchlist_labels(self, asset_id: str, labels: list[str]) -> Dict[str, Any]:
    response = self.dynamodb.Table("watchlist").update_item(
        Key={"id": asset_id},
        UpdateExpression="SET labels = :labels",
        ExpressionAttributeValues={":labels": labels},
        ReturnValues="ALL_NEW",
    )
    return response
```

**aioboto3 (async)**:
```python
async def update_watchlist_labels(self, asset_id: str, labels: list[str]) -> Dict[str, Any]:
    table = await self.dynamodb_resource.Table("watchlist")
    response = await table.update_item(
        Key={"id": asset_id},
        UpdateExpression="SET labels = :labels",
        ExpressionAttributeValues={":labels": labels},
        ReturnValues="ALL_NEW",
    )
    return response
```

---

**PATTERN 6: delete_item**

**boto3 (sync)**:
```python
def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
    response = self.dynamodb.Table("watchlist").delete_item(
        Key={"id": asset_id}
    )
    return response
```

**aioboto3 (async)**:
```python
async def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
    table = await self.dynamodb_resource.Table("watchlist")
    response = await table.delete_item(Key={"id": asset_id})
    return response
```

---

**PATTERN 7: batch_writer (Bulk Operations)**

**boto3 (sync)**:
```python
def batch_put_workflows(self, workflows: List[Dict[str, Any]]) -> None:
    table = self.dynamodb.Table("workflows")
    with table.batch_writer() as batch:
        for workflow in workflows:
            batch.put_item(Item=workflow)
```

**aioboto3 (async)**:
```python
async def batch_put_workflows(self, workflows: List[Dict[str, Any]]) -> None:
    table = await self.dynamodb_resource.Table("workflows")
    async with table.batch_writer() as batch:
        for workflow in workflows:
            await batch.put_item(Item=workflow)
```

**Key Differences**:
- `with` becomes `async with`
- `batch.put_item()` becomes `await batch.put_item()`
- Automatic retry and exponential backoff still handled by aioboto3

---

#### Error Handling Changes

**boto3 Error Handling Pattern**:
```python
def get_item(self, key: str):
    try:
        response = self.dynamodb.Table("items").get_item(Key={"id": key})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"Error: {response}")
            return None
        return response.get("Item")
    except Exception as e:
        self.logger.error(f"Exception: {e}")
        return None
```

**aioboto3 Error Handling Pattern**:
```python
async def get_item(self, key: str):
    try:
        table = await self.dynamodb_resource.Table("items")
        response = await table.get_item(Key={"id": key})
        # Note: Response metadata checking works the same
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"Error: {response}")
            return None
        return response.get("Item")
    except Exception as e:
        self.logger.error(f"Exception: {e}")
        return None
```

**Important**: Error structure and exception types remain the same. The only change is async/await syntax.

#### Pagination Details for Scan/Query

Both scan and query operations in DynamoDB have a 1MB limit per request (default, unless Limit is smaller). For pagination:

1. Operation returns `response` with `Items` and optionally `LastEvaluatedKey`
2. If `LastEvaluatedKey` exists, more items remain
3. Use as `ExclusiveStartKey` in next request
4. Continue until no `LastEvaluatedKey` is present

aioboto3 pagination logic is identical to boto3, only requiring `await` keywords.

### References
- [boto3 DynamoDB Operations](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)
- [aioboto3 Usage Examples](https://aioboto3.readthedocs.io/en/latest/usage.html)
- [boto3 Query Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/query.html)

---

## RESEARCH TOPIC 3: Testing Strategy for Async Code

### Question
How to test async DynamoDB operations with pytest and maintain test isolation?

### Investigation

#### pytest-asyncio Configuration

**Plugin Requirements**:
```bash
pip install pytest-asyncio pytest
```

**pytest.ini Configuration**:
```ini
[pytest]
asyncio_mode = auto
```

**Key Points**:
- `asyncio_mode = auto`: Automatically detects and runs async test functions
- Available since pytest-asyncio 0.21+

#### Async Test Function Patterns

**Pattern 1: Basic Async Test**
```python
import pytest

@pytest.mark.asyncio
async def test_get_workflow():
    # Test code here
    result = await some_async_function()
    assert result == expected_value
```

**Pattern 2: Async Fixture**
```python
@pytest.fixture
async def dynamodb_client():
    # Setup
    client = AsyncDynamoDBClient()
    await client.initialize()
    yield client
    # Teardown
    await client.close()

@pytest.mark.asyncio
async def test_with_fixture(dynamodb_client):
    result = await dynamodb_client.get_item("test_id")
    assert result is not None
```

#### Mocking Async Context Managers

**Challenge**: Standard `unittest.mock.MagicMock` doesn't support `__aenter__` and `__aexit__` methods.

**Solution 1: Custom Async Context Manager Mock**
```python
from unittest.mock import AsyncMock, MagicMock

class AsyncContextManagerMock(MagicMock):
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

# Usage
mock_resource = AsyncContextManagerMock()
async with mock_resource:
    # This works!
    pass
```

**Solution 2: Using AsyncMock (Python 3.8+)**
```python
from unittest.mock import AsyncMock, MagicMock
import aioboto3

# Mock the session
mock_session = MagicMock()
mock_resource = AsyncMock()

# Setup context manager behavior
mock_session.resource.return_value.__aenter__.return_value = mock_resource
mock_session.resource.return_value.__aexit__.return_value = None

# Mock table access
mock_table = AsyncMock()
mock_resource.Table.return_value = mock_table

# Mock DynamoDB operation
mock_table.get_item.return_value = {"Item": {"id": "test", "name": "Test"}}
```

#### Complete Async Testing Example

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from client.aws_client import DynamoDBClient

@pytest.mark.asyncio
async def test_get_workflow():
    # Create async mocks for aioboto3 components
    mock_dynamodb_resource = AsyncMock()
    mock_table = AsyncMock()

    # Configure Table access mock
    mock_dynamodb_resource.Table.return_value = mock_table

    # Configure get_item mock
    mock_table.get_item.return_value = {
        "Item": {
            "id": "workflow-1",
            "name": "Test Workflow",
            "status": "active"
        },
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }

    # Create client with mocked resource
    client = DynamoDBClient()
    client.dynamodb_resource = mock_dynamodb_resource

    # Call async method
    result = await client.get_workflow_by_id("workflow-1")

    # Verify behavior
    assert result["name"] == "Test Workflow"
    mock_table.get_item.assert_called_once()

@pytest.mark.asyncio
async def test_batch_put_workflows():
    mock_dynamodb_resource = AsyncMock()
    mock_table = AsyncMock()
    mock_batch_writer = AsyncMock()

    # Configure context manager for batch_writer
    mock_table.batch_writer.return_value.__aenter__.return_value = mock_batch_writer
    mock_table.batch_writer.return_value.__aexit__.return_value = None
    mock_dynamodb_resource.Table.return_value = mock_table

    client = DynamoDBClient()
    client.dynamodb_resource = mock_dynamodb_resource

    # Test batch operation
    workflows = [
        {"id": "w1", "name": "Workflow 1"},
        {"id": "w2", "name": "Workflow 2"},
    ]
    await client.batch_put_workflows(workflows)

    # Verify batch_writer was used
    mock_table.batch_writer.assert_called_once()
    assert mock_batch_writer.put_item.call_count == 2

@pytest.mark.asyncio
async def test_query_with_pagination():
    mock_dynamodb_resource = AsyncMock()
    mock_table = AsyncMock()
    mock_dynamodb_resource.Table.return_value = mock_table

    # Simulate pagination with two responses
    mock_table.query.side_effect = [
        {
            "Items": [{"id": "order-1"}, {"id": "order-2"}],
            "LastEvaluatedKey": {"id": "order-2", "workflow_id": "w1"},
            "ResponseMetadata": {"HTTPStatusCode": 200}
        },
        {
            "Items": [{"id": "order-3"}],
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
    ]

    client = DynamoDBClient()
    client.dynamodb_resource = mock_dynamodb_resource

    # Call query method with pagination
    results = await client.get_workflow_orders("workflow-1")

    # Verify all items were collected
    assert len(results) == 3
    assert mock_table.query.call_count == 2

@pytest.mark.asyncio
async def test_error_handling():
    mock_dynamodb_resource = AsyncMock()
    mock_table = AsyncMock()
    mock_dynamodb_resource.Table.return_value = mock_table

    # Simulate error response
    from botocore.exceptions import ClientError

    mock_table.get_item.side_effect = ClientError(
        {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "Requested resource not found"
            }
        },
        "GetItem"
    )

    client = DynamoDBClient()
    client.dynamodb_resource = mock_dynamodb_resource

    # Verify error handling
    result = await client.get_workflow_by_id("nonexistent")
    assert result is None
```

#### Alternative: aiomoto for In-Memory DynamoDB

**Installation**:
```bash
pip install aiomoto
```

**Benefits**:
- Real DynamoDB behavior without AWS API calls
- Supports async operations
- In-memory testing database
- Shared backend between sync and async clients

**Example Using aiomoto**:
```python
import pytest
from aiomoto import mock_dynamodb
import aioboto3

@pytest.mark.asyncio
@mock_dynamodb
async def test_with_aiomoto():
    # Create table
    session = aioboto3.Session()
    async with session.resource('dynamodb', region_name='eu-west-1') as dynamo:
        table = await dynamo.create_table(
            TableName='test_table',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Test operations
        await table.put_item(Item={'id': 'test1', 'data': 'value'})
        response = await table.get_item(Key={'id': 'test1'})
        assert response['Item']['data'] == 'value'
```

### References
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock AsyncMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
- [aiomoto Documentation](https://pypi.org/project/aiomoto/)
- [Testing Async Context Managers](https://pfertyk.me/2017/06/testing-asynchronous-context-managers-in-python/)

---

## RESEARCH TOPIC 4: Connection Pool Sizing and Performance Tuning

### Question
What connection pool size and timeout values optimize for Lambda and local development environments?

### Investigation

#### Connection Pool Basics

**aioboto3/aiobotocore Connection Pooling**:
- Uses `aiohttp` connector for HTTP connections
- Manages concurrent connections to AWS APIs
- Default max connections depend on aiobotocore version

**Configuration Parameter**: `max_pool_connections` in aiobotocore session

```python
from aiobotocore.session import AioSession
import aioboto3

aio_session = AioSession()
aioboto3_session = aioboto3.Session(botocore_session=aio_session)
```

#### Sizing Recommendations

| Environment | Recommended Pool Size | Reasoning |
|-------------|----------------------|-----------|
| **Local Development** | 5-10 | Single developer, sequential requests during testing |
| **FastAPI Server (10 workers)** | 10-20 | One pool per worker, ~1-2 connections per worker |
| **AWS Lambda (concurrent)** | 10-50 | Depends on Lambda concurrent execution setting |
| **High-throughput API** | 50-100 | 100+ concurrent requests expected |

**Formula**: `pool_size = min(concurrent_requests, lambda_concurrency_limit)`

For the saxo-order project (spec suggests 50 concurrent requests):
- **Recommended pool size**: 10 (default) with option to increase to 20-30 for higher throughput
- **Justification**: 10 covers normal concurrent requests; can be tuned later if performance testing indicates need

#### Timeout Configuration

**Types of Timeouts**:
1. **Connection timeout**: Time to establish TCP connection to AWS
2. **Read timeout**: Time to receive response from AWS
3. **Total timeout**: Maximum total time for operation

**Recommended Settings for DynamoDB**:
```python
import botocore.config

config = botocore.config.Config(
    connect_timeout=5,      # 5 seconds to establish connection
    read_timeout=5,         # 5 seconds to read response
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'   # Use adaptive retry with backoff
    }
)

session = aioboto3.Session()
async with session.resource('dynamodb', config=config) as dynamo:
    # operations here
```

**Default Values**: If not specified, boto3/aioboto3 use reasonable defaults (60s total per operation)

#### Performance Under Concurrent Load

**What Happens When Pool Exhausted**:
1. New requests wait for an available connection (blocking)
2. Requests may fail with timeout if pool remains exhausted
3. Eventually requests fail with `ConnectionPoolError`

**Mitigation**:
- Set reasonable connection timeout (5-10s)
- Implement exponential backoff for retries
- Monitor pool utilization in logs
- Scale pool size if frequently exhausted

#### Retry Configuration

**boto3/aioboto3 Built-in Retry Logic**:
```python
config = botocore.config.Config(
    retries={
        'max_attempts': 3,        # Total attempts (1 original + 2 retries)
        'mode': 'adaptive'        # Intelligent retry strategy
    }
)
```

**Retry Modes**:
- `legacy` (default for older versions): Fixed exponential backoff, capped at 20s
- `standard`: Random jitter with exponential backoff
- `adaptive`: Same as standard plus client-side throttling

**Exponential Backoff Pattern**:
```
Attempt 1: Immediate
Attempt 2: 50ms + jitter
Attempt 3: 100ms + jitter
(Maximum backoff: 20 seconds)
```

#### AWS Lambda Considerations

**Lambda Execution Model**:
- Each Lambda invocation is a separate Python process
- Connection pool is per-process
- Multiple concurrent Lambdas = multiple independent pools
- No connection reuse between Lambda invocations

**Optimization**: Use Lambda reserved concurrency with connection pool sizing

```
If Lambda has 100 reserved concurrency:
- Don't create 100 connections per Lambda
- Create 10-20 connections per Lambda instance
- AWS manages connection reuse when Lambdas reuse containers
```

**Implementation for Lambda**:
```python
# Use single global session (reused across Lambda invocations)
session = aioboto3.Session()

async def lambda_handler(event, context):
    async with session.resource('dynamodb', region_name='eu-west-1') as dynamo:
        # Operations here
        pass
```

#### Local Development Performance

**Testing Concurrent Requests**:
```python
import asyncio
import time

async def test_concurrent_operations():
    start = time.time()

    # Simulate 10 concurrent DynamoDB operations
    tasks = [
        dynamodb_client.get_workflow(f"workflow-{i}")
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start
    print(f"10 concurrent operations completed in {elapsed:.2f}s")
    # Expected: ~2-3 seconds (DynamoDB latency ~200-300ms per operation)
    # With sync/blocking: ~20-30 seconds (sequential)
```

### References
- [boto3 Configuration Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)
- [aiobotocore Connection Configuration](https://github.com/aio-libs/aiobotocore)
- [AWS Lambda Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/managing-concurrency.html)

---

## RESEARCH TOPIC 5: CLI Compatibility Pattern

### Question
How to make async DynamoDB client work in synchronous CLI command context?

### Investigation

#### The Challenge

**Current CLI Architecture**:
```
Click Command (sync)
    → Service Layer (currently sync)
        → DynamoDBClient (currently sync)
            → DynamoDB
```

**After Migration**:
```
Click Command (sync)
    → ???
        → Service Layer (now async)
            → DynamoDBClient (now async)
                → DynamoDB
```

**Problem**: Click commands are synchronous but async service layer requires event loop management

#### Option 1: asyncio.run() Wrapper (RECOMMENDED)

**Pattern**:
```python
import asyncio
from click import command, argument
from services.workflow_service import WorkflowService

@command()
@argument('workflow-id')
def get_workflow(workflow_id: str):
    """Get workflow details."""
    # Create service instance (with async client)
    service = WorkflowService()

    # Run async function in event loop
    result = asyncio.run(
        service.get_workflow(workflow_id)
    )

    click.echo(f"Workflow: {result}")
```

**Pros**:
- Simple, clean, minimal boilerplate
- Works with Click decorators
- Natural async/await syntax in async code

**Cons**:
- Creates new event loop per command call
- Slight startup overhead per invocation

**Nested asyncio.run() Handling**:
```python
import asyncio
import sys

async def main():
    # Async code
    pass

# For CLI (Python 3.7+):
if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
```

#### Option 2: Separate Sync Wrapper Client

**Pattern**:
```python
class DynamoDBClientSync:
    """Synchronous wrapper around async DynamoDBClient for CLI compatibility."""

    def __init__(self):
        self.async_client = DynamoDBClient()

    def get_workflow(self, workflow_id: str):
        """Sync wrapper for async get_workflow."""
        return asyncio.run(
            self.async_client.get_workflow(workflow_id)
        )

    def get_all_workflows(self):
        """Sync wrapper for async get_all_workflows."""
        return asyncio.run(
            self.async_client.get_all_workflows()
        )

# Usage in CLI
@command()
def list_workflows():
    client = DynamoDBClientSync()
    workflows = client.get_all_workflows()
    for wf in workflows:
        click.echo(f"- {wf['name']}")
```

**Pros**:
- Preserves async for API layer
- Provides familiar sync interface for CLI
- Could be reused for other sync contexts

**Cons**:
- Duplicate code (wrapper methods)
- Maintenance burden (keep sync/async in sync)
- Hides async nature

**Verdict**: Not recommended for this project

#### Option 3: Async-Aware CLI Framework (Typer)

**Alternative Framework - Typer**:
```python
import typer
from services.workflow_service import WorkflowService

app = typer.Typer()

@app.command()
async def get_workflow(workflow_id: str):
    """Get workflow details."""
    service = WorkflowService()
    result = await service.get_workflow(workflow_id)
    typer.echo(f"Workflow: {result}")

# Typer handles asyncio.run() automatically
if __name__ == "__main__":
    app()
```

**Pros**:
- Native async/await support
- No asyncio.run() boilerplate
- Modern CLI framework

**Cons**:
- Requires migrating from Click to Typer
- Out of scope for this project (would be separate feature)

**Verdict**: Nice future enhancement, but not recommended for current migration

#### Option 4: Keep CLI Synchronous (Alternative Approach)

**Pattern**:
```python
# Create separate DynamoDB client for CLI operations
# CLI stays sync, API uses async

# cli_client.py - uses boto3 (sync)
import boto3

class CLIDynamoDBClient:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

    def get_workflow(self, workflow_id: str):
        # Sync operations
        table = self.dynamodb.Table('workflows')
        response = table.get_item(Key={'id': workflow_id})
        return response.get('Item')

# Usage in CLI
@command()
def get_workflow(workflow_id: str):
    client = CLIDynamoDBClient()  # Uses boto3 sync
    workflow = client.get_workflow(workflow_id)
    click.echo(f"Workflow: {workflow}")
```

**Pros**:
- No async complexity in CLI
- CLI stays exactly as it is
- Clear separation: async API, sync CLI

**Cons**:
- Duplicate client code (one sync, one async)
- Maintains boto3 dependency just for CLI
- More code to maintain

**Verdict**: Acceptable middle ground if asyncio.run() approach causes issues

#### RECOMMENDED APPROACH: asyncio.run() Wrapper

Based on investigation, the **asyncio.run() wrapper (Option 1)** is recommended for the saxo-order project because:

1. **Minimal changes**: Only adds `asyncio.run()` in Click command handlers
2. **No code duplication**: Single async implementation
3. **Clean**: Preserves async/await syntax naturally
4. **Standard pattern**: Widely used in Python async libraries
5. **Future-proof**: If later migrate to Typer, can remove asyncio.run() wrappers

**Implementation Template**:
```python
# saxo_order/commands/workflow.py
import asyncio
import click
from services.workflow_service import WorkflowService

@click.command()
@click.argument('workflow-id')
def get_workflow(workflow_id: str):
    """Get workflow by ID."""
    service = WorkflowService()
    # Run async function in event loop
    result = asyncio.run(service.get_workflow(workflow_id))
    click.echo(f"Workflow: {result['name']}")

@click.command()
def list_workflows():
    """List all workflows."""
    service = WorkflowService()
    # Run async function in event loop
    workflows = asyncio.run(service.get_all_workflows())
    for wf in workflows:
        click.echo(f"- {wf['name']}")
```

#### CLI Event Loop Edge Cases

**Multiple asyncio.run() Calls in Sequence**:
```python
# ❌ PROBLEMATIC: Creates multiple event loops
asyncio.run(operation1())
asyncio.run(operation2())

# ✅ BETTER: Create single event loop for multiple operations
async def cli_handler():
    await operation1()
    await operation2()

asyncio.run(cli_handler())
```

**Nested asyncio.run() (Should Avoid)**:
```python
# ❌ WRONG: Can't nest asyncio.run()
async def operation():
    asyncio.run(nested_operation())

# ✅ CORRECT: Pass event loop or use asyncio.gather()
async def operation():
    await nested_operation()
```

### References
- [asyncio.run() Documentation](https://docs.python.org/3/library/asyncio.html#asyncio.run)
- [Typer CLI Framework](https://typer.tiangolo.com/)
- [Click Framework](https://click.palletsprojects.com/)

---

## SUMMARY: Migration Patterns and Templates

### Complete Migration Checklist

#### Phase 1: Client Layer (DynamoDBClient)
- [ ] Add aioboto3 to pyproject.toml dependencies
- [ ] Create async DynamoDBClient class replacing boto3 usage
- [ ] Implement all 20+ DynamoDB methods as async
- [ ] Add error handling for async operations
- [ ] Test with unit tests and mocks

#### Phase 2: Service Layer
- [ ] Make all service methods async that call DynamoDBClient
- [ ] Update method signatures to `async def`
- [ ] Add `await` keywords for DynamoDB client calls
- [ ] Update service docstrings to indicate async nature

#### Phase 3: API Layer (FastAPI)
- [ ] Update FastAPI main.py with lifespan context manager
- [ ] Initialize aioboto3 session in startup
- [ ] Clean up resources in shutdown
- [ ] Update all router methods to `async def` (most already are)
- [ ] Add `await` keywords for service layer calls
- [ ] Update type hints if needed

#### Phase 4: CLI Layer
- [ ] Wrap CLI command handlers with `asyncio.run()`
- [ ] Import asyncio in CLI command files
- [ ] Verify CLI still works with async service layer

#### Phase 5: Testing
- [ ] Update test fixtures to use pytest-asyncio
- [ ] Convert test functions to async
- [ ] Update mocks to use AsyncMock and async context managers
- [ ] Test with aiomoto if needed for integration tests
- [ ] Verify all existing tests pass

#### Phase 6: Deployment
- [ ] Build and test Docker image with aioboto3
- [ ] Test Lambda function with async operations
- [ ] Verify CloudWatch logs show async operation timing
- [ ] Monitor connection pool utilization

### Migration Timeline Estimate
- **Client refactor**: 4-6 hours (20+ methods × 15 min each)
- **Service layer updates**: 1-2 hours (async/await syntax)
- **API router updates**: 1-2 hours (await service calls)
- **CLI updates**: 30-60 minutes (asyncio.run wrappers)
- **Testing migration**: 3-4 hours (async mocks, fixtures)
- **Integration testing**: 2-3 hours (testing, verification)
- **Total estimate**: 12-18 hours development + testing

---

## RESEARCH CONCLUSION

### Key Findings

1. **Session Management**: FastAPI lifespan context manager with `AsyncExitStack` is the optimal approach for managing aioboto3 session lifecycle

2. **Migration Patterns**: Direct 1:1 mapping from boto3 to aioboto3 with addition of `async def` and `await` keywords; API surface is largely identical

3. **Testing**: pytest-asyncio with AsyncMock provides clean testing approach; aiomoto offers alternative for in-memory testing

4. **Connection Pooling**: Default pool size of 10 connections suitable for spec's 50 concurrent request requirement; can be tuned later

5. **CLI Compatibility**: `asyncio.run()` wrapper is standard, minimal-overhead approach; recommended over creating separate sync client

### Risks and Mitigation

| Risk | Mitigation |
|------|-----------|
| Connection pool exhaustion | Monitor utilization, set appropriate timeout, implement retry logic |
| Async/await mistakes (missing await) | Type checking with mypy, thorough testing |
| Test isolation issues | Use async fixtures properly, avoid shared state |
| Lambda cold start slowdown | Reuse session across invocations, optimize initialization |
| Breaking existing API contracts | No API changes required, only internal implementation |

### Recommendations

1. **Start with client layer refactoring**: Lowest risk, isolated changes
2. **Use FastAPI lifespan for session management**: Production-ready pattern
3. **Implement comprehensive async tests before API updates**: Verify client works
4. **Keep CLI simple with asyncio.run() wrappers**: Minimal boilerplate, familiar pattern
5. **Performance test after implementation**: Verify concurrent request improvements

---

## References

**Official Documentation**:
- [aioboto3 GitHub Repository](https://github.com/terricain/aioboto3)
- [aioboto3 ReadTheDocs](https://aioboto3.readthedocs.io/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [boto3 DynamoDB Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/)

**AWS Documentation**:
- [DynamoDB Error Handling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html)
- [boto3 Retry Behavior](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html)
- [AWS SDK Retry Behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)

**Testing and Best Practices**:
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock AsyncMock](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Async Context Managers](https://pfertyk.me/2017/06/testing-asynchronous-context-managers-in-python/)

**Community Resources**:
- [How to Access DynamoDB in FastAPI](https://retz.dev/blog/how-to-access-dynamodb-in-fastapi/)
- [FastAPI Discussion: Long-lived Client Initialization](https://github.com/fastapi/fastapi/discussions/6068)
- [aiobotocore Examples](https://github.com/aio-libs/aiobotocore/tree/master/examples)

---

**End of Research Document**
Generated: 2026-02-22
Status: Complete and Ready for Phase 1 Design
