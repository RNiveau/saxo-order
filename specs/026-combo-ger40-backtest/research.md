# Phase 0 Research: "GER40 Combo" Backtest (5m / 15m / H1)

All findings are grounded in the code as it stands on `main` at
`1aab598`. Each decision names what it reuses, because the value of this
feature is measuring the *existing* indicator, not re-deriving it.

---

## R1. Where the combo strategy lives

**Decision**: introduce a **strategy seam** in `api/services/backtest/`.
`BacktestService` stays the single entry point; the existing day-scoped
engine moves behind a `Strategy` protocol as `SessionRangeStrategy`
(behavior unchanged, code moved verbatim), and `ComboStrategy` is added
as a second implementation. `BacktestService.run_range` / `evaluate_day`
dispatch on the definition.

**Rationale**: `service.py::_evaluate_trades` is structurally a *day*
loop — it takes `h1_high`/`h1_low`, builds a `DirectionSearch` per side
off those levels, and force-closes at the last candle. FR-C11 (positions
carry overnight) and FR-C02 (entry from an indicator, no reference range)
remove both of its inputs. `BacktestDefinition` already carries 14
variant flags; "this is not a 9h strategy at all" as flag #15 would force
`rules.py`, `entry.py`, `candle_source.py` and `service.py` to each
branch on it, and `entry.py::DirectionSearch` would be dead code on three
of the nine definitions.

**Alternatives considered**:
- *Another flag on `BacktestDefinition`* — rejected: the flag would have
  to disable the reference range, the entry search, the entry gate, the
  end-of-day close and the day loop all at once. That is a different
  strategy, not a variant.
- *A separate `ComboBacktestService` beside `BacktestService`* —
  rejected: it would duplicate the router, the response mapping, the CSV
  export and the summary, and the Backtest menu would need to know which
  service to call per definition.

**Reused unchanged**: `side.py`, `position.py` (one additive method, R2),
`policies.py::Stop` / `DoubleTarget` / `resolve_exit`,
`lots.py::TwoLotAccounting`, `statistics.py::build_summary`,
`api/routers/backtest.py`, `api/models/backtest.py`, the CSV exports, and
the frontend page.

---

## R2. Moving take-profit levels on an existing `Position`

**Decision**: add `Position.retarget(first_target, take_profit)` and
reuse `policies.DoubleTarget` **unchanged**. The combo engine recomputes
the MM20 and the opposite band from the candle window at the top of each
iteration and calls `retarget` before `resolve_exit`.

**Rationale**: `DoubleTarget` already implements exactly FR-C07 + FR-C08 —
first lot fills at `first_target_level`, banks it, sets `be_armed = True`,
runner exits at `take_profit_level`. The only thing that differs is that
the two levels move. Mutating them through a named method is a two-line
change that buys the whole double-TP + break-even mechanic, its
gap-fill and its points accounting for free.

**Consequence — the combo exit chain is two policies**:
`[Stop(), DoubleTarget()]`. `Stop()` leading satisfies FR-C14
(stop before target on the same candle); `Position.initial_stop_price`
carries FR-C06; `Position.stop_level` returns `entry_price` once
`be_armed`, which is FR-C08. **No `ArmBreakEven`** (FR-C08: no
points-based trigger), no trail, no structural/impulsive stop, no time
cut.

**Alternatives considered**:
- *A new `MovingDoubleTarget` policy that computes bands itself* —
  rejected: it would need the candle window, which the `ExitPolicy`
  signature does not carry, so either every policy's signature changes or
  the policy holds a side-channel to the series. Both are more machinery
  than a setter.
- *`Optional[Callable]` level fields* — rejected: makes the level types
  polymorphic for all nine definitions to serve three.

**Required edit**: `Position.__init__` takes `h1_high`/`h1_low` as
required floats today, and `structural_level` reads them. A combo
position has no H1 range. Make both `Optional[float] = None` and have
`structural_level` raise `SaxoException` when they are absent (**not**
`assert` — constitution §II.5). Only `StructuralStop`/`ImpulsiveStop`
call it, and neither is in the combo chain.

---

## R3. Candle acquisition for a continuous multi-day stream

**Decision**: a new `ComboCandleSource`, fetching **one Saxo window per
trading day per timeframe** via the existing
`CandlesService.get_candles_in_window(instrument, ut, horizon,
start_utc, end_utc)`, over the **CFD session** bounds already produced by
`calendar.paris_session_end_utc` / a session-start helper, concatenated
chronologically across the range.

**Rationale**: `get_candles_in_window` is already generic over `ut` and
`horizon` and is already the only fetch the backtests use; Saxo supports
horizons 5, 15 and 60 natively, so **the 15-minute timeframe needs no
reconstruction** (the `get_candles_per_minutes` M15 rebuild path is for
in-progress periods, which a closed historical day never is). Per-day
windows rather than one giant window keep each Saxo `count` small and
make the cache key per-day, matching the existing cache's granularity.

