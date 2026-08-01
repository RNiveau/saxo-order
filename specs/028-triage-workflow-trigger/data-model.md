# Data Model: Workflow-Trigger Corroboration

**Feature**: 028-triage-workflow-trigger | **Date**: 2026-08-01

No new table. No schema migration. One new domain entity, one new field on an existing entity, and
an additive field inside the existing `alert_digests` item.

## 1. `WorkflowTrigger` (new — `model/__init__.py`)

A same-day firing of a registered workflow, already resolved to the asset it corroborates.

| Field | Type | Notes |
|-------|------|-------|
| `workflow_name` | `str` | From the `workflow_orders` row; shown to the trader |
| `direction` | `Direction` | Existing enum. **Parsed by name** — see §4 |
| `order_price` | `float` | Price of the order the workflow produced |
| `trigger_close` | `Optional[float]` | Market close at firing; `None` when the engine could not record it |
| `placed_at` | `int` | Epoch seconds; the source of the displayed time of day |
| `dry_run` | `bool` | From the **workflow definition**, not the order row |

**Validation**
- `order_price > 0` — `workflow_orders` already enforces this at write time (`WorkflowOrder.__post_init__`), so a violation means corrupt data: log and drop the trigger.
- `direction` must resolve to a `Direction` member; an unknown value raises `SaxoException` inside the collector, which catches it, logs, and drops that trigger.
- `placed_at` must fall inside the session window (§5); out-of-window rows are filtered before construction.

**Not carried**: `order_quantity`, `order_type`, `asset_type`, `execution_context`, `ttl`, `id`,
`workflow_id`. The brief answers "was this corroborated, which way, when" — position sizing and
order mechanics belong to the workflow orders page.

## 2. `TriagedAsset` (modified — `model/__init__.py`)

```python
@dataclass
class TriagedAsset:
    asset_code: str
    asset_description: str
    exchange: str
    conviction: Conviction
    rationale: str
    patterns: List[AlertType]
    ma50_slope: Optional[float] = None
    rank: Optional[int] = None
    country_code: Optional[str] = None
    workflow_triggers: List[WorkflowTrigger] = field(default_factory=list)   # NEW
```

Empty list on most assets. Defaulting to `[]` rather than `None` keeps every consumer's iteration
unconditional; "has corroboration" is `len(...) > 0`, expressed once.

## 3. `AlertDigest`

Unchanged — same fields, same key schema, same absence of TTL. Only the contents of its
`triaged_assets` grow.

## 4. Join: `workflow_orders` row → asset

Three steps, each of which can drop a trigger without affecting the rest.

**Step 1 — window filter.** Keep rows whose `placed_at` is inside the session window (§5).

**Step 2 — resolve the underlying.** `workflow_orders.order_code` is the **CFD actually traded**,
not the asset the alert scan sees. Join `workflow_orders.workflow_id` against the
`{workflow_id: (name, index, dry_run)}` map built from one `get_all_workflows()` read.
`workflow.index` is the underlying; `workflow.dry_run` is the label. A `workflow_id` absent from the
map (deleted workflow) drops the trigger.

**Step 3 — match to an alert asset.** Case-insensitive, reusing the semantics of
`WorkflowService.get_workflows_by_asset`:

```
index.lower() == asset_code.lower()
  or index.lower() == f"{asset_code}:{country_code}".lower()
```

**Trap — never match on `Alert.id`.** `Alert.id` joins with an underscore (`AI_xpar`);
`workflow.index` uses a colon (`AI:xpar`). Comparing ids would silently never match and the feature
would appear to do nothing. Match on the `asset_code` / `country_code` fields.

**Trap — `order_direction` is stored as the enum NAME.** `WorkflowEngine` writes
`order_direction.name`, so the stored value is `"BUY"`, while `Direction.BUY.value` is `"Buy"`.
Parse with `Direction[value]`, not `Direction(value)`.

Unmatched triggers are logged with both sides of the comparison — a mismatch must be diagnosable
from one run's logs, not inferred from an absence of corroboration.

