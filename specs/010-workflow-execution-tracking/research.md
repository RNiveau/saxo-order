# Research: Workflow Order History Tracking

**Date**: 2026-02-22
**Feature**: 010-workflow-execution-tracking
**Status**: Complete

This document consolidates research findings for implementing workflow order history tracking in the saxo-order system.

---

## 1. DynamoDB TTL Configuration

### Decision: Use TTL attribute "ttl" with Pulumi configuration

**Rationale:**
- Existing alerts table already uses this pattern successfully
- TTL attribute "ttl" is AWS standard convention
- 7-day retention matches alerts table pattern (604800 seconds)
- Automatic deletion prevents manual cleanup overhead

**Implementation Pattern:**

```python
# pulumi/dynamodb.py - Add new table
def workflow_orders_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "workflow_orders",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="workflow_id", type="S"),
            aws.dynamodb.TableAttributeArgs(name="placed_at", type="N"),  # Epoch timestamp for sorting
        ],
        hash_key="workflow_id",
        range_key="placed_at",
        name="workflow_orders",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
        ttl=aws.dynamodb.TableTtlArgs(
            enabled=True,
            attribute_name="ttl",
        ),
    )
```

**Setting TTL Values:**

```python
# Calculate TTL when writing records
now = datetime.datetime.now(datetime.timezone.utc)
ttl_timestamp = int((now + datetime.timedelta(days=7)).timestamp())

# Store with reserved word protection
ExpressionAttributeNames={"#ttl": "ttl"}
ExpressionAttributeValues={":ttl": ttl_timestamp}
```

**Alternatives Considered:**
- Using "expires_at" as attribute name → Rejected: Non-standard, inconsistent with existing tables
- Longer retention (30 days) → Rejected: 7 days sufficient per spec requirements
- Client-side deletion → Rejected: Manual overhead, risk of missed deletions

**References:**
- `/Users/kiva/codes/saxo-order/pulumi/dynamodb.py` - alerts_table (lines ~35-50)
- `/Users/kiva/codes/saxo-order/client/aws_client.py` - store_alerts() method with TTL calculation

---

## 2. Order Event Capture Integration Point

### Decision: Add tracking after order signal generation in WorkflowEngine.run()

**Rationale:**
- WorkflowEngine.run() generates order signals but does NOT place orders
- Lines 131-146 contain the loop where order signals are logged and sent to Slack
- This is the correct point to capture order metadata before actual placement
- All order details are available: workflow name, order price/quantity/direction, asset info

**Integration Point:**

**File:** `engines/workflow_engine.py`
**Method:** `WorkflowEngine.run()`
**Location:** Lines 131-146 (the `if order[1] is not None:` block)

```python
for order in results:
    if order[1] is not None:
        asset = self.saxo_client.get_asset(order[1][1].code)
        log = f"Workflow `{order[0].name}` will trigger an order..."
        self.logger.debug(log)

        # EXISTING: Slack notification
        channel = "#workflows-stock" if asset["AssetType"] == AssetType.STOCK else "#workflows"
        self.slack_client.chat_postMessage(channel=channel, text=log)

        # NEW: Record order tracking (add here)
        try:
            self.dynamodb_client.record_workflow_order(
                workflow_id=order[0].id,  # Workflow UUID
                workflow_name=order[0].name,
                order_code=order[1][1].code,
                order_price=order[1][1].price,
                order_quantity=order[1][1].quantity,
                order_direction=order[1][1].direction,
                order_type=order[1][1].type,
                asset_type=asset["AssetType"],
                trigger_close=order[1][0].close,
            )
        except Exception as e:
            self.logger.error(f"Failed to track order for {order[0].name}: {e}")
            # Continue - don't block workflow execution
```

**Available Data at This Point:**

From `order[0]` (Workflow):
- `workflow.id` - UUID
- `workflow.name` - Display name
- `workflow.cfd`, `workflow.index` - Asset identifiers

From `order[1][1]` (Order):
- `code` - Asset code (e.g., "FRA40.I")
- `price` - Entry price
- `quantity` - Order size
- `direction` - Buy/Sell (enum)
- `type` - LIMIT/OPEN_STOP (enum)

From `order[1][0]` (Trigger Candle):
- `close`, `higher`, `lower`, `open` - Price data

**Error Handling Pattern:**
- Wrap in try/except to prevent blocking workflow execution
- Log errors using existing logger
- Follow pattern from existing error handlers (lines 62-70)

**Alternatives Considered:**
- Track at actual order placement → Rejected: Order placement happens elsewhere (not in WorkflowEngine)
- Track before condition evaluation → Rejected: Would track all workflow runs, not just order placements
- Add to Lambda function → Rejected: WorkflowEngine is called from both Lambda and CLI

