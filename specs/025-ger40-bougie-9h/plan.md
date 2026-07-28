# Implementation Plan: Hardcoded "GER40 Bougie de 9h" Backtest (double take-profit)

**Branch**: `claude/ger40-backtest-spec-025-k9togf` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/025-ger40-bougie-9h/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a third hardcoded backtest — **"GER40 Bougie de 9h"** — to the existing Backtest menu. It reuses the entire "CAC40 Bougie de 9h" engine (spec 021): the 9:00–10:00 Paris-local H1 reference range, both-direction 5-minute breakout/reversal detection, entry-validity, exit ordering, gap-fill, one-position-at-a-time, and the range/day/CSV outputs. It differs only by: (1) instrument `GER40.I`; (2) GER40 default thresholds (stop **150**, take-profit offset **10**, break-even trigger **50**, max entry distance **40**); (3) a **two-lot / double take-profit** overlay — every entry opens two lots, the first exits at the H1 midpoint (TP1 = `(h1_high+h1_low)/2`), the runner at the full target (TP2 = H1 high − 10 / H1 low + 10), and once TP1 fills the runner's stop moves to break-even; (4) the stop-loss is measured **from the H1 reference level** (150 pts below the H1 low / above the H1 high), not from entry as CAC40 does.

The implementation stays inside the existing layered architecture: a new `Strategy.G9H` enum value, per-definition **default parameters** and **double-TP properties** on `BacktestDefinition`, a double-TP branch in the existing `api/services/backtest_service.py` trade engine, no new response shape (a two-lot position is surfaced as **one aggregated `Trade`**, FR-G07/FR-G10), and the definition auto-appears in the frontend menu. The `/definitions` response is extended to carry each definition's default thresholds so the frontend pre-fills the correct GER40 defaults. No new external dependency, no persistence, no infrastructure change.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) — no change from existing stack.
**Primary Dependencies**: FastAPI + Pydantic v2 (existing), `zoneinfo` (already used by the backtest service for Paris-local math), Python stdlib `csv` (existing exports), existing `SaxoClient`/`CandlesService`; React Router DOM v7+, Axios, Vite (frontend, existing). **No new dependency.**
**Storage**: N/A — ephemeral, computed on demand per request, nothing persisted (inherits spec 021's decision).
**Testing**: pytest with the existing mocked-`CandlesService` convention used by `tests/api/services/test_backtest_service.py`; no frontend test framework (existing gap, unchanged).
**Target Platform**: Existing FastAPI backend (Lambda-deployable) + React SPA (Vite).
**Project Type**: Web application (backend packages at repo root + `frontend/`) — the codebase's established flat layout.
**Performance Goals**: Single-day run within a few seconds (SC-G01); range runs synchronous, scaling with the number of trading days (one H1 + one 5-minute Saxo call per day) — identical cost profile to CAC40; the double-TP overlay is pure in-memory arithmetic per candle.
**Constraints**: Constitution I (Layered Architecture) — engine logic stays in `api/services/backtest_service.py`, candle fetches in `services/candles_service.py`; Constitution II — reuse `Strategy` enum (new `G9H` member), no hardcoded strings, no speculative generic engine; the 50% first-target fraction and two-lot count are **fixed** strategy properties (not tunable), the four numeric thresholds stay tunable per run with **GER40 defaults** (FR-G09). GER40.I uses the same `EUMarket`/Europe/Paris session logic as FRA40.I (Xetra ≈ Euronext hours), so no new market/timezone code is needed.
**Scale/Scope**: One new `BacktestDefinition` (`G9H`); no new endpoints (the existing `/definitions`, `/run`, `/day`, `/run/csv`, `/day/csv` all take the definition code); `/definitions` response gains per-definition default-threshold + double-TP fields; one new `Strategy` enum value; a double-TP branch in the trade engine; frontend pre-fills per-definition defaults. Single-user tool, no concurrency concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | No new router; the existing thin `api/routers/backtest.py` gains only per-definition default resolution. Double-TP rule logic lives in the Service layer (`api/services/backtest_service.py`); candle fetches stay in `services/candles_service.py`. New domain fields live in `model/backtest.py` (dataclasses, no external deps). Frontend keeps all API calls in `frontend/src/services/api.ts`; the page reads per-definition defaults from the definitions response (props in). | PASS |
| II. Clean Code First | Reuses the `Strategy` enum via a new `G9H` member instead of a hardcoded name; reuses `Direction`/`ExitReason`/`DayStatus`; the two-lot mechanic is expressed as fields on the existing `_OpenPosition`/`BacktestDefinition`, not a parallel engine; no generic backtest-authoring capability is built (FR-G01). No `assert` in production code (Constitution II.5 / 1.3.0) — invariant violations raise explicit exceptions, matching `_candle_date`. | PASS |
| III. Configuration-Driven Design | Thresholds remain per-run analysis inputs (defaults now attached per `BacktestDefinition` rather than a single global default), not deployment config — appropriate, same rationale as spec 021's resolved exception. No new external integration or credential. | PASS |
| IV. Safe Deployment Practices | Additive within the existing API/frontend deployment; no new Lambda, ECR, or Pulumi change. Conventional commits (`feat:`). | PASS |
| V. Domain Model Integrity | Reuses `model.workflow.Candle` everywhere outside the client; GER40.I is a single hardcoded Saxo instrument (index), so the `exchange`/`country_code` inference rule does not apply; the H1/5-minute historical fetches for closed past days respect the "current period not returned" Saxo limitation the same way CAC40 does. | PASS |

No violations requiring justification — see Complexity Tracking for the one design point (stop measured from the H1 level) that is a spec-mandated per-definition difference, not a constitutional exception.

## Project Structure

### Documentation (this feature)

```text
specs/025-ger40-bougie-9h/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── backtest-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
model/
├── enum.py                        # + Strategy.G9H = "Bougie de 9h GER40"
└── backtest.py                    # BacktestDefinition: + default_parameters,
                                    #   double_take_profit, first_target_fraction,
                                    #   stop_from_reference_level fields.
                                    #   BacktestParameters unchanged (shape); its
                                    #   defaults stay the CAC40 values, GER40 supplies
                                    #   its own via default_parameters.

api/
├── models/
│   └── backtest.py                # BacktestDefinitionResponse: + default_parameters
                                    #   (+ double_take_profit flag) so the frontend
                                    #   pre-fills GER40 defaults. Trade/Day/Run
                                    #   response shapes UNCHANGED (FR-G10).
├── routers/
│   └── backtest.py                # _params -> optional overrides; resolve against
                                    #   the definition's default_parameters after the
                                    #   definition is looked up (per-definition
                                    #   defaults, not a single global default).
└── services/
    └── backtest_service.py        # BACKTEST_DEFINITIONS: + G9H entry (GER40.I,
                                    #   GER40 defaults, double-TP props). _OpenPosition:
                                    #   + first_target_level/first_target_taken/
                                    #   banked_points + reference-based stop. New
                                    #   double-TP exit path in _resolve_exit +
                                    #   aggregated-trade close helper. _build_summary:
                                    #   points-sign classification for double-TP defs
                                    #   (FR-G08). resolve_parameters helper.

frontend/src/
├── pages/
│   └── Backtest.tsx               # Pre-fill threshold inputs from the selected
                                    #   definition's default_parameters (falls back
                                    #   to the current constants for CAC40).
└── services/
    └── api.ts                     # BacktestDefinition interface + default_parameters
                                    #   (+ double_take_profit) fields.

tests/
└── api/
    ├── services/
    │   └── test_backtest_service.py  # + GER40 double-TP engine tests (all SC-G02
                                    #   outcome types) mirroring the acceptance scenarios
    └── routers/
        └── test_backtest.py          # + G9H definition listed w/ GER40 defaults;
                                    #   run/day/csv against G9H; per-definition default
                                    #   resolution; positivity validation still 422
```

**Structure Decision**: Follows the codebase's existing flat layout (backend packages `api/`, `services/`, `model/` at repo root, `frontend/` alongside), matching spec 021 and every prior feature. The feature extends the existing backtest modules rather than adding new ones, and introduces no new top-level directory.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations. Two design points are recorded here because they are deliberate deviations from "CAC40 Bougie de 9h" mandated by the spec, not because they need justification against a principle:

| Design point | Why | Note |
|---|---|---|
| Stop-loss measured from the **H1 reference level** (150 pts beyond it) for `G9H`, while `B9H` measures its stop from **entry**. | Spec FR-G05 / user rule "SL 150 points below the lower". | Implemented as a `stop_from_reference_level` flag on `BacktestDefinition` so `B9H`/`B9HTC` behavior is byte-for-byte unchanged; only `G9H` takes the reference-based branch. Surfaced in the spec Clarifications for the owner to confirm during validation. |
| A two-lot position is surfaced as **one aggregated `Trade`** whose `points` ≠ `exit_price − entry_price`. | Spec FR-G07 (owner chose one aggregated trade over two rows). | Kept within the existing `Trade` shape (no response change, FR-G10); the engine computes the summed points explicitly via a dedicated close helper. The aggregated `exit_price`/`exit_reason` reflect the runner's final exit. |

---

# Addendum: "GER40 Bougie de 9h (bougie impulsive)" variant (`G9HIC`)

**Branch**: `claude/dax-backtest-impulsive-candle-61dj2p` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md) §Addendum

