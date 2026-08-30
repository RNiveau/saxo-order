# Feature Specification: Local MCP Server for Asset Analysis

**Feature Branch**: `030-mcp-asset-analysis`
**Created**: 2026-08-30
**Status**: Draft
**Input**: User description: "Local MCP server for asset analysis: a read-only stdio MCP server exposing search_asset, get_candles, get_indicators, detect_patterns, get_alerts/get_digest and get_watchlist/get_workflows over the existing indicator and candle services, with declared data source and token-efficient payloads."

## Context

Analysis logic in this project is currently reachable three ways: the CLI (`k-order`), the web API/frontend, and the scheduled Lambda scan. None of them is usable by an AI assistant working in the repository. To answer "what does this asset look like right now?", the assistant has to re-derive the plumbing every session and write a throwaway script against the Saxo client — slow, error-prone, and easy to get subtly wrong (missing today's candle, wrong `saxo_uic`, mock data mistaken for live data).

This feature adds a fourth entry point aimed at that consumer: a local, read-only analysis surface that exposes the existing indicators and candle building over the Model Context Protocol, so an assistant can inspect an asset conversationally.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Look up an asset and read its current state (Priority: P1)

The analyst asks their assistant about an asset by its human name ("Air Liquide", "the DAX"). The assistant resolves it to a tradeable instrument, then retrieves that instrument's current technical state — moving averages and their slopes, Bollinger bands, volatility and trend strength, last price and variation — in a single step, and explains it.

**Why this priority**: This is the minimum viable slice. Resolution plus a state snapshot answers the most common question ("where is this thing?") and everything else builds on the identifiers resolution produces. Shipped alone, it already removes the throwaway-script workflow.

**Independent Test**: Ask the assistant for the state of a known asset by name only; verify it returns the correct instrument and indicator values matching those shown by the existing web UI for the same asset and period.

**Acceptance Scenarios**:

1. **Given** an asset name that matches several instruments, **When** the analyst asks about it, **Then** the candidate instruments are returned with enough detail (description, symbol, identifier, type, exchange) to choose between them.
2. **Given** a resolved instrument with full history, **When** its current state is requested for a period, **Then** all supported indicators are returned in one response, together with the period and the timestamp of the most recent bar used.
3. **Given** an instrument with only 80 bars of history, **When** its current state is requested, **Then** the indicators that can be computed are returned and each one that cannot is reported as unavailable **with the reason** (bars required vs. bars available) — the response is not an error.
4. **Given** the underlying market connection is unavailable and simulated data would be substituted, **When** any state is requested, **Then** the response declares that its data is simulated.

---

### User Story 2 - Inspect the bars behind an indicator (Priority: P2)

Having seen the summary, the analyst asks the assistant to look at the actual price action — "did it gap or grind?", "what happened the day the average was crossed?" The assistant retrieves the recent bars for the instrument and period and reasons over them.

**Why this priority**: Indicators are lossy. Without the underlying bars the assistant can describe the numbers but cannot corroborate them, and the analyst has to open a chart anyway. Valuable, but useless before Story 1 exists.

**Independent Test**: Request recent bars for a known instrument and confirm they match the same instrument's chart, including the in-progress current period.

**Acceptance Scenarios**:

1. **Given** a resolved instrument, **When** recent bars are requested, **Then** they are returned newest-first with their dates, capped at a documented maximum.
2. **Given** the current trading day or hour is still in progress, **When** daily or hourly bars are requested, **Then** the in-progress period is present and flagged as incomplete.
3. **Given** more bars are requested than the cap allows, **When** the request is made, **Then** the cap is applied and the response states that the result was truncated.

---

### User Story 3 - Run the project's own setup detection on demand (Priority: P2)

The analyst asks whether an asset is showing any of the setups the project scans for. The assistant runs the same detections the scheduled scan uses and reports which fired, in which direction, and the numbers behind each.

**Why this priority**: This is where the project's edge lives — these are the analyst's rules, not generic indicators. Equal in value to Story 2 but riskier, because the existing detection entry point has a side effect that must not be inherited.

**Independent Test**: Run detection on an asset known to have triggered an alert in the scheduled scan and confirm the same setups are reported; then confirm the alerts store is unchanged afterwards.

**Acceptance Scenarios**:

1. **Given** an instrument currently showing a known setup, **When** detection is requested, **Then** that setup is reported with its direction and supporting values.
2. **Given** detection is requested any number of times, **When** it completes, **Then** **no alert is written to storage** and no other persistent state changes.
3. **Given** an instrument showing no setups, **When** detection is requested, **Then** an explicit empty result is returned, distinguishable from a failure.

---

### User Story 4 - Explain a past alert and situate it against current exposure (Priority: P3)

The morning digest flagged an asset. The analyst asks why. The assistant retrieves the stored alert and digest entry for that date, compares them against the asset's state today, and reports whether the analyst already holds exposure or has the asset labelled in the watchlist.

**Why this priority**: Turns the tool from a measuring instrument into a decision aid, and makes threshold tuning possible ("this fired but decayed within a day"). Depends on Stories 1 and 3 to be meaningful.

**Independent Test**: Pick a date with stored alerts, ask why a named asset was flagged, and confirm the answer cites the stored alert data and the asset's watchlist labels and open workflow orders.

**Acceptance Scenarios**:

1. **Given** stored alerts for a date, **When** they are requested, **Then** each alert's type, direction, date and recorded supporting data are returned.
2. **Given** a triage digest exists for a date, **When** it is requested, **Then** its ranked assets, conviction levels and rationales are returned.
3. **Given** an asset present in the watchlist, **When** its context is requested, **Then** its labels and any open workflow orders are returned; **and given** it is absent, an explicit "not held / not watched" result is returned rather than an error.

---

### Edge Cases

- **Simulated data substituted silently**: the market connection falls back to simulated data when no valid credential is present. Every response MUST declare which source produced it, so simulated bars are never read as live ones.
- **Insufficient history**: indicators have very different history requirements (a 7-period average needs 7 bars; the lag-reduced MACD needs several hundred). One unsatisfiable indicator MUST NOT void the whole response.
- **Instrument cannot be resolved**: a name matching nothing, or matching an instrument with no market identifier, returns a clear "not resolvable" result naming what was missing.
- **No country code**: an instrument legitimately has no country/market code. This MUST NOT be treated as an error, nor as an implicit signal about which exchange the instrument belongs to.
- **Market data provider unavailable or rate-limited**: the response reports the failure as such, distinct from "no data" and from "indicator not computable".
- **Credentials absent for stored data**: when the alert/watchlist store cannot be reached, the market-data capabilities MUST still work; the affected results report their own unavailability.
- **Requested period unsupported for an instrument**: reported explicitly, listing the periods that are supported.
- **Long-running session**: the server runs for the lifetime of an assistant session; an access token expiring mid-session MUST be refreshed or reported, not silently degraded to simulated data.

## Requirements *(mandatory)*

### Functional Requirements

#### Surface and safety

- **FR-001**: The system MUST expose asset-analysis capabilities to a locally running AI assistant over the Model Context Protocol, started as a local process with no network listener.
- **FR-002**: The system MUST be strictly read-only with respect to the analyst's money and records: it MUST NOT expose order creation, modification or cancellation, and MUST NOT write to any persistent store.
- **FR-003**: The system MUST NOT reuse any existing routine that persists alerts as a side effect of detection; on-demand detection MUST be side-effect free (see FR-002).
- **FR-004**: Every response returning market-derived data MUST declare its data source, distinguishing live market data from simulated data.
- **FR-005**: The system MUST reuse the project's existing indicator, detection and candle-building logic rather than reimplementing any calculation, so that on-demand results and scheduled-scan results cannot diverge.

#### Resolution and market data

- **FR-006**: Users MUST be able to resolve an instrument from a free-text name or symbol, receiving for each candidate its description, symbol, market identifier, instrument type and exchange.
- **FR-007**: The system MUST return recent bars for a resolved instrument and period, ordered newest-first, including the in-progress current period reconstructed as the project already does for daily and hourly data, with incomplete periods flagged.
- **FR-008**: The system MUST cap the number of bars returned in a single response and state when a result was truncated.

#### Indicators

- **FR-009**: The system MUST return, in a single response for a given instrument and period, the project's supported indicator set: moving averages over the standard periods and their slopes, Bollinger bands including flatness, average true range, trend strength, the lag-reduced MACD and its signal, last price, and variation against the previous period's close.
- **FR-010**: The system MUST fetch the underlying bars **once** per indicator request, at the greatest history depth required by the indicators actually requested.
- **FR-011**: The system MUST isolate each indicator's failure: an indicator that cannot be computed is reported as unavailable with a reason, while all others are returned normally. A response is only a failure when **no** indicator could be computed.
- **FR-012**: Users MUST be able to restrict an indicator request to a subset of indicators, so a shallow request does not incur the deepest indicator's history cost.

#### Detection

- **FR-013**: The system MUST run the project's setup detections on demand for a resolved instrument and period, reporting for each whether it fired, in which direction, and the values supporting it.
- **FR-014**: The system MUST express detection results using the project's existing setup and direction vocabulary, not ad-hoc labels.

#### Stored context

- **FR-015**: Users MUST be able to read stored alerts for a given date and asset, including each alert's recorded supporting data.
- **FR-016**: Users MUST be able to read a stored triage digest for a given date, including ranked assets, conviction and rationale.
- **FR-017**: Users MUST be able to read an asset's watchlist entry (including its labels) and its open workflow orders, with an explicit result when the asset is in neither.

#### Payload economy

- **FR-018**: Responses MUST be economical for a language-model consumer: numeric values rounded to a sensible precision, bar series returned in a compact form, and no field repeated per row that could be stated once.
- **FR-019**: Each response MUST carry the instrument, the period, and the timestamp of the most recent bar used, so results are never ambiguous about what and when they describe.

#### Operability

- **FR-020**: The system MUST be startable with a single documented command and require no service (web API, database emulator) to be running beyond the credentials the CLI already uses.
- **FR-021**: Failures MUST be returned to the assistant as structured, readable results explaining what failed and why — never as an opaque crash or an empty success.

### Key Entities

- **Instrument reference**: the resolved identity of a tradeable asset — description, symbol, market identifier, instrument type, exchange, optional country/market code. Produced by resolution, consumed by every other capability.
- **Bar series**: an ordered, newest-first sequence of price bars for an instrument and period, each with date, open, high, low, close, and a flag for an in-progress period.
- **Indicator snapshot**: the computed technical state of an instrument for a period at a point in time, including per-indicator availability and reason-for-absence.
- **Detection result**: which of the project's setups fired for an instrument and period, with direction and supporting values. Transient — never persisted.
- **Stored alert / digest entry**: existing records of what the scheduled scan and triage produced on a past date. Read-only here.
- **Asset context**: the analyst's own relationship to an asset — watchlist labels and open workflow orders. Read-only here.
- **Data provenance**: the declared origin (live vs. simulated) attached to every market-derived response.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The analyst can go from an asset's plain name to a complete, explained technical state in **one exchange** with the assistant, with no script written and no file read.
- **SC-002**: A full state snapshot for one asset costs **at most 2 retrieval steps** (resolve, then snapshot) and **exactly one** market-data fetch.
- **SC-003**: For an asset with fewer bars than the deepest indicator requires, the response still returns **every** indicator that the available history supports, and names the reason for each one it does not.
- **SC-004**: Running on-demand detection any number of times leaves the stored alert record **byte-identical** — verified by comparing the store before and after.
- **SC-005**: **100%** of market-derived responses state whether their data is live or simulated; a reviewer can determine provenance without inspecting logs.
- **SC-006**: On-demand results for a given asset, period and date **match** what the scheduled scan produced for the same inputs, since both run the same logic.
- **SC-007**: A full state snapshot for one asset consumes **under 2,000 tokens** of the assistant's context, and a capped bar series **under 3,000**.
- **SC-008**: The analyst can determine why a past alert fired, and whether they already hold the asset, **without opening the web UI**.

## Assumptions

- The consumer is an AI assistant running locally on the analyst's machine on their behalf; there is no multi-user, authentication or authorisation dimension to this feature.
- Configuration and credentials are the ones the CLI already uses; this feature introduces no new secret and no new stored configuration.
- Stored-data capabilities (alerts, digests, watchlist, workflow orders) are read from the existing tables with their current schemas. No table, field or migration is introduced.
- Supported periods are those the project's indicators already support; this feature adds no new timeframe.
- The bar cap defaults to roughly 100 bars, adjustable per request up to a hard ceiling.
- Indicator values are rounded to 4 decimal places, consistent with what the existing API already returns.
- This feature is not deployed: it runs locally only and is out of scope for the Lambda/Pulumi deployment path.
- Frontend and web API are untouched.

## Out of Scope

- Any write operation: placing, amending or cancelling orders; creating alerts, workflows or watchlist entries.
- Remote or shared hosting of this server; multi-user access.
- New indicators, new setups, or changes to existing thresholds.
- Fundamental data, news, or broker account/position reporting.
- Replacing or altering the scheduled scan, the triage digest, or the web UI.

## Clarifications Needed

- **Q1 (scope)**: Which exchanges must the first version cover? [NEEDS CLARIFICATION: Saxo only, or also Binance/Ouinex crypto instruments from the outset?]
- **Q2 (safety)**: When only simulated data is available, should analysis capabilities **refuse** to answer, or answer while clearly labelling the data as simulated? [NEEDS CLARIFICATION: refuse-by-default vs. label-and-proceed]
