# Data Model: Workflow Management UI & Database Migration

**Feature**: 009-workflow-db-ui
**Date**: 2026-02-08

## Entity: Workflow

### Description
Complete trading strategy configuration stored in DynamoDB. Represents an automated workflow that monitors technical indicators and triggers trading orders when conditions are met.

### Storage
**Table**: `workflows`
**Primary Key**: `id` (String, UUID v4)
**Unique Constraint**: `name` field must be unique (enforced in migration script)

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `id` | String (UUID) | Yes | Unique identifier generated during migration | UUID v4 format |
| `name` | String | Yes | Human-readable workflow name (e.g., "buy bbb h1 dax") | Unique across all workflows, max 200 chars |
| `index` | String | Yes | Target index symbol (e.g., "DAX.I", "CAC40.I") | Non-empty string |
| `cfd` | String | Yes | CFD symbol for order execution (e.g., "GER40.I") | Non-empty string |
| `enable` | Boolean | Yes | Whether workflow is active | true or false |
| `dry_run` | Boolean | Yes | Whether workflow generates orders without execution | true or false, defaults to false |
| `is_us` | Boolean | Yes | Whether workflow targets US market (affects market hours) | true or false, defaults to false |
| `end_date` | String (ISO 8601) | No | Optional expiration date for workflow (YYYY-MM-DD) | ISO 8601 date format or null |
| `conditions` | Array[Condition] | Yes | List of conditions that must be met for workflow trigger | Non-empty array, min 1 condition |
| `trigger` | Trigger | Yes | Order generation parameters when conditions met | Valid Trigger object |
| `created_at` | String (ISO 8601) | Yes | Timestamp when workflow was created | ISO 8601 datetime format |
| `updated_at` | String (ISO 8601) | Yes | Timestamp when workflow was last modified | ISO 8601 datetime format |

### Relationships
- **None** (single-table design, no foreign keys)
- Workflows reference asset indices by string, not database relationships

---

## Entity: Condition

### Description
Evaluation rule nested within Workflow. Defines when a workflow should trigger based on indicator values and close candle parameters.

### Storage
**Nested within**: `Workflow.conditions` array

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `indicator` | Indicator | Yes | Technical indicator to monitor | Valid Indicator object |
| `close` | Close | Yes | Close candle evaluation parameters | Valid Close object |
| `element` | String (Enum) | No | Specific candle element to check (close, high, low) | "close", "high", "low", or null |

### Validation Rules
- Condition must have at least `indicator` and `close` defined
- If `element` is specified, must be one of supported types

---

## Entity: Indicator

### Description
Technical analysis indicator specification nested within Condition. Defines which indicator to calculate and monitor.

### Storage
**Nested within**: `Condition.indicator` object

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `name` | String (Enum) | Yes | Indicator type | "ma50", "combo", "bbb", "bbh", "polarite", "zone" |
| `ut` | String (Enum) | Yes | Unit time for indicator calculation | "daily", "h1", "h4", "15m", "weekly", "monthly" |
| `value` | Number (Decimal) | No | Fixed indicator value (for polarite/zone) | Decimal number or null |
| `zone_value` | Number (Decimal) | No | Zone upper bound (for zone indicator) | Decimal number or null, required if name="zone" |

### Validation Rules
- `name` must be one of supported indicator types
- `ut` must be one of supported time frames
- If `name` is "zone", both `value` and `zone_value` must be provided
- If `name` is "polarite", `value` must be provided

---

## Entity: Close

### Description
Close candle evaluation parameters nested within Condition. Defines how to evaluate if price is near the indicator.

### Storage
**Nested within**: `Condition.close` object

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `direction` | String (Enum) | Yes | Whether to check above or below indicator | "above" or "below" |
| `ut` | String (Enum) | Yes | Unit time for close candle retrieval | "daily", "h1", "h4", "15m", "weekly", "monthly" |
| `spread` | Number (Decimal) | Yes | Tolerance in points for condition matching | Non-negative decimal, defaults to 0 |

### Validation Rules
- `direction` must be "above" or "below"
- `ut` must be one of supported time frames
- `spread` must be >= 0

