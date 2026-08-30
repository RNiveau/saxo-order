# Data Model: Local MCP Server for Asset Analysis

**Feature**: 030-mcp-asset-analysis | **Date**: 2026-08-30

All models are **transient response shapes** (Pydantic v2, in `mcp_server/models.py`). Nothing here is persisted — no new table, no new column, no migration. Existing stored records are read through `DynamoDBClient` and mapped into these shapes.

Pydantic annotations double as the MCP output schema, so field names and enums are the wire contract.

---

## Cross-cutting

### `Provenance` (new enum, `model/enum.py`)

| Value | Meaning |
|---|---|
| `LIVE` | Data came from the real market connection |
| `SIMULATED` | Data came from `MockSaxoClient`; only reachable with an explicit per-request opt-in |

Required on **every** market-derived response (FR-004). A response missing it is a bug, not a default.

### `ResponseMeta` (embedded in every market-derived response)

| Field | Type | Notes |
|---|---|---|
| `provenance` | `Provenance` | FR-004 |
| `exchange` | `Exchange` | Existing enum. **Always explicit** — never inferred from `country_code` (Constitution V.4) |
| `unit_time` | `UnitTime` | Existing enum |
| `last_bar_date` | `datetime` | Timestamp of the most recent bar used (FR-019) |
| `truncated` | `bool` | Set when a cap was applied (FR-008) |

---

## Instrument reference

**`InstrumentRef`** — output of `search_asset`, input identity for everything else.

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | Symbol, e.g. `"AI"` |
| `description` | `str` | Human name |
| `instrument_id` | `int \| None` | Venue identifier (Saxo UIC today). `None` means **not analysable** — surfaced as an explicit reason, not a silent skip. Named venue-generically because Story 5 adds a second venue |
| `asset_type` | `AssetType` | Existing enum. **Required downstream** — `get_historical_data` has no default for it, so every market-data tool takes it back (contracts/tools.md) |
| `exchange` | `Exchange` | Explicit |
| ~~`country_code`~~ | — | **Removed.** `Asset` (`model/asset.py`) carries only `symbol`, `description`, `asset_type`, `exchange`, `identifier` — `SaxoClient.search` never sets a country code, so the field would always be `None`. It is available on stored-context reads (watchlist, alerts), where it is populated; it is not part of resolution |

**Validation**: a candidate with `instrument_id is None` is returned with an `unavailable_reason`, never dropped — the analyst should see that the instrument exists but cannot be analysed.

**Known limit of the layer below**: `SaxoClient.search` skips any result whose `AssetType` is not in the enum (`saxo_client.py:130-134` — `continue` after a warning), so such candidates never reach this model. The "never dropped" rule is therefore scoped to *this* layer; it cannot promise completeness the client does not provide. Pre-existing behaviour, accepted as-is rather than changed for a read-only feature.

---

## Bar series

**`BarSeries`** — output of `get_candles`. Columnar for token economy (FR-018).

| Field | Type | Notes |
|---|---|---|
| `meta` | `ResponseMeta` | |
| `columns` | `list[str]` | Fixed: `["date", "open", "high", "low", "close"]` — stated once, not per row |
| `rows` | `list[list]` | **Newest-first** (Constitution V.1) |
| `current_incomplete` | `bool` | True when row 0 is an in-progress period (FR-007) |
| `count` | `int` | Rows returned |

**Validation**:
- Ordering is newest-first and asserted in tests (Constitution V enforcement).
- The in-progress period comes from the **scan's** reconstruction — the helper extracted from `alerting._build_candles`, not `CandlesService.build_candles` (research.md §10). Using `CandlesService` here would both diverge from the scheduled scan (breaking FR-005/SC-006) and turn a 235-bar daily request into ~13 paginated 30m round-trips.
- When the instrument's market cannot be determined, the top-up is skipped and `current_incomplete` is `False` — never a bar assembled against guessed session hours.
- `count` ≤ the hard cap; exceeding it sets `meta.truncated`.
- Prices rounded to 4dp, matching the existing API.

---

## Indicator snapshot

**`IndicatorValue`** — one indicator, present or absent with a reason.

| Field | Type | Notes |
|---|---|---|
| `name` | `IndicatorName` | New enum — no string literals (Constitution II.3) |
| `value` | `float \| dict \| None` | `None` **only** when `unavailable_reason` is set |
| `unavailable_reason` | `str \| None` | e.g. `"needs 235 bars, got 80"` (FR-011, SC-003) |