**Warm-up (FR-C13)**: extend the fetch backwards over prior *trading*
days until at least **250 candles** precede the range's first candle, or
30 calendar days are exhausted. 250 matches what the live alerting path
feeds `combo` (`alerting.py::_build_candles` fetches `count=250`), which
matters because `macd0lag` is a recursive EMA — a truncated window gives
a *different* MACD than the live engine would have seen. Over the 20-hour session that is
~13 trading days of lead-in on H1 (20 candles/day), ~4 on 15m, and ~2 on
5m - hence the 30-calendar-day cap rather than 15.

**Caching**: the existing DynamoDB raw-candle cache stores an
`h1_candle` + `m5_candles` pair, which does not fit an arbitrary-UT
series. Add **new client methods** `store_backtest_series` /
`get_cached_backtest_series` on `DynamoDBClient` (constitution §I: never
reach into client internals) writing to the same table under a new key
namespace `"{instrument}:{session_key}:{ut}:v1"`, item shape
`{has_data, candles}`. Existing cache entries and `cache_key` are
untouched.

**Why cache at all**: the feature's whole workflow is running the same
range on three definitions, then re-running with a different stop. A
6-month run is ~130 Saxo windows per timeframe; uncached that is ~390
calls repeated on every parameter tweak.

**Alternatives considered**:
- *No cache in v1* — viable and would cut ~2 tasks, but makes the
  three-way comparison the feature exists for painfully slow.
- *Reusing `CachedDayCandles` by stuffing the series into `m5_candles`* —
  rejected: it would make the field name a lie and collide with the
  existing key namespace.

---

## R4. What "MM20" and "the opposite Bollinger band" resolve to

**Decision**: both come from the existing
`indicator_service.bollinger_bands(candles, 2.0)`:
- **TP1 = `.middle`** — the 20-period simple moving average of the
  closes, which is by construction the Bollinger middle band.
- **TP2 = `.up`** for a long, **`.bottom`** for a short, at deviation
  **2.0**.

**Rationale**: 2.0 is the deviation `combo` itself treats as the inner
band (`bb20 = bollinger_bands(candles, 2.0)` in
`indicator_service.combo`), so entry and exit are read off the same
band the signal is defined against. Both are recomputed from the window
ending at the current candle, which is what makes them move (FR-C07).

**Flagged in the spec for validation**: if the intent was the 2.5 outer
band for TP2, only the deviation constant changes.

---

## R5. Evaluating `combo` per candle — cost and correctness

**Decision**: evaluate `combo` **only while flat**. FR-C09 ignores every
signal while a position is open, so skipping the call is
behavior-preserving, not an approximation.

**Window**: pass a **newest-first slice of the most recent 250 candles**
ending at the candle under evaluation, mirroring the live path (R3).
`combo` requires ≥60 (`mobile_average(candles[10:], 50)`); 250 is what
makes the MACD comparable to live.

**Cost**: a 6-month 5m run over the 20-hour session is ~240 candles/day
× ~130 trading days ≈ **31k candles**. Each `combo` call does 5 `bollinger_bands`, 2
`mobile_average`, 1 `macd0lag` and 1 `average_true_range` over the
window. `macd0lag` was made materially faster in `1aab598`. **Action**:
task T037 measures a 6-month 5m run and, if it exceeds ~30s, caches the
rolling band computation rather than changing the strategy.

**Ordering**: `combo` expects newest-first (`candles[0]` = the candle
being evaluated), per CLAUDE.md's candle-ordering rule. The engine walks
chronologically, so the window is built by reversing a bounded tail —
never by reversing the whole series per candle.

---

## R6. The pending-entry state machine (FR-C03 / FR-C04)

**Decision**: a small `ComboEntrySearch` in a new `signals.py`, holding
at most one pending level and its originating signal candle.

Per candle, while flat:
1. If a pending level from the **previous** candle exists and this candle
   reached it → entry at `side.worse(level, candle.open)` (the existing
   conservative gap-fill convention), stop from the **pending signal's**
   candle (FR-C06).
2. Otherwise the pending level is dropped (FR-C04: one candle only).
3. Evaluate `combo` on this candle. `WEAK` → nothing. `MEDIUM`/`STRONG`
   and `has_been_triggered` → entry now at `signal.price` (the close).
   `MEDIUM`/`STRONG` and not triggered → arm a pending level at
   `signal.price` for the next candle.

Step 1 precedes step 3 so a candle that fills yesterday's pending level
opens the position and its own signal is then ignored by FR-C09.

**Entry rejection (FR-C10)** is checked at open time against the MM20 of
the entry candle: `side.favorable(mm20, entry_price) <= 0` → no position,
pending state cleared, search continues.

---

## R7. New enum values

- `ExitReason.END_OF_RUN = "end_of_run"` (FR-C12) — distinct from
  `END_OF_DAY`, which the session backtests keep.
- `Strategy.C5M / C15M / C1H` — `"Combo GER40 5m" / "15m" / "h1"`.
  Constitution §II.3 and CLAUDE.md forbid hardcoded strings where an enum
  exists; `BacktestDefinition.name` is already `Strategy.<X>.value`
  everywhere.

