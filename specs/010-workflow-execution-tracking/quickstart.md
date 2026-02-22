# Quickstart Guide: Workflow Order History Tracking

**Feature**: 010-workflow-execution-tracking
**Date**: 2026-02-22
**Audience**: Developers implementing and testing this feature

This guide provides step-by-step instructions for developing and testing the workflow order history tracking feature.

---

## Prerequisites

- Python 3.11 installed
- Poetry package manager
- Node.js 18+ and npm
- AWS CLI configured with DynamoDB Local (or AWS credentials)
- Docker (for DynamoDB Local testing)

---

## Phase 1: Local Development Setup

### 1.1 Install DynamoDB Local

```bash
# Start DynamoDB Local via Docker
docker run -d \
  -p 8001:8000 \
  --name dynamodb-local \
  amazon/dynamodb-local

# Verify it's running
aws dynamodb list-tables \
  --endpoint-url http://localhost:8001 \
  --region us-east-1
```

### 1.2 Create workflow_orders Table Locally

```bash
# Create table with TTL
aws dynamodb create-table \
  --endpoint-url http://localhost:8001 \
  --region us-east-1 \
  --table-name workflow_orders \
  --attribute-definitions \
    AttributeName=workflow_id,AttributeType=S \
    AttributeName=placed_at,AttributeType=N \
  --key-schema \
    AttributeName=workflow_id,KeyType=HASH \
    AttributeName=placed_at,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# Enable TTL (note: TTL doesn't work in DynamoDB Local, but command validates schema)
aws dynamodb update-time-to-live \
  --endpoint-url http://localhost:8001 \
  --region us-east-1 \
  --table-name workflow_orders \
  --time-to-live-specification "Enabled=true,AttributeName=ttl"
```

### 1.3 Update Backend Configuration

```yaml
# config.yml - Add DynamoDB Local endpoint for testing
dynamodb:
  endpoint_url: "http://localhost:8001"  # Comment out for AWS production
  region: "us-east-1"
```

### 1.4 Install Dependencies

```bash
# Backend
poetry install

# Frontend
cd frontend
npm install
cd ..
```

---

## Phase 2: Backend Development

### 2.1 Implement DynamoDB Client Method

**File**: `client/dynamodb_client.py`

```python
def record_workflow_order(
    self,
    workflow_id: str,
    workflow_name: str,
    order_code: str,
    order_price: float,
    order_quantity: float,
    order_direction: str,  # Direction enum name
    order_type: str,  # OrderType enum name
    asset_type: Optional[str] = None,
    trigger_close: Optional[float] = None,
    execution_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a workflow order placement to DynamoDB.

    Args:
        workflow_id: Workflow UUID
        workflow_name: Workflow display name
        order_code: Asset code
        order_price: Entry price
        order_quantity: Order size
        order_direction: BUY or SELL
        order_type: LIMIT or OPEN_STOP
        asset_type: Optional asset classification
        trigger_close: Optional trigger candle close
        execution_context: Optional Lambda/CLI context

    Returns:
        DynamoDB put_item response
    """
    import uuid
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    placed_at = int(now.timestamp())
    ttl = placed_at + (7 * 24 * 60 * 60)  # 7 days

    item = {
        "id": str(uuid.uuid4()),
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "placed_at": placed_at,
        "order_code": order_code,
        "order_price": order_price,
        "order_quantity": order_quantity,
        "order_direction": order_direction,
        "order_type": order_type,
        "#ttl": ttl,  # Reserved word protection
    }

    if asset_type:
        item["asset_type"] = asset_type
    if trigger_close is not None:
        item["trigger_close"] = trigger_close
    if execution_context:
        item["execution_context"] = execution_context

    # Convert floats to Decimal
    item = self._convert_floats_to_decimal(item)

    response = self.dynamodb.Table("workflow_orders").put_item(
        Item=item,
        ExpressionAttributeNames={"#ttl": "ttl"},  # Handle reserved word
    )

    if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
        self.logger.error(f"DynamoDB put_item error: {response}")

    return response


def get_workflow_orders(
    self,
    workflow_id: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get order history for a workflow, sorted newest first.

    Args:
        workflow_id: Workflow UUID
        limit: Optional max orders to return

    Returns:
        List of order dictionaries
    """
    try:
        query_params = {
            "KeyConditionExpression": "workflow_id = :wf_id",
            "ExpressionAttributeValues": {":wf_id": workflow_id},
            "ScanIndexForward": False,  # DESC order
        }

        if limit:
            query_params["Limit"] = limit

        response = self.dynamodb.Table("workflow_orders").query(**query_params)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB query error: {response}")
            return []

        items = response.get("Items", [])

        # Pagination
        while "LastEvaluatedKey" in response:
            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self.dynamodb.Table("workflow_orders").query(**query_params)
            items.extend(response.get("Items", []))

        return items

    except Exception as e:
        self.logger.error(f"Error querying orders for workflow {workflow_id}: {e}")
        return []
```

