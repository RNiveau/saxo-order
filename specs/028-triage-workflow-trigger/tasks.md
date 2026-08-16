---

description: "Task list for 028-triage-workflow-trigger"
---

# Tasks: Workflow-Trigger Corroboration in the Alert Triage Agent

**Input**: Design documents from `/specs/028-triage-workflow-trigger/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Included. Not an optional extra here — the constitution's Pre-Merge Gates require passing
tests and maintained coverage, and FR-019 ("the brief is identical when workflow data is
unavailable") is a claim that can only be made good by a test.

**Organization**: Grouped by user story so each ships independently. US1 alone is a complete,
useful feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete work)
- **[Story]**: US1 / US2 / US3, mapping to the spec's user stories
- Exact file paths in every description

## Path Conventions

Repository root. Backend: `model/`, `services/`, `client/`, `api/`, `saxo_order/commands/`.
Frontend: `frontend/src/`. Tests mirror source under `tests/`.

---

## Phase 1: Setup

**Purpose**: Establish a known-good baseline so any later failure is attributable to this feature.

- [x] T001 Run the full backend gate on a clean tree and record the result: `poetry run pytest`, `poetry run mypy .`, `poetry run flake8`
- [ ] T002 [P] ⚠️ BLOCKED — no AWS credentials in the dev container (`UnrecognizedClientException`). Capture a pre-feature digest sample from `GET /api/alert-digests?limit=1` into `/tmp/digest-before.json` — the byte-comparison baseline for FR-019 and SC-004. Must be run from an environment with AWS access before T038.
- [ ] T003 [P] ⚠️ BLOCKED — same missing credentials. Run quickstart step 2 (`get_all_workflows()` dump) and record which `index` values match scanned asset codes — confirms A-001 against live data. Not blocking Phase 2 (the trader confirmed the overlap), but it is the cheapest way to catch an `index`-format mismatch before US1 ships.

> **Phase 1 result**: T001 baseline recorded — 873 passed, 10 skipped; flake8 clean; mypy reports 4
> pre-existing `aioboto3` missing-stub errors (unchanged by this feature). T002 and T003 need AWS
> credentials this container does not have.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The domain model and the collector. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Add the `WorkflowTrigger` dataclass to `model/__init__.py` with fields `workflow_name`, `direction: Direction`, `order_price: float`, `trigger_close: Optional[float]`, `placed_at: int`, `dry_run: bool` per data-model.md §1
- [x] T005 Add `workflow_triggers: List[WorkflowTrigger] = field(default_factory=list)` to `TriagedAsset` in `model/__init__.py` (data-model.md §2)
- [x] T006 Create `services/workflow_trigger_service.py` with async `collect_todays_triggers(dynamodb_client, run_date, alerts) -> Dict[str, List[WorkflowTrigger]]`, returning `{}` on any exception (research R4, R10)
- [x] T007 Implement the Paris session window in `services/workflow_trigger_service.py` using `zoneinfo.ZoneInfo("Europe/Paris")`, deriving bounds from `run_date` rather than an assumed schedule (data-model.md §5, FR-004)
- [x] T008 Implement workflow resolution in `services/workflow_trigger_service.py`: one `get_all_workflows()` read into a `{workflow_id: (name, index, dry_run)}` map; drop triggers whose `workflow_id` is absent (research R1, FR-003)
- [x] T009 Implement asset matching in `services/workflow_trigger_service.py` — case-insensitive `order_code` then `index` against `asset_code` and `f"{asset_code}:{country_code}"`, matching on Alert **fields** not `Alert.id`; log all candidates on every non-match (data-model.md §4, FR-003)
- [x] T010 Parse `order_direction` with the enum's own `Direction.get_value(...)` in `services/workflow_trigger_service.py` — it accepts the stored `"BUY"` name form as well as `"Buy"`, and raises `ValueError` on anything else; no hand-rolled parsing, no `assert` (research R5, Constitution II.3/II.5)
- [x] T011 [P] Create `tests/services/test_workflow_trigger_service.py` covering: in-window vs out-of-window rows, deleted-workflow drop, unmatched-index drop, `BUY`-name parse, dry-run flag read from the workflow record, and `{}` on a raising client

**Checkpoint**: Triggers can be collected and resolved. Nothing consumes them yet.

---

## Phase 3: User Story 1 — Workflow-corroborated assets rise in the brief (Priority: P1) 🎯 MVP

**Goal**: An asset that fired patterns *and* triggered a workflow in the same direction ranks at the
top, with a rationale that names the workflow.

**Independent Test**: Run a triage over an alert set where exactly one asset also has a same-day
trigger aligned with its patterns; confirm it outranks otherwise comparable assets and that its
rationale names the workflow.

- [x] T012 [US1] Add the optional `triggers: Optional[Dict[str, List[WorkflowTrigger]]] = None` parameter to `TriageAgent.synthesize` in `services/alert_triage_service.py`, keeping the method synchronous and storage-free (research R4)
- [x] T013 [US1] Extend `TriageAgent._build_payload` in `services/alert_triage_service.py` to emit `workflow_triggers` per asset **only when non-empty**, with `workflow`, `direction`, `dry_run`, and Paris-local `hour` (data-model.md §7)
- [x] T014 [US1] Add the workflow-trigger section to `TRIAGE_SYSTEM_PROMPT` in `services/alert_triage_service.py`: independent mechanism = one convergence point (contrast with the `congestion20`/`congestion100` collapse), directional authority at least equal to `combo`, contradiction is a red flag (parallel to `mm50_touch`), multiple same-day triggers still count once, dry-run weighs one step lower (FR-007 – FR-012)
- [x] T015 [US1] Re-attach triggers from the input map in `TriageAgent._parse_triaged` / `_build_triaged_asset` in `services/alert_triage_service.py` — never read them back from the model response; leave `TRIAGE_RESPONSE_SCHEMA` unchanged (research R7)
- [x] T016 [US1] Wire `collect_todays_triggers` into `run_alerting` in `saxo_order/commands/alerting.py`, inside the existing triage try/except, passing the map into `synthesize` (FR-001, FR-019)
- [x] T017 [P] [US1] Add tests to `tests/services/test_alert_triage_service.py`: payload omits `workflow_triggers` for assets without one, includes it with the right shape for assets with one, and the returned `TriagedAsset` carries the trigger even though the model response never mentions it
- [x] T018 [P] [US1] Add a test to `tests/services/test_alert_triage_service.py` asserting that `synthesize(alerts)` with no `triggers` argument produces output identical to the pre-feature behaviour (SC-004, FR-019)
- [ ] T019 [US1] ⚠️ BLOCKED — needs AWS credentials (same as T002/T003). Verify end-to-end via quickstart step 4 against a narrow asset list; confirm rank and rationale name the workflow (SC-001, SC-002) and that no asset appears solely because a workflow triggered (SC-003). SC-003 is covered by a unit test in the meantime (`test_triggers_never_introduce_an_asset_into_the_digest`); SC-001/SC-002 depend on live reasoning and cannot be asserted offline

**Checkpoint**: US1 is shippable. Ranking is corroboration-aware; nothing is displayed yet.

---

## Phase 4: User Story 2 — The trigger is visible wherever the brief is read (Priority: P2)

**Goal**: The trader can see which workflow, which direction, at what time, live or dry-run — in the
app and in Slack — without leaving the brief.

**Independent Test**: Generate a brief with one corroborated asset; confirm the trigger details are
persisted, served by the API, rendered in the Daily Brief, and reflected in the Slack message.

- [x] T020 [US2] Serialise `workflow_triggers` inside each triaged-asset item in `store_alert_digest` in `client/aws_client.py`, omitting the key when empty and storing `direction` as the enum name (data-model.md §8, FR-015)
- [x] T021 [US2] Add `WorkflowTriggerResponse` to `api/models/alert_digest.py` and an optional `workflow_triggers` field on `TriagedAssetResponse`, per `contracts/alert-digests.openapi.yaml`
- [x] T022 [US2] Hydrate `workflow_triggers` in `api/services/alert_digest_service.py`, converting `Decimal` back to `float` and defaulting a **missing** key to empty for pre-feature digests (data-model.md §8, A-005)
- [x] T023 [P] [US2] Add the `WorkflowTrigger` interface and the optional field on `TriagedAsset` in `frontend/src/services/api.ts`, mirroring the Pydantic models field-for-field (Constitution — API Contract Standards)
- [x] T024 [US2] Render the trigger line on corroborated assets in `frontend/src/components/DailyBriefCarousel.tsx` — workflow name, direction, Paris-local time of day, distinct dry-run marker; render nothing at all when the list is empty (FR-017, edge case "no empty section")
- [x] T025 [P] [US2] Style the trigger line and the dry-run marker in `frontend/src/components/DailyBriefCarousel.css`, consistent with the existing conviction badges
- [x] T026 [US2] Mark corroborated assets in `format_slack_digest` in `services/alert_triage_service.py` without expanding into a per-trigger listing (FR-018)
- [x] T027 [P] [US2] Add tests to `tests/client/test_aws_client_alert_digests.py` for the store/read round trip: triggers present, key absent when empty, and a pre-feature item without the key reading back cleanly
- [x] T028 [P] [US2] Add a `format_slack_digest` test to `tests/services/test_alert_triage_service.py` covering a corroborated asset and confirming an uncorroborated digest is unchanged
- [ ] T029 [US2] ⚠️ BLOCKED — needs AWS credentials to produce a real digest to render. Verify in the browser via quickstart step 5 (SC-006), including a dry-run trigger and a no-trigger day. `npm run build` and `npm run lint` pass, so the component compiles and types match the backend, but it has not been rendered against live data

**Checkpoint**: US1 + US2 shippable. Corroboration is ranked, stored, served, and visible.

---

## Phase 5: User Story 3 — Corroboration survives degraded reasoning (Priority: P3)

**Goal**: When reasoning is unavailable, a corroborated asset still outranks an equivalent
uncorroborated one.

**Independent Test**: Force the reasoning step to fail over an alert set with one corroborated
asset; confirm the fallback lifts it and still flags the brief as a fallback.

- [x] T030 [US3] Count an attached trigger as one extra confluence point in `TriageAgent._fallback_conviction` in `services/alert_triage_service.py` — one point regardless of trigger count (FR-013, A-004)
- [x] T031 [US3] Thread triggers through `_fallback_digest` ordering in `services/alert_triage_service.py` so the primary sort key reflects the extra point (FR-013)
- [x] T032 [US3] Append the workflow name and direction to the templated string in `TriageAgent._fallback_rationale` in `services/alert_triage_service.py` (FR-014)
- [x] T033 [P] [US3] Add tests to `tests/services/test_alert_triage_service.py`: one pattern + one trigger lifts the tier, two triggers on one asset add only one point, and the fallback flag is still set

**Checkpoint**: All three stories complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T034 Add tests to `tests/services/test_workflow_trigger_service.py` for the remaining spec edge cases: several triggers on one asset, triggers disagreeing on direction, and a trigger on an asset outside the alert set
- [x] T035 [P] Confirm no `assert` in any new production code and that every new public method omits the leading underscore (Constitution II.5, I)
- [x] T036 [P] Run `poetry run black . && poetry run isort . && poetry run mypy . && poetry run flake8`
- [x] T037 [P] Run `npm run lint && npm run build` in `frontend/`
- [ ] T038 ⚠️ BLOCKED — depends on the T002 baseline, which needs AWS. Diff a no-trigger-day digest against `/tmp/digest-before.json` and confirm equivalence (SC-004, FR-019). Covered offline in the meantime by `test_synthesize_without_triggers_matches_pre_feature_behaviour` and `test_fallback_rationale_unchanged_when_nothing_is_corroborated`, which pin the digest fields and the exact fallback string
- [x] T039 Time the triage step with and without the enrichment (SC-007). **In-process cost is unmeasurable**: 400 assets / 20 corroborated ran at 1.4 ms/synthesize either way. The remaining cost is the two DynamoDB scans in `collect_todays_triggers`, which cannot be timed without AWS — small tables, once per run, after detection completes
- [x] T040 Confirm no Pulumi or IAM change is required — existing `workflows` / `workflow_orders` read grants already cover the alerting Lambda (plan.md Technical Context)


> **Phase 6 result**: T034–T037 and T040 done. T039 measured as far as possible offline. T038 is
> blocked on the T002 baseline. Suite: **934 passed, 10 skipped**; flake8 clean; mypy 4 pre-existing
> missing-stub notes (`aioboto3`, `binance.error`), unchanged by this feature; frontend `npm run
> build` succeeds, `npm run lint` 0 errors / 3 pre-existing warnings in untouched files.
>
> **Four verification tasks remain blocked on AWS credentials** — T002, T003, T019, T029, plus T038
> which depends on T002. Nothing in this feature has run against a real recorded workflow order or
> been rendered in a browser.

---

## Dependencies

```
Phase 1 (Setup)
   └─► Phase 2 (Foundational: model + collector)   ← BLOCKS EVERYTHING
          ├─► Phase 3 US1 (P1, MVP)  ─┐
          ├─► Phase 4 US2 (P2)        ├─► Phase 6 (Polish)
          └─► Phase 5 US3 (P3)       ─┘
