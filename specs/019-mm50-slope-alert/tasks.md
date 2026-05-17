---

description: "Task list for feature 019-mm50-slope-alert"
---

# Tasks: MM50 Proximity Alert with Slope Filter

**Input**: Design documents from `/Users/kiva/conductor/workspaces/saxo-order/denpasar/specs/019-mm50-slope-alert/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/mm50-touch-alert.md, quickstart.md

**Tests**: Test tasks are included because (a) `tests/services/test_indicator_service.py` and `tests/saxo_order/commands/test_alerting.py` are the established convention for every detector + pipeline change in this codebase, (b) the Constitution requires test coverage to be maintained, and (c) the spec's success criteria (SC-001, SC-002) explicitly reference hand-curated test sets that map naturally to unit tests.

**Organization**: Tasks are grouped by the two user stories from spec.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 = detect, US2 = deliver via existing channels)
- All file paths are absolute

## Path Conventions

This is an existing single-repo Python backend + React frontend. The feature touches **backend only**. Paths used below:

- `/Users/kiva/conductor/workspaces/saxo-order/denpasar/model/enum.py`
- `/Users/kiva/conductor/workspaces/saxo-order/denpasar/services/indicator_service.py`
- `/Users/kiva/conductor/workspaces/saxo-order/denpasar/saxo_order/commands/alerting.py`
- `/Users/kiva/conductor/workspaces/saxo-order/denpasar/tests/services/test_indicator_service.py`
- `/Users/kiva/conductor/workspaces/saxo-order/denpasar/tests/saxo_order/commands/test_alerting.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the local environment is healthy before changing code.

- [ ] T001 Confirm baseline test suite is green by running `poetry run pytest tests/services/test_indicator_service.py tests/saxo_order/commands/test_alerting.py` from `/Users/kiva/conductor/workspaces/saxo-order/denpasar` — establishes a clean baseline for the new tests to be added later.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Introduce the new `AlertType` enum member that both user stories depend on.

**⚠️ CRITICAL**: Both US1 (detection) and US2 (delivery) reference `AlertType.MM50_TOUCH`. This task MUST complete before either story can start.

- [ ] T002 Add `MM50_TOUCH = "mm50_touch"` as a new member of the `AlertType` enum in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/model/enum.py` (append after `CONTAINING_CANDLE`, preserving snake_case lowercase value convention).

**Checkpoint**: Foundation ready — both user stories can now begin.

---

## Phase 3: User Story 1 - Detect assets approaching MM50 in an uptrend (Priority: P1) 🎯 MVP

**Goal**: When the daily alerting workflow runs against an asset, emit an `Alert` of type `MM50_TOUCH` whenever the latest close is within 1% of the MM50 AND the MM50 slope (base-100, 10-candle window) is ≥ 3. Silently skip assets with fewer than 60 candles.

**Independent Test**: Construct a candle series whose last close is 0.5% from `mobile_average(candles, 50)` and whose `slope_percentage(0, mobile_average(candles[10:], 50), 10, mobile_average(candles, 50))` is ≥ 3, feed it through `mm50_touch(candles)` and through `run_detection_for_asset`, and verify both return / emit the new alert with the expected `data` payload.

### Tests for User Story 1

> Add the tests in the same commit as the implementation (project convention). Verify they fail against an unstubbed detector first, then pass once T004 and T006 land.

- [ ] T003 [P] [US1] Add unit tests for `mm50_touch` in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/tests/services/test_indicator_service.py` covering: (a) match when distance == 0.5% and slope == 5.0; (b) match at exact 1% boundary; (c) match at exact slope 3.0 boundary; (d) no match when distance == 1.5%; (e) no match when slope == 2.9; (f) returns `None` (no exception) when `len(candles) < 60`; (g) match with negative `distance_pct` when close is below MM50. Use pytest fixtures and `unittest.mock` only where strictly needed — these are pure-function tests.

### Implementation for User Story 1

