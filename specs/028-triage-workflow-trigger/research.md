# Research: Workflow-Trigger Corroboration in the Alert Triage Agent

**Feature**: 028-triage-workflow-trigger | **Date**: 2026-08-01
**Input**: [spec.md](./spec.md)

## R1. Resolving a trigger to the asset the workflow watches

- **Decision**: Read the workflow definitions **once per run** with the existing
  `DynamoDBClient.get_all_workflows()` and build an in-memory
  `{workflow_id: (name, index, dry_run)}` map. Join each `workflow_orders` row to that map by
  `workflow_id`. Do **not** call `get_workflow_by_id` per trigger.
- **Rationale**: The `workflows` table is tiny (one item per registered workflow) and
  `get_all_workflows()` already exists and is already used this way by
  `WorkflowService.get_workflows_by_asset`. One scan replaces N round trips, and the same record
  carries both fields the join needs — `index` (the underlying) and `dry_run` — so there is no
  second lookup for the dry-run label. This deviates from the feature description's suggested
  `get_workflow_by_id` path, deliberately.
- **Alternatives considered**: (a) `get_workflow_by_id` per triggering workflow — correct but N
  reads for data that fits in one scan, and N failure points inside a step that must not slow the
  scan. (b) Denormalising `index` onto `workflow_orders` at write time — would make triage a pure
  single-table read, but changes the order-recording path, which FR-021 forbids, and would not
  backfill existing rows.

## R2. The session window

- **Decision**: The window is `[Paris-local midnight of the run date, run time]`, computed with
  `zoneinfo.ZoneInfo("Europe/Paris")` and compared against `workflow_orders.placed_at`
  (epoch seconds, Number). The run date comes from the digest's own `run_date`, not from an
  assumed 18:15 schedule.
- **Rationale**: FR-004. `zoneinfo` is already the codebase's tool for Paris-local math
  (`utils/helper.py`), so DST is handled by the same mechanism as the rest of the project. Deriving
  the window from the run itself keeps manual and on-demand runs correct (spec edge case
  "manual or off-schedule triage run").
- **Alternatives considered**: (a) A rolling 24-hour window — simpler, but bleeds the previous
  evening's triggers into the morning of a manual run. (b) UTC day boundaries — wrong for a
  Euronext-hours product; a 00:30 Paris trigger in summer would land on the previous UTC day.

## R3. Matching the underlying to the alert asset

- **Decision**: Reuse the matching semantics already established in
  `WorkflowService.get_workflows_by_asset`: case-insensitive equality of `workflow.index` against
  either the bare `asset_code` or the composite `f"{asset_code}:{country_code}"`. Match on the
  `Alert`'s `asset_code`/`country_code` **fields**, never on `Alert.id`.
- **Rationale**: FR-003. One matching rule for "which workflows watch this asset" already exists
  and is proven; a second, subtly different rule would drift. The field-level caution matters:
  `Alert.id` joins with an underscore (`AI_xpar`) while `workflow.index` uses a colon
  (`AI:xpar`), so an id-level comparison would silently never match.
- **Alternatives considered**: (a) Normalising both sides through a new shared helper — worth doing
  if a third caller appears, but extracting it now for two callers is the speculative abstraction
  the constitution's Clean Code First principle warns against. (b) Fuzzy or prefix matching — FR-003
  requires dropping unresolvable triggers rather than guessing.

## R4. Where the logic lives

- **Decision**: A new `services/workflow_trigger_service.py` exposing an async
  `collect_todays_triggers(dynamodb_client, run_date) -> Dict[str, List[WorkflowTrigger]]`, keyed by
  the alert-asset key. `TriageAgent.synthesize` gains an optional `triggers` parameter and stays
  **synchronous and pure** — it receives the already-resolved map and never touches storage.
  `run_alerting` calls the collector and passes the result in.
- **Rationale**: Constitution I — the fetch-and-join is business logic and belongs in the Service
  layer, not in the CLI command; `TriageAgent` remaining pure keeps it unit-testable without async
  storage mocks, which is how its existing tests are written. Keeping the collector separate from
  `alert_triage_service.py` also means a total failure of trigger collection is an empty dict, not a
  broken triage.
- **Alternatives considered**: (a) Collecting inside `TriageAgent.synthesize` — would make the agent
  async and storage-dependent, forcing every existing triage test to grow a DynamoDB mock. (b)
  Inlining in `run_alerting` — puts business logic in the CLI layer, violating Constitution I.

## R5. Domain model for a trigger

- **Decision**: New `WorkflowTrigger` dataclass in `model/__init__.py`, carrying `workflow_name`,
  `direction: Direction`, `order_price: float`, `trigger_close: Optional[float]`,
  `placed_at: int`, `dry_run: bool`. Direction uses the existing `Direction` enum; no new enum is
  introduced.
- **Rationale**: Constitution II.3 (enum-driven) and V. `workflow_orders` stores
  `order_direction` as the enum **name** (`WorkflowEngine` writes `order_direction.name`), so
  parsing is `Direction[value]`, not `Direction(value)` — a real trap, since `Direction.BUY.value`
  is `"Buy"` while its name is `"BUY"`.
