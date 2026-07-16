# Phase 1 Data Model: Alert Triage & Synthesis Agent

## Domain models (`model/`)

### `Conviction` (enum, `model/enum.py`)

`EnumWithGetValue`, mirroring existing enums (no hardcoded tier strings anywhere).

| Member | Value |
|--------|-------|
| `HIGH`  | `"high"` |
| `WATCH` | `"watch"` |
| `NOISE` | `"noise"` |

### `TriagedAsset` (dataclass, `model/__init__.py`)

One asset's entry inside a brief.

| Field | Type | Notes |
|-------|------|-------|
| `asset_code` | `str` | e.g. `"SAN"` |
| `asset_description` | `str` | Human-readable name |
| `exchange` | `str` | **Explicit** source exchange (`"saxo"` / `"binance"`) — never inferred from `country_code` (Constitution V) |
| `country_code` | `Optional[str]` | May be absent for a Saxo asset |
| `conviction` | `Conviction` | Tier |
| `rank` | `Optional[int]` | 1-based within high+watch; `None` for noise |
| `rationale` | `str` | One-line explanation (may be empty for noise) |
| `patterns` | `List[AlertType]` | Distinct patterns that fired on this asset |
| `ma50_slope` | `Optional[float]` | Trend context used in ranking (from `alert.data`) |

### `AlertDigest` (dataclass, `model/__init__.py`)

The synthesized output of one scan run.

| Field | Type | Notes |
|-------|------|-------|
| `run_date` | `str` | `YYYY-MM-DD` — hash key |
| `created_at` | `int` | epoch seconds — range key, orders same-day runs |
| `summary` | `str` | Overall one/two-line brief headline |
| `counts` | `Dict[str, int]` | `{"high": n, "watch": n, "noise": n}` |
| `triaged_assets` | `List[TriagedAsset]` | Ordered; high+watch ranked, noise unranked |
| `fallback_used` | `bool` | `True` when produced by deterministic fallback (FR-012) |
| `model` | `str` | Reasoning model id used, or `"deterministic-fallback"` |

**Validation / invariants**
- Every alerting asset appears in exactly one tier (FR-002).
- `rank` is unique and contiguous across high+watch, ordered by conviction then agent order (FR-003).
- Assets not in the scan are never present; scan assets are never dropped (FR-018) — reconciled in the service.
- `counts` values sum to `len(triaged_assets)`.

## Persistence (`alert_digests` DynamoDB table)

| Attribute | Type | Role |
|-----------|------|------|
| `run_date` | S | Hash key (`YYYY-MM-DD`) |
| `created_at` | N | Range key (epoch seconds) |
| `summary` | S | |
| `counts` | M | |
| `triaged_assets` | L(M) | Each map = one `TriagedAsset` (floats → Decimal on write) |
| `fallback_used` | BOOL | |
| `model` | S | |

- `billing_mode=PAY_PER_REQUEST`, `stream_enabled=True`, `stream_view_type=NEW_AND_OLD_IMAGES`.
- **No TTL attribute** — deliberate, history is permanent (FR-009, SC-006).
- Writes go through `DynamoDBClient.store_alert_digest`; floats converted via existing `_convert_floats_to_decimal`.

## `DynamoDBClient` methods (`client/aws_client.py`)

Public methods (no `_` prefix — called from service/CLI layers; Constitution I):

- `async store_alert_digest(digest: AlertDigest) -> Dict[str, Any]` — `put_item` on `alert_digests`.
- `async get_alert_digests(limit: Optional[int] = None) -> List[Dict[str, Any]]` — scan, sorted by `created_at` desc (newest-first). Small table (≈1 item/day).
- `async get_alert_digest(run_date: str) -> Optional[Dict[str, Any]]` — query by `run_date`, return latest `created_at` for that day.

## API models (`api/models/alert_digest.py`, Pydantic v2)

Field names mirror the domain models exactly so the frontend TS interfaces match 1:1 (Constitution API Contract Standards).

- `TriagedAssetResponse`: `asset_code, asset_description, exchange, country_code, conviction, rank, rationale, patterns: List[str], ma50_slope`
- `AlertDigestResponse`: `run_date, created_at, summary, counts, triaged_assets: List[TriagedAssetResponse], fallback_used, model`
- `AlertDigestListResponse`: `digests: List[AlertDigestResponse]` — the list endpoint returns **full** digests (with per-asset payloads) for the recent window so the homepage carousel pages client-side without extra calls. The table is ~1 item/day, so payload size is not a concern.

## State / lifecycle

`AlertDigest` is immutable once written — one record per run, never updated. History accrues append-only. No deletes in scope.