## Summary

A fourth GER40 backtest that keeps the single-lot `G9HSL` setup (take-profit at the H1 far level − 10, break-even arming at +50) and replaces the fixed 150-point stop with an **impulse stop**: the position closes only on a 5-minute candle that is at least 70 points wide, closes within 25% of its range from the extreme adverse to the position, and closes beyond the H1 reference level — or on its take-profit, its armed break-even stop, or end of day. Days whose 9:00–10:00 H1 range is not strictly greater than 70 points are not traded. The session runs 9:00–22:00 Paris on a new `EuCfdMarket` instead of the 17:30 cash close.

**Note on the base**: this addendum is written against the **refactored backtest package** (`api/services/backtest/`, PR #672), not the single `api/services/backtest_service.py` module the sections above describe. The refactor is what makes this variant cheap: the impulse rule is one new `ExitPolicy` plus one new `Side` predicate, composed in `rules.build_exit_chain`. No engine code branches on which backtest is running.

## Design

### 1. `EuCfdMarket` and per-definition markets

`Market`, `USMarket` and `EUMarket` move from `model/__init__.py` into a new `model/market.py`, re-exported from `model/__init__.py` so every existing import keeps working. The move is required, not cosmetic: `model/__init__.py` imports `model.backtest` at line 5, so `BacktestDefinition` cannot reference a market class defined further down the same file without a circular import.

`EuCfdMarket` follows the `USMarket` convention for a close that is not on an H1 boundary label: `close_hour=21, end_minute=60` → a 22:00 close, where `close_hour` stays the last-full-H1-candle label hour. `h4_blocks=[3, 4, 4, 2]` (9-12 / 12-16 / 16-20 / 20-22).

`BacktestDefinition` gains `market: Market = field(default_factory=EUMarket)`. `api/services/backtest/calendar.py` stops hardcoding `EUMarket()` and takes the market as a parameter (`paris_reference_window_utc`, `paris_session_end_utc`, `is_today_not_yet_closed`); `candle_source.py` and `service._fetch_daily_candles` pass `definition.market`; `api/routers/backtest.py` threads it into `_parse_date`/`_parse_range`, which every endpoint already calls **after** `_resolve_definition`.

No cache-schema bump: the raw-candle cache key is `code:instrument:vN`, so a new definition code gets its own namespace and no existing entry is reinterpreted under the longer session. *(Updated 2026-07-28: the key is now `instrument:session window:vN`, dropping the definition code. The longer CFD session is still isolated — it is now the session window itself, rather than the definition code, that keeps this variant from reading a cash-session entry.)*

### 2. The impulse rule

One new predicate on `Side`, so the long and short forms are one expression rather than two:

```python
def closed_near_adverse_extreme(self, candle: Candle, fraction: float) -> bool:
    span = candle.higher - candle.lower
    return self.favorable(candle.close, self.adverse_extreme(candle)) <= fraction * span
```

For a long, `adverse_extreme` is the candle's low and `favorable(close, low)` is `close − low`; for a short it is the high and the expression becomes `high − close`. Multiplicative, so a zero-range candle needs no guard (and cannot pass the 70-point amplitude test anyway).

One new policy, `policies.ImpulsiveStop(points, fraction)`, closing at the candle's close with `ExitReason.STOP_LOSS`. It sits **after** `Target()` in the chain for the same reason `StructuralStop` does — it is measured on the close, while a target is touched intrabar — and returns `None` once break-even is armed, at which point `Stop(only_when_armed=True)` at the head of the chain owns the exit.

Chain for `G9HIC`: `Stop(only_when_armed=True)` → `Target()` → `ImpulsiveStop(70, 0.25)` → `ArmBreakEven(50)`.

### 3. Definition fields and guards

`impulsive_candle_points: Optional[float] = None` and `impulsive_close_fraction: Optional[float] = None`, both off by default. `BacktestDefinition.__post_init__` gains guards in the style of the existing ones — a flag that cannot take effect must fail at registration, never ship as a silent no-op: `impulsive_candle_points > 0`; `0 < impulsive_close_fraction < 1`; the two are set together or not at all; and the combination with `structural_stop` is rejected (two competing close-measured stops, no backtest needs it and none has been validated against it).

### 4. The definition

`G9HIC` — `Strategy.G9HIC`, `GER40.I`, `market=EuCfdMarket()`, GER40 defaults 150/10/50/40 (`stop_loss_points` unused, as it already is for `B9HWS`), `min_h1_range_points=70.0`, `impulsive_candle_points=70.0`, `impulsive_close_fraction=0.25`.

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture Discipline | The market is a Model-layer type (`model/market.py`, stdlib only); the impulse rule is a Service-layer policy; no router or client change beyond threading the definition's market into date parsing. | PASS |
| II. Clean Code First | New `Strategy.G9HIC` enum member, no hardcoded strategy string; the rule is composed from the existing policy chain rather than a new engine branch; the long/short forms are one `Side` expression; no `assert` in production code — the registration guards raise `ValueError`. | PASS |
| III. Configuration-Driven Design | The impulse threshold and close fraction are fixed strategy properties on the definition (FR-G18), not deployment config and not per-run knobs; the four numeric thresholds stay per-run analysis inputs. | PASS |
| IV. Safe Deployment Practices | Purely additive: one new definition, one new market, two new definition fields. No Lambda/ECR/Pulumi change. Conventional commits. | PASS |
| V. Domain Model Integrity | `Candle` used throughout outside the client; `GER40.I` is a hardcoded index instrument so the `country_code` inference rule does not apply; the longer CFD session only changes the fetch window, not the "Saxo does not return the current period" handling. | PASS |

## Complexity Tracking

| Design point | Why | Note |
|---|---|---|
| Moving `Market`/`USMarket`/`EUMarket` to `model/market.py`. | `model/__init__.py` imports `model.backtest` before the market classes are defined, so `BacktestDefinition.market` would be a circular import. | Pure move + re-export; every `from model import EUMarket` keeps working, and no other module changes. |
| A definition with **no stop-loss distance at all** while unarmed. | FR-G15 — the variant's entire premise. | Not new machinery: `B9HWS` already runs `Stop(only_when_armed=True)`. `stop_loss_points` stays on the params object (it is a shared shape) and is simply unread, as it already is for `B9HWS`. |
| The impulse test is amplitude **and** shape **and** level, not amplitude alone. | Clarifications 2026-07-27 — amplitude alone would fire on long-wick reversal candles that closed back inside the range, which are indecision, not impulse. | Makes the name honest: "impulsive" implies a decisive move, and the 25% close fraction is what enforces it. |

---

# Addendum 2: entry cut-off and daily loss cap (`G9HIC`)

**Branch**: `claude/dax-backtest-impulsive-candle-61dj2p` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md) §Addendum 2

