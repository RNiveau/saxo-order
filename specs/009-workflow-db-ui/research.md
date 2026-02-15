# Research: Workflow Management UI & Database Migration

**Feature**: 009-workflow-db-ui
**Date**: 2026-02-08
**Purpose**: Technical research for implementing workflow database storage and management UI

## Decision 1: DynamoDB Table Schema Design

**Decision**: Use simple partition key (`id`) with nested JSON storage for conditions and trigger

**Rationale**:
- Primary access pattern is by ID (`GET /api/workflows/{id}`)
- Workflows are always fetched/stored as complete units
- Nested JSON aligns with existing patterns (alerts table stores nested alert arrays)
- Read-heavy workload (Lambda hourly + UI views) with rare writes (manual migrations)
- Items will be 2-5 KB well under DynamoDB's 400 KB limit
- No natural composite key exists (unlike alerts with asset_code + country_code)

**Table Definition**:
```python
aws.dynamodb.Table(
    "workflows",
    attributes=[aws.dynamodb.TableAttributeArgs(name="id", type="S")],
    hash_key="id",
    billing_mode="PAY_PER_REQUEST",
    stream_enabled=True,
    stream_view_type="NEW_AND_OLD_IMAGES"
)
```

**Item Structure**:
```python
{
    "id": "uuid-string",  # Partition key
    "name": "buy bbb h1 dax",  # Unique constraint enforced in migration
    "index": "DAX.I",
    "cfd": "GER40.I",
    "enable": True,
    "dry_run": False,
    "is_us": False,
    "end_date": "2026-12-31" or None,  # ISO 8601
    "conditions": [  # JSON array
        {
            "indicator": {"name": "bbb", "ut": "h1", "value": None, "zone_value": None},
            "close": {"direction": "above", "ut": "h1", "spread": 20},
            "element": None
        }
    ],
    "trigger": {  # JSON object
        "ut": "h1",
        "signal": "breakout",
        "location": "higher",
        "order_direction": "buy",
        "quantity": 0.1
    },
    "created_at": "2026-02-08T10:00:00Z",
    "updated_at": "2026-02-08T10:00:00Z"
}
```

**Alternatives Considered**:
1. **Normalized multi-table design** (workflows, conditions, triggers tables):
   - Rejected: Requires complex joins, increases latency, no benefit for atomic workflow operations
2. **Composite key (name + index)**:
   - Rejected: Primary access is by generated ID, not name lookups
3. **Global Secondary Index (GSI) for filtering**:
   - Deferred: With 50-100 workflows, Scan + FilterExpression is faster and cheaper than GSI write amplification
   - Add GSI only if scale exceeds 500 workflows or <100ms query requirement emerges

**Cost Analysis** (100 workflows):
- Storage: 400 KB × $0.25/GB/month = $0.0001/month
- Lambda reads: 24 scans/day × 50 RCUs = $0.30/month
- API reads: 100 requests/day × 1 RCU = $0.0075/month
- **Total: ~$0.31/month**

---

## Decision 2: Query Pattern Implementation

**Decision**: Use Scan with FilterExpression for MVP, not GSI

**Rationale**:
- Small dataset (50-100 workflows, ~500 KB total)
- Scan completes in <500ms at this scale
- FilterExpression costs: 50 RCUs per full scan × 24/day = negligible cost
- Avoids GSI complexity (backfill, consistency, write amplification)
- Lambda loads ALL enabled workflows into memory - single Scan is acceptable

**Implementation**:
```python
def list_workflows(enabled: Optional[bool], index: Optional[str]):
    scan_kwargs = {}
    filters = []
    expr_values = {}

    if enabled is not None:
        filters.append("enable = :enabled")
        expr_values[":enabled"] = enabled

    if index:
        filters.append("contains(#idx, :index)")
        scan_kwargs["ExpressionAttributeNames"] = {"#idx": "index"}
        expr_values[":index"] = index.lower()

    if filters:
        scan_kwargs["FilterExpression"] = " AND ".join(filters)
        scan_kwargs["ExpressionAttributeValues"] = expr_values

    response = table.scan(**scan_kwargs)
    items = response["Items"]

    # Handle pagination
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        items.extend(response["Items"])

    return items
```

**Sorting**: Application-level after fetch (100 items sort in <1ms)

**Filtering by indicator_type**: Application-level (scan nested conditions array)

**Alternatives Considered**:
- **GSI on enable + index**: Deferred until >500 workflows

---

## Decision 3: Migration Strategy

**Decision**: Use DynamoDB batch_writer with pre-migration validation

