# Phase 0 Research: Weekly-Timeframe Combo Detection

**Feature**: 029-combo-weekly-timeframe | **Date**: 2026-08-23

All findings below were verified against the working tree at the spec's base commit. Line
references are to that state.

---

## R1 — How the weekly series is assembled inside the alerting scan

**Decision**: add a local `_build_weekly_candles(saxo_client, asset, daily_candles)` to
`saxo_order/commands/alerting.py`. It issues **one** provider request (`horizon=10080`,
`count=70`), maps it with `ut=UnitTime.W`, and prepends the forming week built by
`utils.helper.build_current_weekly_candle_from_daily(daily_candles)` — reusing the daily candles
`_build_candles` has already fetched for that asset — when the newest returned bar is not the
current ISO week.

**Rationale**: the forming week is exactly the elapsed days of the current ISO week, and those days
are already in memory. Assembling from them costs zero additional requests and satisfies FR-003.
`horizon=10080` is already in the client's 30-minute TTL cache list (`client/saxo_client.py:450`),
so repeated runs within the window are free. Net cost is **+1 request per asset per scan**, the
floor US4 allows.

**Alternatives considered**:
- `CandlesService.build_weekly_candles` (`services/candles_service.py:301`) — does the right thing
  but is keyed on `code` + `Market`, while the scan carries `saxo_uic` from `stocks.json`. Reuse
  would mean an extra `get_asset(code)` resolution **plus** its own 5-candle daily fetch for the
  forming week: 3 requests per asset instead of 1. Rejected on cost, not correctness.
- Re-cutting weekly bars from the existing daily fetch — impossible: `count=250` daily candles
  (`alerting.py:664-670`) is roughly one trading year, ~50 weeks, short of the 60 required.

**Edge case covered for free**: `build_current_weekly_candle_from_daily` returns `None` when no
daily candle falls in the current ISO week, which is precisely the weekend / Monday-before-open
case in the spec. The weekly series then ends at the last completed week.

---

## R2 — Expressing the reduced criteria set without a second implementation

**Decision**: introduce a frozen `ComboSettings` dataclass (min candles, MA50 slope floor and
"strong" level, BB flat-slope ceiling, the two ATR margins, strong-signal minimum, and a
`use_macd` flag) and a `COMBO_SETTINGS: Dict[UnitTime, ComboSettings]` map. `combo()`,
`_ComboContext` and `_combo_for_direction` take the settings; `combo(candles)` keeps today's daily
behaviour as the default.

**Rationale**: the criteria bodies are identical across timeframes — only the constants and one
criterion's presence differ. One parameterised implementation keeps the buy/sell mirror logic in a
single place, which is the property `_combo_for_direction` was written to preserve. `_ComboContext`
already computes `macd0lag` lazily (`indicator_service.py:288-297`), so omitting the criterion
needs no restructuring: the property is simply never read.

**Alternatives rejected**: a `combo_weekly()` copy (duplicates the mirror logic and the five
criteria); a `use_macd` boolean threaded through without a settings object (five more parameters at
every call site, and the thresholds would still be global).

---

## R3 — Strength bands for the reduced set

**Decision**: weekly `strong_signal_min = 3` (of 4 criteria). Daily keeps 4 (of 5).

**Rationale**: dropping `macd` leaves four criteria (`ma50_over_bb`, `price_within_bb`,
`strong_ma50`, `both_bb_flat` — `indicator_service.py:390-405`) against the inherited
`COMBO_STRONG_SIGNAL_MIN = 4` (`indicator_service.py:123`), which would make "strong" mean a
perfect score and collapse the band. Three of four (75%) is the nearest band preserving the daily
proportion (four of five, 80%) without demanding perfection. This is an initial value; R8's
calibration may move it and FR-004 requires it to be stated deliberately either way.

---

## R4 — Repeat suppression keyed on the weekly bar and direction

**Decision**: add a signature function to the **model** layer, used by `store_alerts` for both the
stored items and the incoming alerts. Default signature is unchanged —
`(alert_type, date.date())`. For `COMBO_WEEKLY` only, it is
`(alert_type, data["weekly_bar_date"], data["direction"])`.

**Rationale**: `DynamoDBClient.store_alerts` builds `existing_signatures` from stored dicts and
compares them to signatures of incoming `Alert` objects (`client/aws_client.py:534-554`). Routing
both sides through one function keeps them symmetric by construction. Deriving the signature is
domain logic, so it belongs in `model/`, not the client (Constitution I); the client calls it.

**Provable inertness (FR-013, SC-007)**: every alert type other than `COMBO_WEEKLY` takes the
default branch, which returns the identical tuple the current code builds inline — including the
existing `except (KeyError, ValueError): continue` behaviour for malformed stored rows. A test
asserts the signature of each existing type is unchanged, and a second asserts a stored alert
written before this feature still de-dupes exactly as before.