**References:**
- `/Users/kiva/codes/saxo-order/engines/workflow_engine.py` - Lines 131-146
- `/Users/kiva/codes/saxo-order/lambda_function.py` - execute_workflow() caller

---

## 3. DynamoDB Query Patterns for Order Retrieval

### Decision: Use Query (not Scan) with ScanIndexForward=False for DESC ordering

**Rationale:**
- Query is more efficient than Scan for partition key lookups
- Composite key (workflow_id + placed_at) enables sorting by timestamp
- ScanIndexForward=False gives newest-first ordering (required by spec)
- Pagination with LastEvaluatedKey handles large result sets

**Query Implementation:**

```python
# client/dynamodb_client.py - Add new method
def get_workflow_orders(
    self,
    workflow_id: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all orders for a workflow, sorted by timestamp (newest first).

    Args:
        workflow_id: Workflow unique identifier
        limit: Optional maximum number of orders to return

    Returns:
        List of order dictionaries sorted by placed_at DESC
    """
    try:
        query_params = {
            "KeyConditionExpression": "workflow_id = :wf_id",
            "ExpressionAttributeValues": {":wf_id": workflow_id},
            "ScanIndexForward": False,  # DESC order - newest first
        }

        if limit:
            query_params["Limit"] = limit

        response = self.dynamodb.Table("workflow_orders").query(**query_params)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB query error: {response}")
            return []

        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self.dynamodb.Table("workflow_orders").query(**query_params)
            items.extend(response.get("Items", []))

        return items

    except Exception as e:
        self.logger.error(f"Error querying orders for workflow {workflow_id}: {e}")
        return []
```

**Pagination Pattern:**
- Use `LastEvaluatedKey` from response
- Pass as `ExclusiveStartKey` to continue query
- Loop until `LastEvaluatedKey` not present
- Consistent with existing `get_all_workflows()` pattern

**Sort Key Format:**
- Store `placed_at` as Number (epoch timestamp in seconds)
- Enables efficient range queries and sorting
- Consistent with TTL attribute format

**Alternatives Considered:**
- Store placed_at as String (ISO format) → Rejected: Less efficient for sorting, requires lexicographic comparison
- Use Global Secondary Index → Rejected: Not needed, partition key + sort key sufficient
- Scan with FilterExpression → Rejected: Inefficient, reads entire table

**References:**
- `/Users/kiva/codes/saxo-order/client/aws_client.py` - get_all_workflows() pagination pattern
- `/Users/kiva/codes/saxo-order/pulumi/dynamodb.py` - alerts_table composite key example

---

## 4. Frontend Order History Integration

### Decision: Hybrid approach - last order in list, full history in modal

**Rationale:**
- Minimal overhead: Last order timestamp fetched with existing 60-second poll
- Lazy loading: Full history only loaded when modal opens
- Separation of concerns: Modal manages its own order history state
- Performance: Avoids loading full history for all workflows on list load

**List View Integration:**

**Add "Last Order" Column to WorkflowTable.tsx:**

```typescript
// Add after "End Date" column
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

**Backend Changes:**

```python
# model/workflow_api.py - Update WorkflowListItem
class WorkflowListItem(BaseModel):
    id: str
    name: str
    # ... existing fields ...
    # NEW FIELDS:
    last_order_timestamp: Optional[str] = None
    last_order_direction: Optional[str] = None
    last_order_quantity: Optional[float] = None
```

**Modal Order History Section:**

**Add Order History to WorkflowDetailModal.tsx:**

```typescript
// Local component state
const [orderHistory, setOrderHistory] = useState<OrderHistoryItem[]>([]);
const [orderHistoryLoading, setOrderHistoryLoading] = useState(false);

// Load on modal mount
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

