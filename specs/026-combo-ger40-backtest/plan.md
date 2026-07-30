# Implementation Plan: "GER40 Combo" Backtest (5m / 15m / H1)

**Branch**: `claude/combo-indicator-ger40-backtest-klzp2d` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/026-combo-ger40-backtest/spec.md`

## Summary

Add three hardcoded backtests on `GER40.I` — Combo 5m, Combo 15m, Combo
H1 — driven by the existing `indicator_service.combo` signal instead of a
9:00 reference range. Entry on MEDIUM/STRONG signals (immediate on a
triggered signal, otherwise a one-candle pending stop level); a two-lot
position with its stop 50 points beyond the signal candle's adverse
extreme; TP1 at the MM20 and TP2 at the opposite Bollinger band, both
recomputed every candle; break-even on the runner when TP1 fills; one
position at a time, held across days until an exit fires.

**Technical approach**: introduce a `Strategy` seam inside
`api/services/backtest/`. The existing day-scoped engine moves behind it
verbatim as `SessionRangeStrategy`; `ComboStrategy` is added beside it.
`Side`, `Position`, `Stop`, `DoubleTarget`, `resolve_exit`,
`TwoLotAccounting`, `build_summary`, the router, the response models, the
CSV exports and the frontend page are all reused. The genuinely new code
is the signal→entry state machine, a per-candle band recomputation, and a
continuous multi-day candle source at an arbitrary timeframe.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend)
**Primary Dependencies**: FastAPI + Pydantic v2, existing `services/indicator_service.py` (`combo`, `bollinger_bands`), existing `services/candles_service.py` (`get_candles_in_window`), `aioboto3` (DynamoDB), `zoneinfo`; React Router DOM v7+, Axios, Vite. **No new dependency.**
**Storage**: existing DynamoDB backtest raw-candle table, under a **new key namespace** for arbitrary-timeframe series (`{instrument}:{session}:{ut}:v1`). No new table, no migration of existing entries.
**Testing**: pytest (`tests/api/services/backtest/`), including the existing golden/characterization suite as the no-regression net.
**Target Platform**: Linux (FastAPI backend + AWS Lambda), browser frontend.
**Project Type**: Web (existing `api/` + `services/` backend, `frontend/` React app).
**Performance Goals**: a 6-month range run returns in under ~30s on the slowest timeframe (5m, ~20k candles). Warm-cache runs are dominated by computation, not I/O.
**Constraints**: existing backtests must stay **bit-for-bit identical** (SC-C03), enforced by `tests/api/services/backtest/test_backtest_golden.py`; `combo` itself and the live workflow engine are not modified.
**Scale/Scope**: 3 new definitions; ~6 new backend modules; ~2 shared-model edits; 1 new enum value + 3 `Strategy` entries; ~40 lines of frontend.

## Constitution Check

*GATE: evaluated before Phase 0 and re-checked after Phase 1 design. Constitution v1.3.0.*

| Principle | Assessment |
|---|---|
| **I. Layered Architecture** | ✅ Strategy logic in `api/services/backtest/` (Service layer); Saxo access only via `CandlesService`; DynamoDB access only via **new `DynamoDBClient` methods** — never `client.dynamodb.Table()` (research R3). Router stays thin. Frontend API calls stay in `services/api.ts`. |
| **II. Clean Code First** | ✅ No new abstraction beyond the one `Strategy` protocol, which exists because two implementations genuinely differ (R1). `Position.retarget` reuses `DoubleTarget` instead of forking a policy (R2). **No `assert`** — the `structural_level` guard raises `SaxoException` (R2). |
| **II.3 Enum-Driven** | ✅ `ExitReason.END_OF_RUN` and `Strategy.C5M/C15M/C1H` added rather than string literals; `UnitTime.M5/M15/H1` and `SignalStrength.MEDIUM/STRONG` already exist and are used as-is. |
| **III. Configuration-Driven** | ✅ Thresholds live in `BacktestDefinition.default_parameters` as the other definitions do; the definition registry is the established place for hardcoded backtests. No new config file. |
| **IV. Safe Deployment** | ✅ No infrastructure change (existing DynamoDB table, new key namespace only). Conventional commits. |
| **V. Domain Model Integrity** | ✅ Candle lists newest-first at every `combo` call site (R5); `Candle` objects everywhere outside `SaxoService`; only closed historical windows are read, so no current-period reconstruction is needed (R3). |
| **Planning Requirement** | ✅ Spec clarified with the user before writing; this plan precedes implementation; the `tasks.md` output requires human validation before any code is written. |
| **Testing Standards** | ✅ Tests mirror source structure under `tests/api/services/backtest/`; external calls mocked; behavior asserted, not mock invocations. |

**Result: PASS**, no violations to justify. Complexity Tracking section omitted.

**Post-Phase-1 re-check**: the design added no layer crossing, no new
dependency and no new persistence store; the two shared-code edits
(`Position`'s optional H1 levels, `Position.retarget`) are additive and
covered by the golden suite. Still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/026-combo-ger40-backtest/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── backtest-api.md  # Phase 1 (delta on the existing endpoints)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2
```

### Source Code (repository root)