- **Alternatives considered**: Passing raw dicts into the agent — rejected: the model layer exists so
  that the reasoning payload and the persistence layer agree on shape.

## R6. Teaching the reasoning about triggers

- **Decision**: Extend the payload built by `TriageAgent._build_payload` with an optional
  `workflow_triggers` array per asset (omitted entirely when empty), and add a section to
  `TRIAGE_SYSTEM_PROMPT` covering: independence from the detectors (one convergence point,
  contrasted with the existing `congestion20`/`congestion100` collapse), directional authority at
  least equal to `combo`, contradiction as a red flag (parallel to the existing `mm50_touch`
  guidance), multiple same-day triggers still counting once, and dry-run triggers weighing one step
  lower.
- **Rationale**: FR-007 through FR-012. The existing prompt already teaches independence and
  red-flag reasoning for patterns; triggers slot into that same vocabulary rather than introducing a
  parallel scoring scheme. Omitting the key on assets without triggers keeps the payload honest and
  avoids teaching the model that `null` means anything.
- **Alternatives considered**: (a) A numeric weight or score in the payload — rejected: the whole
  design deliberately reasons in tiers, and a number invites false precision. (b) A separate
  pre-pass that re-ranks after the model responds — rejected: two ranking authorities that can
  disagree.

## R7. Structured-output schema

- **Decision**: `TRIAGE_RESPONSE_SCHEMA` is **unchanged**. Triggers are input-only; the response
  keeps `id`/`conviction`/`rank`/`rationale`, and the trigger appears in the digest because the
  service re-attaches it from the input map when building each `TriagedAsset`.
- **Rationale**: The model must not be able to invent, alter, or drop a trigger — it is a fact from
  storage. Echoing it back through the model would put a fact at the mercy of generation. This
  mirrors how `patterns` and `ma50_slope` are already re-attached from `grouped` in
  `_parse_triaged` rather than read from the response.
- **Alternatives considered**: Adding trigger fields to the response schema — rejected for the
  above; it would also enlarge the schema for zero informational gain.

## R8. Fallback ranking

- **Decision**: `_pattern_families` gains a companion so that an asset with ≥1 attached trigger
  counts one extra family in `_fallback_conviction`'s tally, and `_fallback_rationale` appends the
  workflow name and direction. Multiple triggers on one asset still add exactly one.
- **Rationale**: FR-013, FR-014, and A-004 (one point, no multiplier). The fallback's existing
  contract — pure, synchronous, side-effect-free, always succeeds — is preserved because the
  triggers arrive as plain data.
- **Alternatives considered**: Giving triggers a heavier weight in the fallback than in the
  reasoning — rejected: the two paths should rank consistently, or a fallback day would reorder the
  brief for reasons the trader cannot see.

## R9. Persistence and read-back

- **Decision**: `store_alert_digest` serialises `workflow_triggers` inside each triaged-asset item
  (omitted when empty); the existing `_convert_floats_to_decimal` pass handles the prices.
  `AlertDigestService` converts `Decimal` back to `float` on read, as it already does elsewhere.
- **Rationale**: FR-015 and SC-008 — `workflow_orders` carries a TTL and `alert_digests` does not,
  so a brief read months later must carry its own copy of the corroboration it was ranked on. It
  cannot re-derive it.
- **Alternatives considered**: Storing only the workflow id and re-resolving on read — rejected:
  the trigger row will have expired, and a renamed or deleted workflow would rewrite history.

## R10. Failure tolerance

- **Decision**: `collect_todays_triggers` catches every exception internally, logs a warning, and
  returns `{}`. The caller in `run_alerting` needs no new try/except — the existing triage block is
  already wrapped — and an empty map provably reproduces current behaviour through every downstream
  path (payload key omitted, prompt section inert, fallback tally unchanged, no persisted field).
- **Rationale**: FR-019 and FR-020. "Degrades to exactly today's behaviour" is stronger than
  "degrades gracefully", and an empty map is the same input the system will see on most days
  anyway — so the degraded path is the well-tested path.
- **Alternatives considered**: Letting failures bubble to the existing outer handler — the digest
  would survive, but a mid-loop failure could produce a *partially* enriched brief, where some
  corroborations are missing without any indication. All-or-nothing is easier to reason about.

## R11. Configuration

- **Decision**: No new configuration. The session window is derived, the convergence weight is fixed
  at one point by design (A-004), and dry-run handling is a labelling rule rather than a threshold.
- **Rationale**: Constitution III forbids hardcoded thresholds, but this feature introduces none —
  adding a knob nobody will turn is the over-engineering Constitution II.2 rejects. If the trader
  later wants dry-run triggers filtered out entirely, that becomes a boolean in `config.yml` at
  that point.
- **Alternatives considered**: A `triage_workflow_triggers_enabled` kill switch — rejected: the
  failure path already produces the pre-feature brief, so the switch's only use would be
  disabling a working feature.