**Normalisation**: `weekly_bar_date` is stored as `.date().isoformat()`. The bar date originates as
a `datetime` on a daily candle, and Monday's candle can be provider-supplied on Tuesday but
H1-rebuilt on Monday itself (`alerting.py:672-690`) — the two carry different times. Normalising to
a date makes the signature stable across those two paths; a raw datetime would not be.

**Storage shape**: alerts live as a list inside one item per asset (`get_alerts`,
`aws_client.py:618-635`). Adding `weekly_bar_date` and `direction` inside the weekly alert's `data`
needs no schema change and no migration; `data` is already a free-form map.

**TTL interaction**: `store_alerts` returns before `update_item` when every incoming alert is a
duplicate (`aws_client.py:556-561`), so the item's `ttl = now + 7 days` is refreshed only on a real
write. Bar-keyed suppression means an asset whose only alert is a persisting weekly combo stops
refreshing its item for the rest of that week. This is safe — a weekly bar spans at most 5 scans,
inside the 7-day window — but the margin is now load-bearing where it previously was not, so any
future lengthening of the suppression key must revisit it.

---

## R5 — The layer at which suppression applies

**Decision**: suppression applies to **recording** only. Detection re-runs on every scan, and the
digest keeps being synthesised from what the scan detected.

**Rationale**: the digest is built from `all_alerts` — the alerts detected during that run
(`alerting.py:528-562`) — not from what `store_alerts` accepted. Leaving detection untouched means
the digest always reflects the forming bar as it stands that day, including a direction that
flipped since the alert was first recorded, which the spec's edge case requires. Suppressing at the
detector would remove the asset from the digest for the rest of the week and contradict that
requirement.

**Accepted consequence**: a weekly setup that persists all week is recorded once but surfaced in
five consecutive digests. SC-005 therefore counts asset-days. This was raised in review and
accepted deliberately; the alternative was unreachable.

---

## R6 — A new alert type rather than a timeframe field

**Decision**: add `AlertType.COMBO_WEEKLY = "combo_weekly"`.

**Rationale**: FR-002 requires every consumer to tell the two apart, and `alert_type` is the
dimension all consumers already key on — the frontend label map, the frontend directional list, the
triage directional set, and the API's `alert_type` filter (`api/routers/alerting.py:39`). A
timeframe field inside `data` would force each of those to learn a second dimension, and the
existing de-dup signature would still not separate them.

**Known enumeration sites to update (FR-010)**: four, not three —
`services/alert_triage_service.py:278` (`_DIRECTIONAL_PATTERNS`),
`services/alert_triage_service.py:264` (`_PATTERN_FAMILY`, per R7),
`frontend/src/components/AlertCard.tsx:98` (directional rendering), and
`frontend/src/pages/AssetDetail.css:549` (`.alert-card[data-alert-type="combo"] .alert-type-badge`
— per-type badge colour, which `combo_weekly` does not inherit).

`frontend/src/utils/alertLabels.ts:4` is polish rather than a gap: `getAlertTypeLabel` falls back to
`titleCase` (`:19-20`), so an unmapped type already renders as "Combo Weekly". The CSS rule is the
real one — without it the badge loses the per-type colour that makes US3's "distinguishable at a
glance" true.

---

## R7 — Teaching the triage brief what a weekly combo means

**Decision**: add `COMBO_WEEKLY` to `_DIRECTIONAL_PATTERNS`, and add a `combo_weekly` entry to the
prompt's pattern-semantics block placing it above `combo`, with the long-only consequence spelled
out: a `"Buy"` weekly combo is the strongest reason to surface an asset; a `"Sell"` weekly combo
disqualifies it as a long exactly as a `"Sell"` combo does.

**Rationale**: the prompt already documents the meaning and rank of every pattern it receives
(`alert_triage_service.py:100-120`), and the long-only mandate (`:55-70`) makes bearish evidence
disqualifying rather than symmetric. A directional pattern arriving without semantics would be
weighted by the model's own guess. `_alert_direction` needs no change — it reads `data["direction"]`,
which the weekly alert carries in the same shape as the daily one.

**Deterministic fallback**: add `COMBO_WEEKLY: COMBO` to `_PATTERN_FAMILY`
(`alert_triage_service.py:264`), collapsing the two timeframes into **one** confluence point.

This is a correction to an earlier reading of this decision, and it matters. `_confluence_points`
is `len(_structural_families(patterns)) + _trigger_point`, and `_fallback_conviction` returns
`HIGH` at `points >= 2` (`:422-441`). Counting weekly as its own family would make a daily + weekly
combo an **automatic HIGH** with no second mechanism agreeing — and the fallback path consults no
direction at all (`_DIRECTIONAL_PATTERNS` is read only when building the LLM payload, `:507`), so a
**Sell** daily plus a **Sell** weekly would land in HIGH, precisely what the long-only work exists
to prevent and what FR-009 forbids.