---

## Entity: Trigger

### Description
Order generation parameters nested within Workflow. Defines how to generate trading orders when conditions are met.

### Storage
**Nested within**: `Workflow.trigger` object

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `ut` | String (Enum) | Yes | Unit time for trigger candle retrieval | "daily", "h1", "h4", "15m", "weekly", "monthly" |
| `signal` | String (Enum) | Yes | Signal type for order generation | "breakout" (only supported value) |
| `location` | String (Enum) | Yes | Where to place order relative to indicator | "higher" or "lower" |
| `order_direction` | String (Enum) | Yes | Buy or sell direction | "buy" or "sell" |
| `quantity` | Number (Decimal) | Yes | Order quantity | Positive decimal, typically 0.1 |

### Validation Rules
- `signal` must be "breakout"
- `location` must be "higher" or "lower"
- `order_direction` must be "buy" or "sell"
- `quantity` must be > 0

---

## State Transitions

### Workflow States
Workflows don't have explicit state machines, but their behavior is controlled by:

1. **Enable State**:
   - `enable: true` → Workflow is active, Lambda will execute it
   - `enable: false` → Workflow is inactive, Lambda skips it

2. **Lifecycle**:
   - **Created**: Workflow inserted during migration with `created_at` timestamp
   - **Active**: `enable: true` and (no `end_date` or `end_date` in future)
   - **Expired**: `enable: true` but `end_date` in past (Lambda skips)
   - **Disabled**: `enable: false` (Lambda skips regardless of end_date)

3. **Dry Run Mode**:
   - `dry_run: true` → Workflow generates order notifications but doesn't execute trades
   - `dry_run: false` → Workflow executes actual trades (when integrated with order system)

**No State Transitions in Database**: Workflow states are determined by field values at read time, not stored as separate state field.

---

## Data Integrity Rules

### Uniqueness Constraints
- **Workflow.name**: Must be unique across all workflows (enforced in migration script via conditional put)

### Referential Integrity
- **None**: No foreign keys or database-level referential integrity
- Index symbols (e.g., "DAX.I") are validated against Saxo API at runtime, not at storage time

### Data Validation
- **Enum Values**: Indicator names, unit times, directions, signals validated against allowed sets
- **Required Fields**: All top-level Workflow fields except `end_date` are required
- **Array Constraints**: `conditions` array must have at least 1 element
- **Number Constraints**: `quantity` must be positive, `spread` must be non-negative

### Default Values (Migration)
If YAML workflow omits trigger configuration, apply defaults:
```python
{
    "ut": "h1",
    "signal": "breakout",
    "location": "higher" if close.direction == "above" else "lower",
    "order_direction": "buy" if close.direction == "above" else "sell",
    "quantity": 0.1
}
```

---

## Query Patterns

### Primary Queries

1. **Get by ID** (O(1)):
```python
workflow = dynamodb.Table("workflows").get_item(Key={"id": workflow_id})
```

2. **List all workflows with filters** (Scan):
```python
workflows = dynamodb.Table("workflows").scan(
    FilterExpression="enable = :enabled AND contains(#idx, :index)",
    ExpressionAttributeNames={"#idx": "index"},
    ExpressionAttributeValues={":enabled": True, ":index": "DAX"}
)
```

3. **Get enabled workflows for Lambda** (Scan + filter):
```python
workflows = dynamodb.Table("workflows").scan(
    FilterExpression="enable = :enabled",
    ExpressionAttributeValues={":enabled": True}
)
# Application-level filtering by end_date
active = [w for w in workflows if not w["end_date"] or w["end_date"] >= today]
```

### Secondary Queries (Application-Level)

4. **Filter by indicator type** (post-fetch):
```python
ma50_workflows = [
    w for w in workflows
    if any(c["indicator"]["name"] == "ma50" for c in w["conditions"])
]
```

5. **Sort by name** (post-fetch):
```python
sorted_workflows = sorted(workflows, key=lambda w: w["name"])
```

---