- [ ] T004 [US1] Implement the detector function `mm50_touch(candles: List[Candle]) -> Optional[Dict[str, float]]` in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/services/indicator_service.py`. Also define two module-level constants `MM50_TOUCH_PROXIMITY = 0.01` and `MM50_TOUCH_SLOPE_MIN = 3.0` in the same file. The function must: return `None` if `len(candles) < 60`; compute `ma50_last = mobile_average(candles, 50)` and `ma50_first = mobile_average(candles[10:], 50)`; compute `slope = slope_percentage(0, ma50_first, 10, ma50_last)`; compute `close = candles[0].close`; return `None` when `abs(close - ma50_last) / ma50_last > MM50_TOUCH_PROXIMITY` or `slope < MM50_TOUCH_SLOPE_MIN`; otherwise return `{"close": close, "ma50": ma50_last, "distance_pct": (close - ma50_last) / ma50_last * 100, "slope": slope}`. No I/O, no mutation of inputs.
- [ ] T005 [P] [US1] Add unit tests for the pipeline wiring in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/tests/saxo_order/commands/test_alerting.py` covering: (a) `run_detection_for_asset` appends an `Alert` of type `AlertType.MM50_TOUCH` when the detector returns a match, with `data` containing `close`, `ma50`, `distance_pct`, `slope`, **and** `ma50_slope` (same numeric value as `slope`); (b) no `MM50_TOUCH` alert is appended when the detector returns `None`; (c) when fewer than 60 candles are available, no `MM50_TOUCH` alert is appended and the existing detection blocks for other alert types are still attempted. Mock `SaxoClient` and `DynamoDBClient` with `unittest.mock` per the existing test patterns in this file.
- [ ] T006 [US1] Wire the new detector into `run_detection_for_asset` in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/saxo_order/commands/alerting.py`. After the COMBO detection block (around line 357) and before the `if len(asset_alerts) > 0: await dynamodb_client.store_alerts(...)` call, add the block specified in `contracts/mm50-touch-alert.md` §2: call `indicator_service.mm50_touch(candles)`, if non-`None` append an `Alert(alert_type=AlertType.MM50_TOUCH, date=datetime.datetime.now(), data={**result, "ma50_slope": ma50_slope}, asset_code=..., asset_description=..., exchange=exchange, country_code=country_code)`. Depends on T002 (enum member) and T004 (detector).

**Checkpoint**: User Story 1 fully functional. Running `poetry run pytest tests/services/test_indicator_service.py tests/saxo_order/commands/test_alerting.py` is green. Detection is now happening end-to-end, alerts are persisted to DynamoDB (existing `store_alerts` path), and the `POST /api/alerts/run` endpoint returns `mm50_touch` alerts in its response with no API code change required.

---

## Phase 4: User Story 2 - View the new alert alongside existing alerts (Priority: P2)

**Goal**: The new alert appears in the Slack `#stock` grouped message produced by the daily cron, in the on-demand API JSON response (already covered structurally by US1 — verified here), and in the alerts UI (already covered by the existing generic `AlertCard` and dynamic `available_filters` — verified here).

**Independent Test**: Trigger the cron (or simulate it in a test) so it emits at least one `MM50_TOUCH` alert, and confirm: (a) the Slack `#stock` channel receives a message containing a `Indicator mm50_touch` block; (b) the alerts UI page renders a card with the badge `Mm50 Touch`; (c) `GET /api/alerts` exposes `"mm50_touch"` in `available_filters.alert_types`.

### Tests for User Story 2

- [ ] T007 [P] [US2] Add a unit test for the Slack rendering in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/tests/saxo_order/commands/test_alerting.py` covering: given a list of assets that produced one `MM50_TOUCH` alert, `run_alerting` calls `slack_client.chat_postMessage` with a message whose text starts with `Indicator mm50_touch` and contains the asset name, close, ma50, distance_pct, and slope values. Mock `WebClient`, `SaxoClient`, and `DynamoDBClient`.

### Implementation for User Story 2

- [ ] T008 [US2] In `run_alerting` in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/saxo_order/commands/alerting.py`, add the key `"mm50_touch": []` to the `slack_messages` dict initialization (around line 487, alongside `"double_top"`, `"container_candle"`, etc.).
- [ ] T009 [US2] In the same function, add a new `elif alert.alert_type == AlertType.MM50_TOUCH:` branch in the per-alert dispatch chain (after the `COMBO` branch around line 567) that builds a one-line message per the contract: `f"{asset['name']}: {date} close={close} ma50={ma50} dist={dist:.2f}% slope={slope:.2f}%"` and appends it to `slack_messages["mm50_touch"]`. Use `alert.data.get(...)` for `close`, `ma50`, `distance_pct` (passed to local `dist`), and `slope`. Depends on T008.
- [ ] T010 [US2] Manual verification of the API + frontend pass-through (no code change): follow the steps in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/specs/019-mm50-slope-alert/quickstart.md` §4 and §5 to confirm `POST /api/alerts/run` returns the new alert in its JSON, `GET /api/alerts`'s `available_filters.alert_types` includes `"mm50_touch"`, and the `AlertCard` component renders a `Mm50 Touch` badge with the MA50 Slope reading correctly. If any of these surfaces fails, file a follow-up bug — do **not** patch around it here, since the design relies on these being generic.

**Checkpoint**: All deliverables of the spec are present. The trader will see the new alert in Slack on the next scheduled run, on the alerts UI page, and in the on-demand API response.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and deployment.

- [ ] T011 [P] Run `poetry run black .` and `poetry run isort .` from `/Users/kiva/conductor/workspaces/saxo-order/denpasar` to format the modified files (`model/enum.py`, `services/indicator_service.py`, `saxo_order/commands/alerting.py`, and the two test files).
- [ ] T012 [P] Run `poetry run mypy .` and `poetry run flake8` from the same directory and resolve any new violations introduced by the change.
- [ ] T013 Run the full backend test suite `poetry run pytest --cov` from `/Users/kiva/conductor/workspaces/saxo-order/denpasar` and confirm no regressions in any pre-existing test, and that the new tests added in T003, T005, and T007 are all green.
- [ ] T014 Execute the end-to-end validation in `/Users/kiva/conductor/workspaces/saxo-order/denpasar/specs/019-mm50-slope-alert/quickstart.md` against a real asset (e.g. `SAN:xpar` or another mid-cap with recent MM50 proximity) and confirm: detector unit tests pass, pipeline tests pass, on-demand `POST /api/alerts/run` surfaces the new alert when conditions hold, Slack receives an `Indicator mm50_touch` block when applicable, and the alerts UI renders the badge correctly.
- [ ] T015 Stage the implementation commit using conventional commit format: `feat: add mm50_touch alert for assets near MM50 with slope ≥ 3` covering the enum change, detector, pipeline wiring, Slack rendering, and new tests in one logical change. Do **not** commit until the user explicitly asks for it.
- [ ] T016 Deploy via `./deploy.sh` from `/Users/kiva/conductor/workspaces/saxo-order/denpasar` once the commit is merged to `main`. Monitor the next 6:15 PM Paris scheduled run for an `Indicator mm50_touch` block in `#stock`. Do **not** deploy without explicit user authorization.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1. **Blocks** all user-story work.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2 **and** Phase 3 (Slack rendering branches over alerts emitted by US1; testing Phase 4 in isolation requires US1 to actually produce alerts).
- **Phase 5 (Polish)**: Depends on Phase 3 and Phase 4.