**Rationale**:
- Batch writer automatically handles batching (25 items/batch) and retries
- Pre-validation catches duplicate names before any writes occur
- UUID generation ensures no ID conflicts
- Date format conversion (YYYY/MM/DD → ISO 8601) standardizes storage

**Migration Flow**:
1. Load workflows.yml
2. Validate no duplicate names (fail fast if found)
3. Transform each workflow (generate UUID, convert dates, apply trigger defaults)
4. Batch insert with progress logging
5. Post-migration verification (count match)

**Idempotency**: Add conditional expression to prevent duplicate names:
```python
batch.put_item(
    Item=item,
    ConditionExpression="attribute_not_exists(#name)",
    ExpressionAttributeNames={"#name": "name"}
)
```

**Rollback Capability**: Track created IDs during migration for batch deletion on failure

**Alternatives Considered**:
- **Single put_item per workflow**: Rejected - no automatic retry, slower
- **TransactWriteItems**: Rejected - limited to 100 items, overkill for migration

---

## Decision 4: React Table Component Pattern

**Decision**: Build custom table component (no library)

**Rationale**:
- Existing codebase uses native HTML `<table>` elements (Watchlist.tsx, LongTermPositions.tsx)
- Shared CSS (`shared.css`) provides `.data-table` utilities
- No table libraries currently installed - maintains zero-dependency approach
- 50-1000 workflows performs well with custom solution
- Aligns with existing component patterns

**Implementation Pattern**:
```tsx
<div className="data-table">
  <table>
    <thead>
      <tr>
        <th onClick={() => handleSort('name')}>Name</th>
        <th>Index</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {paginatedWorkflows.map((workflow) => (
        <tr key={workflow.id} onClick={() => navigate(`/workflows/${workflow.id}`)}>
          <td>{workflow.name}</td>
          <td>{workflow.index}</td>
          <td>
            {workflow.enable ? (
              <span className="badge badge-success">✓ Enabled</span>
            ) : (
              <span className="badge badge-danger">✗ Disabled</span>
            )}
          </td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

**Alternatives Considered**:
- **TanStack Table (react-table)**: Deferred - adds complexity, not needed for current scale
- **Material React Table**: Deferred - heavy library for simple table needs

---

## Decision 5: Pagination Strategy

**Decision**: Client-side pagination

**Rationale**:
- Existing Alerts page successfully uses client-side filtering/sorting
- 50-1000 workflows fits comfortably in browser memory
- Instant pagination without network requests
- Simpler implementation than server-side
- Reduces API calls

**Implementation**:
```tsx
const [currentPage, setCurrentPage] = useState(1);
const itemsPerPage = 50;

const paginatedWorkflows = useMemo(() => {
  const startIndex = (currentPage - 1) * itemsPerPage;
  return filteredWorkflows.slice(startIndex, startIndex + itemsPerPage);
}, [filteredWorkflows, currentPage]);
```

**When to Switch to Server-Side**:
- Workflow count regularly exceeds 1000 items
- Initial load time becomes problematic
- Memory constraints on client devices

**Alternatives Considered**:
- **Server-side pagination**: Deferred - unnecessary complexity for current scale

---

## Decision 6: Filtering and Sorting Strategy

**Decision**: Client-side filtering and sorting

**Rationale**:
- Instant feedback without network latency
- Works offline/with network issues
- Alerts.tsx demonstrates successful client-side filtering pattern
- Negligible performance overhead for 100+ workflows

**Implementation** (following Alerts.tsx pattern):
```tsx
const [sortBy, setSortBy] = useState<'name' | 'index'>('name');
const [filterEnabled, setFilterEnabled] = useState<'all' | 'enabled' | 'disabled'>('all');

const filteredAndSortedWorkflows = workflows
  .filter((workflow) => {
    if (filterEnabled === 'enabled') return workflow.enable;
    if (filterEnabled === 'disabled') return !workflow.enable;
    return true;
  })
  .sort((a, b) => {
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    return a.index.localeCompare(b.index);
  });
```

**Alternatives Considered**:
- **Server-side filtering with API query params**: Deferred - adds latency, no benefit at current scale

---

## Decision 7: State Management

**Decision**: React hooks + URL query parameters

**Rationale**:
- useState for component-local state
- URL params for shareable state (filters, pagination, sort order)
- Enables bookmarking: `/workflows?status=enabled&page=2`
- Browser back/forward buttons work naturally
- State persists across page refreshes
- React Router DOM 7+ already in dependencies

**Implementation**:
```tsx
import { useSearchParams } from 'react-router-dom';

const [searchParams, setSearchParams] = useSearchParams();