### 2.2 Update WorkflowEngine

**File**: `engines/workflow_engine.py`

```python
# In __init__, add DynamoDBClient injection
def __init__(
    self,
    logger: logging.Logger,
    saxo_client: SaxoClient,
    slack_client: WebClient,
    dynamodb_client: DynamoDBClient,  # ADD THIS
):
    self.logger = logger
    self.saxo_client = saxo_client
    self.slack_client = slack_client
    self.dynamodb_client = dynamodb_client  # ADD THIS

# In run() method, add order tracking (lines ~145-160)
for order in results:
    if order[1] is not None:
        asset = self.saxo_client.get_asset(order[1][1].code)
        log = f"Workflow `{order[0].name}` will trigger an order..."
        self.logger.debug(log)

        # Existing Slack notification
        channel = "#workflows-stock" if asset["AssetType"] == AssetType.STOCK else "#workflows"
        self.slack_client.chat_postMessage(channel=channel, text=log)

        # NEW: Record order tracking
        try:
            self.dynamodb_client.record_workflow_order(
                workflow_id=order[0].id,
                workflow_name=order[0].name,
                order_code=order[1][1].code,
                order_price=float(order[1][1].price),
                order_quantity=float(order[1][1].quantity),
                order_direction=order[1][1].direction.name,
                order_type=order[1][1].type.name,
                asset_type=asset["AssetType"].name if asset.get("AssetType") else None,
                trigger_close=float(order[1][0].close) if order[1][0].close else None,
                execution_context="cli",  # or get from Lambda context
            )
            self.logger.info(f"Recorded order for workflow {order[0].name}")
        except Exception as e:
            self.logger.error(f"Failed to track order for {order[0].name}: {e}")
            # Continue - don't block workflow execution
```

### 2.3 Add API Endpoint

**File**: `api/routers/workflow.py`

```python
@router.get("/workflows/{workflow_id}/orders")
async def get_workflow_order_history(
    workflow_id: str = Path(..., description="Workflow UUID"),
    limit: int = Query(20, ge=1, le=100, description="Max orders to return"),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Get order history for a specific workflow."""
    try:
        orders = workflow_service.get_workflow_order_history(workflow_id, limit)
        return WorkflowOrderHistoryResponse(
            workflow_id=workflow_id,
            orders=orders,
            total_count=len(orders),
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2.4 Run Backend Server

```bash
# Start API server
poetry run python run_api.py

# Server will start on http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## Phase 3: Frontend Development

### 3.1 Update API Service

**File**: `frontend/src/services/api.ts`

```typescript
// Add to workflowService
export const workflowService = {
  // ... existing methods ...

  getWorkflowOrderHistory: async (
    workflowId: string,
    limit: number = 20
  ): Promise<OrderHistoryItem[]> => {
    const response = await axios.get<OrderHistoryResponse>(
      `${API_URL}/api/workflow/workflows/${workflowId}/orders`,
      { params: { limit } }
    );
    return response.data.orders;
  },
};

// Type definitions
interface OrderHistoryItem {
  id: string;
  workflow_id: string;
  placed_at: string;
  order_code: string;
  order_price: number;
  order_quantity: number;
  order_direction: string;
}

interface OrderHistoryResponse {
  workflow_id: string;
  orders: OrderHistoryItem[];
  total_count: number;
  limit: number;
}
```

