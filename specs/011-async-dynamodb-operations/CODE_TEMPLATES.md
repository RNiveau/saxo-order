# Ready-to-Use Code Templates: boto3 to aioboto3 Migration

**Date**: 2026-02-22
**Purpose**: Copy/paste templates for common DynamoDB operations

---

## FastAPI Application Setup

### Template: api/main.py (Lifespan Setup)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aioboto3

# Store session globally for app lifecycle
dynamodb_session = None
dynamodb_resource = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage aioboto3 DynamoDB session lifecycle."""
    global dynamodb_session, dynamodb_resource

    # Startup
    dynamodb_session = aioboto3.Session(region_name='eu-west-1')
    dynamodb_resource = await dynamodb_session.resource('dynamodb').__aenter__()
    app.state.dynamodb = dynamodb_resource

    print("✓ DynamoDB async session initialized")

    yield

    # Shutdown
    if dynamodb_resource:
        await dynamodb_resource.__aexit__(None, None, None)
    dynamodb_session = None
    dynamodb_resource = None
    print("✓ DynamoDB async session closed")

app = FastAPI(lifespan=lifespan)

# Your routes here...
```

### Template: api/dependencies.py (Dependency Injection)

```python
from fastapi import Request
from client.aws_client import AsyncDynamoDBClient

async def get_dynamodb_client(request: Request) -> AsyncDynamoDBClient:
    """Dependency: Get DynamoDB client from app state."""
    return AsyncDynamoDBClient(resource=request.app.state.dynamodb)
```

### Template: api/routers/example.py (Route with DynamoDB)

```python
from fastapi import APIRouter, Depends
from client.aws_client import AsyncDynamoDBClient
from api.dependencies import get_dynamodb_client

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    db: AsyncDynamoDBClient = Depends(get_dynamodb_client)
):
    """Get workflow by ID."""
    workflow = await db.get_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.get("")
async def list_workflows(
    db: AsyncDynamoDBClient = Depends(get_dynamodb_client)
):
    """List all workflows."""
    workflows = await db.get_all_workflows()
    return {"workflows": workflows}
```

---

## DynamoDBClient Class (Complete Async Implementation)

### Template: client/aws_client.py (Async Client Class)

```python
import asyncio
import datetime
import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aioboto3
from model import Alert, AlertType
from utils.json_util import dumps_indicator, hash_indicator
from utils.logger import Logger


class AsyncDynamoDBClient:
    """Async DynamoDB client using aioboto3."""

    def __init__(self, region_name: str = "eu-west-1"):
        """Initialize async DynamoDB client."""
        self.logger = Logger.get_logger("dynamodb_client", logging.INFO)
        self.session = aioboto3.Session(region_name=region_name)
        self.dynamodb_resource = None

    async def initialize(self):
        """Initialize DynamoDB resource (for standalone usage)."""
        self.dynamodb_resource = await self.session.resource(
            'dynamodb'
        ).__aenter__()

    async def close(self):
        """Close DynamoDB resource (for standalone usage)."""
        if self.dynamodb_resource:
            await self.dynamodb_resource.__aexit__(None, None, None)
            self.dynamodb_resource = None

    @staticmethod
    def _convert_floats_to_decimal(obj: Any) -> Any:
        """Recursively convert float values to Decimal for DynamoDB."""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {
                k: AsyncDynamoDBClient._convert_floats_to_decimal(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [
                AsyncDynamoDBClient._convert_floats_to_decimal(item)
                for item in obj
            ]
        return obj

    @staticmethod
    def _normalize_country_code(country_code: Optional[str]) -> str:
        """Normalize country code for DynamoDB (handles None as 'NONE')."""
        return country_code if country_code else "NONE"

    # ========== BASIC CRUD OPERATIONS ==========

    async def get_workflow_by_id(
        self, workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single workflow by ID."""
        table = await self.dynamodb_resource.Table("workflows")
        response = await table.get_item(Key={"id": workflow_id})

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None

        return response.get("Item")

    async def get_all_workflows(self) -> List[Dict[str, Any]]:
        """Retrieve all workflows from DynamoDB."""
        workflows = []
        table = await self.dynamodb_resource.Table("workflows")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return workflows

        workflows.extend(response.get("Items", []))

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                break
            workflows.extend(response.get("Items", []))

        return workflows

    async def batch_put_workflows(
        self, workflows: List[Dict[str, Any]]
    ) -> None:
        """Batch insert workflows into DynamoDB."""
        table = await self.dynamodb_resource.Table("workflows")

        async with table.batch_writer() as batch:
            for workflow in workflows:
                converted = self._convert_floats_to_decimal(workflow)
                await batch.put_item(Item=converted)

        self.logger.info(f"Batch inserted {len(workflows)} workflows")

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
                "ScanIndexForward": False,
            }

            if limit:
                query_params["Limit"] = limit

            response = await table.query(**query_params)

            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB query error: {response}")
                return []

            items.extend(response.get("Items", []))

            # Pagination loop
            while "LastEvaluatedKey" in response and (
                not limit or len(items) < limit
            ):
                query_params["ExclusiveStartKey"] = response[
                    "LastEvaluatedKey"
                ]
                response = await table.query(**query_params)
                items.extend(response.get("Items", []))

            return items

        except Exception as e:
            self.logger.error(
                f"Error querying orders for workflow {workflow_id}: {e}"
            )
            return []

    async def record_workflow_order(
        self,
        workflow_id: str,
        order_code: str,
        order_price: float,
        order_quantity: float,
        order_direction: str,
        order_type: str,
    ) -> Dict[str, Any]:
        """Record a workflow order placement to DynamoDB."""
        import uuid

        now = datetime.datetime.now(datetime.timezone.utc)
        placed_at = int(now.timestamp())
        ttl = placed_at + (7 * 24 * 60 * 60)  # 7-day TTL

        item = {
            "id": str(uuid.uuid4()),
            "workflow_id": workflow_id,
            "placed_at": placed_at,
            "order_code": order_code,
            "order_price": order_price,
            "order_quantity": order_quantity,
            "order_direction": order_direction,
            "order_type": order_type,
            "ttl": ttl,
        }

        item = self._convert_floats_to_decimal(item)
        table = await self.dynamodb_resource.Table("workflow_orders")
        response = await table.put_item(Item=item)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")

        return response

    # ========== WATCHLIST OPERATIONS ==========

    async def add_to_watchlist(
        self,
        asset_id: str,
        asset_symbol: str,
        description: str,
        country_code: str,
        labels: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Add an asset to the watchlist with metadata."""
        item: Dict[str, Any] = {
            "id": asset_id,
            "asset_symbol": asset_symbol,
            "description": description,
            "country_code": country_code,
            "added_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "labels": labels if labels is not None else [],
        }

        table = await self.dynamodb_resource.Table("watchlist")
        response = await table.put_item(Item=item)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")

        return response

    async def get_watchlist(self) -> List[Dict[str, Any]]:
        """Get all assets in the watchlist."""
        table = await self.dynamodb_resource.Table("watchlist")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []

        return response.get("Items", [])

    async def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
        """Remove an asset from the watchlist."""
        table = await self.dynamodb_resource.Table("watchlist")
        response = await table.delete_item(Key={"id": asset_id})

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB delete_item error: {response}")

        return response

    async def is_in_watchlist(self, asset_id: str) -> bool:
        """Check if an asset is in the watchlist."""
        table = await self.dynamodb_resource.Table("watchlist")
        response = await table.get_item(Key={"id": asset_id})
        return "Item" in response

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

    # ========== ALERT OPERATIONS ==========

    async def store_alerts(
        self,
        asset_code: str,
        country_code: Optional[str],
        alerts: list,
    ) -> Dict[str, Any]:
        """Append new alerts for a given asset with 7-day TTL."""
        country_code_value = self._normalize_country_code(country_code)

        # Get existing alerts to check for duplicates
        existing_alerts = await self.get_alerts(asset_code, country_code)

        # Create set of existing alert signatures for deduplication
        existing_signatures = set()
        for existing in existing_alerts:
            try:
                alert_date = datetime.datetime.fromisoformat(
                    existing["date"]
                )
                signature = (
                    existing["alert_type"],
                    alert_date.date().isoformat(),
                )
                existing_signatures.add(signature)
            except (KeyError, ValueError):
                continue

        # Filter duplicate alerts
        unique_alerts = []
        for alert in alerts:
            signature = (
                alert.alert_type.value,
                alert.date.date().isoformat(),
            )
            if signature not in existing_signatures:
                unique_alerts.append(alert)
                existing_signatures.add(signature)

        if not unique_alerts:
            self.logger.info(
                f"No unique alerts to store for {asset_code}"
            )
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

        # Prepare alert data
        alerts_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type.value,
                "asset_code": alert.asset_code,
                "asset_description": alert.asset_description,
                "country_code": (
                    alert.country_code if alert.country_code else "NONE"
                ),
                "date": alert.date.isoformat(),
                "data": self._convert_floats_to_decimal(alert.data),
            }
            for alert in unique_alerts
        ]

        now = datetime.datetime.now(datetime.timezone.utc)
        ttl_timestamp = int((now + datetime.timedelta(days=7)).timestamp())

        table = await self.dynamodb_resource.Table("alerts")
        response = await table.update_item(
            Key={"asset_code": asset_code, "country_code": country_code_value},
            UpdateExpression=(
                "SET alerts = list_append(if_not_exists(alerts, :empty_list), "
                ":new_alerts), last_updated = :last_updated, #ttl = :ttl"
            ),
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={
                ":empty_list": [],
                ":new_alerts": alerts_data,
                ":last_updated": now.isoformat(),
                ":ttl": ttl_timestamp,
            },
            ReturnValues="UPDATED_NEW",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB update_item error: {response}")

        return response

    async def get_alerts(
        self, asset_code: str, country_code: Optional[str]
    ) -> list:
        """Get alerts for a specific asset."""
        country_code_value = self._normalize_country_code(country_code)

        table = await self.dynamodb_resource.Table("alerts")
        response = await table.get_item(
            Key={"asset_code": asset_code, "country_code": country_code_value}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return []

        if "Item" not in response:
            return []

        return response["Item"].get("alerts", [])

    async def get_all_alerts(self) -> List[Alert]:
        """Get all alerts from the alerts table."""
        table = await self.dynamodb_resource.Table("alerts")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []

        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        # Convert to Alert objects
        all_alerts: List[Alert] = []
        for item in items:
            alerts_data = item.get("alerts", [])
            for alert_dict in alerts_data:
                country_code = alert_dict.get("country_code")
                if country_code == "NONE":
                    country_code = None

                alert = Alert(
                    alert_type=AlertType(alert_dict["alert_type"]),
                    date=datetime.datetime.fromisoformat(alert_dict["date"]),
                    data=alert_dict["data"],
                    asset_code=alert_dict["asset_code"],
                    asset_description=alert_dict.get(
                        "asset_description", alert_dict["asset_code"]
                    ),
                    country_code=country_code,
                )
                all_alerts.append(alert)

        return all_alerts

    # ========== HELPER OPERATIONS ==========

    async def _paginate_scan(
        self, table_name: str, **scan_kwargs
    ) -> List[Dict[str, Any]]:
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

    async def _paginate_query(
        self, table_name: str, **query_kwargs
    ) -> List[Dict[str, Any]]:
        """Helper: Paginate through query results."""
        items = []
        table = await self.dynamodb_resource.Table(table_name)
        response = await table.query(**query_kwargs)

        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = await table.query(**query_kwargs)
            items.extend(response.get("Items", []))

        return items
```

---

## Service Layer Template

### Template: services/workflow_service.py (Async Service)

```python
from typing import Any, Dict, List, Optional
from client.aws_client import AsyncDynamoDBClient


class WorkflowService:
    """Service layer for workflow operations."""

    def __init__(self, db_client: AsyncDynamoDBClient):
        """Initialize with async DynamoDB client."""
        self.db = db_client

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID."""
        return await self.db.get_workflow_by_id(workflow_id)

    async def get_all_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows."""
        return await self.db.get_all_workflows()

    async def get_workflow_orders(
        self, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """Get orders for workflow."""
        return await self.db.get_workflow_orders(workflow_id)

    async def record_order(
        self,
        workflow_id: str,
        order_code: str,
        order_price: float,
        order_quantity: float,
        order_direction: str,
        order_type: str,
    ) -> bool:
        """Record order placement."""
        try:
            response = await self.db.record_workflow_order(
                workflow_id=workflow_id,
                order_code=order_code,
                order_price=order_price,
                order_quantity=order_quantity,
                order_direction=order_direction,
                order_type=order_type,
            )
            return response["ResponseMetadata"]["HTTPStatusCode"] < 400
        except Exception as e:
            print(f"Error recording order: {e}")
            return False
```

---

## CLI Command Template

### Template: saxo_order/commands/workflow.py (Async CLI)

```python
import asyncio
import click
from services.workflow_service import WorkflowService
from client.aws_client import AsyncDynamoDBClient


@click.group()
def workflow_cli():
    """Workflow commands."""
    pass


@workflow_cli.command("list")
def list_workflows():
    """List all workflows."""

    async def _list():
        db = AsyncDynamoDBClient()
        await db.initialize()
        try:
            service = WorkflowService(db)
            workflows = await service.get_all_workflows()

            if not workflows:
                click.echo("No workflows found")
                return

            for wf in workflows:
                click.echo(f"- {wf['id']}: {wf.get('name', 'Unknown')}")
        finally:
            await db.close()

    asyncio.run(_list())


@workflow_cli.command("get")
@click.argument("workflow_id")
def get_workflow(workflow_id: str):
    """Get workflow details."""

    async def _get():
        db = AsyncDynamoDBClient()
        await db.initialize()
        try:
            service = WorkflowService(db)
            wf = await service.get_workflow(workflow_id)

            if not wf:
                click.echo(f"Workflow {workflow_id} not found")
                return

            click.echo(f"ID: {wf['id']}")
            click.echo(f"Name: {wf.get('name', 'Unknown')}")
            click.echo(f"Status: {wf.get('status', 'Unknown')}")
        finally:
            await db.close()

    asyncio.run(_get())


@workflow_cli.command("orders")
@click.argument("workflow_id")
def get_orders(workflow_id: str):
    """Get orders for workflow."""

    async def _get_orders():
        db = AsyncDynamoDBClient()
        await db.initialize()
        try:
            service = WorkflowService(db)
            orders = await service.get_workflow_orders(workflow_id)

            if not orders:
                click.echo(f"No orders for workflow {workflow_id}")
                return

            for order in orders:
                click.echo(
                    f"- {order['id']}: {order['order_code']} "
                    f"@ {order['order_price']}"
                )
        finally:
            await db.close()

    asyncio.run(_get_orders())


if __name__ == "__main__":
    workflow_cli()
```

---

## Testing Templates

### Template: tests/client/test_aws_client.py (Async Tests)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from client.aws_client import AsyncDynamoDBClient


@pytest.mark.asyncio
async def test_get_workflow():
    """Test get_workflow async operation."""
    # Create mocks
    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()

    # Configure mocks
    mock_dynamodb.Table.return_value = mock_table
    mock_table.get_item.return_value = {
        "Item": {"id": "w1", "name": "Test Workflow"},
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    # Create client with mock
    client = AsyncDynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    # Test
    result = await client.get_workflow_by_id("w1")

    # Verify
    assert result["name"] == "Test Workflow"
    mock_table.get_item.assert_called_once_with(Key={"id": "w1"})


@pytest.mark.asyncio
async def test_get_all_workflows():
    """Test get_all_workflows with pagination."""
    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()

    # First page response
    first_response = {
        "Items": [{"id": "w1", "name": "Workflow 1"}],
        "LastEvaluatedKey": {"id": "w1"},
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    # Second page response
    second_response = {
        "Items": [{"id": "w2", "name": "Workflow 2"}],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    mock_table.scan.side_effect = [first_response, second_response]
    mock_dynamodb.Table.return_value = mock_table

    client = AsyncDynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    result = await client.get_all_workflows()

    assert len(result) == 2
    assert mock_table.scan.call_count == 2


@pytest.mark.asyncio
async def test_batch_put_workflows():
    """Test batch writing workflows."""
    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()
    mock_batch = AsyncMock()

    # Configure context manager
    mock_table.batch_writer.return_value.__aenter__.return_value = mock_batch
    mock_table.batch_writer.return_value.__aexit__.return_value = None
    mock_dynamodb.Table.return_value = mock_table

    client = AsyncDynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    workflows = [
        {"id": "w1", "name": "Workflow 1"},
        {"id": "w2", "name": "Workflow 2"},
    ]

    await client.batch_put_workflows(workflows)

    assert mock_batch.put_item.call_count == 2


@pytest.mark.asyncio
async def test_get_workflow_orders_with_pagination():
    """Test query with pagination."""
    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()

    # First page
    first_response = {
        "Items": [{"id": "o1", "workflow_id": "w1"}],
        "LastEvaluatedKey": {"id": "o1", "workflow_id": "w1"},
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    # Second page
    second_response = {
        "Items": [{"id": "o2", "workflow_id": "w1"}],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    mock_table.query.side_effect = [first_response, second_response]
    mock_dynamodb.Table.return_value = mock_table

    client = AsyncDynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    result = await client.get_workflow_orders("w1")

    assert len(result) == 2
    assert mock_table.query.call_count == 2


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling for DynamoDB failures."""
    from botocore.exceptions import ClientError

    mock_dynamodb = AsyncMock()
    mock_table = AsyncMock()

    # Simulate DynamoDB error
    error_response = {
        "Error": {
            "Code": "ResourceNotFoundException",
            "Message": "Table not found",
        }
    }
    mock_table.get_item.side_effect = ClientError(error_response, "GetItem")
    mock_dynamodb.Table.return_value = mock_table

    client = AsyncDynamoDBClient()
    client.dynamodb_resource = mock_dynamodb

    # Should handle error gracefully
    result = await client.get_workflow_by_id("nonexistent")
    assert result is None
```

### Template: tests/conftest.py (Async Fixtures)

```python
import pytest
import aioboto3
from aiomoto import mock_dynamodb
from client.aws_client import AsyncDynamoDBClient


@pytest.fixture
async def dynamodb_client_mock():
    """Fixture: DynamoDB client with mocked resource."""
    from unittest.mock import AsyncMock

    client = AsyncDynamoDBClient()
    client.dynamodb_resource = AsyncMock()
    return client


@pytest.fixture
@mock_dynamodb
async def dynamodb_client_real():
    """Fixture: DynamoDB client with in-memory moto database."""
    client = AsyncDynamoDBClient()

    # Initialize with real in-memory DynamoDB
    session = aioboto3.Session()
    client.dynamodb_resource = await session.resource(
        "dynamodb", region_name="eu-west-1"
    ).__aenter__()

    yield client

    # Cleanup
    await client.dynamodb_resource.__aexit__(None, None, None)
```

---

**End of Code Templates**
