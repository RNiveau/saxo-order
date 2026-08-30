# Implementation Plan: Local MCP Server for Asset Analysis

**Branch**: `claude/local-mcp-asset-analysis-ek8xag` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/030-mcp-asset-analysis/spec.md`

> **Branch note**: the speckit scripts expect a `NNN-` branch name. Work stays on
> `claude/local-mcp-asset-analysis-ek8xag`; run the scripts with
> `SPECIFY_FEATURE=030-mcp-asset-analysis` so they resolve the feature directory without
> switching branches.

## Summary

Add a fourth entry point to the backend — alongside the CLI, the FastAPI app and the Lambda scan — that exposes the project's existing indicator, candle-building and detection logic to a locally running AI assistant over MCP stdio.

The server is a **thin orchestration layer** in the constitutional sense: it owns no calculation. Indicators come from `services/indicator_service.py`, bars from `services/candles_service.py`, stored context from `client/aws_client.py`. New code is limited to a tool surface, an indicator-depth registry, a detection orchestrator that does not persist, and response models.

Three findings from Phase 0 drive the design and are not optional:

1. **Errors must be raised as `ToolError`.** The SDK masks unhandled exceptions as `Error executing tool <name>`, withholding the message from the model. Without translation, FR-021 fails silently.
2. **stdout is the protocol wire.** `utils/logger.py` is already safe (stderr), but three `print()` calls in `client/saxo_client.py` — two on the rate-limiting path — are not.
3. **Provenance must come from a dedicated factory.** `get_saxo_client()` substitutes `MockSaxoClient` silently, which is exactly what FR-004a forbids.

## Technical Context

**Language/Version**: Python 3.12 (`pyproject.toml` declares `^3.12`)
**Primary Dependencies**: NEW — `mcp` (official Python SDK). Existing — `services/indicator_service.py`, `services/candles_service.py`, `client/saxo_client.py`, `client/aws_client.py` (`aioboto3`), `pydantic` v2
**Storage**: Read-only. Existing DynamoDB tables (`alerts`, `alert_digests`, `watchlist`, `workflow_orders`), unchanged schemas. No new table, no migration, no write path.
**Testing**: `pytest` + `pytest-asyncio` + `unittest.mock`, mirroring source structure under `tests/mcp_server/`
**Target Platform**: Local developer machine only — a stdio subprocess launched by an MCP client. Not deployed; out of scope for Lambda/Pulumi.
**Project Type**: Backend entry point (single). Frontend untouched.
**Performance Goals**: One state snapshot ≤ 2 tool calls and exactly 1 market-data fetch (SC-002); snapshot payload < 2,000 tokens, capped bar series < 3,000 (SC-007)
**Constraints**: Strictly read-only (FR-002); detection leaves the alert store byte-identical (SC-004); no simulated data without explicit per-request opt-in (FR-004a/b); nothing on the call path writes to stdout
**Scale/Scope**: Single user, single session, ~8 tools across 5 user stories. Story 5 (crypto venue) deferred to a later slice.

## Constitution Check

*Constitution v1.3.0. GATE: evaluated before Phase 0 and re-checked after Phase 1.*

| Principle | Assessment | Verdict |
|---|---|---|
| **I. Layered Architecture Discipline** | The MCP server is a new entry point peer to the CLI and API layers, and carries the same "NO business logic" obligation. Tools parse arguments, call services, shape responses. The indicator-depth registry and detection orchestrator live in `services/`, not in the tool modules. Clients are injected, never constructed inside a tool. No client internals are touched — stored context goes through `DynamoDBClient` methods, never `client.dynamodb.Table()`. | ✅ PASS |
| **II. Clean Code First** | Reuses existing functions rather than reimplementing any calculation. `UnitTime`, `Exchange`, `AlertType`, `Direction` used throughout — no string literals in tool signatures (they double as the JSON schema, so an enum is also the better contract). No `assert` in production code: the refusal gate and depth checks raise explicit exceptions. §9 of research.md records where abstraction was deliberately *not* added for Story 5. | ✅ PASS |
| **III. Configuration-Driven Design** | No new secret and no new config file. Reuses `Configuration` and the existing `config.yml` / `secrets.yml`. The bar cap, default bar count and rounding precision are constants in the server module rather than hardcoded at call sites. `.mcp.json` is committed (it holds a command, no credentials). | ✅ PASS |
| **IV. Safe Deployment Practices** | Local-only; no Pulumi, ECR or Lambda change. Conventional commits. | ✅ PASS |
| **V. Domain Model Integrity** | Candle ordering (index 0 = newest) preserved into the wire format and asserted in tests. Current-period reconstruction delegated to `CandlesService`, never re-derived. `Candle` objects used everywhere outside the client. Every asset-bearing response model carries an explicit `exchange` field; `country_code` is passed through and **never** used to infer the venue. | ✅ PASS |
| **Planning Requirement** | Spec reviewed and two clarifications answered by the owner before this plan. Implementation awaits approval of this plan. | ✅ PASS |

**Result: PASS, no violations.** Complexity Tracking omitted — nothing to justify.

One item is worth flagging as a judgement call rather than a violation: research.md §8 declines to refactor `run_detection_for_asset` into a shared pure core, even though that would be the tidier long-term shape, because it edits the live scheduled-scan path for a read-only feature's benefit. FR-005 (no divergence) still holds because both callers use the same `indicator_service` functions.

## Project Structure

### Documentation (this feature)

```text
specs/030-mcp-asset-analysis/
├── spec.md              # Phase -1 (/speckit.specify)
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── tools.md         # Phase 1 - MCP tool contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
mcp_server/                         # NEW - entry point layer, peer to saxo_order/ and api/
├── __init__.py
├── server.py                       # MCPServer instance, lifespan, main()
├── dependencies.py                 # Client factories + provenance; DynamoDB lifespan resource
├── errors.py                       # @tool_boundary: domain exception -> ToolError; refusal gate
├── formatters.py                   # Candle -> columnar payload, rounding, truncation
├── models.py                       # Pydantic response models (structured output)
└── tools/
    ├── __init__.py
    ├── assets.py                   # search_asset, get_candles
    ├── indicators.py               # get_indicators
    ├── detection.py                # detect_patterns
    └── context.py                  # get_alerts, get_digest, get_watchlist, get_workflow_orders