```

- **US1** depends only on Phase 2.
- **US2** depends on Phase 2 and consumes the field US1 populates — sequence it after US1 in practice, though its persistence and display tasks touch disjoint files.
- **US3** depends only on Phase 2 and touches the fallback path exclusively. It can be built in parallel with US1 or US2.
- T003 (live overlap check) gates nothing technically, but a null result should prompt a conversation before Phase 2 rather than after Phase 6.

## Parallel Opportunities

**Phase 1**: T002, T003 together.
**Phase 2**: T004 → T005 sequentially (same file); T006 – T010 sequentially (same file); T011 alongside once T010 lands.
**Phase 3 (US1)**: T012 – T016 sequentially (T012 – T015 share `alert_triage_service.py`); T017 and T018 in parallel afterwards.
**Phase 4 (US2)**: T020, T021, T023, T025 touch four different files and can run in parallel; T022 follows T021; T024 follows T023; T027 and T028 in parallel at the end.
**Phase 5 (US3)**: T030 – T032 sequentially (same file); T033 after.
**Phase 6**: T035, T036, T037 in parallel.

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1).** Twenty tasks deliver the actual value: the brief ranks
corroborated assets first and says why. Everything after that is presentation and resilience.

**Recommended increments**:

1. **Foundational + US1** — ship, then watch a few real runs. This is where A-001 gets tested for
   real: if no asset is ever corroborated, stop and revisit the premise rather than building US2 on
   top of a feature that never fires.
2. **US2** — once corroboration is demonstrably appearing, make it visible.
3. **US3** — the fallback path is rare; it can follow at leisure.

**Verification order that matters**: T018 and T038 are the two tasks that prove the feature is safe.
Neither tests the feature working — they test that it changes nothing when it has nothing to say,
which is its behaviour on most days.
