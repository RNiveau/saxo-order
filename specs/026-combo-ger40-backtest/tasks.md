# Tasks: "GER40 Combo" Backtest (5m / 15m / H1)

**Input**: Design documents from `/specs/026-combo-ger40-backtest/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/backtest-api.md](./contracts/backtest-api.md)

**Tests**: included. The strategy is arithmetic on candles with no UI to
eyeball, and the constitution's testing standards apply; more importantly
the existing golden suite is the only thing that proves the refactor left
six shipped backtests untouched (SC-C03).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on another
  incomplete task.
- **[Story]**: US1 (P1, run a combo backtest over a range), US2 (P2,
  compare the three timeframes), US3 (P3, inspect a position).

---

## Phase 1: Foundation — shared model and enum changes

**Purpose**: the vocabulary every later phase needs. Nothing here changes
behavior on its own.

- [ ] **T001** [P] Add `ExitReason.END_OF_RUN = "end_of_run"` and
  `Strategy.C5M / C15M / C1H` in `model/enum.py` (data-model §2).
- [ ] **T002** Add `unit_time: Optional[UnitTime] = None` and
  `combo_entry: bool = False` to `BacktestDefinition` in
  `model/backtest.py`, plus the `__post_init__` validation from
  data-model §1 (combo requires `unit_time` and `double_take_profit`;
  combo rejects every session-range flag). Depends on T001.
- [ ] **T003** [P] Extend `tests/api/services/backtest/test_definitions.py`
  with the `__post_init__` rejection cases from T002 — each invalid combo
  flag combination must raise at construction, which is what stops a flag
  shipping as a silent no-op.
- [ ] **T004** Make `Position.h1_high` / `h1_low` `Optional[float] = None`
  and have `structural_level` raise `SaxoException` when they are absent
  (**never `assert`** — constitution §II.5), in
  `api/services/backtest/position.py`. Add `Position.retarget(first_target,
  take_profit)` (data-model §3).
- [ ] **T005** [P] Add `ComboTwoLot(TwoLotAccounting)` to
  `api/services/backtest/lots.py` with a `targets` that raises
  (data-model §4), and cover it in
  `tests/api/services/backtest/test_lots.py`.

**Checkpoint**: `poetry run pytest tests/api/services/backtest/ -q` still
green, golden snapshot **not** regenerated.

---

## Phase 2: The strategy seam (blocking refactor)

**⚠️ This is the phase that can break shipped backtests.** Do it as a pure
code move and prove it.

- [ ] **T006** Add `api/services/backtest/strategy.py`: a `Strategy`
  protocol with `run_range(definition, start, end, params)` and
  `evaluate_day(definition, date, params)`, plus a `for_definition()`
  selector keying off `definition.combo_entry`.
- [ ] **T007** Move today's engine from
  `api/services/backtest/service.py` into
  `api/services/backtest/session_range.py` as `SessionRangeStrategy`
  **verbatim** — `_evaluate_from_candles`, `_evaluate_trades`,
  `_open_position`, `_take_profit_level`, `_reset`, `_fetch_daily_candles`.
  No logic edits in this task; behavior changes belong to no task at all.
- [ ] **T008** Reduce `BacktestService` to construction + dispatch:
  `list_definitions` / `get_definition` unchanged, `run_range` /
  `evaluate_day` delegating to `strategy.for_definition(definition)`. The
  public method signatures the router calls must not change. Depends on
  T006, T007.
- [ ] **T009** Run `poetry run pytest tests/api/services/backtest/ -q`.
  **`test_backtest_golden.py` must pass without regeneration.** If it
  fails, the move was not a move — fix the seam, never the snapshot.

**Checkpoint**: six shipped backtests provably unchanged; the combo
strategy has somewhere to live.

---

## Phase 3: User Story 1 — run a combo backtest over a range (P1) 🎯 MVP

**Goal**: a correct multi-week run of one combo definition, end to end.

**Independent Test**: run `C15M` over a known GER40.I range and verify
each position's entry, exits and net points against a manual evaluation
of `combo` and the bands on the same candles.

### Candle acquisition

- [ ] **T010** [US1] Add `store_backtest_series` /
  `get_cached_backtest_series` to `client/aws_client.py::DynamoDBClient`
  (data-model §7): same table, new key namespace
  `"{instrument}:{session}:{ut}:v1"`, item `{has_data, candles}`. Client
  layer only — no business logic (constitution §I).
- [ ] **T011** [US1] Add a session-start helper beside
  `paris_session_end_utc` in `api/services/backtest/calendar.py` (the
  reference-window helper returns a 1-hour window; the combo source needs
  the whole session).
- [ ] **T012** [US1] Add `api/services/backtest/combo_candle_source.py`:
  `series(definition, start, end)` returning one chronological candle list
  across the range, fetched per trading day via
  `CandlesService.get_candles_in_window(instrument, ut, horizon, start,
  end)`, cache-first via T010, with the failure policy inherited from
  `CandleSource` — cache a genuine empty day, **never** cache a
  `SaxoException`, degrade to Saxo on any cache error. Depends on
  T010, T011.
- [ ] **T013** [US1] Add the warm-up lead-in to T012 (FR-C13): extend
  backwards over prior trading days until ≥250 candles precede the
  range's first candle, or 15 calendar days are exhausted. 250 matches
  `alerting.py::_build_candles`, which is what keeps the MACD comparable
  to live (research R3/R5).
- [ ] **T014** [P] [US1] `tests/api/services/backtest/test_combo_candle_source.py`:
  cache hit / miss / malformed item, an empty day cached as
  `has_data=False`, a `SaxoException` **not** cached, warm-up length per
  timeframe, and chronological contiguity across a weekend.

### Signal → entry

- [ ] **T015** [US1] Add `api/services/backtest/bands.py`: `BandLevels`
  (data-model §5) and `levels(window)` computing
  `bollinger_bands(window, 2.0)` once per candle — `.middle` is TP1,
  `.up` / `.bottom` is TP2 by side.
- [ ] **T016** [P] [US1] `tests/api/services/backtest/test_bands.py`:
  `opposite()` resolves per side; levels move as the window advances;
  fewer than 20 candles is handled without raising into the engine.
- [ ] **T017** [US1] Add `api/services/backtest/signals.py`:
  `PendingEntry` (data-model §6) and `ComboEntrySearch.feed(candle,
  window)` implementing research R6 in order — fill or drop yesterday's
  pending level **first**, then evaluate this candle's `combo`; WEAK
  ignored (FR-C02); triggered → entry at the close; untriggered → arm a
  one-candle pending level (FR-C03/FR-C04). Fills use
  `side.worse(level, candle.open)`, the existing conservative gap-fill.
- [ ] **T018** [P] [US1] `tests/api/services/backtest/test_signals.py`,
  with `combo` mocked so the state machine is tested and not the
  indicator: WEAK skipped; triggered entry at the close; untriggered
  filled on the next candle; untriggered **not** filled → dropped, no
  entry; a gap through the level fills at the open; the pending signal's
  **own** candle is retained for the stop (FR-C06); short mirrors long.

### The engine

- [ ] **T019** [US1] Add `api/services/backtest/combo_strategy.py`
  implementing the loop in plan.md §Phase 1: retarget-then-resolve while
  in a position, feed the entry search while flat, ignore every signal
  while in a position (FR-C09), never close at end of day (FR-C11), close
  any open position after the last candle as `END_OF_RUN` (FR-C12).
  Depends on T004, T005, T012, T015, T017.
- [ ] **T020** [US1] Open-position construction in T019: two lots,
  `initial_stop_price` = the **signal** candle's adverse extreme ∓
  `params.stop_loss_points` (FR-C06), `lots=ComboTwoLot()`, `h1_high` /
  `h1_low` left `None`. Reject the entry when the current MM20 is not
  strictly favorable (FR-C10).
- [ ] **T021** [US1] Exit chain for a combo definition in
  `api/services/backtest/rules.py::build_exit_chain`: exactly
  `[Stop(), DoubleTarget()]` — no `ArmBreakEven` (FR-C08), no
  structural/impulsive stop, no time cut, no trail. Route
  `build_lot_model` to `ComboTwoLot` for `combo_entry` definitions.
- [ ] **T022** [US1] `run_range` in `ComboStrategy`: walk the series once,
  attribute each trade to its **entry** day, build `DayResultSummary`
  rows with `h1_*` as `None` and `mm50_slope` / `adx14` /
  `overnight_gap` still populated from the daily series (research R8),
  and reuse `statistics.build_summary` unchanged.
- [ ] **T023** [US1] Evaluate `combo` **only while flat** (research R5) —
  behavior-preserving under FR-C09 and the single biggest cost saving on
  the 5m timeframe.
- [ ] **T024** [P] [US1] `tests/api/services/backtest/test_combo_strategy.py`,
  one test per acceptance scenario of spec US1: triggered entry;
  pending-level entry; pending level expiring; WEAK skipped; TP1 at the
  MM20 arming break-even; TP2 at the band; runner back to break-even;
  both lots stopped out (the ×2 loss); short mirror; a position carried
  across a day boundary; a signal ignored while in a position; a position
  open at range end reported `END_OF_RUN`.
- [ ] **T025** [P] [US1] Edge-case tests in the same file: entry rejected
  because the MM20 is already past (FR-C10); stop and TP1 on one candle →
  stop wins (FR-C14); TP1 and TP2 on one candle; the MM20 crossing below
  the entry so TP1 banks a loss; a gap through the stop over a weekend.

### Registration

- [ ] **T026** [US1] Register `C5M`, `C15M`, `C1H` in
  `api/services/backtest/definitions.py` per data-model §1 —
  `GER40.I`, `EuCfdMarket`, `combo_entry=True`,
  `double_take_profit=True`, `stop_loss_points=50`.
- [ ] **T027** [US1] Make `resolve_parameters` ignore the three
  non-tunable thresholds for combo definitions (FR-C16), and extend
  `tests/api/services/backtest/test_parameters.py`.
- [ ] **T028** [US1] Regenerate the golden snapshot **once, deliberately**,
  to add the three new definitions. Review the diff line by line: the six
  existing definitions' blocks must be **byte-identical**.

**Checkpoint**: US1 delivered. `GET /api/backtest/run?definition=C15M`
returns real positions over a real range.

---

## Phase 4: User Story 2 — compare the three timeframes (P2)

**Goal**: the three definitions selectable and independently correct,
with only the meaningful parameter exposed.

**Independent Test**: run one range on all three and get three distinct
result sets, none affected by running the others.

- [ ] **T029** [US2] Add `tunable_parameters: List[str] = []` to
  `BacktestDefinitionResponse` and populate it in
  `backtest_definition_to_response` (`api/models/backtest.py`,
  contract §1): all four names for existing definitions,
  `["stop_loss_points"]` for combo ones.
- [ ] **T030** [P] [US2] Mirror it on `BacktestDefinition` in
  `frontend/src/services/api.ts` — exact field name and type
  (constitution §I).
- [ ] **T031** [P] [US2] Filter `PARAM_FIELDS` by
  `selectedDef.tunable_parameters` in
  `frontend/src/pages/Backtest.tsx:18-30`, falling back to all four when
  the array is empty so nothing regresses for existing definitions.
- [ ] **T032** [P] [US2] Tests for T029 in
  `tests/api/` covering the definitions endpoint: existing definitions
  report four tunables, combo ones report one, and existing payloads are
  otherwise unchanged.
- [ ] **T033** [US2] Verify the three timeframes independently: 15m is
  served natively at horizon 15 with no reconstruction (research R3), and
  each definition's run reads only its own series.

**Checkpoint**: US2 delivered — the side-by-side comparison works.

---

## Phase 5: User Story 3 — inspect a position (P3)

**Goal**: a day's detail is readable and honest for a strategy with no H1
range.

**Independent Test**: open a day containing a position and reconcile its
entry and exits against the displayed candles.

- [ ] **T034** [US3] `evaluate_day` for a combo definition = a one-day
  range run bounded at that day, force-closing an open position as
  `END_OF_RUN` (research R9). Return that day's candles and the trades
  that entered that day.
- [ ] **T035** [P] [US3] Hide the `H1 range: {detail.h1_low} -
  {detail.h1_high}` line in
  `frontend/src/components/BacktestDayDetail.tsx:49,56` when the levels
  are absent — today it would render `null - null`.
- [ ] **T036** [P] [US3] Verify both CSV exports on a combo run: empty H1
  cells, `end_of_run` as an exit reason, one row per day, a two-lot
  position counted as one trade (FR-C15).

**Checkpoint**: US3 delivered.

---

## Phase 6: Polish and gates

- [ ] **T037** Measure a 6-month `C5M` run (quickstart §Performance). If
  warm-cache runtime exceeds ~30s, cache the rolling band computation —
  **never** change the strategy rules to go faster.
- [ ] **T038** [P] Full quality gates: `poetry run black . && isort . &&
  mypy . && flake8`, `poetry run pytest --cov`, and in `frontend/`:
  `npm run lint && npm run build`.
- [ ] **T039** Manual smoke test per quickstart: run all three timeframes
  from the UI, open a day detail, export both CSVs, and confirm the
  existing CAC40/GER40 backtests still behave identically.
- [ ] **T040** Hand-verify the SC-C02 set — at least 8 historical signals
  across the three timeframes covering every outcome type — against
  manual calculation. This is the acceptance evidence for the whole
  feature, not a formality.

---

## Dependencies

```text
Phase 1 (T001-T005)  ─┐
Phase 2 (T006-T009)  ─┴─> Phase 3 (T010-T028) ─> Phase 4 (T029-T033)
                                              └─> Phase 5 (T034-T036)
                                                       └─> Phase 6
```

- **T002 → T001**; **T008 → T006, T007**; **T009 gates all of Phase 3**.
- **T019 → T004, T005, T012, T015, T017**; **T020-T023 → T019**.
- **T026 → T002, T021**; **T028 → T026**.
- Phases 4 and 5 are independent of each other and can run in parallel.

## Parallel opportunities

- Phase 1: T003 and T005 alongside T004.
- Phase 3: the three test tasks T014, T016, T018 are independent of each
  other and of the engine tasks, since each mocks its collaborators.
  T024/T025 share a file and must be sequential with respect to each
  other.
- Phase 4: T030, T031, T032 touch three different files.

## MVP scope

**Phases 1-3 (T001-T028) are the MVP.** They deliver a working, correct
combo backtest reachable through the existing API and the existing menu.
Phase 4 makes the comparison ergonomic; Phase 5 makes the day view
honest. Neither is required for the strategy to be measurable.