services/
├── indicator_bundle_service.py     # NEW - depth registry + isolated computation (FR-010/011/012)
└── detection_service.py            # NEW - side-effect-free detection (FR-003)

client/
└── saxo_client.py                  # MODIFIED - 3 print() -> logger (research.md §3)

tests/
├── mcp_server/
│   ├── test_errors.py              # ToolError translation, refusal gate
│   ├── test_formatters.py          # ordering, rounding, truncation
│   └── tools/
│       ├── test_assets.py
│       ├── test_indicators.py
│       ├── test_detection.py       # includes the "store unchanged" assertion
│       └── test_context.py
└── services/
    ├── test_indicator_bundle_service.py
    └── test_detection_service.py

.mcp.json                           # NEW - registers the server for this project
pyproject.toml                      # MODIFIED - mcp dependency; k-mcp script
```

**Structure Decision**: A top-level `mcp_server/` package, peer to `saxo_order/` (CLI) and `api/` (HTTP), because MCP is a fourth *entry point* — not a service and not a client. Constitution Principle I gives entry points one job: thin orchestration. Anything reusable by another entry point (the depth registry, the detection orchestrator) goes to `services/` instead, where the API could later expose it too.

## Implementation Phases

### Phase A — Foundation (blocks everything)

1. Add `mcp` to `pyproject.toml`; add the `k-mcp` script; commit `.mcp.json`.
2. `client/saxo_client.py`: replace the three `print()` calls with logger calls (research.md §3). Independently valuable; no behaviour change.
3. `mcp_server/dependencies.py`: market-client factory returning an explicit `(client, provenance)` pair — **not** `get_saxo_client()`. DynamoDB resource held for the server lifetime.
4. `mcp_server/errors.py`: the `@tool_boundary` decorator — translates domain exceptions to `ToolError`, and enforces the simulated-data refusal (FR-004a) so no individual tool can forget it.
5. `mcp_server/server.py` + `main()`: server boots, exposes zero tools, responds to a client.

### Phase B — User Story 1 (P1, MVP)

6. `search_asset` — `SaxoClient.search` via `asyncio.to_thread`, `exchange` explicit on every result.
7. `services/indicator_bundle_service.py` — the depth registry, single fetch at `max()`, per-indicator isolation with reasons.
8. `get_indicators` — bundle + provenance + `include` parameter.

**Ships alone as a usable MVP**: name → resolved instrument → full technical state.

### Phase C — User Stories 2 & 3 (P2, independent of each other)

9. `get_candles` — columnar payload, newest-first, in-progress flag, cap + truncation notice.
10. `services/detection_service.py` — detectors called directly, nothing persisted.
11. `detect_patterns` — plus the test that asserts the alert store is unchanged (SC-004).

### Phase D — User Story 4 (P3)

12. `get_alerts`, `get_digest`, `get_watchlist`, `get_workflow_orders` — read-only, degrading independently of the market-data tools.

### Phase E — Polish

13. `quickstart.md` verification pass; token-budget measurement against SC-007; full `black` / `isort` / `mypy` / `flake8` / `pytest` gate.

**Story 5 (crypto venue, P4) is out of this slice** — a later change implementing the market-data boundary for Ouinex.

## Risks

| Risk | Mitigation |
|---|---|
| An unhandled exception hides its message from the model, making failures undiagnosable | `@tool_boundary` on every tool; a test asserts `SaxoException` surfaces as a readable `ToolError` |
| Detection accidentally persists alerts, corrupting the triage digest | Separate orchestrator; `run_detection_for_asset` never imported; before/after store comparison in tests (SC-004) |
| Simulated data read as live | Provenance from a dedicated factory, required field on every market response, refusal in the shared decorator |
| Sync `SaxoClient` blocks the event loop, stalling concurrent tool calls | `asyncio.to_thread` at every client call site |
| Token expiry mid-session degrades to mock data | Factory resolves provenance per request, not once at startup, for the refusal check |
| Payloads blow the context budget | Columnar OHLC, rounding to 4dp, hard bar cap, measured against SC-007 in Phase E |

## Post-Design Constitution Re-check

Re-evaluated after data-model.md and contracts/tools.md: **still PASS**. The contracts introduce no calculation in the tool layer, every enum-valued field uses an existing enum, every asset-bearing model carries an explicit `exchange`, and no response model requires a new stored field.