// Read from URL
const currentPage = parseInt(searchParams.get('page') || '1', 10);
const filterStatus = searchParams.get('status') || 'all';

// Update URL
const updatePage = (page: number) => {
  const newParams = new URLSearchParams(searchParams);
  newParams.set('page', page.toString());
  setSearchParams(newParams);
};
```

**Important**: Reset to page 1 when filters change

**Alternatives Considered**:
- **Pure useState without URL params**: Simpler but loses shareability/bookmarking

---

## Decision 8: Detail View Pattern

**Decision**: Separate route (`/workflows/:workflowId`)

**Rationale**:
- Existing codebase uses separate routes for detail views (`/asset/:symbol`)
- Provides deep linking for sharing specific workflows
- Browser back button support
- Better mobile experience
- SEO benefits

**Implementation**:
```tsx
// Router configuration
<Route path="/workflows" element={<Workflows />} />
<Route path="/workflows/:workflowId" element={<WorkflowDetail />} />

// Table row click
const handleWorkflowClick = (workflow) => {
  navigate(`/workflows/${workflow.id}`);
};
```

**Optional Enhancement**: Render as modal overlay while maintaining route (best of both patterns)

**Responsive Design**:
- Desktop: Full page or modal
- Mobile: Slide-up drawer with swipe-to-dismiss

**Alternatives Considered**:
- **Modal without route change**: Rejected - no deep linking, back button doesn't work

---

## Decision 9: Auto-Refresh Pattern

**Decision**: Visibility API + setInterval (copy from LongTermPositions.tsx)

**Rationale**:
- LongTermPositions.tsx implements perfect pattern (lines 17-47)
- Uses `document.visibilitychange` to pause polling when tab hidden
- Prevents unnecessary API calls and battery drain
- Immediately refreshes when tab becomes visible

**Implementation** (from LongTermPositions.tsx):
```tsx
useEffect(() => {
  loadWorkflows();

  let intervalId: NodeJS.Timeout | null = null;

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      loadWorkflows(); // Reload immediately
      if (!intervalId) {
        intervalId = setInterval(loadWorkflows, 60000); // 60 seconds
      }
    } else {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }
  };

  handleVisibilityChange();
  document.addEventListener('visibilitychange', handleVisibilityChange);

  return () => {
    if (intervalId) clearInterval(intervalId);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  };
}, []);
```

**Alternatives Considered**:
- **Always polling**: Wastes resources when tab hidden
- **React Query auto-refetch**: Adds library dependency, existing pattern works well

---

## Decision 10: Lambda Workflow Loading

**Decision**: Check for DynamoDB table first, fallback to S3/YAML if unavailable

**Rationale**:
- Graceful degradation if database migration hasn't occurred
- Backward compatibility during rollout
- Reduces deployment risk

**Implementation**:
```python
def load_workflows(force_from_disk: bool = False) -> List[Workflow]:
    if force_from_disk:
        return _load_from_yaml()

    try:
        # Try database first
        dynamodb_client = DynamoDBClient()
        workflows = dynamodb_client.get_enabled_workflows()
        if workflows:
            logger.info(f"Loaded {len(workflows)} workflows from DynamoDB")
            return workflows
    except Exception as e:
        logger.warning(f"Failed to load workflows from DynamoDB: {e}")

    # Fallback to S3/YAML
    logger.info("Falling back to YAML workflow loading")
    return _load_from_yaml()
```

**Alternatives Considered**:
- **Database-only (no fallback)**: Rejected - creates hard cutover requirement

---

## Technology Stack Summary

**Backend**:
- Python 3.11
- FastAPI (existing)
- boto3 DynamoDB client (existing)
- Pydantic models (existing)

**Database**:
- DynamoDB (PAY_PER_REQUEST billing)
- Table: `workflows` with simple partition key `id`
- No GSI for MVP

**Frontend**:
- React 19 with TypeScript 5+
- React Router DOM v7+ (existing)
- Axios for API calls (existing)
- Custom table component (no library)
- Shared CSS utilities from `shared.css`

**Migration**:
- Python script using boto3 batch_writer
- YAML parsing with PyYAML (existing)
- UUID generation for IDs

**Testing**:
- pytest for backend (existing)
- Mock DynamoDB with moto (if needed)
- Frontend testing TBD (no framework currently configured)

---

## References

- DynamoDB single-table design patterns
- React 19 best practices for data tables
- Existing codebase patterns (Watchlist.tsx, LongTermPositions.tsx, Alerts.tsx)
- Constitution adherence (layered architecture, clean code, configuration-driven)
