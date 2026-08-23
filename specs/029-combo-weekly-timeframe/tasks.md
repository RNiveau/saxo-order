---
description: "Task list for weekly-timeframe combo detection"
---

# Tasks: Weekly-Timeframe Combo Detection

**Input**: Design documents from `/specs/029-combo-weekly-timeframe/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included. The constitution's Testing Standards make passing tests a pre-merge gate, and
three success criteria (SC-002, SC-007, SC-008) are only verifiable by test. Tests assert behaviour,
never that a mock was called.

**Organization**: Grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete work)
- **[Story]**: US1..US4, mapping to the spec's user stories
- Paths are repository-relative and exact

## Path Conventions

Backend packages live at the repository root (`model/`, `services/`, `client/`, `saxo_order/`,
`utils/`, `api/`); the SPA lives in `frontend/src/`; tests mirror source under `tests/`.

---

## Phase 1: Setup (Calibration Prerequisite)

**Purpose**: produce the threshold values US1 needs. FR-011 makes calibration a release gate, and
the daily constants demonstrably do not transfer (research.md R8).

- [x] T001 Create `scripts/calibrate_weekly_combo.py`: read a sample of assets from `stocks.json`, fetch `horizon=10080` per asset through `SaxoClient.get_historical_data`, cache raw responses to a local JSON file so re-runs cost nothing, and report the distributions of `ma50_slope`, `bbh_slope` and `bbb_slope` over the weekly bars plus the share of sampled assets returning at least 60 bars
- [x] T002 Run `poetry run python scripts/calibrate_weekly_combo.py` over the whole universe (the default — one cached pass, no sampling noise in a figure that gates release) and record the chosen weekly threshold values and the eligibility ratio (SC-004) in `specs/029-combo-weekly-timeframe/calibration.md`

**Checkpoint**: weekly thresholds are known values with a recorded derivation, and SC-004 is answered

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the alert identity every story keys on.

**⚠️ CRITICAL**: no user story work begins until this phase is complete

- [x] T003 Add `COMBO_WEEKLY = "combo_weekly"` to `AlertType` in `model/enum.py`

**Checkpoint**: the new alert type exists — stories can start

> **Note (implementation)**: T003 could not land alone. `test_prompt_documents_every_alert_type_it_can_receive`
> asserts every `AlertType` member appears in the triage prompt, so adding the enum member forced
> T017–T019 forward from Phase 4, and T016 with them to cover the behaviour change. T015 remains
> outstanding in Phase 4. T002 is blocked: it needs live provider credentials (`secrets.yml`), which
> the development container does not hold. T004 (a `weekly_combo_enabled` toggle) was removed from
> the plan as speculative — see research.md R10.

---

## Phase 3: User Story 1 - Detect a combo on the weekly timeframe (Priority: P1) 🎯 MVP

**Goal**: the daily scan evaluates each asset's weekly bars and records a weekly combo, without
disturbing any existing detector.

**Independent Test**: run the scan against an asset whose weekly bars form a combo; a
`combo_weekly` alert is stored with direction, strength, price, a four-key `details` map and
`weekly_bar_date`. Re-run it four more times: still one stored record.

### Tests for User Story 1

- [x] T005 [P] [US1] Test `combo()` on weekly candles with the reduced criteria set in `tests/services/test_indicator_service.py`: a bullish and a bearish weekly fixture produce the expected direction, a four-key `details` map, and `STRONG` at 3 of 4 criteria
- [x] T006 [P] [US1] Test the `ComboSettings` invariants in `tests/services/test_indicator_service.py`: `strong_signal_min` never exceeds the number of active criteria, and `min_candles` is at least 235 whenever `use_macd` is true
- [x] T007 [P] [US1] Test weekly series assembly in `tests/saxo_order/commands/test_alerting.py`: the forming week is built from the daily candles already fetched and prepended; on a weekend or before Monday's open the series ends at the last completed week; an asset with fewer than 60 bars yields no weekly alert while its other detectors still store theirs
- [x] T008 [P] [US1] Test the de-duplication signature in `tests/client/test_aws_client.py`: same bar and direction across five scans stores one record (SC-002); a direction flip on the same bar stores a second; every other alert type produces the signature it produces today (SC-007); a weekly alert whose `data` lacks `weekly_bar_date` falls back to the default signature instead of raising

### Implementation for User Story 1

- [x] T009 [US1] Add a frozen `ComboSettings` dataclass and a `COMBO_SETTINGS: Dict[UnitTime, ComboSettings]` map to `services/indicator_service.py`, with the daily entry carrying today's constants and the weekly entry carrying the T002 values, `min_candles=60`, `strong_signal_min=3` and `use_macd=False`
- [x] T010 [US1] Thread the settings through `combo()`, `_ComboContext` and `_combo_for_direction` in `services/indicator_service.py`, defaulting to the daily entry so existing call sites are unchanged, and skip the `macd` criterion when `use_macd` is false (depends on T009)
- [x] T011 [P] [US1] Add the alert de-duplication signature function to `model/__init__.py`: default `(alert_type, date.date().isoformat())`, and `(alert_type, data["weekly_bar_date"], data["direction"])` for `COMBO_WEEKLY`, falling back to the default when either key is missing
- [x] T012 [US1] Route both sides of the duplicate comparison in `DynamoDBClient.store_alerts` (`client/aws_client.py`) through the T011 function, preserving the existing skip-on-malformed-row behaviour (depends on T011)
- [x] T013 [US1] Add `_build_weekly_candles(saxo_client, asset, daily_candles)` to `saxo_order/commands/alerting.py`: one `horizon=10080`, `count=70` fetch mapped with `ut=UnitTime.W`, with the forming week from `build_current_weekly_candle_from_daily(daily_candles)` prepended when the newest returned bar is not the current ISO week
- [x] T014 [US1] Run weekly detection inside `run_detection_for_asset` in `saxo_order/commands/alerting.py`, wrapped in `_safe_detect`, emitting an `AlertType.COMBO_WEEKLY` alert whose `data` carries `price`, `direction`, `strength`, `has_been_triggered`, `details`, `ma50_slope` (the asset's **daily** slope, the same value every other alert carries — see research.md R13), `weekly_bar_date` (normalised with `.date().isoformat()`) and `timeframe` (depends on T003, T010, T013)

**Checkpoint**: weekly combos are detected and recorded; reverting the change reproduces the
pre-feature alert set exactly

---

## Phase 4: User Story 2 - Triage ranks the weekly combo as higher-timeframe evidence (Priority: P1)

**Goal**: the brief treats a Buy weekly combo as the strongest reason to surface an asset, a Sell
weekly combo as disqualifying, and never promotes an asset on the strength of one detector counted
twice.

**Independent Test**: submit triage payloads built from synthetic `combo_weekly` alerts — no
detection needed — and check the conviction band and rationale for each case.

### Tests for User Story 2

- [ ] T015 [P] [US2] Test the reasoned path in `tests/services/test_alert_triage_service.py`: a Buy-weekly-only asset is eligible for the top band and its rationale names the weekly timeframe; a Sell-weekly-only asset never reaches the top band; a Buy weekly ranks at or above an equivalent Buy daily; a Buy weekly with a Sell daily produces a rationale naming the disagreement (SC-006)
- [x] T016 [P] [US2] Test the deterministic fallback in `tests/services/test_alert_triage_service.py`: an asset carrying a daily and a weekly combo and nothing else reaches the same conviction band as an asset carrying the daily combo alone (SC-008, FR-015)

### Implementation for User Story 2

- [x] T017 [P] [US2] Add `AlertType.COMBO_WEEKLY` to `_DIRECTIONAL_PATTERNS` in `services/alert_triage_service.py`
- [x] T018 [P] [US2] Add `AlertType.COMBO_WEEKLY: AlertType.COMBO` to `_PATTERN_FAMILY` in `services/alert_triage_service.py`, with a comment stating that the two are one detector at two timeframes exactly as the congestion pair is one detector at two windows
- [x] T019 [US2] Extend the prompt's pattern-semantics block in `services/alert_triage_service.py` with a `combo_weekly` entry ranked above `combo`, and state the long-only consequence: a Buy weekly combo is the strongest reason to surface an asset, a Sell weekly combo disqualifies it as a long exactly as a Sell combo does (depends on T017)

**Checkpoint**: the brief ranks weekly evidence correctly and the fallback grants it no unearned
promotion

---

## Phase 5: User Story 3 - See the weekly combo where alerts are already consumed (Priority: P2)

**Goal**: the weekly combo is visible and visually distinct wherever alerts are already read.

**Independent Test**: store one `combo_weekly` alert, open the alerts view, and confirm a distinct
label, a direction badge, and a badge colour that is not the daily combo's.

- [ ] T020 [P] [US3] Add `combo_weekly: 'Combo Weekly'` to `ALERT_TYPE_LABELS` in `frontend/src/utils/alertLabels.ts`
- [ ] T021 [P] [US3] Add `combo_weekly` to the directional-alert handling in `frontend/src/components/AlertCard.tsx` so its Buy/Sell direction renders as other directional alerts do
- [ ] T022 [P] [US3] Add a `.alert-card[data-alert-type="combo_weekly"] .alert-type-badge` rule in `frontend/src/pages/AssetDetail.css` with a colour distinct from the daily combo's
- [ ] T023 [US3] Verify the alerts API returns `combo_weekly` and accepts it in the `alert_type` filter, matching `specs/029-combo-weekly-timeframe/contracts/alerts.openapi.yaml`; add a test in `tests/api/routers/` if the filter path is not already covered

**Checkpoint**: the alert is distinguishable at a glance and reachable through the API

---

## Phase 6: User Story 4 - Keep the scan within its operating budget (Priority: P2)

**Goal**: the added timeframe costs one provider request per asset and never breaks the scan.

**Independent Test**: run a full scan, and the same scan with weekly detection reverted, comparing
duration and request count.

- [ ] T024 [US4] Test in `tests/saxo_order/commands/test_alerting.py` that a scan with weekly detection enabled issues exactly one additional `get_historical_data` call per asset — three would mean the forming week is being fetched separately instead of built from the daily candles (research.md R1)
- [ ] T025 [US4] Test in `tests/saxo_order/commands/test_alerting.py` that a provider failure on the weekly fetch for one asset leaves that asset's other detectors storing their alerts and the scan continuing over the remaining assets (FR-006)
- [ ] T026 [US4] Run a full scan of the production universe, and the same scan with weekly detection reverted; record duration, request count and the unused share of the execution window (SC-003) in `specs/029-combo-weekly-timeframe/calibration.md`

**Checkpoint**: the cost of the second timeframe is measured, bounded and recorded

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T027 Walk `specs/029-combo-weekly-timeframe/quickstart.md` end to end and correct any step that does not match the built behaviour
- [ ] T028 [P] Run the backend gates: `poetry run black . && poetry run isort .`, `poetry run mypy .`, `poetry run flake8`, `poetry run pytest`
- [ ] T029 [P] Run the frontend gates: `npm run lint` and `npm run build` in `frontend/`
- [ ] T030 Confirm no `assert` was introduced in production code and that no hardcoded string was used where `AlertType` or `UnitTime` exists (Constitution II, V)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T002 depends on T001.
- **Foundational (Phase 2)**: independent of Phase 1 in code, but US1 needs T002's values to be meaningful. BLOCKS all user stories.
- **US1 (Phase 3)**: depends on Phase 2. Blocks nothing — US2, US3 and US4 are testable without it.
- **US2 (Phase 4)**: depends on Phase 2 only. Testable against synthetic alerts.
- **US3 (Phase 5)**: depends on Phase 2 only.
- **US4 (Phase 6)**: depends on US1 — there is no second request to measure until detection exists.
- **Polish (Phase 7)**: depends on every story being delivered.

### Within User Story 1

T009 → T010 (settings before the code that reads them) · T011 → T012 (signature before its caller) ·
T003, T004, T010, T013 → T014 (detection is the integration point)

### Parallel Opportunities

- T005–T008 are four separate test files' worth of work and can run together
- T011 (model) is independent of T009/T010 (indicator) and T013 (command)
- T017 and T018 touch different maps in one file — sequence them if the same person holds the file
- T020, T021 and T022 are three different frontend files
- US2 and US3 can be delivered in parallel with US1 by different people

## Parallel Example: User Story 1

```bash
# The four test tasks, together:
Task: "Weekly combo scoring in tests/services/test_indicator_service.py"
Task: "ComboSettings invariants in tests/services/test_indicator_service.py"
Task: "Weekly series assembly in tests/saxo_order/commands/test_alerting.py"
Task: "De-duplication signature in tests/client/test_aws_client.py"

# Then the independent implementation strands:
Task: "ComboSettings + COMBO_SETTINGS in services/indicator_service.py"
Task: "De-dup signature in model/__init__.py"
Task: "_build_weekly_candles in saxo_order/commands/alerting.py"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 — calibrate, so the thresholds mean something
2. Phase 2 — the enum member
3. Phase 3 — detection and recording
4. **STOP and VALIDATE**: run the scan on a known asset, then five consecutive days' worth; confirm one stored record, and an unchanged daily alert set when the change is reverted

At that point the signal exists and is safe to leave running, even though nothing consumes it yet.

### Incremental delivery

US2 makes the signal actionable in the brief and is the story with real behavioural risk — the
fallback collapse (T018) is what keeps the long-only guarantee intact, so it should not lag far
behind US1 in production. US3 is presentation. US4 is measurement and can only be done last.

### Release gates (outside the task flow)

- The weekly thresholds from T002 must be committed, not placeholders
- The labelled sample of at least 20 historical setups (spec Dependencies) must exist before SC-001 can be claimed
