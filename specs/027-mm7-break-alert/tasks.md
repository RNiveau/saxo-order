# Tasks: MM7 Break Alert

**Input**: Design documents from `/specs/027-mm7-break-alert/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md)

**Tests**: included. Detector thresholds are arithmetic on candles with no UI
to eyeball, the constitution's testing standards apply, and the spec's SC-001 /
SC-002 (no false negatives on decisive breaks, no false positives on grazes and
chop) map one-to-one onto unit tests.

**Status**: T001-T009 are **done** — implemented, reviewed against the
constitution, committed on `claude/triage-agent-ma7-alerting-mypata`, and
pushed. T010 is the one open task: it needs a live run and cannot be closed
from the repo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on another
  incomplete task.
- **[Story]**: US1 (P1, detect the break), US2 (P1, triage weighs it
  correctly), US3 (P2, visible in the existing channels).

---

## Phase 1: Foundation — shared vocabulary

**Purpose**: the enum member every later phase refers to. Changes no behavior
on its own.

- [x] **T001** Add `MM7_BREAK = "mm7_break"` to the `AlertType` enum in
  `model/enum.py`, after `MM50_TOUCH`, keeping the snake_case lowercase value
  convention. **Done**: single additive member; the value is the string that
  reaches DynamoDB, the API, and the UI label map.

**Checkpoint**: US1 and US3 can begin.

---

## Phase 2: User Story 1 — Detect the break (P1) 🎯 MVP

**Goal**: emit an `MM7_BREAK` alert when the latest close clears its MM7 by more
than 0.5% and the 3 prior candles each closed on the other side.

**Independent Test**: feed `mm7_break` a series whose last close is 4% below a
7-MA that the 3 prior candles closed above, and confirm a `Direction.SELL`
result; feed it a graze and a chop series and confirm `None`.

- [x] **T002** [US1] Add the constants `MM7_PERIOD = 7`,
  `MM7_BREAK_MIN_DISTANCE = 0.005`, `MM7_BREAK_MIN_STREAK = 3`, and the derived
  `MM7_BREAK_MIN_CANDLES = MM7_PERIOD + MM7_BREAK_MIN_STREAK` to
  `services/indicator_service.py`, beside the `MM50_TOUCH_*` constants
  (plan §Key Design Decisions 4; FR-004). **Done**: the minimum candle count is
  derived rather than a literal `10`, so re-tuning the streak cannot silently
  desync the history requirement.
- [x] **T003** [US1] Implement `_mm7_at`, `_mm7_streak`, and
  `mm7_break(candles) -> Optional[Dict[str, Any]]` in
  `services/indicator_service.py` (FR-003, FR-004, FR-005, FR-006, FR-007).
  Pure function, no I/O, no input mutation. Returns `close`, `mm7`,
  `previous_close`, `previous_mm7`, `distance_pct`, `direction`, `streak`.
  **Done**: direction uses `Direction.SELL` / `Direction.BUY` from the existing
  enum rather than a `"up"`/`"down"` string (CLAUDE.md); the MM7 is evaluated at
  each candle's own offset (plan §Key Design Decisions 2); `_mm7_streak` stops
  when history runs short instead of raising.
- [x] **T004** [P] [US1] Add detector unit tests to
  `tests/services/test_indicator_service.py`: bearish break, bullish reclaim,
  `None` on a graze inside the distance threshold, `None` on chop that breaks
  the streak, `None` below the candle minimum (SC-001, SC-002). **Done**: 5
  tests in `TestMm7Break`, using the file's existing `_make_candles` helper.
- [x] **T014** [P] [US1] Pin the threshold boundaries the spec calls out as
  assumptions. **Done**: 4 more tests — exactly 0.5% returns `None` (exclusive)
  with a companion that fires just past it on the same shape, so the distance
  gate is isolated from the streak; a 2-candle prior run returns `None` (the
  chop test only ever produced a 1-candle run, so `MM7_BREAK_MIN_STREAK` was
  never exercised from below); and a strictly one-sided run fires, since both
  happy-path tests satisfied the streak only through the equality branch.
  Raised in review of PR #693.
- [x] **T005** [US1] Wire the detector into `run_detection_for_asset` in
  `saxo_order/commands/alerting.py`, after the `MM50_TOUCH` block and before the
  `store_alerts` call, going through the existing `detect(...)` /`_safe_detect`
  wrapper so a detector that cannot run never costs the other detectors their
  alerts (FR-002, FR-006). Merge `ma50_slope` into the alert `data` (FR-007).
  Depends on T001, T003. **Done**: mirrors the `MM50_TOUCH` block exactly; no
  extra Saxo call — reuses the candles already loaded by `_build_candles`.
- [x] **T006** [P] [US1] Add pipeline tests to
  `tests/saxo_order/commands/test_alerting.py`: the alert is emitted with the
  expected direction, payload fields, and `ma50_slope`, and `store_alerts` is
  awaited; no alert when price hugs a flat average. **Done**: 2 tests in
  `TestRunDetectionForAssetMM7Break`, reusing the file's `patched_alerting`
  fixture.

**Checkpoint**: the detector fires and persists — US1 is independently
shippable at this point.

---

## Phase 3: User Story 2 — Triage weighs the break correctly (P1)

**Goal**: the agent treats MM7 as a short-term timing trigger, not a thesis.

**Independent Test**: an asset whose only pattern is an MM7 break on a flat
trend must not come back "high"; the same break agreeing with a steep slope
alongside another directional pattern must rank above it.

- [x] **T007** [US2] Add the `mm7_break` pattern-semantics entry to
  `TRIAGE_SYSTEM_PROMPT` in `services/alert_triage_service.py`, in the same
  block as the `mm50_touch` and `double_top` entries: directional but
  short-term; weighed against the **sign** of `ma50_slope` (agreeing =
  continuation trigger and real directional evidence, opposing = early warning
  on an intact trend, explicitly not a reversal); never sufficient alone for
  "high" (FR-009, FR-010). **Done**: written to the same line-width convention
  as the surrounding prompt text.
- [x] **T008** [US2] ~~Confirm the deterministic fallback satisfies FR-010
  without code changes.~~ **Superseded by T011 — the original conclusion was
  wrong.** It checked only the lone-MM7 case (1 family → `watch`, FR-010 holds)
  and missed the co-firing case: an asset with one existing family that also
  breaks its MM7 reached `family_count >= 2` and was promoted `watch` → `high`.
  Raised in review of PR #693.
- [x] **T011** [US2] Exclude timing patterns from the fallback confluence count
  in `services/alert_triage_service.py` (FR-013): add `_TIMING_PATTERNS =
  {AlertType.MM7_BREAK}` and `_structural_families()`, and use the structural
  count in `_fallback_conviction`, `_fallback_rationale`, and the ranking sort.
  **Done**: the `watch` gate moved from `family_count == 1` to
  `structural_count >= 1` so an asset that co-fires MM7 keeps the tier it had
  before this feature rather than dropping to `noise` through the `== 1` test.
  3 tests added to `tests/services/test_alert_triage_service.py` (no promotion
  on co-fire, lone MM7 → `noise`, two structural patterns still → `high`).

---

## Phase 4: User Story 3 — Visible in the existing channels (P2)

**Goal**: the alert reads clearly wherever the trader already looks.

- [x] **T009** [P] [US3] Add `mm7_break: 'MM7 Break'` to `ALERT_TYPE_LABELS` in
  `frontend/src/pages/Alerts.tsx` (FR-011). **Done**, but the note that it fixed
  `mm50_touch` "everywhere" was wrong: that map feeds only the filter dropdown.
  See T012. No API, DynamoDB, or Slack change is needed: the alerts endpoints
  are generic over `AlertType.value`, `data` is a free-form dict, and
  `format_slack_digest` renders triaged assets rather than enumerating alert
  types.
- [x] **T012** [US3] Extract the label map into
  `frontend/src/utils/alertLabels.ts` as a single exported `getAlertTypeLabel`,
  and use it in both `Alerts.tsx` and `AlertCard.tsx` (FR-011). **Done**: the
  card had its own `formatAlertType` that title-cased the raw value, so the
  filter said "MM7 Break" while the badge said "Mm7 Break". The helper falls
  back to title-casing for unmapped types, so no alert type can regress to raw
  snake_case. `double_bottom` was missing from the map and was added. Raised in
  review of PR #693.
- [x] **T013** [US3] Surface `direction` and `distance_pct` on the alert card in
  `frontend/src/components/AlertCard.tsx` (SC-005). **Done**: a Direction row
  beside the MA50 slope, coloured green for `Buy` / red for `Sell`, showing the
  signed distance beside it. Previously both fields were only visible by
  expanding the raw JSON dump, so SC-005 was not met by the UI. The row is
  generic over any alert carrying `direction`, so `combo` gains it too. Raised
  in review of PR #693.

---

## Phase 5: Acceptance — live calibration

- [ ] **T010** Check the first live runs against spec **SC-003**: count how many
  scanned assets carry an `mm7_break` per day. If the count is a large fraction
  of the universe rather than a handful, raise `MM7_BREAK_MIN_DISTANCE` and/or
  `MM7_BREAK_MIN_STREAK` (both single-line changes in
  `services/indicator_service.py`) and re-check. **Open** — the thresholds were
  calibrated from the shape of the neighbouring detectors, not from measured hit
  rates, so this is the real acceptance evidence for the feature, not a
  formality. It cannot be closed from the repo.

---

## Dependencies

```text
Phase 1 (T001) ─┬─> Phase 2 (T002-T006) ─> Phase 5 (T010)
                ├─> Phase 3 (T007-T008)
                └─> Phase 4 (T009)
```

- **T003 → T002**; **T005 → T001, T003**; **T006 → T005**.
- Phases 3 and 4 depend only on T001 and are independent of Phase 2 and of each
  other.
- T010 depends on Phase 2 being deployed, not merely merged.

## Parallel opportunities

- T004 and T006 are test files independent of each other.
- T007 (prompt) and T009 (frontend label) touch different files and neither
  blocks the other.

## MVP scope

**Phases 1-2 (T001-T006) are the MVP** — the alert fires, carries its direction,
and persists. Phase 3 is what makes the feature deliver on its stated
motivation (improving the triage agent) rather than merely adding a row to the
alerts table; it is P1 for that reason. Phase 4 is cosmetic. Phase 5 is the only
thing that can confirm the thresholds were set right.