**`IndicatorSnapshot`** — output of `get_indicators`.

| Field | Type | Notes |
|---|---|---|
| `meta` | `ResponseMeta` | |
| `instrument` | `InstrumentRef` | |
| `current_price` | `float` | |
| `variation_pct` | `float \| None` | vs. previous period close |
| `indicators` | `list[IndicatorValue]` | Every requested indicator appears — computed or explained |
| `bars_fetched` | `int` | The single fetch depth. Makes SC-002 observable |

**Validation**:
- **Every requested indicator appears in the list.** Absence is expressed by `unavailable_reason`, never by omission — omission would leave the assistant unable to tell "failed" from "flat".
- The response fails only when *all* indicators are unavailable (FR-011).
- `bars_fetched == max(minimum_bars)` over the requested set (FR-010).

### `IndicatorName` (new enum)

`MM7`, `MM20`, `MM50`, `MM200`, `MM7_SLOPE`, `MM20_SLOPE`, `MM50_SLOPE`, `MM200_SLOPE`, `BOLLINGER`, `ATR`, `ADX`, `MACD0LAG`

Each maps in the registry to `(minimum_bars, callable)` — see research.md §6.

---

## Detection result

**`PatternHit`**

| Field | Type | Notes |
|---|---|---|
| `alert_type` | `AlertType` | **Existing** enum — same vocabulary as the scheduled scan (FR-014) |
| `direction` | `Direction \| None` | Existing enum |
| `data` | `dict[str, float]` | Supporting values, as the detectors return them |

**`DetectionResult`**

| Field | Type | Notes |
|---|---|---|
| `meta` | `ResponseMeta` | |
| `instrument` | `InstrumentRef` | |
| `hits` | `list[PatternHit]` | Empty list = "nothing fired", explicitly distinct from a failure (Story 3 scenario 3) |
| `evaluated` | `list[AlertType]` | What was actually checked — so an empty `hits` is interpretable. MUST cover all ten types the scheduled scan emits when the full set is requested (SC-006) |
| `failed` | `list[DetectorFailure]` | Detectors that raised, each with a reason |

**`DetectorFailure`**: `alert_type: AlertType`, `reason: str`.

Without `failed`, a detector that raised would simply drop out of `evaluated` with no explanation — the exact silent-omission failure mode FR-011 forbids on the indicator side. The two halves of the response now behave the same way: absence is always explained, never implied.

**Validation**: producing this MUST NOT write to any store (FR-003, SC-004). Never persisted.

---

## Stored context (read-only projections)

**`StoredAlert`** — projection of an existing `alerts` row.

| Field | Type | Notes |
|---|---|---|
| `code` / `description` | `str` | |
| `exchange` | `Exchange` | Explicit |
| `alert_types` | `list[AlertType]` | |
| `date` | `str` | |
| `data` | `dict[str, Any]` | The existing free-form map, passed through unchanged (it already carries `weekly_bar_date`, `timeframe`, slopes) |

**`DigestEntry`** — projection of an existing `alert_digests` item: `code`, `conviction` (`Conviction` enum), `rank`, `rationale`, plus the run's `summary`.

**`AssetContext`** — output of `get_watchlist` / `get_workflow_orders`.

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | |
| `in_watchlist` | `bool` | |
| `labels` | `list[str]` | Existing watchlist labels |
| `open_workflow_orders` | `list[dict]` | Projection of `workflow_orders` |

**Validation**: an asset in neither returns `in_watchlist=False` with empty lists — an explicit "not held / not watched", never an error (Story 4 scenario 3).

---

## Relationships

```text
search_asset ──> InstrumentRef ──┬──> BarSeries          (get_candles)
                                 ├──> IndicatorSnapshot  (get_indicators)
                                 └──> DetectionResult    (detect_patterns)

date ──> [StoredAlert] / DigestEntry     (get_alerts / get_digest)
code ──> AssetContext                    (get_watchlist / get_workflow_orders)

ResponseMeta ─ embedded in every market-derived response above
```

`InstrumentRef` is the join key: produced once by resolution, consumed by all three analysis capabilities. Stored-context reads are keyed by date or code and need no resolution, which is why they still work when the market connection is down.