## 5. Session window

```
start = midnight of run_date in ZoneInfo("Europe/Paris")   → epoch seconds
end   = now                                                → epoch seconds
keep row if start <= placed_at <= end
```

`run_date` comes from the digest being built, so manual and off-schedule runs compute their own
window rather than assuming the 18:15 schedule.

## 6. Collector signature and output

```python
async def collect_todays_triggers(
    dynamodb_client, run_date: str, alerts: List[Alert]
) -> Dict[str, List[WorkflowTrigger]]
```

The alert set is a **parameter, not an afterthought**: FR-002 makes the scanned assets the domain
of the result, and the output is keyed by `Alert.id`, which only the alerts can supply. (Earlier
drafts of this document showed a two-argument signature; that could not have satisfied FR-002.)

Keyed by the same key `TriageAgent._group_by_asset` uses (`Alert.id`), so attaching is a dict
lookup with no second matching rule. Assets with no trigger are **absent** from the map, not present
with an empty list. On any failure the whole map is `{}`.

## 7. Reasoning payload

Per asset, `workflow_triggers` is added **only when non-empty**:

```json
{
  "id": "AI_xpar",
  "patterns": ["combo", "mm50_touch"],
  "ma50_slope": 4.2,
  "workflow_triggers": [
    {"workflow": "AI breakout H1", "direction": "Buy", "dry_run": false, "hour": "14:30"}
  ]
}
```

`hour` is Paris-local `HH:MM` derived from `placed_at` — the model reasons about "when in the
session", not about epoch arithmetic. Prices are omitted from the payload: they carry no ranking
information and would invite spurious precision. The response schema is **unchanged** (research R7);
triggers are re-attached from the collector map when building each `TriagedAsset`, never read back
from the model.

## 8. Persistence (inside the existing `alert_digests` item)

```json
{
  "asset_code": "AI",
  "conviction": "high",
  "rank": 1,
  "patterns": ["combo", "mm50_touch"],
  "ma50_slope": 4.2,
  "workflow_triggers": [
    {
      "workflow_name": "AI breakout H1",
      "direction": "BUY",
      "order_price": 158.4,
      "trigger_close": 157.9,
      "placed_at": 1785412200,
      "dry_run": false
    }
  ]
}
```

Omitted entirely when empty, so existing items and no-trigger days are byte-identical to today.
Floats pass through the existing `_convert_floats_to_decimal` on write; `AlertDigestService`
converts `Decimal` back to `float` on read. `direction` is stored as the enum **name**, matching
`workflow_orders` and keeping one parse rule across both tables.

Digests written before this feature have no `workflow_triggers` key — readers must treat a missing
key as an empty list, never as an error (A-005: no backfill).

## 9. API shape

`WorkflowTriggerResponse` mirrors the persisted fields, plus `placed_at` rendered for display. The
field on `TriagedAssetResponse` is `Optional[List[...]] = None`, omitted when empty so a no-trigger
brief serialises exactly as it does today. The TypeScript interface mirrors it field for field, per
the constitution's API Contract Standards.

## 10. Entity relationships

```
Workflow (workflows)
  └─ id ──────────────┐
                      │  (resolution: 1 read for all)
WorkflowOrder (workflow_orders, TTL'd)
  ├─ workflow_id ─────┘
  ├─ order_code  → the CFD traded  (NOT the join key)
  └─ placed_at   → window filter
                      │
                      ▼  workflow.index ≈ asset_code[:country_code]
Alert (in memory, this run)
  └─ asset_code + country_code
                      │
                      ▼
TriagedAsset ──► workflow_triggers: List[WorkflowTrigger]
                      │
                      ▼
AlertDigest (alert_digests, no TTL — outlives the source rows, SC-008)
```

The lifetime asymmetry is the reason for §8: `workflow_orders` expires, `alert_digests` does not, so
the digest must carry its own copy of the corroboration it was ranked on. It cannot re-derive it.
