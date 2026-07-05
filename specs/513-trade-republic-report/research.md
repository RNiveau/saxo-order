# Phase 0 Research: Trade Republic Report

## 1. CSV delimiter detection

**Decision**: Use Python's `csv.Sniffer` to detect the delimiter (falling back to comma `,` if sniffing fails), rather than hardcoding a single delimiter.

**Rationale**: The sample provided in the spec was pasted as tab-separated, but real-world Trade Republic exports are commonly comma- or semicolon-delimited depending on locale/export settings. Sniffing avoids hardcoding an assumption that may not match the file the trader actually uploads, and fails safely (falls back to comma, then reports a parse error via FR-006 if the header still doesn't match) instead of silently misreading columns.

**Alternatives considered**:
- Hardcode comma: rejected — brittle if the real export uses `;` or tab.
- Ask the user to pick a delimiter in the UI: rejected — adds a UI step the spec doesn't ask for; detection is cheap and reliable for a fixed, known header.

## 2. Transient data flow (no server-side persistence)

**Decision**: The upload endpoint parses the CSV and returns the full list of transactions in the HTTP response; nothing is cached or stored server-side. Because of this, the export endpoint must receive the full transaction payload(s) the trader selected (not just an id/index), since the backend has no memory of a previous upload by the time export is called.

**Rationale**: Directly follows the resolved clarification (FR-010): transactions are session-only. This is a real architectural consequence, not just a storage detail — it shapes the API contract (export request carries transaction data, not a reference) and rules out patterns like "fetch orders by from_date" used in the existing Saxo/Binance report (which re-queries the broker per request). Here there is no broker API to re-query — the CSV was a one-time upload — so the frontend is the only place still holding the parsed batch.

**Alternatives considered**:
- Server-side in-memory cache keyed by an upload id: rejected — reintroduces state and a cleanup/expiry concern the spec explicitly ruled out (FR-010), for no added benefit since the browser already holds the data.

## 3. Category / type / account_type as strings, not enums

**Decision**: `category`, `type`, and `account_type` are modeled as plain strings (not enums), even though the constitution favors enums over hardcoded strings.

**Rationale**: The constitution's enum rule targets internal, fully-known domain vocabularies (e.g. `Direction`, `AssetType`) where the codebase owns the full set of valid values. Trade Republic's category/type vocabulary is external and only partially known — the spec's sample shows exactly one value per column (`CASH`, `INTEREST_PAYMENT`, `DEFAULT`). Encoding a guessed enum (e.g. inventing `TRADE`, `SAVEBACK`, `CARD_PAYMENT` values never confirmed against a real file) risks silently rejecting or mis-parsing legitimate rows the first time a trader uploads a statement with a category we didn't guess — directly undermining FR-008 (don't silently drop parseable rows). Strings are validated only for non-emptiness where the CSV format requires it (e.g. every row must have a `category`); the UI displays the raw value.

**Alternatives considered**:
- Strict enum with the two known values + `OTHER` fallback: rejected — adds ceremony without safety, since "OTHER" loses the actual value the trader would want to see.
- Enum now, extend later as new values are observed: rejected for v1 — would require a code change for every new statement variety Trade Republic emits; strings are the simpler, correct choice until the vocabulary is actually enumerated from real exports.

**Note for future work**: once a larger set of real exports is available, promoting the *known, stable* values (e.g. `category`) to an enum-with-fallback is a reasonable follow-up — out of scope here.

## 4. Currency field

**Decision**: Reuse the existing `Currency` enum (`model.enum.Currency`) for `currency` and `original_currency`, parsed leniently (unknown currency codes kept as the raw string rather than raising, since `Currency` doesn't yet cover every ISO code Trade Republic might report).

**Rationale**: `Currency` already exists and EUR (the sample's value) is covered; reusing it satisfies the constitution's enum-driven principle where a matching enum genuinely exists, while not blocking parsing on a code that isn't in the enum yet.

## 5. Google Sheets export target (placeholder layout)

**Decision**: Add one new method to `client/gsheet_client.py` (e.g. `append_trade_republic_row`) that appends a row to a dedicated sheet/tab (name from a new `trade_republic_sheet_name` config key) with one column per `TradeRepublicTransaction` field, in CSV column order. This is explicitly a placeholder, not a designed layout.

**Rationale**: Spec FR-013 explicitly defers the real column mapping/layout to a follow-up spec. A raw, one-column-per-field append is the simplest possible implementation that satisfies "a defined, reviewable, per-transaction export action exists" (FR-004/FR-013) without inventing a layout that will just be replaced. Using a dedicated sheet/tab (rather than the existing "Liste d'ordre" journal sheet) avoids corrupting the unrelated, carefully-formatted trading journal used by the existing Saxo/Binance reporting feature.

**Alternatives considered**:
- Reuse the existing `_generate_row` / "Liste d'ordre" layout: rejected — that layout encodes Saxo/Binance-specific order semantics (stop/objective/strategy columns) that don't map to Trade Republic transactions (interest payments, card fees, etc. have no strategy/signal).

## 6. File upload mechanics

**Decision**: Standard FastAPI `UploadFile` (multipart/form-data) on the new `POST /api/trade-republic/upload` endpoint; parse with Python's built-in `csv` module (via `io.TextIOWrapper`/`csv.DictReader` over the sniffed dialect) rather than adding a new dependency (e.g. pandas).

**Rationale**: This is the first file-upload endpoint in the codebase, so there's no existing pattern to match, but `UploadFile` is FastAPI's standard mechanism and needs no new dependency. The stdlib `csv` module is sufficient for a 23-column, line-oriented format — pulling in pandas for this would be a needless new dependency for a spec that emphasizes reading "line by line".

**Alternatives considered**:
- pandas `read_csv`: rejected — heavier dependency than needed, and DictReader already gives per-row dicts matching the "line by line" requirement (FR-002) directly.