### 3.2 Update WorkflowTable Component

**File**: `frontend/src/components/WorkflowTable.tsx`

```typescript
// Add "Last Order" column after "End Date"
<th>Last Order</th>

// In data row
<td>{formatRelativeTime(workflow.last_order_timestamp)}</td>

// Helper function
const formatRelativeTime = (dateString: string | null) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};
```

### 3.3 Update WorkflowDetailModal Component

**File**: `frontend/src/components/WorkflowDetailModal.tsx`

```typescript
// Add state for order history
const [orderHistory, setOrderHistory] = useState<OrderHistoryItem[]>([]);
const [orderHistoryLoading, setOrderHistoryLoading] = useState(false);

// Load on modal open
useEffect(() => {
  const loadOrderHistory = async () => {
    setOrderHistoryLoading(true);
    try {
      const orders = await workflowService.getWorkflowOrderHistory(workflowId, 20);
      setOrderHistory(orders);
    } catch (err) {
      console.error('Failed to load order history:', err);
    } finally {
      setOrderHistoryLoading(false);
    }
  };

  loadOrderHistory();
}, [workflowId]);

// Add order history section in render (after Trigger, before Metadata)
<div className="detail-section">
  <h3>Order History</h3>
  {orderHistoryLoading && <div className="loading">Loading orders...</div>}
  {!orderHistoryLoading && orderHistory.length === 0 && (
    <div className="order-history-empty">No orders placed yet</div>
  )}
  {!orderHistoryLoading && orderHistory.length > 0 && (
    <table className="order-history-table">
      {/* Table implementation */}
    </table>
  )}
</div>
```

### 3.4 Run Frontend Dev Server

```bash
cd frontend
npm run dev

# Server will start on http://localhost:5173
# Ensure VITE_API_URL=http://localhost:8000 in .env
```

---

## Phase 4: Testing the Feature

### 4.1 Manual Testing Workflow

**Step 1: Trigger a Workflow**

```bash
# Via CLI (if workflow execution implemented)
poetry run k-order workflow run --select-workflow

# Or manually insert test data
aws dynamodb put-item \
  --endpoint-url http://localhost:8001 \
  --table-name workflow_orders \
  --item '{
    "id": {"S": "test-order-001"},
    "workflow_id": {"S": "550e8400-e29b-41d4-a716-446655440000"},
    "workflow_name": {"S": "Test Workflow"},
    "placed_at": {"N": "'$(date +%s)'"},
    "order_code": {"S": "FRA40.I"},
    "order_price": {"N": "7850.25"},
    "order_quantity": {"N": "10"},
    "order_direction": {"S": "BUY"},
    "order_type": {"S": "LIMIT"},
    "ttl": {"N": "'$(($(date +%s) + 604800))'"}
  }'
```

**Step 2: Verify in UI**

1. Navigate to http://localhost:5173/workflows
2. Check "Last Order" column shows timestamp
3. Click workflow row to open detail modal
4. Verify "Order History" section displays order

**Step 3: Test API Endpoints**

```bash
# Get order history
curl http://localhost:8000/api/workflow/workflows/550e8400-e29b-41d4-a716-446655440000/orders

# Expected response:
# {
#   "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
#   "orders": [{...}],
#   "total_count": 1,
#   "limit": 20
# }
```

### 4.2 Automated Testing

**Unit Test: DynamoDB Client**

**File**: `tests/client/test_dynamodb_client.py`

