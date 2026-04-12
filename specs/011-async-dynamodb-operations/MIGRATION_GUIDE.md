# boto3 to aioboto3 Migration Guide: Complete Reference

**Date**: 2026-02-22
**Project**: saxo-order (DynamoDB async operations)
**Status**: Ready for Implementation

---

## Table of Contents

1. [API Differences Quick Reference](#api-differences-quick-reference)
2. [Method-by-Method Migration Templates](#method-by-method-migration-templates)
3. [Error Handling](#error-handling)
4. [Testing Guide](#testing-guide)
5. [Configuration Reference](#configuration-reference)
6. [Troubleshooting](#troubleshooting)

---

## API Differences Quick Reference

### Core Changes

| Aspect | boto3 | aioboto3 | Migration Note |
|--------|-------|---------|-----------------|
| **Module Import** | `import boto3` | `import aioboto3` | Different package |
| **Session Creation** | `boto3.resource()` | `aioboto3.Session()` | Create session first (v9+) |
| **Resource Access** | Direct: `boto3.resource('dynamodb')` | Context manager: `async with session.resource('dynamodb')` | Must use `async with` |
| **Table Access** | Direct: `dynamodb.Table('name')` | Awaited: `table = await dynamodb.Table('name')` | Table is awaitable |
| **All Operations** | Synchronous: `table.put_item()` | Asynchronous: `await table.put_item()` | All methods need await |
| **Context Managers** | `with table.batch_writer():` | `async with table.batch_writer():` | Async context manager |
| **Error Handling** | Try/except with boto3 errors | Try/except with same botocore errors | Identical error types |

### Method Signature Changes

| Operation | Return Value | Notes |
|-----------|--------------|-------|
| `get_item()` | Returns awaitable | Same key structure, returns same response dict |
| `put_item()` | Returns awaitable | Same item structure, returns same response dict |
| `query()` | Returns awaitable | Same KeyConditionExpression, pagination identical |
| `scan()` | Returns awaitable | Same ProjectionExpression, pagination identical |
| `update_item()` | Returns awaitable | Same UpdateExpression, returns same response dict |
| `delete_item()` | Returns awaitable | Same Key structure, returns same response dict |
| `batch_writer()` | Returns async context manager | Automatic retry/batching same as boto3 |

---

## Method-by-Method Migration Templates

### Template 1: get_item (Simple Key Lookup)

**Purpose**: Retrieve single item by primary key

**Current (boto3)**:
```python
def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve workflow by ID."""
    response = self.dynamodb.Table("workflows").get_item(
        Key={"id": workflow_id}
    )
    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB get_item error: {response}")
        return None
    if "Item" not in response:
        return None
    return response["Item"]
```

**Migrated (aioboto3)**:
```python
async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve workflow by ID."""
    table = await self.dynamodb_resource.Table("workflows")
    response = await table.get_item(Key={"id": workflow_id})

    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB get_item error: {response}")
        return None
    if "Item" not in response:
        return None
    return response["Item"]
```

**Changes**:
- Add `async def` keyword
- Add `await` for `Table()` access
- Add `await` for `get_item()` operation

**Error Handling**: Same response structure, same HTTP status code checking

---

### Template 2: put_item (Insert/Upsert Single Item)

**Purpose**: Write single item to table (creates or overwrites)

**Current (boto3)**:
```python
def add_to_watchlist(
    self,
    asset_id: str,
    asset_symbol: str,
    description: str,
    country_code: str,
    labels: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Add asset to watchlist with metadata."""
    item: Dict[str, Any] = {
        "id": asset_id,
        "asset_symbol": asset_symbol,
        "description": description,
        "country_code": country_code,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "labels": labels if labels is not None else [],
    }

    response = self.dynamodb.Table("watchlist").put_item(Item=item)
    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB put_item error: {response}")
    return response
```

**Migrated (aioboto3)**:
```python
async def add_to_watchlist(
    self,
    asset_id: str,
    asset_symbol: str,
    description: str,
    country_code: str,
    labels: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Add asset to watchlist with metadata."""
    item: Dict[str, Any] = {
        "id": asset_id,
        "asset_symbol": asset_symbol,
        "description": description,
        "country_code": country_code,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "labels": labels if labels is not None else [],
    }

    table = await self.dynamodb_resource.Table("watchlist")
    response = await table.put_item(Item=item)

    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB put_item error: {response}")
    return response
```

**Changes**:
- Add `async def` keyword
- Add `await` for `Table()` access
- Add `await` for `put_item()` operation

**Data Conversion**: No changes needed for Decimal conversion, same `_convert_floats_to_decimal()` helper works

---

### Template 3: query (Filtered Search with Pagination)

**Purpose**: Find items by partition key with sort key conditions

**Current (boto3)**:
```python
def get_workflow_orders(
    self, workflow_id: str, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get order history for a workflow, sorted newest first."""
    try:
        items = []
        query_params = {
            "KeyConditionExpression": "workflow_id = :wf_id",
            "ExpressionAttributeValues": {":wf_id": workflow_id},
            "ScanIndexForward": False,  # Newest first
        }

        if limit:
            query_params["Limit"] = limit

        response = self.dynamodb.Table("workflow_orders").query(**query_params)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB query error: {response}")
            return []

        items.extend(response.get("Items", []))

        # Pagination loop
        while "LastEvaluatedKey" in response and (not limit or len(items) < limit):
            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self.dynamodb.Table("workflow_orders").query(**query_params)
            items.extend(response.get("Items", []))

        return items

    except Exception as e:
        self.logger.error(f"Error querying orders: {e}")
        return []
```

**Migrated (aioboto3)**:
```python
async def get_workflow_orders(
    self, workflow_id: str, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get order history for a workflow, sorted newest first."""
    try:
        items = []
        table = await self.dynamodb_resource.Table("workflow_orders")

        query_params = {
            "KeyConditionExpression": "workflow_id = :wf_id",
            "ExpressionAttributeValues": {":wf_id": workflow_id},
            "ScanIndexForward": False,  # Newest first
        }

        if limit:
            query_params["Limit"] = limit

        response = await table.query(**query_params)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB query error: {response}")
            return []

        items.extend(response.get("Items", []))

        # Pagination loop
        while "LastEvaluatedKey" in response and (not limit or len(items) < limit):
            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = await table.query(**query_params)
            items.extend(response.get("Items", []))

        return items

    except Exception as e:
        self.logger.error(f"Error querying orders: {e}")
        return []
```

**Changes**:
- Add `async def` keyword
- Add `await` for `Table()` access
- Add `await` for each `query()` call
- Pagination logic remains identical

**Key Concepts**:
- `KeyConditionExpression`: Condition on partition/sort keys (same syntax)
- `ScanIndexForward=False`: Sort descending (same parameter)
- `ExclusiveStartKey`: Pagination token from previous response

---

### Template 4: scan (Full Table Scan with Pagination)

**Purpose**: Retrieve all items from table (potentially filtered), handles pagination

**Current (boto3)**:
```python
def get_all_tradingview_links(self) -> Dict[str, str]:
    """Batch fetch all TradingView links from asset_details table."""
    try:
        response = self.dynamodb.Table("asset_details").scan(
            ProjectionExpression="asset_id, tradingview_url",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return {}

        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = self.dynamodb.Table("asset_details").scan(
                ProjectionExpression="asset_id, tradingview_url",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Build dictionary
        links = {
            item["asset_id"]: item["tradingview_url"]
            for item in items
            if "tradingview_url" in item and item["tradingview_url"]
        }

        self.logger.info(f"Loaded {len(links)} TradingView links")
        return links

    except Exception as e:
        self.logger.error(f"Failed to fetch TradingView links: {e}")
        return {}
```

**Migrated (aioboto3)**:
```python
async def get_all_tradingview_links(self) -> Dict[str, str]:
    """Batch fetch all TradingView links from asset_details table."""
    try:
        table = await self.dynamodb_resource.Table("asset_details")
        response = await table.scan(
            ProjectionExpression="asset_id, tradingview_url",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return {}

        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ProjectionExpression="asset_id, tradingview_url",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Build dictionary
        links = {
            item["asset_id"]: item["tradingview_url"]
            for item in items
            if "tradingview_url" in item and item["tradingview_url"]
        }

        self.logger.info(f"Loaded {len(links)} TradingView links")
        return links

    except Exception as e:
        self.logger.error(f"Failed to fetch TradingView links: {e}")
        return {}
```

**Changes**:
- Add `async def` keyword
- Add `await` for `Table()` access
- Add `await` for each `scan()` call
- Pagination logic identical

**Key Concepts**:
- `ProjectionExpression`: Select specific attributes (reduces data transfer)
- `FilterExpression`: Optional client-side filtering after retrieval
- `LastEvaluatedKey`: Pagination token (1MB limit per scan)

---

### Template 5: update_item (Modify Existing Item)

**Purpose**: Update specific attributes of an item

**Current (boto3)**:
```python
def update_watchlist_labels(
    self, asset_id: str, labels: list[str]
) -> Dict[str, Any]:
    """Update labels for a watchlist item."""
    response = self.dynamodb.Table("watchlist").update_item(
        Key={"id": asset_id},
        UpdateExpression="SET labels = :labels",
        ExpressionAttributeValues={":labels": labels},
        ReturnValues="ALL_NEW",
    )
    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB update_item error: {response}")
    return response
```

**Migrated (aioboto3)**:
```python
async def update_watchlist_labels(
    self, asset_id: str, labels: list[str]
) -> Dict[str, Any]:
    """Update labels for a watchlist item."""
    table = await self.dynamodb_resource.Table("watchlist")
    response = await table.update_item(
        Key={"id": asset_id},
        UpdateExpression="SET labels = :labels",
        ExpressionAttributeValues={":labels": labels},
        ReturnValues="ALL_NEW",
    )
    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB update_item error: {response}")
    return response
```

**Changes**:
- Add `async def` keyword
- Add `await` for `Table()` access
- Add `await` for `update_item()` operation

**Key Concepts**:
- `UpdateExpression`: Syntax like "SET attr1 = :val1, REMOVE attr2"
- `ExpressionAttributeValues`: Maps :val1 placeholders to actual values
- `ReturnValues="ALL_NEW"`: Returns updated item

---

### Template 6: delete_item (Remove Item from Table)

**Purpose**: Delete single item by primary key

**Current (boto3)**:
```python
def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
    """Remove an asset from the watchlist."""
    response = self.dynamodb.Table("watchlist").delete_item(
        Key={"id": asset_id}
    )
    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB delete_item error: {response}")
    return response
```

**Migrated (aioboto3)**:
```python
async def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
    """Remove an asset from the watchlist."""
    table = await self.dynamodb_resource.Table("watchlist")
    response = await table.delete_item(Key={"id": asset_id})

    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB delete_item error: {response}")
    return response
```

**Changes**:
- Add `async def` keyword
- Add `await` for `Table()` access
- Add `await` for `delete_item()` operation

**Key Concepts**:
- `Key`: Must specify all primary key attributes
- Conditional deletion possible with `ConditionExpression`

---

### Template 7: batch_writer (Bulk Writes with Auto-Batching)

**Purpose**: Efficiently write multiple items with automatic batching and retry

**Current (boto3)**:
```python
def batch_put_workflows(self, workflows: List[Dict[str, Any]]) -> None:
    """Batch insert workflows into DynamoDB."""
    table = self.dynamodb.Table("workflows")

    with table.batch_writer() as batch:
        for workflow in workflows:
            converted = self._convert_floats_to_decimal(workflow)
            batch.put_item(Item=converted)

    self.logger.info(f"Batch inserted {len(workflows)} workflows")
```

**Migrated (aioboto3)**:
```python
async def batch_put_workflows(self, workflows: List[Dict[str, Any]]) -> None:
    """Batch insert workflows into DynamoDB."""
    table = await self.dynamodb_resource.Table("workflows")

    async with table.batch_writer() as batch:
        for workflow in workflows:
            converted = self._convert_floats_to_decimal(workflow)
            await batch.put_item(Item=converted)

    self.logger.info(f"Batch inserted {len(workflows)} workflows")
```

**Changes**:
- Add `async def` keyword
- Change `with` to `async with`
- Add `await` for `batch.put_item()` call
- `Table()` access still needs `await`

**Key Concepts**:
- `batch_writer()`: Groups items into batches of 25 (configurable)
- Auto-retry for failed items with exponential backoff
- Flushes remaining items on context exit

**Configuration Options**:
```python
async with table.batch_writer(
    flush_amount=10,  # Custom batch size
    on_exit_loop_sleep=0.1  # Sleep between flushes
) as batch:
    # items
    pass
```

---

### Template 8: Pagination Helper (Extract Pattern)

**Purpose**: Reusable pagination helper for scan/query operations

**Current (boto3)**:
```python
def _paginate_scan(self, table_name: str, **scan_kwargs) -> List[Dict]:
    """Helper: Paginate through scan results."""
    items = []
    table = self.dynamodb.Table(table_name)
    response = table.scan(**scan_kwargs)

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

    return items
```

**Migrated (aioboto3)**:
```python
async def _paginate_scan(self, table_name: str, **scan_kwargs) -> List[Dict]:
    """Helper: Paginate through scan results."""
    items = []
    table = await self.dynamodb_resource.Table(table_name)
    response = await table.scan(**scan_kwargs)

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = await table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

    return items
```

**Usage**:
```python
# Old
async def get_all_alerts(self):
    return self._paginate_scan("alerts")

# New
async def get_all_alerts(self):
    return await self._paginate_scan("alerts")
```

---

## Error Handling

### DynamoDB Exception Types

**Same as boto3** - aioboto3 uses `botocore` exceptions:

```python
from botocore.exceptions import ClientError, BotoCoreError

async def safe_get_item(self, key: str):
    try:
        table = await self.dynamodb_resource.Table("items")
        response = await table.get_item(Key={"id": key})
        return response.get("Item")

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "ResourceNotFoundException":
            self.logger.warning(f"Table not found")
            return None
        elif error_code == "ProvisionedThroughputExceededException":
            self.logger.error(f"DynamoDB throttled - implement backoff")
            raise  # Re-raise for retry logic
        elif error_code == "ValidationException":
            self.logger.error(f"Invalid request: {e}")
            return None
        else:
            self.logger.error(f"DynamoDB error {error_code}: {e}")
            return None

    except BotoCoreError as e:
        self.logger.error(f"Network error: {e}")
        return None
```

### Automatic Retry Configuration

```python
import botocore.config

config = botocore.config.Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'  # Exponential backoff with jitter
    },
    connect_timeout=5,
    read_timeout=5,
)

session = aioboto3.Session()
async with session.resource('dynamodb', config=config) as dynamo:
    # Operations automatically retry with backoff
    pass
```

### HTTP Status Code Checking

**Old pattern** (still works):
```python
response = await table.get_item(Key={"id": "test"})
if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
    # Handle error
    pass
```

**Better pattern** (exception-based):
```python
try:
    response = await table.get_item(Key={"id": "test"})
    return response.get("Item")
except ClientError as e:
    # Handle specific error
    pass
```

---

## Testing Guide

### Async Test Function Basics

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_get_workflow():
    """Test async operation."""
    # Test code here
    result = await some_async_function()
    assert result is not None
```

### Mocking aioboto3 Resources

**Pattern 1: Mock with AsyncMock**
```python
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_get_workflow():
    # Create mocks
    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()

    # Configure mocks
    mock_dynamodb.Table.return_value = mock_table
    mock_table.get_item.return_value = {
        "Item": {"id": "w1", "name": "Workflow 1"},
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }

    # Create client with mock
    client = DynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    # Test
    result = await client.get_workflow("w1")
    assert result["name"] == "Workflow 1"
```

**Pattern 2: Mock Async Context Manager**
```python
@pytest.mark.asyncio
async def test_batch_operations():
    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()
    mock_batch = AsyncMock()

    # Configure batch_writer context manager
    mock_table.batch_writer.return_value.__aenter__.return_value = mock_batch
    mock_table.batch_writer.return_value.__aexit__.return_value = None
    mock_dynamodb.Table.return_value = mock_table

    client = DynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    # Test
    await client.batch_put_workflows([{"id": "w1"}])

    mock_batch.put_item.assert_called_once()
```

**Pattern 3: Using aiomoto for Real-like Testing**
```python
import aioboto3
from aiomoto import mock_dynamodb

@pytest.mark.asyncio
@mock_dynamodb
async def test_with_real_dynamodb_mock():
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

### Async Fixture Pattern

```python
@pytest.fixture
async def dynamodb_client():
    """Fixture: Initialize async DynamoDB client."""
    client = DynamoDBClient()

    # Initialize (similar to lifespan startup)
    session = aioboto3.Session()
    client.dynamodb_resource = await session.resource('dynamodb').__aenter__()

    yield client

    # Cleanup (similar to lifespan shutdown)
    await client.dynamodb_resource.__aexit__(None, None, None)

@pytest.mark.asyncio
async def test_with_fixture(dynamodb_client):
    result = await dynamodb_client.get_workflow("w1")
    assert result is not None
```

---

## Configuration Reference

### Session Initialization with Custom Config

```python
import aioboto3
import botocore.config
from aiobotocore.session import AioSession

# Option 1: Simple session
session = aioboto3.Session()

# Option 2: With custom region
session = aioboto3.Session(region_name='eu-west-1')

# Option 3: With AWS credentials
session = aioboto3.Session(
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='eu-west-1'
)

# Option 4: With retry and timeout config
config = botocore.config.Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    connect_timeout=5,
    read_timeout=5,
)
async with session.resource('dynamodb', config=config) as dynamo:
    # Operations here
    pass
```

### FastAPI Lifespan Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aioboto3

class AppState:
    dynamodb_session = None
    dynamodb_resource = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    state.dynamodb_session = aioboto3.Session(region_name='eu-west-1')
    state.dynamodb_resource = await state.dynamodb_session.resource('dynamodb').__aenter__()

    # Dependency injection: add to app state
    app.state.dynamodb = state.dynamodb_resource

    yield

    # Shutdown
    await state.dynamodb_resource.__aexit__(None, None, None)
    state.dynamodb_session = None
    state.dynamodb_resource = None

app = FastAPI(lifespan=lifespan)

# In routes, access via app.state
@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request):
    table = await request.app.state.dynamodb.Table("workflows")
    response = await table.get_item(Key={"id": workflow_id})
    return response.get("Item")
```

### CLI Integration Pattern

```python
import asyncio
import click
from services.workflow_service import WorkflowService

@click.group()
def cli():
    """CLI commands."""
    pass

@cli.command()
@click.argument('workflow_id')
def get_workflow(workflow_id: str):
    """Get workflow details."""
    service = WorkflowService()
    # Run async function in event loop
    result = asyncio.run(service.get_workflow(workflow_id))
    click.echo(f"Workflow: {result['name']}")

@cli.command()
def list_workflows():
    """List all workflows."""
    service = WorkflowService()
    # Run async function in event loop
    workflows = asyncio.run(service.get_all_workflows())
    for wf in workflows:
        click.echo(f"- {wf['name']}")

if __name__ == '__main__':
    cli()
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "No running event loop"
**Symptom**: `RuntimeError: no running event loop`
**Cause**: Calling async function from sync context without `asyncio.run()`
**Solution**:
```python
# ❌ Wrong
result = await async_function()  # In sync code

# ✅ Correct
result = asyncio.run(async_function())  # In CLI or sync code
```

#### Issue 2: "Cannot use await outside async function"
**Symptom**: `SyntaxError: 'await' outside async function`
**Cause**: Using `await` in non-async function
**Solution**:
```python
# ❌ Wrong
def get_item():
    item = await table.get_item(Key={...})

# ✅ Correct
async def get_item():
    item = await table.get_item(Key={...})
```

#### Issue 3: "Table not found"
**Symptom**: `ResourceNotFoundException`
**Cause**: Table doesn't exist in DynamoDB
**Solution**: Verify table exists in AWS Console or DynamoDB Local

#### Issue 4: "ProvisionedThroughputExceededException"
**Symptom**: Too many concurrent requests
**Solution**: Enable auto-scaling or increase provisioned capacity
```python
# Also helps: exponential backoff via retry config
config = botocore.config.Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)
```

#### Issue 5: "Timeout waiting for table"
**Symptom**: Operations hang indefinitely
**Cause**: Connection pool exhausted or slow DynamoDB
**Solution**: Set timeouts and use async to parallelize
```python
config = botocore.config.Config(
    connect_timeout=5,
    read_timeout=5,
)
```

#### Issue 6: "Mock not working in tests"
**Symptom**: Test calls real AWS instead of mock
**Cause**: Mock not properly configured as async context manager
**Solution**: Use `__aenter__` and `__aexit__` for async mocks
```python
mock.return_value.__aenter__.return_value = real_object
mock.return_value.__aexit__.return_value = None
```

#### Issue 7: "Connection pool exhausted"
**Symptom**: `TooManyConnectionsError` or timeout under load
**Cause**: Pool size too small for concurrent load
**Solution**: Increase pool size in session config
```python
# Via environment variable:
export AWS_DYNAMODB_CONNECTION_POOL_SIZE=50

# Or in code:
aio_session = AioSession(max_pool_connections=50)
```

### Debug Checklist

- [ ] All methods are `async def`
- [ ] All DynamoDB operations have `await`
- [ ] `Table()` access has `await`
- [ ] Context managers use `async with`
- [ ] Error handling catches `ClientError` and `BotoCoreError`
- [ ] Tests use `@pytest.mark.asyncio`
- [ ] Mocks are `AsyncMock` for async operations
- [ ] FastAPI lifespan properly initializes/closes resources
- [ ] CLI commands use `asyncio.run()`
- [ ] Lambda functions properly manage async lifecycle

---

## Quick Migration Checklist

### Client Layer (DynamoDBClient)
- [ ] Create new async client or migrate existing
- [ ] Add `async def` to all methods
- [ ] Add `await` for `Table()` access
- [ ] Add `await` for all DynamoDB operations
- [ ] Update pagination loops
- [ ] Keep error handling, just add try/except around async calls
- [ ] Add `async with` for batch_writer

### Service Layer
- [ ] Make service methods `async def`
- [ ] Add `await` for all client method calls
- [ ] Update docstrings to indicate async

### API Layer (FastAPI)
- [ ] Create lifespan context manager in main.py
- [ ] Initialize aioboto3 session on startup
- [ ] Close resources on shutdown
- [ ] Add `await` for service layer calls (most routers already async)
- [ ] Test with concurrent requests

### CLI Layer
- [ ] Add `import asyncio` to command files
- [ ] Wrap async service calls with `asyncio.run()`
- [ ] No other changes needed

### Testing
- [ ] Install pytest-asyncio
- [ ] Add `asyncio_mode = auto` to pytest.ini
- [ ] Convert test functions to `async def`
- [ ] Add `@pytest.mark.asyncio` to async tests
- [ ] Update mocks to AsyncMock
- [ ] Test batch operations with proper context manager mocks

### Deployment
- [ ] Run `poetry install` to add aioboto3
- [ ] Build Docker image
- [ ] Test Lambda with async operations
- [ ] Verify CloudWatch logs

---

**End of Migration Guide**
