# Phase 0 Research: Alert Triage & Synthesis Agent

All Technical Context items were resolvable from the existing codebase and prior design discussion; there are no open `NEEDS CLARIFICATION` markers. This document records the decisions and the alternatives weighed.

## R1. Reasoning model

- **Decision**: `claude-sonnet-5`, set in `config.yml` as `anthropic_model`, overridable without code change.
- **Rationale**: The task runs once per day over a small structured payload (~20–40 assets, no candle arrays), so cost and latency are negligible for any model. The value of the feature is judgment quality — confluence weighting, trend alignment, and separating signal from noise in a rationale a trader will trust. At once-daily cadence a higher-capability model is effectively free, and a weak brief is worse than none because trust erodes.
- **Alternatives considered**: `claude-haiku-4-5` — right choice only if this were high-volume or latency-critical (it is neither); kept reachable via config for A/B comparison and downgrade.

## R2. Anthropic access as a dedicated Client Layer member

- **Decision**: New `client/anthropic_client.py` exposing `AnthropicClient(configuration)` with a single public method `complete_json(system, user_payload) -> dict`. The `anthropic` SDK is imported **only** here. Failures raise a new `AnthropicException` (in `utils/exception.py`, mirroring `SaxoException`).
- **Rationale**: Constitution Principle I requires external integrations to live in the Client Layer and services to depend on client **methods**, not SDK internals. This mirrors `SaxoClient`/`GSheetClient`: constructed from `Configuration`, owns retries/backoff/logging, returns parsed domain data. Keeps the triage service testable by mocking one method rather than the SDK.
- **Alternatives considered**: Instantiating the SDK inside `TriageAgent` — rejected, violates layering and couples the service to the vendor SDK.

## R3. Structured JSON output from the model

- **Decision**: `complete_json` sends a system prompt describing the ranking rules and a user payload of per-asset facts, instructs a strict JSON schema, extracts the JSON from the response, and `json.loads` it. Invalid/ò unparseable output raises `AnthropicException`; the service treats that as a fallback trigger.
- **Rationale**: Deterministic downstream formatting requires structured output. Parsing/validation belongs in the boundary (client returns a `dict`; service validates shape into `TriagedAsset`s). Any parse failure is funneled into the same fallback path as a transport failure — one recovery path (FR-011).
- **Alternatives considered**: Free-form text posted directly to Slack — rejected, not parseable, not storable as structured history, not reconcilable against detected alerts (FR-018).

## R4. Persistence — `alert_digests` table

- **Decision**: New DynamoDB table `alert_digests`, `hash_key="run_date"` (String, `YYYY-MM-DD`), `range_key="created_at"` (Number, epoch seconds), `PAY_PER_REQUEST`, streams on, **no TTL**. Defined in `pulumi/dynamodb.py` and registered in `pulumi/__main__.py` (instantiate + IAM grant + export), mirroring `workflow_orders_table()`.
- **Rationale**: Run date is the natural key; the range key retains multiple same-day runs distinctly and orders by run time (FR-010). No TTL is deliberate — history must outlive the 7-day raw-alert expiry so "was the agent right?" review is possible (FR-009, SC-006). `Query` by `run_date` fetches a single day; `Scan` (small table, one item/day) lists history.
- **Alternatives considered**: (a) Annotating each existing `alert.data` with triage info — rejected: dies with the alerts' 7-day TTL, no cross-run digest, no single-brief entity. (b) A TTL on digests — rejected: contradicts the history requirement.

## R5. Deterministic fallback ranking

- **Decision**: When reasoning fails, rank assets by a pure function of the raw signals: primary key = number of distinct patterns fired on the asset (confluence), secondary key = `abs(ma50_slope)` (trend strength). Tier mapping: assets with ≥2 patterns → high; exactly 1 pattern with meaningful |slope| → watch; the remainder → noise. Rationale strings are templated (e.g. "3 patterns, slope -2.3%"). The brief is flagged `fallback_used=true` (FR-012).
- **Rationale**: Must be side-effect-free, fast, and dependency-free so it always succeeds inside the scan's time budget (FR-011, FR-013). Uses only data already on the `Alert` objects. Thresholds live in config, not hardcoded.
- **Alternatives considered**: No fallback (skip the brief on failure) — rejected: violates guaranteed-delivery (SC-003) and the "never break the scan" requirement.

