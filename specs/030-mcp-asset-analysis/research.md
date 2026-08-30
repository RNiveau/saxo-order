# Phase 0 Research: Local MCP Server for Asset Analysis

**Feature**: 030-mcp-asset-analysis
**Date**: 2026-08-30

---

## 1. MCP Python SDK — server shape

**Decision**: Use the official `mcp` package (`MCPServer` from `mcp.server`), decorator-registered tools, stdio transport via `mcp.run()` under a `if __name__ == "__main__":` guard, exposed as a `k-mcp` poetry script.

**Rationale**: Type hints *are* the tool schema — `def get_indicators(code: str, unit_time: UnitTime) -> IndicatorSnapshot` generates the JSON schema, parses the request and validates the response with no hand-written protocol code. Pydantic return annotations produce structured output automatically, which the project already has the vocabulary for (`api/models/`). Tool functions may be `async def`, which matters because the stored-context tools are `aioboto3`-based.

**Alternatives considered**:
- *HTTP proxy to the running FastAPI app* — ~30 lines and zero duplication, but requires `run_api.py` to be up before any analysis, and adds a hop for data the process could compute directly. Rejected as the primary design; retained as the fallback in §7.
- *Hand-rolled JSON-RPC over stdio* — no reason to reimplement the SDK.

**Sources**: [python-sdk README](https://github.com/modelcontextprotocol/python-sdk), [py.sdk.modelcontextprotocol.io](https://py.sdk.modelcontextprotocol.io/), [Running your server](https://py.sdk.modelcontextprotocol.io/run/)

---

## 2. Error reporting — `ToolError` is mandatory, not stylistic

**Decision**: Every tool boundary catches domain exceptions (`SaxoException`, `ValueError`, client errors) and re-raises them as `ToolError` with an actionable message. No domain exception is allowed to escape a tool function.

**Rationale**: This is the finding that most directly shapes the code. The SDK logs an unhandled exception once at ERROR with its traceback and sends the client only `Error executing tool <name>` — **the exception message is withheld from the model**. So letting `SaxoException("Missing candles to calcule the ma")` propagate would give the assistant a blank wall, directly violating FR-021. `ToolError` messages *are* forwarded to the client and logged at INFO without a traceback.

**Consequence**: FR-021 is satisfied by a deliberate translation layer, not by default behaviour. A single decorator around each tool keeps this from being repeated by hand.

**Alternatives considered**: returning `CallToolResult(isError=True)` — more control than needed here; `ToolError` covers every case in this feature.

**Sources**: [python-sdk issue #2153](https://github.com/modelcontextprotocol/python-sdk/issues/2153), [Building Servers](https://py.sdk.modelcontextprotocol.io/server/)

---

## 3. stdout is the protocol wire

**Decision**: Nothing in the server's call path may write to stdout. Replace the three `print()` calls in `client/saxo_client.py` with logger calls.

**Rationale**: Under stdio transport, stdout carries the JSON-RPC frames. Two findings, one reassuring and one not:

- ✅ **`utils/logger.py` is safe.** `logging.StreamHandler()` with no argument defaults to **stderr**, so every existing `Logger.get_logger(...)` call is already clear of the wire. No change needed.
- ⚠️ **`client/saxo_client.py` is not.** Three bare `print()` calls go to stdout:
  - `saxo_client.py:263` — "Market is closed, price is set to 1"
  - `saxo_client.py:595` — `Rate limiting: ${response.headers}`
  - `saxo_client.py:614` — `Rate limiting: wait {wait_time}`

  The rate-limiting pair is the dangerous one: a long analysis session is exactly the workload that trips it, so this fires precisely when the server is busiest. The SDK does divert flushed stdout to stderr while serving, but depending on that safety net for a foreseeable, frequent path is not acceptable — and these should have been logger calls regardless.

**Consequence**: A small, independently valuable cleanup lands as a prerequisite task. It is a strict improvement to the existing client (the CLI gets proper log levels for free) and touches no behaviour.

---

## 4. Sync client inside an async server

**Decision**: Wrap `SaxoClient` calls in `asyncio.to_thread(...)`. Never call the sync client directly from an `async def` tool.

**Rationale**: `SaxoClient` is `requests`-based and synchronous; `DynamoDBClient` is `aioboto3`-based and async; MCP tools run on one event loop. Calling the sync client inline blocks the loop for the duration of a network round-trip, stalling every other in-flight tool call — including the token refresh. `asyncio.to_thread` is the minimal correct bridge and needs no new dependency.

**Alternatives considered**: making all tools `def` rather than `async def` (the SDK would run them in a worker thread) — but the DynamoDB tools genuinely need the loop, and a mixed sync/async tool set is harder to reason about than one bridge point.

---

## 5. Provenance and the refusal gate (FR-004a / FR-004b)

**Decision**: The server resolves its market client **per request** through a dedicated factory that returns an explicit `(client, provenance)` pair, and refuses at the tool boundary when provenance is simulated and the request did not opt in.

**Rationale**: `api/dependencies.py:35` (`get_saxo_client`) silently substitutes `MockSaxoClient` on a missing token *and* on any initialisation exception, returning a bare client with the substitution recorded only in a log line. That is the exact failure the spec forbids, so this feature cannot reuse it as-is — the caller must be told which client it got. A separate factory keeps the API's behaviour untouched while giving the MCP server an honest signal.

**Consequence**: `provenance` is a required field on every market-derived response model (FR-004), and the refusal is a guard in the shared tool decorator (FR-004a), so no individual tool can forget it. `allow_simulated: bool = False` is a per-request parameter, never server state (FR-004b).

**Per request, not once at startup** — an earlier draft of this section said startup, which contradicted plan.md and, more importantly, the spec's own edge case: *"an access token expiring mid-session MUST be refreshed, or the affected request refused"*. A provenance resolved once at boot cannot notice a token that dies an hour into the session, so the refusal gate would pass while the data underneath had turned simulated. Provenance is therefore evaluated on every market-derived call.

**Consequence**: the new factory MUST NOT carry `get_saxo_client`'s `@lru_cache()`. Caching the client is what makes startup-time resolution sticky; the cache is exactly the bug here.

**Alternatives considered**: refusing at construction time (server won't start without a token) — too blunt; the stored-context tools (Story 4) do not need market data and should still work.

---

## 6. Indicator depth registry (FR-010 / FR-011 / FR-012)

**Decision**: A declarative registry maps each indicator to `(minimum_bars, compute_callable)`. The tool computes `max(minimum_bars)` over the *requested* indicators, fetches once at that depth, then computes each in an isolated `try/except`.

**Rationale**: This is the single design element that satisfies three requirements at once, and the depth spread is far wider than it looks:

| Indicator | Minimum bars | Source |
|---|---|---|
| `mobile_average(7)` | 7 | `indicator_service.py:96` |
| `bollinger_bands` | period-dependent (~20) | `indicator_service.py:82` |
| `average_true_range` | ~15 | `indicator_service.py:667` |
| `adx` | ~2×period | `indicator_service.py:708` |
| `mobile_average(200)` | 200 | `indicator_service.py:96` |
| **`macd0lag`** | **235** | `indicator_service.py:577` (guard); formula `signal*9 + long*6 - 2` |

A naive "fetch enough for everything" makes a 7-bar question cost a 235-bar fetch; a naive "fetch per indicator" makes six network calls. The registry gives one fetch sized to the actual request, which is what SC-002 measures.

Isolation matters because these raise rather than return `None` (`mobile_average` raises `SaxoException` at line 101; `macd0lag` at line 578). The pattern to generalise already exists at `api/services/indicator_service.py:260`, which catches per-MA and only fails when nothing computed — extend it to every indicator and record the reason.

**Alternatives considered**: computing everything always and dropping failures silently — loses the "why", which SC-003 requires.

---

## 7. Reaching DynamoDB from a long-lived process

**Decision**: Open one `aioboto3` resource for the server's lifetime and hold a single `DynamoDBClient` on it; degrade the four stored-context tools individually when credentials are absent.

**Rationale**: `DynamoDBClient.__init__` accepts a resource and `_get_table` raises `RuntimeError` without one ("Use it within a FastAPI lifespan or via run_async"). The existing `create_dynamodb_client()` in `saxo_order/async_utils.py` is an `asynccontextmanager` built for a single CLI invocation — using it per tool call would open and close a resource on every request. The server needs the lifespan shape instead.

Two operability notes worth stating before implementation:
- `AwsClient.is_aws_context()` (`client/aws_client.py:110`) returns true only when `AWS_LAMBDA_FUNCTION_NAME` or `AWS_PROFILE` is set. Locally, **`AWS_PROFILE` must be exported** or the stored-context tools cannot work. This belongs in `quickstart.md`, not in a runtime surprise.
- Per the spec's edge cases, an unreachable store must not break the market-data tools. The two capability groups fail independently.

---

## 8. Detection without the write (FR-003)

**Decision**: A new `services/` orchestrator calls the detector functions directly. `run_detection_for_asset` is not reused, not refactored, and not imported.

**Rationale**: `saxo_order/commands/alerting.py:205` is the obvious reuse candidate and the wrong one: it builds candles, runs detectors, *and* persists via `store_alerts`. Analysis would then write alert rows as a side effect, polluting the next triage digest — the exact thing SC-004 tests by comparing the store before and after.

Extracting a shared pure core out of `run_detection_for_asset` and having both callers use it would be the tidier long-term shape, but it edits the live scheduled-scan path for a read-only feature's benefit. Deferred deliberately: the new orchestrator calls the same `indicator_service` functions, so results cannot diverge (FR-005), and no scanning behaviour is touched.

**Alternatives considered**: passing a `dry_run` flag into the existing function — a boolean that switches off a side effect is precisely the kind of trap that gets flipped by accident later.

---

## 9. Story 5 (crypto venue) — deferred, not designed away

**Decision**: Define a narrow internal market-data boundary (resolve → bar series) that the Saxo path implements now and the Ouinex path implements later. Do not build an abstraction layer beyond that.

**Rationale**: The constitution forbids speculative abstraction (Principle II.2), and the spec makes Story 5 P4. But the analysis half is genuinely venue-agnostic once bars exist, so the seam belongs where bars are produced. One narrow boundary is not over-engineering; a plugin registry for one implementation would be.

---

## Resolved unknowns

| Unknown | Resolution |
|---|---|
| MCP SDK server class and entry point | `MCPServer` from `mcp.server`, `mcp.run()` under a `__main__` guard |
| Do tool errors reach the model? | Only via `ToolError` — unhandled exceptions are masked (§2) |
| Does existing logging corrupt stdio? | No — `StreamHandler` defaults to stderr. But three `print()` calls in `saxo_client.py` do (§3) |
| Sync/async bridge | `asyncio.to_thread` for `SaxoClient` (§4) |
| How to know data is simulated | Dedicated factory returning `(client, provenance)`; not `get_saxo_client` (§5) |
| Fetch depth | `max()` over the requested indicators' declared minimums (§6) |
| DynamoDB in a long-lived process | One resource for the server lifetime; `AWS_PROFILE` required locally (§7) |
| Detection without persistence | New orchestrator; do not touch `run_detection_for_asset` (§8) |

---

## 10. Which candle path is canonical (added after review of PR #716)

**Decision**: The scheduled scan's reconstruction is canonical. Extract `_build_candles` from `saxo_order/commands/alerting.py` into `services/`, parameterised by `asset_type` and `Market`, and have both the scan and the MCP server call it.

**Rationale**: The first draft said bars "come from `CandlesService`, never re-derived". That is wrong on two counts.

**It is not what the scan does.** `alerting._build_candles` (`alerting.py:721`) fetches daily directly — `horizon=1440, count=250` — then tops up today from `horizon=60, count=10` via `build_daily_candles_from_h1`. `CandlesService.build_candles` is a different algorithm: it needs a `code` and a `Market`, calls `get_asset(code)`, and rebuilds the daily series from **30m** bars. FR-005 and SC-006 promise on-demand results match the scan; they can only match if the same reconstruction produces them.

**It is far more expensive.** For the 235 daily bars `macd0lag` requires, `build_candles` computes `trading_days=235` → `calendar_days ≈ 335` → `nbr_30m ≈ 16,080` (`candles_service.py:270-280`). `get_historical_data` caps each HTTP request at `max_items = 1200` and paginates (`saxo_client.py:520`), so one call becomes **~13 round-trips** — on precisely the rate-limiting path §3 flags. The scan's path costs two requests.

**Why extract rather than reimplement**: FR-005 forbids reimplementing candle-building, and a copy in `services/` would be exactly that — two implementations free to drift. This is a different situation from §8: `run_detection_for_asset` is entangled with persistence, so reusing it means inheriting a side effect, whereas `_build_candles` is a side-effect-free helper whose move is mechanical and leaves scan behaviour identical.

**Open sub-decision — `Market` for an arbitrary instrument.** The scan hardcodes `EUMarket()` because it only sweeps French stocks. This server resolves anything, and the quickstart's own example is an index. `model/market.py` offers `USMarket`, `EUMarket`, `DaxCfdMarket`, `EuCfdMarket`. The top-up path is the only consumer, so: default to `EUMarket`, accept an explicit `market` override on the market-data tools, and **skip the current-period top-up rather than guess** when the instrument's market cannot be determined — reporting `current_incomplete = False` honestly instead of assembling today's bar against the wrong session hours.

**Corroboration from the code itself** (noticed during PR review, after this section was written): `_build_weekly_candles`'s docstring (`alerting.py:762-766`) already makes the same argument on the same grounds — *"This is deliberately not CandlesService.build_weekly_candles … that path re-resolves the asset and fetches its own daily candles for the forming week, three requests per asset where this is one."* This section reached its conclusion independently and agrees with reasoning the scan's author had already recorded. T007 preserves that docstring on the move.

**Consequence for SC-002**: "exactly one market-data fetch" was unachievable — daily-with-today needs two series by construction, and one `get_historical_data` call is itself N HTTP requests. Restated as *at most two provider series fetches*. `bars_fetched` remains useful as the depth actually requested, but it is not a request count.
