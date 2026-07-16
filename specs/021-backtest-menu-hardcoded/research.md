# Research: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

## 1. Timezone handling for the 9:00–10:00 reference window

**Decision**: Compute the 9:00–10:00 and end-of-day boundaries in Paris exchange local time using Python's stdlib `zoneinfo.ZoneInfo("Europe/Paris")`, converting to/from the naive UTC datetimes already used for `Candle.date`.

**Rationale**: The spec (Clarifications, Session 2026-07-14) requires the reference window to always mean 9:00–10:00 at the exchange, DST-aware. The existing `EUMarket` model (`model/__init__.py`) hardcodes `open_hour=7` (UTC) with no DST adjustment — correct only for CEST (summer), off by an hour in CET (winter). Reusing it would silently misalign the reference window for roughly half the year. `Candle.date` values are naive datetimes parsed directly from Saxo's UTC (`...Z`) timestamps (`client/saxo_client.py`, `client/client_helper.py`), so the new code must explicitly attach `timezone.utc`, convert to `Europe/Paris`, do the boundary math there, and convert back to UTC before comparing against candle timestamps or building Saxo API requests.

**Alternatives considered**:
- Reuse `EUMarket.open_hour`/`close_hour` — rejected, not DST-aware, contradicts the clarified requirement.
- Fixed UTC 9:00–10:00 — rejected in clarification; would drift from the real exchange session across DST changes.

## 2. Fetching H1 and 5-minute historical candles for a closed past day

**Decision**: Fetch candles directly via `SaxoClient.get_historical_data(horizon=60, ...)` for the H1 reference candle and `horizon=5` for the 5-minute candles, anchored to explicit past-day timestamps (Mode=UpTo semantics), rather than reconstructing from 1-minute ticks.

**Rationale**: The codebase's well-known Saxo limitation — "doesn't return the current day (horizon 1440) or current hour (horizon 60)" (CLAUDE.md, Constitution V) — only affects *in-progress* periods. Every day a backtest evaluates is fully closed by definition (Assumptions: "operates only on already-closed historical days"), so this limitation does not apply and no reconstruction-from-smaller-horizon workaround (as `CandlesService.get_candles_per_minutes` does for "today so far") is needed. `UnitTime` (`model/workflow.py`) currently has no 5-minute member (`D`, `M15`, `M30`, `H1`, `H4`, `W`, `M`); add `M5 = "5m"` so 5-minute candles are properly labeled per the enum-driven convention (Constitution II) instead of tagging them as an unrelated unit time.

**Alternatives considered**:
- Reuse `CandlesService.get_candles_per_minutes` — rejected: it is built around "reconstruct from `datetime.now()` backwards," not "fetch a specific historical day's window," and only supports `M15`/`H1`.
- Reuse `CandlesService.build_candles` — rejected: it aggregates from 30-minute data using `Market.open_hour`/`close_hour` (the non-DST-aware hours from Decision 1) and does not support 5-minute granularity.

## 3. New candle-fetching capability lives in the Service layer, not the API layer

**Decision**: Add a new method to `services/candles_service.py` (e.g. `get_candles_in_window`) that calls `SaxoClient.get_historical_data` for a given horizon/date/count and returns only the candles whose timestamps fall inside a requested `[start, end)` UTC window, reusing `map_data_to_candles` for the `Candle` mapping.

**Rationale**: Constitution I (Layered Architecture Discipline) requires the Service layer to own domain candle logic and forbids the API-layer business logic (`api/services/backtest_service.py`) from calling `SaxoClient` directly or duplicating candle-fetch/caching behavior that already lives in `CandlesService`.

**Alternatives considered**:
- Call `SaxoClient.get_historical_data` directly from `api/services/backtest_service.py` — rejected, violates the layering rule and bypasses `CandlesService`'s existing caching for horizon 60 (there is no cache for horizon 5, which is fine since these are always distinct historical dates, not repeated "now" calls).

## 4. Strategy naming — reuse the existing `Strategy.B9H` enum

**Decision**: Name this hardcoded backtest after the existing `Strategy.B9H` enum member (`"Bougie de 9h"`, `model/enum.py`), rather than introducing a new hardcoded string.

**Rationale**: Constitution II and CLAUDE.md both mandate enum-driven naming over hardcoded strings. `Strategy.B9H` already exists and is used today when tagging manually-placed orders from the CLI (`saxo_order/commands/input_helper.py::get_strategy`) — confirming "Bougie de 9h" is the trader's real, already-named strategy, not a name invented for this feature. The hardcoded backtest's definition code is `B9H` (the enum member name); its display name is `Strategy.B9H.value`.

**Alternatives considered**:
- New standalone constant/string for the backtest name — rejected, duplicates an existing enum and violates the no-hardcoded-strings rule.

## 5. Splitting the range-summary and day-detail API responses

**Decision**: Expose two read endpoints: a range/summary endpoint that returns the 8-figure aggregate summary plus a compact per-day list (date, status, trade count, net points — no candle data), and a separate day-detail endpoint (computed independently, on demand) that returns the H1 levels, the full 5-minute candle series, and trade entry/exit markers for exactly one day.

**Rationale**: The spec explicitly allows unbounded date ranges (Clarifications, "no explicit UI cap"). Returning full 5-minute candle arrays for every day in a multi-month range would make the common case (viewing the summary) slow and heavy, contradicting SC-001's "a few seconds" expectation. Splitting lets the single-day view (User Story 1) and the drill-down view (User Story 3) both use the day-detail endpoint (cheap: one day's data, computed fresh, no persistence per the clarified "ephemeral for now" decision), while the range view (User Story 2) stays lightweight regardless of range length.

**Alternatives considered**:
- One endpoint returning full per-day candle/trade detail for the whole range — rejected: payload grows unbounded with range length.
- Persist run results so the range endpoint can be paginated — rejected for this iteration per the "no persistence for now" clarification; can be added later without changing the endpoint shapes.

## 6. No persistence

**Decision**: Both endpoints compute synchronously per request, using `CandlesService`/`SaxoClient` live, with nothing written to DynamoDB or any other store.

**Rationale**: Matches the "ephemeral for now" clarification and mirrors existing on-demand-computation endpoints in this codebase (e.g. `/api/report/summary`, `/api/alerts/run` — computed fresh per request, no dedicated backtest-run storage).

**Alternatives considered**: Persist runs to DynamoDB for later retrieval — explicitly deferred by the user during clarification; not part of this feature.

## 7. Frontend integration follows existing page/service/component conventions

**Decision**: Add `frontend/src/pages/Backtest.tsx` (+ `Backtest.css`), a new sidebar entry in `Sidebar.tsx`, a `/backtest` route in `App.tsx`, and a `backtestService` object (mirroring `reportService`) in `frontend/src/services/api.ts` with TypeScript interfaces mirroring the new Pydantic response models.

**Rationale**: This is exactly the established pattern for every other menu item (Report, Trade Republic Report, Watchlist, etc.) and is required by Constitution's Frontend Development Standards (service layer isolates API calls, pages are route-level, TypeScript interfaces mirror Pydantic models).

**Alternatives considered**: None — no deviation from the established convention is warranted.