## R6. Wiring into the scan without touching detection or orders

- **Decision**: In `run_alerting` (`saxo_order/commands/alerting.py`), collect the `Alert` objects already produced per asset into a run-level list, then after the existing per-asset storage loop call `TriageAgent.synthesize(all_alerts)` → `DynamoDBClient.store_alert_digest(digest)` → post the concise Slack digest. The raw-alert `store_alerts` calls and the entire order/workflow path are unchanged. The whole triage+notify block is wrapped so any exception is logged and swallowed (raw alerts already persisted).
- **Rationale**: Detection is the deterministic source of truth (FR-006); triage is a pure read-and-summarize layer appended at the end (FR-007, FR-008, FR-013). Mirrors the existing fallback philosophy already in `run_alerting` (stocks.json fallback).
- **Alternatives considered**: A separate Lambda command reading alerts back from DynamoDB — more moving parts and a second schedule; rejected for the MVP since the alerts are already in memory at end of scan.

## R7. Slack demotion

- **Decision**: Replace the per-indicator `slack_messages` dump to `#stock` with a single concise message: headline tier counts + top high-conviction names + a link to the app's Daily Brief page. The `#errors` operational channel and the workflow channels are unchanged. "No signals" message preserved (FR-019).
- **Rationale**: FR-016 / SC-001 — app becomes source of truth, Slack becomes a pointer. Link target is the frontend homepage `/` (base URL from config), where the brief section renders.
- **Alternatives considered**: Keep both raw and digest — rejected: reintroduces the firehose the feature exists to remove.

## R8. API + Frontend surface

- **Decision**: New router `GET /api/alert-digests` (returns **full** recent digests, newest-first, optional `limit`) and `GET /api/alert-digests/{run_date}` (latest brief for that date), backed by `AlertDigestService` (with a short `TTLCache` like `AlertingService`) and Pydantic models in `api/models/alert_digest.py`. The brief is rendered as a **`DailyBrief` section embedded in the existing `Home` component** (above the current homepage grid), with a **`DailyBriefCarousel`** that pages recent run dates in reverse-chronological order; conviction badges for high/watch, noise as a count. Fetching via a new `alertDigestService` in `services/api.ts`. No new route or sidebar entry.
- **Rationale**: The brief is the trader's primary "what to look at today" artifact — homepage placement gives zero-click access, and the carousel satisfies the run-history requirement (FR-015/US3) without a separate selector or page. The list endpoint returns full digests (not just summaries) because the table is tiny (~1 item/day) and it lets the carousel page client-side with no per-day round-trip. TypeScript interfaces mirror the Pydantic models exactly (constitution API Contract Standards).
- **Scope note**: The carousel covers recent run dates only (bounded by `limit`); arbitrary jump-to-date deep-history lookup is deferred to a future iteration.
- **Alternatives considered**: (a) Standalone `/daily-brief` page + sidebar entry — rejected: adds a click to the most important artifact and duplicates history navigation the carousel already provides. (b) List endpoint returning summaries only + per-day `GET /{run_date}` on each carousel move — rejected: unnecessary round-trips for a one-item-per-day table.

## R9. Configuration & dependency

- **Decision**: Add `anthropic` to `pyproject.toml`. Add `Configuration.anthropic_api_key` (from `self.secrets["anthropic_api_key"]`) and `Configuration.anthropic_model` (from `self.config.get("anthropic_model", "claude-sonnet-5")`), matching the `slack_token` / property pattern. Document the new keys in `secrets.yml`/`config.yml` examples.
- **Rationale**: Principle III — secrets gitignored, non-sensitive model id in `config.yml`, sensible default.
- **Alternatives considered**: Env-var-only — rejected as inconsistent with the established YAML config pattern (though env override remains available per the config design).
