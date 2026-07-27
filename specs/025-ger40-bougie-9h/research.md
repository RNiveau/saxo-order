# Research: Hardcoded "GER40 Bougie de 9h" Backtest (double take-profit)

Phase 0 for spec 025. This feature is a thin extension of spec 021 ("CAC40 Bougie de 9h"), so most of the underlying research (Paris-local windows, Saxo historical-candle limits, one-position-at-a-time engine, ephemeral results) is inherited from `specs/021-backtest-menu-hardcoded/research.md` and not repeated. The items below resolve only what is new or different for GER40.

## §1 — GER40.I trading session and reference window

- **Decision**: Reuse the existing `EUMarket()` + `Europe/Paris` (DST-aware) logic in `api/services/backtest_service.py` verbatim for GER40.I. The 9:00–10:00 reference window, the after-10:00 evaluation start, and the session-end (17:30 local) all apply unchanged.
- **Rationale**: GER40.I (the DAX / German 40 index) trades on Xetra 09:00–17:30 Central European Time; Euronext Paris (FRA40.I) trades 09:00–17:30 CET as well. Both `Europe/Paris` and `Europe/Berlin` share the same UTC offset and DST rules, so `EUMarket` (open 9, close 17, end_minute 30) and `paris_reference_window_utc`/`paris_session_end_utc` produce the correct GER40 bounds without a new market type or timezone.
- **Alternatives considered**: (a) A dedicated `DEMarket`/`Europe/Berlin` variant — rejected: identical offset and DST to `Europe/Paris`, so it would only duplicate code. (b) A separate reference window — rejected: the strategy is explicitly "the same as CAC40 Bougie de 9h" on the 9:00–10:00 candle.
- **Evidence**: `GER40.I` already used elsewhere in the codebase (`saxo_order/commands/snapshot.py`, `shortcuts.py`, `api/services/watchlist_service.py` — "DAX") as a Saxo index instrument; the H1 and 5-minute historical fetches (`CandlesService.get_candles_in_window`) are instrument-agnostic.

## §2 — Two-lot / double take-profit representation

- **Decision**: Model a position's two lots **inside** the existing `_OpenPosition`, tracked as `first_target_level` (TP1 = H1 midpoint), `first_target_taken` (bool), and `banked_points` (lot-A P&L). Surface the closed position as **one aggregated `Trade`** whose `points` is the sum of both lots (FR-G07), constructed via a dedicated close helper because `points ≠ exit_price − entry_price` when the two lots exit at different prices or both stop out (the "SL is x2" case).
- **Rationale**: The owner chose a single aggregated trade over two rows (Clarifications 2026-07-23). Keeping the two lots as internal position state avoids a second engine and preserves the existing `Trade`/`DayResult`/response shapes (FR-G10 — no new response model, no frontend response change). The aggregated `exit_reason`/`exit_price`/`exit_time` reflect the **runner's** final exit (TP1 is a partial scale-out, not the position's close).
- **Alternatives considered**: (a) Two separate `Trade` rows per position — rejected by the owner (would double trade counts and complicate the summary). (b) A new `Position` entity wrapping N `Trade` lots — rejected as over-engineering for a fixed 2-lot strategy (Constitution II); the summary and outputs only need the aggregate. (c) Encoding the split into `exit_price` so `points` still equals the price difference — impossible when both lots stop at one level (net is 2× the per-lot loss), so points must be carried explicitly.

## §3 — Stop-loss reference: from entry vs. from the H1 level

- **Decision**: Add a `stop_from_reference_level: bool` property to `BacktestDefinition`. When `True` (GER40 only), the initial stop is `stop_loss_points` **beyond the H1 reference level** (H1 low − 150 for a long, H1 high + 150 for a short); when `False` (CAC40/`B9H`/`B9HTC`), the stop stays `stop_loss_points` from **entry**, exactly as today.
- **Rationale**: The user rule is "SL 150 points below the lower" (the H1 low), which is a level-based stop, materially different from CAC40's entry-relative stop. A per-definition flag isolates the new behavior so `B9H`/`B9HTC` are provably unchanged (their flag is `False`). Both lots share this one stop level while both are open; after TP1 the runner's stop moves to entry (break-even).
- **Alternatives considered**: (a) Reinterpret CAC40's stop as level-based too — rejected: would silently change `B9H` results. (b) A new `stop_reference` enum with more modes — rejected as speculative (only two modes exist); a bool is sufficient and honest. (c) Making the reference choice a per-run `BacktestParameter` — rejected: it is a fixed property of the strategy, not a knob (FR-G09).
- **Flagged for validation**: This is the one genuine fork from CAC40; recorded in spec Clarifications so the owner confirms "below the lower" means the H1 low, not entry, before merge.