## Summary

Two entry filters on `G9HIC`: no position opened on a candle starting at or after 16:00 Paris, and none once two positions have closed at a loss that day. Exit handling is untouched.

## Design

### Where these belong

The exit-policy chain is the wrong home for both. A policy answers "does this rule close an open position?", and neither of these ever closes anything — they decide whether the engine may open one. Forcing them into the chain would mean a policy that mutates engine state it does not own, which is the coupling the #672 refactor removed.

They also do not belong in `is_valid_entry`/`DirectionSearch`: that layer judges a *candidate breakout* against price levels and is deliberately stateless across positions. The clock and the day's realised losses are properties of the run, not of the breakout.

So they go where the engine already decides whether to open — `service._evaluate_trades` — behind one small, testable object rather than two `if`s inline:

```python
class EntryGate:
    """Whether the engine may open a position on this candle."""
    def allows(self, candle_time) -> bool
    def record(self, trade) -> None     # counts a closed loss
```

`rules.build_entry_gate(definition, trading_date)` constructs it from the definition's flags, mirroring `build_exit_chain`/`build_lot_model` — so `definitions.py` stays the only place variant flags are read, and a definition with neither filter gets a gate that always allows (the existing behavior, no branching at the call site).

The engine change is then two lines: consult `gate.allows(candle_time)` before opening, and `gate.record(closed)` where trades are already appended.