// Render in modal body (after Trigger section, before Metadata)
<div className="detail-section">
  <h3>Order History</h3>
  {orderHistoryLoading && <div>Loading...</div>}
  {!orderHistoryLoading && orderHistory.length === 0 && (
    <div className="order-history-empty">No orders placed yet</div>
  )}
  {!orderHistoryLoading && orderHistory.length > 0 && (
    <table className="order-history-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Direction</th>
          <th>Quantity</th>
          <th>Price</th>
          <th>Asset</th>
        </tr>
      </thead>
      <tbody>
        {orderHistory.map(order => (
          <tr key={order.order_id}>
            <td>{formatDate(order.placed_at)}</td>
            <td>
              <span className={`order-direction-badge order-direction-${order.direction.toLowerCase()}`}>
                {order.direction}
              </span>
            </td>
            <td>{order.quantity}</td>
            <td>${order.price.toFixed(2)}</td>
            <td>{order.asset_code}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )}
</div>
```

**API Service Method:**

```typescript
// frontend/src/services/api.ts - Add to workflowService
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
```

**State Management Strategy:**
- **Page-level state:** Only workflow list data (as currently)
- **Modal component state:** Order history (loaded on modal open)
- **No shared state:** Order data not needed outside modal context
- **Polling:** Optional 30-second refresh in modal (lower priority than list poll)

**CSS Styling:**

```css
/* Reuse existing patterns from WorkflowTable.css and WorkflowDetailModal.css */
.order-history-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.order-history-table th {
  background: #0d1117;
  color: #8b949e;
  font-weight: 600;
  padding: 0.75rem;
  border-bottom: 1px solid #30363d;
  text-align: left;
}

.order-history-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #21262d;
  color: #e6edf3;
}

.order-direction-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.8rem;
}

.order-direction-buy {
  background: rgba(46, 160, 67, 0.15);
  border: 1px solid #3fb950;
  color: #3fb950;
}

.order-direction-sell {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid #f85149;
  color: #f85149;
}

.order-history-empty {
  text-align: center;
  color: #8b949e;
  padding: 2rem;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
}
```

**Alternatives Considered:**
- Fetch full history with list data → Rejected: Performance overhead for unused data
- Page-level state for orders → Rejected: Unnecessary complexity, modal-scoped data
- Real-time polling → Rejected: 30-second interval sufficient per spec (SC-001: <2 seconds retrieval)
- Separate orders page → Rejected: Over-engineering, modal integration sufficient

**References:**
- `/Users/kiva/codes/saxo-order/frontend/src/pages/Workflows.tsx` - Existing polling pattern
- `/Users/kiva/codes/saxo-order/frontend/src/components/WorkflowTable.tsx` - Table styling
- `/Users/kiva/codes/saxo-order/frontend/src/components/WorkflowDetailModal.tsx` - Modal structure

---

## 5. Backward Compatibility Considerations

### Decision: Non-breaking changes with graceful degradation

**Key Compatibility Requirements:**

1. **WorkflowEngine Modifications:**
   - Order tracking is additive (new functionality)
   - Wrapped in try/except to prevent blocking existing workflows
   - No changes to existing method signatures
   - DynamoDB client injection via constructor (existing pattern)

2. **DynamoDB Client Extension:**
   - New method `record_workflow_order()` - no impact on existing methods
   - Follows existing patterns (store_alerts, store_indicator)
   - Error handling prevents cascading failures

3. **API Endpoint Addition:**
   - New endpoint `/api/workflow/workflows/{id}/orders` - no breaking changes
   - Existing endpoints unchanged
   - Frontend can gracefully handle missing order data (display "-" in table)

4. **Frontend Compatibility:**
   - Optional fields in WorkflowListItem (last_order_timestamp, etc.)
   - Modal displays "No orders" if order history API fails
   - Backward compatible with workflows that have never placed orders

**Testing Strategy:**
- Run existing workflow tests to ensure no regressions
- Test workflow execution without DynamoDB available (graceful degradation)
- Test frontend with missing order data (should show "-" or "No orders")

**Migration Plan:**
- Deploy backend first (DynamoDB table + API endpoints)
- Deploy frontend second (UI components + API calls)
- No data migration needed (new table, no existing data)

**Rollback Plan:**
- Remove DynamoDB table via Pulumi
- Revert WorkflowEngine changes
- Revert frontend changes
- No data loss (TTL ensures cleanup)

---

## Summary of Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **TTL Configuration** | Use "ttl" attribute, 7-day retention | Consistent with existing alerts table pattern |
| **Integration Point** | WorkflowEngine.run() lines 131-146 | All order data available, existing notification point |
| **DynamoDB Access** | Query with ScanIndexForward=False | Efficient, sorted results, follows existing patterns |
| **Frontend Strategy** | Hybrid: last order in list, full history in modal | Minimal overhead, lazy loading, separation of concerns |
| **State Management** | Modal component state | Scope-appropriate, reduces complexity |
| **Backward Compatibility** | Non-breaking with graceful degradation | Safe deployment, no data migration needed |

---

## Next Steps

With research complete, proceed to **Phase 1: Design & Contracts** to create:
1. `data-model.md` - Domain models and data structures
2. `contracts/workflow-orders-api.yaml` - OpenAPI specification
3. `quickstart.md` - Development and testing guide
4. Update agent context with new technologies/patterns