## §4 — TP1 = 50% of the H1 candle

- **Decision**: TP1 is the arithmetic midpoint of the H1 range, `(h1_high + h1_low) / 2`, the same absolute level for both long and short. It is a fixed derived level, not a tunable parameter (FR-G09).
- **Rationale**: The owner confirmed "50% of the h1 candle" = the midpoint of the high–low range (Clarifications 2026-07-23), not the body midpoint and not a fraction of the entry-to-TP2 distance. Deriving it from the H1 high/low (already computed for every day) needs no new input.
- **Alternatives considered**: body midpoint `(open+close)/2` and `entry + 0.5·(TP2 − entry)` — both explicitly rejected by the owner's answer.

## §5 — Per-definition default thresholds

- **Decision**: Attach a `default_parameters: BacktestParameters` to each `BacktestDefinition` (CAC40 → 50/10/20/20; GER40 → 150/10/50/40). Change the router's threshold dependency to return **optional overrides**, then resolve them against the selected definition's `default_parameters` (omitted field ⇒ that definition's default). Expose `default_parameters` on `BacktestDefinitionResponse` so the frontend pre-fills the correct defaults per selected definition.
- **Rationale**: Today `BacktestParameters()` carries a single global default set (the CAC40 values), and the frontend hardcodes those same numbers in `PARAM_FIELDS`. GER40 needs different defaults (150/10/50/40). Per-definition defaults on the definition object keep one source of truth and let the frontend display the right placeholders without hardcoding a second set. Positivity validation (`> 0`, FR-G09 / spec 021 FR-027) is unchanged and still rejected at the API boundary with 422.
- **Alternatives considered**: (a) A second global default set keyed by definition code inside the router — rejected: scatters the numbers. (b) Leaving the frontend defaults hardcoded and only fixing the backend — rejected: the GER40 inputs would show CAC40 numbers, misleading the trader. (c) Keeping `BacktestParameters` dataclass defaults as the fallback and ignoring per-definition defaults — rejected: GER40 would silently run with a 50-pt stop.

## §6 — Summary classification of a double-TP position (FR-G08)

- **Decision**: For a double-TP definition, classify each aggregated position by the **sign of its net points**: net > 0 → winning, net < 0 → losing, net == 0 → break-even bucket. For non-double-TP definitions keep the existing mechanism-based classification (`exit_reason == BREAK_EVEN` ⇒ BE). Branch on `definition.double_take_profit` inside `_build_summary`.
- **Rationale**: A TP1-then-break-even runner closes with `exit_reason == BREAK_EVEN` but a **net-positive** result (the banked TP1). Mechanism-based bucketing would miscount it as BE; the owner's model treats it as a win. Sign-based classification (the same approach the time-cut variant already uses for its non-BE exits) matches reality, and the zero bucket still captures genuinely-flat positions (both lots at break-even, no TP filled). Branching on the definition keeps `B9H` counts identical.
- **Alternatives considered**: (a) Change classification globally to sign-based — rejected: would reclassify `B9H`'s rare gap-through BE trades and change spec-021 behavior. (b) A dedicated exit reason for "TP1 then BE" — rejected as unnecessary; the aggregated exit reason already reflects the runner's close and the summary reads the net sign.

## §7 — Testing approach

- **Decision**: Extend `tests/api/services/test_backtest_service.py` with hand-built 5-minute candle sequences (the existing pattern) covering every SC-G02 outcome: both-lots stop-out (net = 2× loss), +50 break-even with no TP, TP1-then-break-even (net-positive), TP1-then-TP2 full winner, end-of-day, a multi-position day, no-trade, and no-data. Add router tests to `tests/api/routers/test_backtest.py` for the `G9H` definition listing (with GER40 defaults), `/run` and `/day` against `G9H`, per-definition default resolution, and the unchanged `422` positivity rejection.
- **Rationale**: Mirrors the spec's acceptance scenarios and the existing mocked-`CandlesService` convention; no live Saxo calls. "DON'T test mock" (CLAUDE.md) — tests assert engine outcomes (entry, per-lot exits, net points, exit reason, summary counts), not that mocks were called.
- **Alternatives considered**: Recording real GER40.I days as fixtures — deferred to the hand-verification in SC-G02 (manual), not automated, to keep the suite deterministic and offline.
