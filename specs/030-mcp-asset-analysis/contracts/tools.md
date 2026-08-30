# Tool Contracts: Local MCP Server for Asset Analysis

**Feature**: 030-mcp-asset-analysis | **Date**: 2026-08-30

The MCP tool surface *is* this feature's API — there are no HTTP endpoints. Type annotations generate the JSON schema, so signatures below are the contract. Enum-typed parameters are deliberate: they constrain the schema the client sees, which is better than validating a free string (Constitution II.3).

**Universal rules** (enforced by `@tool_boundary`, not per tool):

- Domain exceptions are translated to `ToolError`. Nothing propagates unhandled — the SDK would mask the message (research.md §2).
- Market-derived tools refuse when provenance is `SIMULATED` and `allow_simulated` is false (FR-004a).
- `allow_simulated: bool = False` is per request and never remembered (FR-004b).
- Every market-derived response embeds `ResponseMeta` with provenance, exchange, unit time and `last_bar_date` (FR-004, FR-019).
- No tool writes anything (FR-002).
- **`asset_type` is required on every market-data tool.** `SaxoClient.get_historical_data(saxo_uic, asset_type, horizon, count, ...)` (`saxo_client.py:486`) has no default for it. The scan gets away with hardcoding `AssetType.STOCK` (`alerting.py:722`) because it only sweeps stocks; this server resolves arbitrary instruments — the quickstart's own example is an index — so the caller must pass back the `asset_type` that `search_asset` returned.
- **`market` is optional and defaults to `EUMarket`.** It is consumed only by the current-period top-up. When the instrument's market cannot be determined, the top-up is **skipped** and `current_incomplete` reports `False` — an honest omission rather than today's bar assembled against the wrong session hours (research.md §10).
- The identifier parameter is named `instrument_id`, not `saxo_uic`: these tools are venue-generic (`exchange` is a parameter, and Story 5 adds a second venue), so a venue-specific name would either mislead or force a wire-contract break later.

---

## `search_asset`

```python
async def search_asset(
    query: str,
    exchange: Exchange = Exchange.SAXO,
) -> list[InstrumentRef]
```

`InstrumentRef` is the input identity for every other market-data tool: it carries `instrument_id`, `asset_type` **and** `exchange`, all three of which the downstream calls need.

Resolve a free-text name or symbol to candidate instruments (FR-006).

| Case | Behaviour |
|---|---|
| No match | Empty list — a normal result, not an error. **Implementation note**: `SaxoClient.search` raises `SaxoException(f"Nothing found for {keyword}")` on zero results (`saxo_client.py:125`) — it never returns `[]`. This case must be caught explicitly *before* `@tool_boundary` turns it into a `ToolError`, or "no match" and "venue unreachable" become indistinguishable without matching on the message text |
| Candidate without `instrument_id` | Returned with `unavailable_reason`, not dropped |
| `exchange` not covered by this version | `ToolError`: "exchange not supported", distinct from "not found" (FR-008a) |
| Venue unreachable | `ToolError` naming the failure, distinct from "no match" |

---

## `get_candles`

```python
async def get_candles(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime = UnitTime.D,
    count: int = 100,
    exchange: Exchange = Exchange.SAXO,
    market: MarketName | None = None,
    allow_simulated: bool = False,
) -> BarSeries
```

Recent bars, newest-first, including the reconstructed in-progress period (FR-007).

| Case | Behaviour |
|---|---|
| `count` > hard cap | Capped; `meta.truncated = True` (FR-008) |
| Market undeterminable | Top-up skipped, `current_incomplete = False`, no guessed bar |
| Current period in progress | Present at row 0, `current_incomplete = True` |
| `unit_time` unsupported | `ToolError` listing supported values |
| No history | Empty `rows`, `count = 0` — not an error |

---

## `get_indicators`

```python
async def get_indicators(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime = UnitTime.D,
    include: list[IndicatorName] | None = None,
    exchange: Exchange = Exchange.SAXO,
    market: MarketName | None = None,
    allow_simulated: bool = False,
) -> IndicatorSnapshot
```

The bundled state snapshot — the tool the assistant reaches for first (FR-009).

`include=None` means the default set. Fetch depth is `max(minimum_bars)` over the **requested** indicators only, so a shallow request does not pay the 235-bar MACD cost (FR-010, FR-012).

| Case | Behaviour |
|---|---|
| Some indicators lack history | Those carry `unavailable_reason`; the rest return values. **Success**, not an error (FR-011, SC-003) |
| *All* indicators lack history | `ToolError` naming bars available vs. the shallowest requirement |
| `include=[]` | `ToolError` — an empty request is a caller mistake, not an empty answer |

**Invariant**: `len(response.indicators) == len(requested)`. Always.

---

## `detect_patterns`

```python
async def detect_patterns(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime = UnitTime.D,
    exchange: Exchange = Exchange.SAXO,
    market: MarketName | None = None,
    allow_simulated: bool = False,
) -> DetectionResult
```

Runs the project's own detectors on demand (FR-013), reporting hits in the existing `AlertType` / `Direction` vocabulary (FR-014).

| Case | Behaviour |
|---|---|
| Nothing fires | `hits = []` with `evaluated` populated — explicitly distinct from failure |
| Called repeatedly | **The alert store is byte-identical afterwards** (FR-003, SC-004) |
| One detector raises | It appears in `failed` with a reason; the others still return. **Not** silently dropped from `evaluated` |

**Prohibition**: this tool's implementation must not import `run_detection_for_asset` — it persists alerts (research.md §8).

---

## `get_alerts`

```python
async def get_alerts(
    date: str | None = None,
    code: str | None = None,
) -> list[StoredAlert]
```

Read stored alerts, defaulting to the current run date (FR-015). `data` is passed through unchanged so recorded slopes, `weekly_bar_date` and `timeframe` stay readable.

| Case | Behaviour |
|---|---|
| No alerts for the date | Empty list — not an error |
| Store unreachable | `ToolError` naming the cause. **Market-data tools are unaffected** |

---

## `get_digest`

```python
async def get_digest(date: str | None = None) -> DigestEntry | None
```

The stored triage digest for a date: ranked assets, conviction, rationale (FR-016). `None` when no digest was produced — distinct from a failure.

---

## `get_watchlist` / `get_workflow_orders`

```python
async def get_watchlist(code: str | None = None) -> list[AssetContext]
async def get_workflow_orders(code: str | None = None) -> list[AssetContext]
```

The analyst's own relationship to an asset — labels and open exposure (FR-017).

| Case | Behaviour |
|---|---|
| Asset in neither | `in_watchlist = False`, empty lists — explicit, never an error |
| `code=None` | Everything, for a portfolio-level view |

---

## Server registration (`.mcp.json`)

```json
{
  "mcpServers": {
    "saxo-analysis": {
      "command": "poetry",
      "args": ["run", "k-mcp"]
    }
  }
}
```

Committed to the repo: it holds a command, no credentials. Credentials continue to come from `config.yml` / `secrets.yml` (Constitution III).

---

## Tool count and shape

Eight tools across five stories. Deliberately coarse: one indicator call returns the whole bundle rather than one call per indicator, because the expensive shared cost is the market fetch, not the arithmetic — and six round-trips would cost six fetches of the same series (SC-002).

`get_alerts`/`get_digest` and `get_watchlist`/`get_workflow_orders` stay split despite both being "stored context": they are keyed differently (date vs. code) and answer different questions (why did this fire vs. do I already hold it).
