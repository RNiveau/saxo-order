---
description: "Task list for Alert Triage & Synthesis Agent (spec 023)"
---

# Tasks: Alert Triage & Synthesis Agent

**Input**: Design documents from `/specs/023-alert-triage/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — the plan enumerates test files and the constitution mandates coverage (test real behavior, mock only external transport; never assert-a-mock-was-called).

**Organization**: Grouped by user story (US1–US4) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1–US4 from spec.md
- Exact file paths included

## Path Conventions

Web + Lambda layout (per plan.md): backend at repo root (`model/`, `client/`, `services/`, `saxo_order/`, `api/`, `pulumi/`, `utils/`), frontend at `frontend/src/`, tests mirror source under `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency, exception type, and configuration plumbing shared by all stories

- [x] T001 [P] Add `anthropic` dependency to `pyproject.toml` and refresh `poetry.lock` (`poetry lock`)
- [x] T002 [P] Add `AnthropicException` (mirroring `SaxoException`) to `utils/exception.py`
- [x] T003 [P] Add `anthropic_api_key` (from `secrets`) and `anthropic_model` (from `config`, default `claude-sonnet-5`) properties to `utils/configuration.py`, and document the new keys in the `secrets.yml` / `config.yml` example files

**Checkpoint**: Config + exception + dependency available

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain models used by every story (US1 produces them, US3 persists/reads them, US4 summarizes them)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Add `Conviction` enum (`HIGH`/`WATCH`/`NOISE`) to `model/enum.py` using `EnumWithGetValue`
- [x] T005 Add `TriagedAsset` and `AlertDigest` dataclasses to `model/__init__.py` (with explicit `exchange` field per asset; export both) (depends on T004)

**Checkpoint**: Domain models ready — user stories can begin

---

## Phase 3: User Story 1 - Ranked daily brief instead of a firehose (Priority: P1) 🎯 MVP

**Goal**: The triage agent reasons over the day's alerts and produces a conviction-tiered, ranked brief with per-asset rationale.

**Independent Test**: Call `TriageAgent.synthesize(alerts)` on a known mix of alerts; assert multi-pattern + trend-aligned assets outrank single-pattern ones, each high/watch entry has a rank and rationale, and noise is collapsed to a count — no storage, API, or Slack required.

### Implementation for User Story 1

- [x] T006 [P] [US1] Implement `AnthropicClient` in `client/anthropic_client.py`: constructed from `Configuration`, wraps the SDK, public `complete_json(system, user_payload) -> dict` with retries/backoff/logging, raises `AnthropicException` on transport or parse failure (SDK imported ONLY here) (depends on T002, T003)
- [x] T007 [US1] Implement `TriageAgent` in `services/alert_triage_service.py`: `build_payload` (per-asset patterns + `ma50_slope` + combo/mm50 facts), call `AnthropicClient.complete_json`, parse into `TriagedAsset`s with tier/rank/rationale, reconcile against detected alerts (drop unknown assets, never drop scanned assets), assemble `AlertDigest` (`model` = configured id) (depends on T005, T006)
- [x] T008 [US1] Unit test `TriageAgent` reasoning path in `tests/services/test_alert_triage_service.py`: confluence + slope ranking (SC-007), rank+rationale present on high/watch, noise counted, asset reconciliation (mock `AnthropicClient.complete_json`)
- [x] T009 [US1] In `saxo_order/commands/alerting.py` `run_alerting`, collect per-asset `Alert` objects into a run-level list and call `TriageAgent.synthesize` after the scan loop to produce the digest (depends on T007)

**Checkpoint**: A ranked, tiered brief is produced from a scan and unit-tested in isolation

---

## Phase 4: User Story 2 - Never lose a scan to a reasoning failure (Priority: P1)

**Goal**: On any reasoning failure the agent falls back to a deterministic ranking, flags the brief, and the scan/raw-alerts/order path are never affected.

**Independent Test**: Force `complete_json` to fail (raise / return invalid); confirm `synthesize` returns a valid `AlertDigest` with `fallback_used=True` ranked by pattern count then `|ma50_slope|`, and that a failure inside the triage block leaves raw alerts stored and the scan complete.

