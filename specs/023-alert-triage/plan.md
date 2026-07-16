# Implementation Plan: Alert Triage & Synthesis Agent

**Branch**: `023-alert-triage` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/023-alert-triage/spec.md`

## Summary

After the daily French-stock alerting scan runs its deterministic pattern detectors and stores raw `Alert` objects, a new **triage agent** reasons over the day's collected alerts and produces a ranked **daily brief**: every alerting asset is assigned a conviction tier (high / watch / noise), the high/watch assets are ranked and given a one-line rationale, driven by pattern **confluence** (multiple patterns on one asset) and **`ma50_slope` trend alignment** (already attached to each alert's `data`). The brief is persisted to a new **no-TTL DynamoDB table `alert_digests`** for indefinite history, exposed via a new **API** (list newest-first, get by run date), and surfaced in a new **React "Daily Brief" page**. Slack is demoted from a per-indicator firehose to a short digest notification linking into the app.

Technical approach: the Anthropic SDK is wrapped in a **new dedicated `client/anthropic_client.py`** (Client Layer) constructed from `Configuration`, owning retries/errors/logging and raising a new `AnthropicException`; a new `services/alert_triage_service.py` (Service Layer) depends on the client — never the SDK — builds the payload, parses the response, and falls back to a deterministic ranking on any failure so the scan never breaks. Model is config-driven (`claude-sonnet-5` default). Detection logic and the order/workflow path are untouched.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: `anthropic` SDK (NEW, backend), FastAPI + Pydantic v2, Click, `aioboto3` (DynamoDB), `slack_sdk`, `cachetools` (TTLCache); React Router DOM v7+, Vite 7+, Axios (frontend)
**Storage**: AWS DynamoDB — new `alert_digests` table (hash_key `run_date` String, range_key `created_at` Number, **no TTL**); existing `alerts` table unchanged
**Testing**: pytest + `unittest.mock` (backend); frontend has no test framework configured (per constitution)
**Target Platform**: AWS Lambda (scan/triage via `lambda_function.py` `alerting` command) + FastAPI API server; browser (React SPA)
**Project Type**: Web (backend + API + frontend) with a Lambda-invoked CLI/service path
**Performance Goals**: One Claude call per daily scan over a compact per-asset summary payload (no candle arrays); comfortably within the Lambda timeout. No per-asset model calls.
**Constraints**: Triage/persistence failure MUST NOT break the scan, lose raw alerts, or affect the order/workflow path (FR-013). Model swappable via config with zero code change (FR-017).
**Scale/Scope**: ~20–40 alerting assets per daily run; one brief per run; history retained indefinitely.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How this plan complies |
|-----------|--------|------------------------|
| **I. Layered Architecture Discipline** | ✅ PASS | SDK lives ONLY in `client/anthropic_client.py`; `TriageAgent` service receives the client via constructor DI and never touches the SDK. New DynamoDB access goes through `DynamoDBClient` **methods** (`store_alert_digest`, `get_alert_digests`, `get_alert_digest`) — no `client.dynamodb.Table()` from services. API router is thin, delegates to `AlertDigestService`. Frontend calls go through `services/api.ts` only. Public methods have NO `_` prefix; internal helpers keep `_`. |
| **II. Clean Code First** | ✅ PASS | No speculative abstraction — one client method (`complete_json`), one service. New `Conviction` enum instead of hardcoded tier strings. No explanatory inline comments. |
| **III. Configuration-Driven Design** | ✅ PASS | `anthropic_api_key` in `secrets.yml` (gitignored); `anthropic_model` in `config.yml` defaulting to `claude-sonnet-5`; timeouts/retries in config. No hardcoded model id or endpoint. |
| **IV. Safe Deployment Practices** | ✅ PASS | New table added via Pulumi (`pulumi/dynamodb.py` + `__main__.py`); no manual console changes. Conventional commits. |
| **V. Domain Model Integrity** | ✅ PASS | New `AlertDigest`/`TriagedAsset` models carry an explicit `exchange` field per asset (never inferred from `country_code`). Candle ordering untouched (feature reads pre-computed `ma50_slope`, does not recompute). Models live in `model/` with no external deps. |

**Planning Requirement**: This plan is presented for human validation before implementation (constitution Development Standards). No code written until approved.

**Result**: PASS — no violations, Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/023-alert-triage/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── alert-digests.openapi.yaml
├── checklists/
│   └── requirements.md  # from /speckit.specify
└── tasks.md             # /speckit.tasks output (NOT created here)
```

### Source Code (repository root)

```text
model/
├── __init__.py                  # ADD: AlertDigest, TriagedAsset dataclasses (+ exports)
└── enum.py                      # ADD: Conviction (HIGH/WATCH/NOISE) enum

client/
└── anthropic_client.py          # NEW: AnthropicClient (wraps SDK, complete_json, retries/errors)

services/
└── alert_triage_service.py      # NEW: TriageAgent (payload build, parse, deterministic fallback)

client/aws_client.py             # ADD methods: store_alert_digest, get_alert_digests, get_alert_digest

saxo_order/commands/alerting.py  # EDIT: after scan, build+store digest, post concise Slack digest

utils/
├── configuration.py             # ADD: anthropic_api_key, anthropic_model properties
└── exception.py                 # ADD: AnthropicException

pulumi/
├── dynamodb.py                  # ADD: alert_digests_table()
└── __main__.py                  # EDIT: instantiate + grant + export new table

api/
├── main.py                      # EDIT: include_router(alert_digest.router)
├── routers/alert_digest.py      # NEW: GET /api/alert-digests , GET /api/alert-digests/{run_date}
├── services/alert_digest_service.py  # NEW: read/format digests (TTLCache like AlertingService)
└── models/alert_digest.py       # NEW: Pydantic response models

frontend/src/
├── pages/DailyBrief.tsx + .css  # NEW: ranked brief view + run-date history selector
├── services/api.ts              # EDIT: alertDigestService (list, getByRunDate)
├── components/Sidebar.tsx       # EDIT: nav entry "Daily Brief"
└── App.tsx                      # EDIT: <Route path="/daily-brief" ...>

pyproject.toml                   # EDIT: add anthropic dependency

tests/
├── client/test_anthropic_client.py         # NEW (parse + error mapping; mock transport)
├── services/test_alert_triage_service.py   # NEW (payload build, tiering, fallback path)
├── client/test_aws_client_alert_digests.py # NEW (store/get round-trip, float→Decimal)
└── api/test_alert_digest_service.py         # NEW (list newest-first, get by run_date)
```

**Structure Decision**: Web + Lambda layout matching the existing `workflow_orders` precedent end-to-end (new DynamoDB table → `DynamoDBClient` methods → API router/service/model → React page + sidebar route). The only new architectural element is the `AnthropicClient` in the Client Layer; everything else follows established patterns.

## Complexity Tracking

No constitution violations — section intentionally empty.

## Phase Handoff

- Phase 0 → `research.md`: resolves model/SDK, JSON-output strategy, table key design, fallback algorithm, config plumbing.
- Phase 1 → `data-model.md`, `contracts/alert-digests.openapi.yaml`, `quickstart.md`, agent context update.
- Phase 2 (`/speckit.tasks`) → `tasks.md` (NOT produced by this command).
