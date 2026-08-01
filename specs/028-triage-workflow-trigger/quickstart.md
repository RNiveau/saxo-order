# Quickstart: Workflow-Trigger Corroboration

**Feature**: 028-triage-workflow-trigger | **Date**: 2026-08-01

How to exercise the feature without waiting for an 18:15 Lambda run.

## Prerequisites

```bash
poetry install
```

AWS credentials with read access to `workflows` and `workflow_orders`, and read/write on
`alert_digests`.

## 1. Unit tests — the fastest loop

```bash
poetry run pytest tests/services/test_workflow_trigger_service.py -v
poetry run pytest tests/services/test_alert_triage_service.py -v
```

The triage tests run without AWS: `TriageAgent.synthesize` is synchronous and takes the trigger map
as a plain argument, so a corroborated asset is a dict literal, not a mocked table.

## 2. Confirm the join actually matches

The failure mode that produces a silently inert feature is a `workflow.index` that never equals any
scanned asset code. Check the real data before trusting an empty result:

```bash
poetry run python -c "
import asyncio
from client.aws_client import create_dynamodb_client

async def main():
    async with create_dynamodb_client() as db:
        wfs = await db.get_all_workflows()
        for w in wfs:
            print(f\"{w.get('enable')}  dry_run={w.get('dry_run')}  index={w.get('index')!r}  cfd={w.get('cfd')!r}  {w.get('name')}\")
asyncio.run(main())
"
```

Compare the `index` column against the codes in `stocks.json` / `followup-stocks.json`. An `index`
of `AI` or `AI:xpar` matches the alert asset `AI` + `xpar`; an `index` of `GER40.I` will never
match, and that workflow simply never corroborates anything — expected, not a bug.

## 3. Inspect today's triggers

```bash
poetry run python -c "
import asyncio, datetime
from zoneinfo import ZoneInfo
from client.aws_client import create_dynamodb_client

async def main():
    async with create_dynamodb_client() as db:
        orders = await db.get_all_workflow_orders()
        start = datetime.datetime.now(ZoneInfo('Europe/Paris')).replace(
            hour=0, minute=0, second=0, microsecond=0).timestamp()
        today = [o for o in orders if int(o['placed_at']) >= start]
        print(f'{len(today)} trigger(s) today of {len(orders)} retained')
        for o in today:
            ts = datetime.datetime.fromtimestamp(int(o['placed_at']), ZoneInfo('Europe/Paris'))
            print(f\"  {ts:%H:%M}  {o['workflow_name']}  {o['order_direction']}  {o['order_code']}\")
asyncio.run(main())
"
```

Note `order_direction` prints as `BUY`/`SELL` — the enum **name**. Parsing it with
`Direction("BUY")` raises; use `Direction["BUY"]`.

## 4. End-to-end on a narrow asset list

`run_alerting` accepts an explicit asset list, so you can scan just the assets your workflows watch
instead of the full French universe:

```bash
poetry run python -c "
import asyncio
from saxo_order.commands.alerting import run_alerting
asyncio.run(run_alerting('config.yml', assets=[{'code': 'AI:xpar', 'name': 'Air Liquide'}]))
"
```

This performs real detection, real triage, writes a real digest, and posts to Slack. Point
`SAXO_CONFIG` at a test config first if you do not want the Slack post.

## 5. Check the brief

```bash
poetry run python run_api.py
curl -s localhost:8000/api/alert-digests?limit=1 | python -m json.tool
```

A corroborated asset carries `workflow_triggers`; an uncorroborated one omits the key entirely.

Then `cd frontend && npm run dev`, open `http://localhost:5173`, and confirm the Daily Brief shows
the workflow name, direction, and time of day on the corroborated asset, with a visible dry-run
marker when applicable.

## 6. Verify the degraded path

The most important test: with workflow data unavailable, the brief must be **exactly** today's.

```bash
poetry run pytest tests/services/test_workflow_trigger_service.py -k "failure or unavailable" -v
poetry run pytest tests/services/test_alert_triage_service.py -k "no_triggers" -v
```

## Pre-commit gates

```bash
poetry run black . && poetry run isort . && poetry run mypy . && poetry run flake8
poetry run pytest
cd frontend && npm run lint && npm run build
```

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| No asset ever shows corroboration | Neither `order_code` nor `workflow.index` matches a scanned asset code — run step 2 and read the drop logs, which print every candidate tried |
| `ValueError: 'BUY' is not a valid Direction` | Parsed with `Direction(value)` instead of `Direction[value]` — see data-model §4 |
| Triggers appear on the workflow orders page but not in the brief | The asset isn't in the alert set (excluded, or index-only) — working as specified, FR-002 |
| Brief has triggers but ranking looks unchanged | Expected when the trigger agrees with an already-strong read; corroboration breaks ties, it doesn't multiply (A-004) |
| Old digests error on read | A pre-feature digest has no `workflow_triggers` key — readers must default it to empty (data-model §8) |
