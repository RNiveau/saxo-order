# Quickstart: Alert Triage & Synthesis Agent

## Prerequisites

- `poetry install` (adds the new `anthropic` dependency)
- `secrets.yml` contains `anthropic_api_key: <key>`
- `config.yml` may contain `anthropic_model: claude-sonnet-5` (this is the default if omitted)
- AWS credentials configured (DynamoDB `alert_digests` table deployed via Pulumi)

## Deploy the new table

```bash
cd pulumi && pulumi up      # creates the alert_digests table + IAM grants
```

## Run the daily scan locally (produces + stores a brief)

```bash
# Single asset (fast smoke test)
poetry run k-order alerting --code SAN --country-code xpar

# Full French-stock scan (as the Lambda 'alerting' command does)
poetry run python -c "import asyncio; from saxo_order.commands.alerting import run_alerting; asyncio.run(run_alerting('config.yml'))"
```

Expected: scan runs detection as before, then a single **Daily Brief** is written to `alert_digests` and a concise digest is posted to Slack `#stock` with a link to `/daily-brief`.

## Verify the fallback path

Temporarily set an invalid `anthropic_api_key` (or disconnect network) and re-run: the scan still completes, a brief is still stored with `fallback_used: true` and `model: "deterministic-fallback"`, raw alerts are still saved, and no order/workflow behavior changes.

## Read via API

```bash
poetry run python run_api.py          # http://localhost:8000

curl http://localhost:8000/api/alert-digests            # list newest-first
curl http://localhost:8000/api/alert-digests/2026-07-16 # single brief by run date
```

## Frontend

```bash
cd frontend && npm run dev            # http://localhost:5173/daily-brief
```

The Daily Brief page shows the latest brief with conviction badges (🔴 high / 🟡 watch) and a run-date selector to page back through history.

## Test

```bash
poetry run pytest tests/services/test_alert_triage_service.py \
                  tests/client/test_anthropic_client.py \
                  tests/client/test_aws_client_alert_digests.py \
                  tests/api/test_alert_digest_service.py
poetry run black . && poetry run isort . && poetry run mypy . && poetry run flake8
```

## Acceptance smoke checklist

- [ ] Multi-pattern asset ranks above single-pattern asset (US1 / SC-007)
- [ ] Reasoning failure → fallback brief, scan intact, raw alerts stored (US2 / SC-003, SC-004)
- [ ] `GET /api/alert-digests` newest-first; `GET /{run_date}` returns full brief (US3)
- [ ] Slack gets one concise digest + link, not the raw firehose (US4 / SC-001)
- [ ] No-alerts run still records a brief and Slack says "no signals" (FR-019)