### Implementation for User Story 2

- [ ] T010 [US2] Add deterministic fallback to `TriageAgent` in `services/alert_triage_service.py`: rank by distinct-pattern count then `abs(ma50_slope)`, tier mapping (≥2 patterns → high; 1 pattern w/ meaningful |slope| → watch; else noise), templated rationale, `fallback_used=True`, `model="deterministic-fallback"` (thresholds from config) (depends on T007)
- [ ] T011 [US2] Wrap `synthesize` to catch `AnthropicException` and invalid/parse failures → deterministic fallback in `services/alert_triage_service.py`
- [ ] T012 [US2] Wrap the triage+notify block in `run_alerting` (`saxo_order/commands/alerting.py`) so any exception is logged and swallowed after raw alerts are already stored — order/workflow path untouched (depends on T009)
- [ ] T013 [US2] Tests in `tests/services/test_alert_triage_service.py`: transport failure and invalid-output both yield a valid `fallback_used=True` digest; simulated triage exception leaves raw-alert storage intact and scan completing

**Checkpoint**: Guaranteed brief delivery with graceful degradation (SC-003, SC-004)

---

## Phase 5: User Story 3 - Review the history of past briefs (Priority: P2)

**Goal**: Persist each brief without expiry and surface it on the homepage with a carousel to page recent run dates; expose via API.

**Independent Test**: Produce briefs on multiple run dates; `GET /api/alert-digests` returns them newest-first (full), `GET /api/alert-digests/{run_date}` returns one; the homepage renders the latest and the carousel pages backward.

### Implementation for User Story 3

- [ ] T014 [P] [US3] Add `alert_digests_table()` (hash `run_date` S, range `created_at` N, PAY_PER_REQUEST, streams on, **no TTL**) to `pulumi/dynamodb.py`
- [ ] T015 [US3] Register the table in `pulumi/__main__.py` (instantiate + Lambda/API IAM grant + `pulumi.export`) (depends on T014)
- [ ] T016 [US3] Add public `store_alert_digest`, `get_alert_digests(limit)`, `get_alert_digest(run_date)` to `client/aws_client.py` (float→Decimal on write; scan newest-first by `created_at`; query by `run_date`) (depends on T005)
- [ ] T017 [P] [US3] Test store/get round-trip incl. float→Decimal and newest-first ordering in `tests/client/test_aws_client_alert_digests.py`
- [ ] T018 [US3] Persist the digest: call `store_alert_digest` after `synthesize` in `run_alerting` (`saxo_order/commands/alerting.py`) (depends on T009, T016)
- [ ] T019 [P] [US3] Pydantic v2 models `TriagedAssetResponse`, `AlertDigestResponse`, `AlertDigestListResponse` (list carries **full** digests) in `api/models/alert_digest.py` (field names mirror domain models exactly)
- [ ] T020 [US3] Implement `AlertDigestService` in `api/services/alert_digest_service.py`: list full digests newest-first, get by run_date, short `TTLCache` like `AlertingService` (uses `DynamoDBClient` methods only — no client internals) (depends on T016, T019)
- [ ] T021 [US3] Test `AlertDigestService` newest-first list + get-by-run_date in `tests/api/test_alert_digest_service.py`
- [ ] T022 [US3] Implement router `api/routers/alert_digest.py` (`GET /api/alert-digests`, `GET /api/alert-digests/{run_date}`, 404 on missing) and `include_router` in `api/main.py` (depends on T020)
- [ ] T023 [P] [US3] Add `alertDigestService` (`listRecent`, `getByRunDate`) + TS interfaces mirroring the Pydantic models in `frontend/src/services/api.ts`
- [ ] T024 [US3] Build `DailyBrief.tsx` + `DailyBriefCarousel.tsx` (+ CSS) in `frontend/src/components/`: conviction badges (🔴 high / 🟡 watch), noise as a count, fallback indicator, reverse-chronological carousel paging (depends on T023)
- [ ] T025 [US3] Render the `DailyBrief` section above the existing grid in `frontend/src/components/Home.tsx` (depends on T024)

**Checkpoint**: Briefs persist indefinitely (SC-006) and are browsable on the homepage

---