### Definition fields

- `last_entry_time: Optional[datetime.time] = None` — 16:00 for `G9HIC`. Stored as a naive local time and resolved against the definition's market timezone per trading date, the same DST-aware path `paris_reference_window_utc` uses, so it is 14:00 UTC in summer and 15:00 in winter. Candle timestamps are naive UTC, so the gate compares in UTC.
- `max_daily_losses: Optional[int] = None` — 2 for `G9HIC`.

`__post_init__` guards, in the existing style: a positive `max_daily_losses`, and a `last_entry_time` that actually falls inside the session (a cut-off at 23:00 on a 22:00 market, or at 08:00 before the 10:00 scan start, is a filter that could never fire or could never allow — both are configuration errors worth failing at registration).

### What counts as a loss

`trade.points < 0`, matching `SingleLot.classify`'s losing branch and therefore the summary's "number of losing positions". Deliberately not `exit_reason == STOP_LOSS`: under an impulse stop a day can bleed through end-of-day closes without a single stop firing, and a cap that ignored those would not bound what it claims to.

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Layered Architecture | Definition fields in `model/`; the gate and its construction in the Service layer beside the exit chain; no router, client or frontend change. | PASS |
| II. Clean Code First | One object with two methods rather than two inline conditions; built by the same `rules.py` that builds the chain, so variant flags stay read in one place; no `assert` — the registration guards raise `ValueError`. | PASS |
| III. Configuration-Driven | Both are fixed strategy properties (FR-G22), not deployment config and not per-run knobs. | PASS |
| IV. Safe Deployment | Additive to one definition; no infrastructure change. The `G9HIC` golden rows move, which is the intended, reviewable evidence. | PASS |
| V. Domain Model Integrity | `Candle`/`Trade` throughout; no new instrument or market handling. | PASS |

## Complexity Tracking

| Design point | Why | Note |
|---|---|---|
| A new `EntryGate` concept rather than two `if`s in `_evaluate_trades`. | The engine loop is the one place that already knows both the clock and the closed trades; adding two stateful conditions inline would put day-scoped state in the middle of the candle walk. | It is ~20 lines and is unit-testable without building candles. `build_entry_gate` returns an always-allow gate for the five definitions with neither filter, so their code path is unchanged. |
| The `G9HIC` golden snapshot moves. | FR-G19/FR-G20 change which entries are taken. | Expected and load-bearing: the diff shows exactly which trades the filters removed. The other five definitions must stay byte-for-byte identical (SC-G13). |