`SignalStrength` already has `WEAK`, `MEDIUM`, `STRONG` — no change.
`UnitTime` already has `M5`, `M15`, `H1` — no change.

---

## R8. Per-day reporting for a multi-day strategy (FR-C15)

**Decision**: keep `DayResultSummary` unchanged. A trade is attributed to
the day it **entered**. `h1_high` / `h1_low` / `h1_open` are `None` for
combo days; `mm50_slope`, `adx14` and `overnight_gap` are still computed
from the daily series (they measure the *instrument*, not the strategy —
`service.py::_fetch_daily_candles` documents exactly this) and are worth
keeping for regime analysis of combo results.

`DayStatus`: `TRADED` when a position entered that day, `NO_TRADE`
otherwise, `NO_DATA` when the day yielded no candles. A day that a
position merely runs *through* is `NO_TRADE` with 0 points — correct, and
called out in the spec's assumptions.

**Frontend consequence**: `BacktestDayDetail.tsx:49,56` prints
`H1 range: {detail.h1_low} - {detail.h1_high}` unconditionally and would
render `null - null`. It must hide that line when the levels are absent.

---

## R9. Single-day detail for a multi-day strategy

**Decision**: `evaluate_day(definition, date)` for a combo definition
runs the identical stream, bounded at the end of that day, and
force-closes any open position as `END_OF_RUN` — i.e. **a one-day range
run**. It returns that day's candles and the trades that entered that day.

**Rationale**: no new semantics to explain. The caveat that a position's
result can change when the range is extended is already FR-C12's, stated
once and true in both views.

---

## R10. Parameter exposure (FR-C16)

**Decision**: add `tunable_parameters: List[str]` to
`BacktestDefinitionResponse` (and the matching TypeScript interface),
defaulting to all four names for existing definitions and
`["stop_loss_points"]` for the combo ones. `Backtest.tsx` filters its
`PARAM_FIELDS` by it.

**Rationale**: `resolve_parameters` merges four thresholds for every
definition and the frontend renders four inputs from a module constant.
Three of them are inert for combo; leaving them editable invites a trader
to tune a number that does nothing and conclude the strategy is
insensitive to it. `BacktestParameters` keeps its shape — the unused
fields simply keep their dataclass defaults.

---

## R11. What must NOT change

`FRA40.I`/`GER40.I` "bougie de 9h" results must be bit-for-bit identical
(SC-C03). The moved `SessionRangeStrategy` is a pure code move; the two
edits touching shared code are `Position`'s optional H1 levels (R2) and
the additive `retarget` method. **Regression guard**: the existing
`tests/api/services/backtest/` suite must pass unmodified, and a task
adds an explicit golden-range assertion for one existing definition.

---

## R12. The DAX CFD session is 02:00-22:00, and needs its own `Market`

**Decision**: add `DaxCfdMarket` to `model/market.py` (open 02:00, close
22:00 Paris local) and give the three combo definitions that market.
`EuCfdMarket` (09:00-22:00) is left exactly as it is.

**Rationale**: GER40.I quotes from 02:00 — twenty hours a day, seven of
them before the Xetra cash open. A strategy that reads the instrument
continuously rather than off a session reference range should see all of
them; the first draft's 09:00 open would have discarded a third of the
session's candles and every signal in it.

**Why a separate market rather than widening `EuCfdMarket`**: the two
GER40 impulsive variants (`G9HIC`, `G9HICD`) are "bougie de 9h"
strategies whose 09:00-10:00 reference candle is derived from
`market.open_hour` via `calendar.paris_reference_window_utc`. Moving that
market's open to 02:00 would silently relocate their reference candle to
the middle of the night and change six months of shipped results without
a single line of their own code changing. Kept apart, the golden suite
stays green by construction.

**Shape** (following the `EuCfdMarket` conventions):

```python
open_hour=2, open_minutes=0, close_hour=21, end_minute=60,
h4_blocks=[4, 4, 4, 4, 4], timezone="Europe/Paris"
```

`close_hour=21` with `end_minute=60` is the existing "last full H1 candle
label, not the literal close" convention. `h4_blocks` sums to the 20
session hours.

**Verified against both DST regimes** (the constraint that actually
bounds this): `market_in_utc` documents that it only handles a session
staying inside one UTC day with `open_hour < close_hour`. A 02:00 Paris
open resolves to **01:00 UTC in winter and 00:00 UTC in summer** — inside
the day in both, but with no margin. An 01:00 local open would resolve to
23:00 UTC the *previous* day under CEST and break that assumption, so
02:00 is the earliest open this `Market` can express. `session_key`
returns `0200-2200@Europe/Paris`, which puts the combo cache in its own
namespace automatically.

**Knock-on effects**: ~240 5-minute candles per day instead of ~156
(R5's cost estimate becomes ~31k candles over six months), and the
warm-up lead-in needs a 30-calendar-day cap rather than 15 to reach 250
H1 candles (R3).