Collapsing also matches the one precedent in that map: `_PATTERN_FAMILY` already folds
`CONGESTION100` into `CONGESTION20` because they are one detector at two lookback windows. Daily and
weekly combo are one detector at two timeframes — the same relationship — and the spec calls their
agreement "reinforcing evidence", which under this model is one point, not two.

With the collapse, an asset carrying only combos scores exactly as it does today: one structural
family, WATCH when the slope clears the threshold. The fallback's direction-blindness is unchanged
and pre-existing, not something this feature introduces.

**Where rank lives**: weekly outranking daily is expressed in the prompt, which is the only place
that reasons about rank. The fallback counts families; it does not rank them.

---

## R8 — Source of the calibration and validation data

**Decision**: calibration is a one-off developer script, `scripts/calibrate_weekly_combo.py`, that
fetches `horizon=10080` directly from the provider for a **sample of the scanned universe** (a few
dozen French stocks drawn from `stocks.json`, not the whole list), caches the raw response to a
local file so re-runs cost nothing, and reports the distribution of `ma50_slope`, `bbh_slope` and
`bbb_slope` over those weekly bars. The chosen constants are then committed. It runs outside the
scan and is paid once.

**Rationale**: the existing `backtest_candle_cache` table cannot serve this, on two counts:

- **Wrong shape.** Its only writer, `CandleSource`, persists an `h1_candle` plus `m5_candles` per
  `trading_date` (`client/aws_client.py:1013-1045`). It holds no weekly bars and no daily ones;
  producing weekly series from it would mean aggregating H1 → daily → weekly across a
  session-scoped window.
- **Wrong universe.** The key is `{instrument}:{session_key}:v2`
  (`api/services/backtest/candle_source.py:51-60`) and every backtest definition names `FRA40.I` or
  `GER40.I` (`api/services/backtest/definitions.py`). Two index CFDs — not the few hundred French
  single stocks the alerting scan covers. Thresholds for "how flat are the bands" and "how steep is
  the MA50" calibrated on two indices would not transfer to that equity universe.

(The `{instrument}:{session}:{ut}:v1` namespace CLAUDE.md attributes to spec 026 is not what the
code keys on; `CACHE_SCHEMA_VERSION = 2` dropped the definition code and carries no `ut` segment.)

**Cost**: one request per sampled asset, once, outside the scheduled scan. That is the price of
calibrating on the universe the thresholds will actually be applied to, and it is paid by a
developer running a script rather than by the Lambda.

**Not resolved here**: the labelled sample of ≥20 historical setups that SC-001 verifies against is
produced by the trader. It is a release prerequisite recorded under the spec's Dependencies, not an
output of this plan.

---

## R9 — Where the weekly thresholds live

**Decision**: as module constants beside the daily ones in `services/indicator_service.py`, carried
by the `ComboSettings` map from R2. The feature **toggle** goes in `config.yml`.

**Rationale**: Constitution III says thresholds live in configuration, and `triage_slope_threshold`
sets that precedent (`config.yml`, `utils/configuration.py:165`). These particular values are
different in kind: they are calibrated constants that define what the indicator *is*, reviewed as
code alongside the criteria they gate, and identical in every environment. The daily set already
lives in code; splitting the pair across two homes would make the timeframes harder to compare than
either home alone. Recorded in Complexity Tracking as a deliberate deviation.

---

## R10 — The off switch

**Decision**: `weekly_combo_enabled` in `config.yml`, exposed as a `Configuration` property,
consulted once in the scan.

**Rationale**: FR-012 asks for a revert path without a deploy of different code, which is exactly
what Constitution III's configuration rule is for. With it false, the scan issues no weekly request,
emits no weekly alert, and hands the digest the same alert set as today — the direct proof SC-007
asks for.

---

## R11 — How many weekly bars to request

**Decision**: `count=70`.

**Rationale**: the reduced set needs 60 (`mobile_average(candles[10:], 50)` reads 60 bars; the
Bollinger reads need 23). The margin absorbs the forming-week insert and any gap the provider
returns. Requesting substantially more would cost nothing per call but would narrow the pool of
eligible assets for no analytical gain.

---

## R12 — Measuring eligibility for SC-004

**Decision**: measure during a dry run of the scan — count assets whose weekly fetch returns ≥60
bars, log the ratio, report it once. No persistent metric, no new table.

**Rationale**: SC-004 is a release gate answered once, not a runtime property worth instrumenting.
Adding a metric store for a single question would be the speculative abstraction Constitution II
rejects.
