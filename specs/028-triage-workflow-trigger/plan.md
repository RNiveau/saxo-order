# Implementation Plan: Workflow-Trigger Corroboration in the Alert Triage Agent

**Branch**: `028-triage-workflow-trigger` | **Date**: 2026-08-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/028-triage-workflow-trigger/spec.md`

## Summary

The daily brief ranks assets on chart-pattern detectors and MA50 slope — evidence that all comes
from one mechanism, on one set of candles, at one moment. This feature adds the one signal in the
system that is structurally independent: a same-day workflow trigger, meaning a rule the trader
registered in advance fired during the session and produced a directional order.

A new `WorkflowTriggerService` reads the day's `workflow_orders` rows and matches each one to a
scanned asset — by the code on the order itself, falling back to the workflow's watched underlying —
alongside a single read of the workflow definitions for the dry-run label. The resulting map is handed to `TriageAgent.synthesize`, which stays synchronous and
pure. Triggers enrich assets already in the alert set and never add new ones. The reasoning prompt
learns that a trigger is one point of convergence from a separate mechanism, that it carries
directional authority at least equal to `combo`, and that a trigger contradicting the pattern read
is a red flag. The deterministic fallback counts a trigger as one extra pattern family. The
corroboration is stored with the digest and surfaced in the API, the Daily Brief, and Slack.

If anything in the collection or join fails, the collector returns an empty map — which provably
reproduces today's brief through every downstream path.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: existing only — `aioboto3` (DynamoDB), `anthropic` SDK, `slack_sdk`,
FastAPI + Pydantic v2, `zoneinfo` (stdlib, already used for Paris-local math in `utils/helper.py`);
Axios + React Router DOM v7+ on the frontend. **No new dependency.**
**Storage**: existing tables only — reads `workflow_orders` and `workflows`, writes the enriched
asset entries into the existing `alert_digests` items. **No new table, no schema migration, no
Pulumi change.**
**Testing**: pytest with `unittest.mock`; tests mirror source structure under `tests/`
**Target Platform**: AWS Lambda (`alerting` command, 18:15 Paris weekdays) + FastAPI API + Vite SPA
**Project Type**: Web (backend + frontend) with a Lambda entry point
**Performance Goals**: the enrichment adds two DynamoDB scans of small tables per run — a few
seconds at most against the scan's existing budget (SC-007)
**Constraints**: must never delay or break the end-of-day scan; must reproduce the pre-feature brief
exactly when workflow data is unavailable (FR-019); must not write to any workflow table (FR-021)
**Scale/Scope**: ~1 digest/day; a handful of triggering workflows per day against a few hundred
scanned assets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| **I. Layered Architecture** | PASS. New logic sits in the Service layer (`services/workflow_trigger_service.py`); the CLI command only calls it and passes the result on. No new client methods are needed — `get_all_workflow_orders()` and `get_all_workflows()` already exist, so no service touches client internals. `WorkflowTrigger` lives in the Model layer with no external dependencies. Frontend changes stay in `services/api.ts` (types) and a component (render). |
| **II. Clean Code First** | PASS. Reuses the matching semantics of `get_workflows_by_asset` rather than inventing a second rule; no shared helper is extracted for two callers (R3). No new config knob (R11). No `assert` — the direction parse raises an explicit exception on an unknown value. |
| **III. Configuration-Driven** | PASS by vacuity — the feature introduces no threshold, endpoint, or timeout. R11 records why. |
| **IV. Safe Deployment** | PASS. No infrastructure change; existing tables and IAM grants suffice. Conventional commits throughout. |
| **V. Domain Model Integrity** | PASS. `Direction` is the existing enum, parsed by **name** because `WorkflowEngine` writes `order_direction.name` (R5). `TriagedAsset` already carries an explicit `exchange`; triggers attach to it and never infer an exchange from `country_code`. |
| **Planning Requirement** | PASS. Spec and this plan precede implementation; `/speckit.implement` awaits human validation. |
| **Testing Standards** | PASS. Tests mirror structure; behaviour is asserted (ranking, tier, payload, degraded output), not mock invocation. |

**Post-Phase-1 re-check**: no new violations. The design added no client-internals access, no new
table, and no cross-layer call. Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/028-triage-workflow-trigger/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — 11 decisions with alternatives
├── data-model.md        # Phase 1 — entities, serialisation, join rules
├── quickstart.md        # Phase 1 — how to exercise the feature locally
├── contracts/
│   └── alert-digests.openapi.yaml   # Phase 1 — the additive API change
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 — /speckit.tasks output
```

### Source Code (repository root)

```text
model/
└── __init__.py                      # MODIFIED: + WorkflowTrigger; TriagedAsset gains workflow_triggers

services/
├── workflow_trigger_service.py      # NEW: collect + resolve today's triggers
└── alert_triage_service.py          # MODIFIED: prompt section, payload, re-attach, fallback tally

saxo_order/commands/
└── alerting.py                      # MODIFIED: collect triggers, pass into synthesize

client/
└── aws_client.py                    # MODIFIED: store_alert_digest serialises triggers

api/
├── models/alert_digest.py           # MODIFIED: + WorkflowTriggerResponse, optional field
└── services/alert_digest_service.py # MODIFIED: hydrate triggers, Decimal → float

frontend/src/
├── services/api.ts                  # MODIFIED: + WorkflowTrigger interface, optional field
└── components/
    ├── DailyBriefCarousel.tsx       # MODIFIED: render trigger line on corroborated assets
    └── DailyBriefCarousel.css       # MODIFIED: trigger line + dry-run styling

tests/
├── services/test_workflow_trigger_service.py   # NEW
├── services/test_alert_triage_service.py       # MODIFIED
└── client/test_aws_client_alert_digests.py     # MODIFIED
```

**Structure Decision**: Standard backend layering for this repo — new Service, existing Clients,
Model extension — with the frontend change confined to a type and a component. Two deliberate
divergences from the feature description, both recorded in research: a single `get_all_workflows()`
scan instead of per-trigger `get_workflow_by_id` calls (R1), and `order_code` as the primary join
key rather than an opaque CFD name (R3, corrected by the repo owner during implementation). The
workflow read survives the second change because `dry_run` has no other source.

## Phase Handoff

- Phase 0 → `research.md`: resolution strategy, session window, matching rule, service placement,
  model shape, prompt design, schema stability, fallback tally, persistence, failure tolerance,
  configuration.
- Phase 1 → `data-model.md`, `contracts/alert-digests.openapi.yaml`, `quickstart.md`: entity
  definitions with validation and join rules, the additive API contract, and a local exercise path.
- Phase 2 → `tasks.md` via `/speckit.tasks`.

## Risks

| Risk | Mitigation |
|------|------------|
| Identifier formatting drifts from the alert asset code, so triggers silently never match | Largely retired: `order_code` is the asset code and is tried first, so matching no longer hinges on `index` formatting. `index` remains a fallback, FR-003 drops rather than guesses, and every drop is logged with all candidates so a mismatch is diagnosable from one run's logs rather than inferred from an absence |
| Reasoning over-weights a trigger and floods the top tier | A-004 fixes it at one convergence point with no multiplier; the prompt states the cap explicitly, and the fallback uses the same weight so the two paths agree |
| `order_direction` parsed as value instead of name, yielding a wrong or crashed direction | Called out in R5 and data-model.md; covered by a dedicated round-trip test against a row written by `WorkflowEngine`'s own format |
| Enrichment slows the end-of-day scan | Two scans of small tables, once per run, after all detection has completed; a failure or timeout returns `{}` rather than retrying |

## Complexity Tracking

No constitution violations — section intentionally empty.