## Example Workflow Document

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "buy bbb h1 dax",
  "index": "DAX.I",
  "cfd": "GER40.I",
  "enable": true,
  "dry_run": false,
  "is_us": false,
  "end_date": null,
  "conditions": [
    {
      "indicator": {
        "name": "bbb",
        "ut": "h1",
        "value": null,
        "zone_value": null
      },
      "close": {
        "direction": "above",
        "ut": "h1",
        "spread": 20
      },
      "element": null
    }
  ],
  "trigger": {
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

---

## Migration Transformations

### YAML to DynamoDB Mapping

| YAML Field | DynamoDB Field | Transformation |
|------------|----------------|----------------|
| `name` | `name` | Direct copy |
| `index` | `index` | Direct copy |
| `cfd` | `cfd` | Direct copy |
| `enable` | `enable` | Direct copy (boolean) |
| `dry_run` | `dry_run` | Default to `false` if missing |
| `is_us` | `is_us` | Default to `false` if missing |
| `end_date` | `end_date` | Convert from "YYYY/MM/DD" to "YYYY-MM-DD", null if missing |
| `conditions[]` | `conditions[]` | Nest indicator + close + element into array |
| `trigger{}` | `trigger{}` | Copy if present, apply defaults if missing |
| N/A | `id` | Generate UUID v4 |
| N/A | `created_at` | Set to current timestamp |
| N/A | `updated_at` | Set to current timestamp |

### Type Conversions
- **Floats to Decimals**: All numeric values (value, zone_value, spread, quantity) converted to `Decimal` type for DynamoDB compatibility
- **Date Formats**: "2026/12/31" → "2026-12-31"
- **Booleans**: YAML booleans map directly to DynamoDB BOOL type

---

## Performance Characteristics

### Storage Estimates
- **Average Item Size**: 2-5 KB per workflow
- **100 Workflows**: ~400 KB total
- **1000 Workflows**: ~4 MB total

### Query Performance
- **Get by ID**: <10ms (single-item read)
- **Scan all workflows**: 100 items in ~200-500ms
- **Filter by indicator**: Add 10-50ms for application-level filtering

### Cost Projections (100 workflows)
- **Storage**: $0.0001/month
- **Read Operations**: $0.31/month (24 Lambda scans/day + 100 API calls/day)
- **Write Operations**: Negligible (rare manual migrations)

---

## Validation Logic

### Migration-Time Validation
```python
def validate_workflow(yaml_data: Dict) -> None:
    # Required fields
    assert yaml_data.get("name"), "Workflow name is required"
    assert yaml_data.get("index"), "Index is required"
    assert yaml_data.get("cfd"), "CFD is required"
    assert "enable" in yaml_data, "Enable flag is required"

    # Indicator type validation
    for cond in yaml_data["conditions"]:
        indicator_name = cond["indicator"]["name"]
        assert indicator_name in ["ma50", "combo", "bbb", "bbh", "polarite", "zone"], \
            f"Invalid indicator type: {indicator_name}"

    # Zone indicator validation
    for cond in yaml_data["conditions"]:
        if cond["indicator"]["name"] == "zone":
            assert cond["indicator"].get("value") is not None, \
                "Zone indicator requires value"
            assert cond["indicator"].get("zone_value") is not None, \
                "Zone indicator requires zone_value"
```

### Runtime Validation (Lambda Loader)
```python
def validate_loaded_workflow(workflow: Dict) -> bool:
    try:
        assert workflow["enable"] is True
        if workflow.get("end_date"):
            assert datetime.fromisoformat(workflow["end_date"]).date() >= date.today()
        assert len(workflow["conditions"]) > 0
        return True
    except (AssertionError, KeyError, ValueError):
        return False
```

---

## Future Schema Extensions

### Potential Additions (Out of Scope)
- `version` field for schema versioning
- `last_executed_at` timestamp
- `execution_count` counter
- `performance_metrics` object (P&L, win rate, etc.)
- `tags` array for categorization
- `created_by` user identifier (if multi-tenant)
- `revision_history` array for audit trail

These are explicitly **not included in MVP** to maintain simplicity.