### User Story Dependencies

- **US1 (P1)**: Independent of US2. Can be fully implemented and tested without any Slack/API/UI work — its independent test runs through `run_detection_for_asset`, not through delivery.
- **US2 (P2)**: Depends on US1 in practice — the Slack branch can be unit-tested in isolation (T007), but the end-to-end "trader sees the alert" outcome only materializes once US1 emits alerts.

### Within Each User Story

- Models (enum) before services (detector) before orchestration (pipeline wiring) before delivery (Slack rendering).
- Tests can be authored in parallel with implementation in this codebase's convention (same commit). The tests in T003 and T005 are marked [P] because they live in different files than the implementation tasks.

### Parallel Opportunities

- T003 (detector tests, `test_indicator_service.py`) and T005 (pipeline tests, `test_alerting.py`) target different test files and can be written in parallel.
- T011 and T012 (black/isort/mypy/flake8) target the whole repo from different commands — both can run in parallel after implementation lands.

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1 can be authored in parallel:
Task: "Add unit tests for mm50_touch in tests/services/test_indicator_service.py"
Task: "Add unit tests for pipeline wiring in tests/saxo_order/commands/test_alerting.py"

# Implementation order within US1 is strict (T004 → T006), so no implementation parallelism inside US1.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 Setup → green baseline.
2. T002 Foundational → enum member added.
3. T003–T006 US1 → detection works end-to-end; alerts are stored in DynamoDB and returned by `POST /api/alerts/run`.
4. **STOP and VALIDATE**: a trader hitting the on-demand `/api/alerts/run` endpoint or opening the alerts UI page after the next cron run will already see the new alert. This is a viable MVP — the only missing piece is the Slack channel notification.

### Incremental Delivery

1. Phase 1 + Phase 2 → foundation ready.
2. Phase 3 (US1) → deploy: alerts are detected, stored, and surfaced via API + UI. **Demo possible.**
3. Phase 4 (US2) → deploy: alerts are also pushed to Slack on the daily cron. **Demo possible.**
4. Phase 5 → polish + deploy production.

### Parallel Team Strategy

This feature is small enough for a single developer; parallelization is not the bottleneck. If two developers split the work, Dev A handles T003–T006 (detector + pipeline) while Dev B drafts T007–T009 (Slack rendering + Slack test) against a stub of `AlertType.MM50_TOUCH` (already merged in T002).

---

## Notes

- The frontend, `AlertItemResponse`, `available_filters`, and DynamoDB schema are intentionally untouched. The design (see `research.md` §6, `data-model.md` §3–5) ensures the new alert type flows through these surfaces generically. If T010 reveals a regression in any of them, the fix belongs in those modules — not in the alerting pipeline.
- The `data` payload must include both `slope` (alert-defining) and `ma50_slope` (same value, under the existing field name) so the existing frontend MM50 Slope badge keeps working without code changes — see `data-model.md` §2.
- Commit after each phase or logical group; the spec encourages a single `feat:` commit for the whole feature, but reviewers may prefer splitting Phase 3 and Phase 4 into separate commits.
- Do not run `./deploy.sh` without explicit user authorization (T016).