## Phase 6: User Story 4 - Concise notification linking to the app (Priority: P2)

**Goal**: Replace the raw per-indicator Slack firehose with a short digest message that links to the homepage.

**Independent Test**: After a scan the primary channel receives one concise message (tier counts + top high-conviction names + homepage link) and not the per-indicator dump; a no-alerts run says "no signals".

### Implementation for User Story 4

- [ ] T026 [US4] In `run_alerting` (`saxo_order/commands/alerting.py`), replace the per-indicator `slack_messages` posting with a single concise digest message (counts + top high-conviction names + homepage link from config); preserve the "no signals" message (depends on T009)
- [ ] T027 [US4] Test the concise-message formatting (counts, top names, link, and no-signals branch) in `tests/services/test_alert_triage_service.py` or a dedicated formatter test — assert real output, not mock calls

**Checkpoint**: Firehose removed; app is source of truth (SC-001)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T028 [P] Run `poetry run black . && poetry run isort . && poetry run mypy . && poetry run flake8` and fix any issues in new/edited backend files
- [ ] T029 [P] In `frontend/`, ensure `npm run lint` and `npm run build` pass (TypeScript compiles, no hardcoded API URL — use `import.meta.env.VITE_API_URL`)
- [ ] T030 Run `quickstart.md` validation end-to-end (single-asset scan → digest stored; forced-failure → flagged fallback with raw alerts intact; API list/get; homepage carousel)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: after Setup — BLOCKS all stories
- **US1 (Phase 3)**: after Foundational — MVP
- **US2 (Phase 4)**: after US1 (extends `TriageAgent.synthesize` and the `run_alerting` triage block)
- **US3 (Phase 5)**: after Foundational for models/storage; its `run_alerting` persist step (T018) depends on US1's T009
- **US4 (Phase 6)**: its notification step (T026) depends on US1's T009
- **Polish (Phase 7)**: after all desired stories

### Story independence notes

- **US1** is fully testable alone via `synthesize` unit tests (no storage/API/Slack).
- **US2** layers resilience onto US1's agent + scan wiring.
- **US3** (persistence + API + carousel) shares only the foundational models with US1; its backend (T014–T017, T019–T022) is independent of US1 and can be built in parallel — only the `run_alerting` persist wiring (T018) waits on T009.
- **US4** touches only the Slack branch of `run_alerting`; independent of US3.

### Parallel Opportunities

- Setup: T001, T002, T003 all [P].
- US1: T006 (`AnthropicClient`) [P]; T007 (`TriageAgent`) waits on T006.
- US3 backend fan-out: T014, T017, T019, T023 [P]; table→register (T014→T015), client→service→router (T016→T020→T022), frontend service→components→home (T023→T024→T025).
- Polish: T028, T029 [P].

---

## Parallel Example: User Story 3 backend

```bash
# After Foundational, these can start together:
Task: "Add alert_digests_table() to pulumi/dynamodb.py"           # T014
Task: "Pydantic models in api/models/alert_digest.py"             # T019
Task: "alertDigestService + TS interfaces in frontend/src/services/api.ts"  # T023
Task: "Round-trip test in tests/client/test_aws_client_alert_digests.py"    # T017
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 Setup → Phase 2 Foundational.
2. Phase 3 US1 → **STOP & VALIDATE** `synthesize` produces a correct ranked brief.
3. Phase 4 US2 → guarantee the scan never breaks. This pairing (P1+P1) is the true MVP: a trustworthy brief that always ships.

### Incremental Delivery

1. Setup + Foundational → ready.
2. US1 + US2 → the agent produces a resilient brief (validate, demo).
3. US3 → persist + homepage carousel (validate, demo).
4. US4 → demote Slack to a concise pointer (validate, demo).

---

## Notes

- [P] = different files, no dependency on incomplete tasks.
- Detection logic (`run_detection_for_asset`, indicators) and the order/workflow engine are NEVER modified (FR-006, FR-008).
- Raw-alert `store_alerts` calls remain exactly as today (FR-007).
- Tests assert real behavior; mock only external transport (Anthropic SDK, DynamoDB) — never assert a mock was called.
- Commit after each task or logical group; conventional commit messages.