```python
@patch("client.aws_client.boto3")
def test_record_workflow_order(self, mock_boto3):
    """Test recording workflow order to DynamoDB."""
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table

    client = DynamoDBClient(logger=MagicMock())
    response = client.record_workflow_order(
        workflow_id="550e8400-e29b-41d4-a716-446655440000",
        workflow_name="Test Workflow",
        order_code="FRA40.I",
        order_price=7850.25,
        order_quantity=10.0,
        order_direction="BUY",
        order_type="LIMIT",
    )

    # Verify put_item called
    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]

    # Verify item structure
    assert call_args["Item"]["workflow_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert call_args["Item"]["order_direction"] == "BUY"
    assert "ttl" in call_args["ExpressionAttributeNames"]


@patch("client.aws_client.boto3")
def test_get_workflow_orders(self, mock_boto3):
    """Test retrieving workflow orders from DynamoDB."""
    mock_table = MagicMock()
    mock_table.query.return_value = {
        "Items": [
            {
                "id": "test-order-001",
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "placed_at": 1740254400,
                "order_code": "FRA40.I",
                "order_price": Decimal("7850.25"),
                "order_quantity": Decimal("10"),
                "order_direction": "BUY",
                "order_type": "LIMIT",
                "ttl": 1740859200,
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    mock_boto3.resource.return_value.Table.return_value = mock_table

    client = DynamoDBClient(logger=MagicMock())
    orders = client.get_workflow_orders("550e8400-e29b-41d4-a716-446655440000", limit=20)

    # Verify query called with correct parameters
    mock_table.query.assert_called_once()
    call_args = mock_table.query.call_args[1]
    assert call_args["ScanIndexForward"] is False  # DESC order
    assert call_args["Limit"] == 20

    # Verify results
    assert len(orders) == 1
    assert orders[0]["order_direction"] == "BUY"
```

**Run Tests:**

```bash
poetry run pytest tests/client/test_dynamodb_client.py -v
```

### 4.3 Integration Testing

```bash
# 1. Start all services
docker-compose up -d dynamodb-local  # or docker run command
poetry run python run_api.py &
cd frontend && npm run dev &

# 2. Run integration test script
poetry run pytest tests/integration/test_workflow_orders_integration.py

# 3. Cleanup
pkill -f "python run_api.py"
pkill -f "npm run dev"
docker stop dynamodb-local
```

---

## Phase 5: Deployment

### 5.1 Deploy DynamoDB Table (Pulumi)

```bash
# Add to pulumi/dynamodb.py (already done in research)
# Then deploy
cd pulumi
pulumi up

# Verify table created
aws dynamodb describe-table --table-name workflow_orders
```

### 5.2 Deploy Backend

```bash
# Build Docker image and deploy Lambda
./deploy.sh

# Verify Lambda function updated
aws lambda get-function --function-name saxo-order-lambda
```

### 5.3 Deploy Frontend

```bash
cd frontend
npm run build

# Deploy dist/ to hosting service (S3, Vercel, etc.)
# Ensure VITE_API_URL points to production API
```

---

## Troubleshooting

### Issue: DynamoDB Local TTL Not Working

**Solution**: TTL doesn't expire items in DynamoDB Local. Test TTL in AWS environment or manually delete test items.

### Issue: Frontend Shows "No orders" Despite Orders Existing

**Checklist**:
1. Verify API endpoint returns data: `curl http://localhost:8000/api/workflow/workflows/{id}/orders`
2. Check browser console for CORS errors
3. Verify VITE_API_URL in frontend/.env
4. Check workflow_id matches between frontend and backend

### Issue: WorkflowEngine Injection Error

**Solution**: Ensure DynamoDBClient is passed in WorkflowEngine constructor in all call sites (lambda_function.py, workflow.py command).

---

## Next Steps

After completing development and testing:
1. Run `/speckit.tasks` to generate implementation tasks
2. Follow task execution workflow
3. Create PR with conventional commit: `feat: add workflow order history tracking`

---

## Reference Links

- [Spec](./spec.md) - Feature specification
- [Data Model](./data-model.md) - Domain models and entities
- [API Contract](./contracts/workflow-orders-api.yaml) - OpenAPI specification
- [Research](./research.md) - Technical research findings