```text
api/services/backtest/
├── strategy.py            # NEW - Strategy protocol + dispatch on definition
├── session_range.py       # NEW (code move) - today's day-scoped engine
├── combo_strategy.py      # NEW - the continuous combo engine
├── signals.py             # NEW - ComboEntrySearch (FR-C02/C03/C04/C10)
├── bands.py               # NEW - per-candle MM20 / opposite-band levels
├── combo_candle_source.py # NEW - continuous multi-day series at any UT
├── service.py             # EDIT - dispatch to the strategy, keep the public API
├── definitions.py         # EDIT - register C5M / C15M / C1H
├── position.py            # EDIT - optional H1 levels + retarget()
├── rules.py               # EDIT - exit chain for a combo definition
└── (side|policies|lots|statistics|calendar|analytics).py  # UNCHANGED

model/
├── backtest.py            # EDIT - BacktestDefinition.unit_time + combo_entry
└── enum.py                # EDIT - ExitReason.END_OF_RUN, Strategy.C5M/C15M/C1H

client/aws_client.py       # EDIT - store_backtest_series / get_cached_backtest_series
api/models/backtest.py     # EDIT - tunable_parameters on the definition response

frontend/src/
├── services/api.ts        # EDIT - tunable_parameters on BacktestDefinition
├── pages/Backtest.tsx     # EDIT - filter parameter inputs by tunable_parameters
└── components/BacktestDayDetail.tsx  # EDIT - tolerate absent H1 levels

tests/api/services/backtest/
├── test_signals.py             # NEW
├── test_bands.py               # NEW
├── test_combo_strategy.py      # NEW
├── test_combo_candle_source.py # NEW
├── test_backtest_golden.py     # UNCHANGED - the no-regression net
└── (all existing tests)        # UNCHANGED - must pass as-is
```

**Structure Decision**: the existing web layout is kept exactly. All new
backend code lands in the established `api/services/backtest/` package,
whose module-per-concern convention (`entry.py`, `policies.py`,
`lots.py`, `side.py`) this follows. Nothing new is introduced at the
repository level.

## Phase 0 — Research

Complete: [research.md](./research.md). Eleven decisions, each with
rationale and rejected alternatives. Every unknown is resolved; the three
assumptions the spec flagged for the user (TP2 band deviation,
one-candle pending validity, CFD session) are carried forward as stated,
each isolated to a single constant or requirement.

## Phase 1 — Design

Complete: [data-model.md](./data-model.md),
[contracts/backtest-api.md](./contracts/backtest-api.md),
[quickstart.md](./quickstart.md).

**Design summary — the per-candle loop of `ComboStrategy`**, walking the
continuous chronological series once:

```text
for each candle:
    if a position is open:
        levels = bands(window)                     # MM20, opposite band
        position.retarget(levels.mm20, levels.opposite)
        trade = resolve_exit([Stop(), DoubleTarget()], position, candle)
        if trade: record it, go flat
        continue                                   # FR-C09: signals ignored
    entry = entry_search.feed(candle, window)      # FR-C02/C03/C04
    if entry and the MM20 is favorable (FR-C10):
        open a two-lot Position:
            initial_stop_price = signal candle's adverse extreme -/+ 50
after the last candle:
    close any open position at its close, ExitReason.END_OF_RUN   # FR-C12
```

**Requirement → module map**

| Requirement | Where it lands |
|---|---|
| FR-C01 (three definitions) | `definitions.py`, `model/enum.py` |
| FR-C02, FR-C03, FR-C04 (signal → entry) | `signals.py::ComboEntrySearch` |
| FR-C05 (two lots, one aggregated trade) | reused `lots.py::TwoLotAccounting` |
| FR-C06 (stop from the signal candle) | `combo_strategy.py` → `Position.initial_stop_price` |
| FR-C07 (moving MM20 / band targets) | `bands.py` + `Position.retarget` + reused `DoubleTarget` |
| FR-C08 (break-even on TP1 only) | reused `DoubleTarget`; chain omits `ArmBreakEven` |
| FR-C09 (one position, signals ignored) | `combo_strategy.py` loop |
| FR-C10 (reject entry past TP1) | `signals.py` / `combo_strategy.py` open guard |
| FR-C11 (carry overnight) | `combo_strategy.py` — no end-of-day close |
| FR-C12 (end-of-run close) | `combo_strategy.py` + `ExitReason.END_OF_RUN` |
| FR-C13 (250-candle warm-up) | `combo_candle_source.py` |
| FR-C14 (stop before target) | chain order `[Stop(), DoubleTarget()]` |
| FR-C15 (existing outputs) | reused `statistics.py`, router, `api/models/backtest.py` |
| FR-C16 (only the stop is tunable) | `api/models/backtest.py` + `Backtest.tsx` |

**Risk register**

| Risk | Mitigation |
|---|---|
| The strategy seam silently changes an existing backtest | `test_backtest_golden.py` runs every registered definition against a fixed synthetic market and diffs a committed snapshot. It must pass **unmodified**; regenerating it is a red flag, not a fix. |
| `combo` evaluated ~20k times is too slow on 5m | Evaluate only while flat (behavior-preserving, R5); measure in T037 before optimizing anything else. |
| MACD differs from what the live engine would have seen | Fixed 250-candle window matching `alerting.py::_build_candles` (R5). |
| A moving target that crosses the entry produces a "take-profit" at a loss | Specified behavior (spec edge case), not a bug; covered by an explicit test. |
| 15m candles need reconstruction | They do not — Saxo serves horizon 15 natively and only closed windows are read (R3). Verified against `get_candles_in_window`. |
| The three flagged assumptions turn out wrong | Each is one constant: TP2 deviation (`bands.py`), pending validity (`signals.py`), session (`definitions.py`). |
