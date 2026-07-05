# Phase 0 Research: Trade Republic Report

## 1. `asset_class` field

**Decision**: Reuse the existing `AssetType` enum (`model.enum.AssetType`) for `asset_class`, mapping the CSV's two confirmed values: `FUND` → `AssetType.ETF`, `STOCK` → `AssetType.STOCK` (per FR-014). Unlike `category`/`type`/`account_type` (§4), this field is not left as a raw string, because the trader has confirmed the full set of values and they map cleanly onto an enum the codebase already owns.

**Rationale**: This is exactly the case the constitution's enum-driven principle targets — an existing enum with a direct, confirmed mapping. Unlike §4's category/type/account_type (where only one sample value is known and the vocabulary is broker-controlled and open-ended), `asset_class` has an explicitly closed, two-value domain given by the trader, so there's no guessing risk.

## 2. CSV delimiter detection

**Decision**: Use Python's `csv.Sniffer` to detect the delimiter (falling back to comma `,` if sniffing fails), rather than hardcoding a single delimiter.

**Rationale**: The sample provided in the spec was pasted as tab-separated, but real-world Trade Republic exports are commonly comma- or semicolon-delimited depending on locale/export settings. Sniffing avoids hardcoding an assumption that may not match the file the trader actually uploads, and fails safely (falls back to comma, then reports a parse error via FR-006 if the header still doesn't match) instead of silently misreading columns.

**Alternatives considered**:
- Hardcode comma: rejected — brittle if the real export uses `;` or tab.
- Ask the user to pick a delimiter in the UI: rejected — adds a UI step the spec doesn't ask for; detection is cheap and reliable for a fixed, known header.

## 3. Transient data flow (no server-side persistence)

**Decision**: The upload endpoint parses the CSV and returns the full list of transactions in the HTTP response; nothing is cached or stored server-side. Because of this, the export endpoint must receive the full transaction payload(s) the trader selected (not just an id/index), since the backend has no memory of a previous upload by the time export is called.

**Rationale**: Directly follows the resolved clarification (FR-010): transactions are session-only. This is a real architectural consequence, not just a storage detail — it shapes the API contract (export request carries transaction data, not a reference) and rules out patterns like "fetch orders by from_date" used in the existing Saxo/Binance report (which re-queries the broker per request). Here there is no broker API to re-query — the CSV was a one-time upload — so the frontend is the only place still holding the parsed batch.

**Alternatives considered**:
- Server-side in-memory cache keyed by an upload id: rejected — reintroduces state and a cleanup/expiry concern the spec explicitly ruled out (FR-010), for no added benefit since the browser already holds the data.

## 4. Category / type / account_type as strings, not enums

**Decision**: `category`, `type`, and `account_type` are modeled as plain strings (not enums), even though the constitution favors enums over hardcoded strings.

**Rationale**: The constitution's enum rule targets internal, fully-known domain vocabularies (e.g. `Direction`, `AssetType`) where the codebase owns the full set of valid values. Trade Republic's category/type vocabulary is external and only partially known — the spec's sample shows exactly one value per column (`CASH`, `INTEREST_PAYMENT`, `DEFAULT`). Encoding a guessed enum (e.g. inventing `TRADE`, `SAVEBACK`, `CARD_PAYMENT` values never confirmed against a real file) risks silently rejecting or mis-parsing legitimate rows the first time a trader uploads a statement with a category we didn't guess — directly undermining FR-008 (don't silently drop parseable rows). Strings are validated only for non-emptiness where the CSV format requires it (e.g. every row must have a `category`); the UI displays the raw value.

**Alternatives considered**:
- Strict enum with the two known values + `OTHER` fallback: rejected — adds ceremony without safety, since "OTHER" loses the actual value the trader would want to see.
- Enum now, extend later as new values are observed: rejected for v1 — would require a code change for every new statement variety Trade Republic emits; strings are the simpler, correct choice until the vocabulary is actually enumerated from real exports.

**Note for future work**: once a larger set of real exports is available, promoting the *known, stable* values (e.g. `category`) to an enum-with-fallback is a reasonable follow-up — out of scope here.

## 5. Currency field

**Decision**: Reuse the existing `Currency` enum (`model.enum.Currency`) for `currency` and `original_currency`, parsed leniently (unknown currency codes kept as the raw string rather than raising, since `Currency` doesn't yet cover every ISO code Trade Republic might report).

**Rationale**: `Currency` already exists and EUR (the sample's value) is covered; reusing it satisfies the constitution's enum-driven principle where a matching enum genuinely exists, while not blocking parsing on a code that isn't in the enum yet.

## 6. Google Sheets export target ("ETF / DCA" sheet)

**Decision**: Add one new method to `client/gsheet_client.py` (e.g. `append_etf_dca_row`) that appends a row to the existing "ETF / DCA" sheet (sheet name stored in a new `trade_republic_sheet_name` config key, following the existing `spreadsheet_id`/`gsheet_creds_path` pattern rather than hardcoding the sheet name in code), with columns mapped per spec FR-013:

| Sheet column | Cell (row `r`) | Source |
|---|---|---|
| `ETF` | A`r` | `name` |
| `ISIN` | B`r` | `symbol` |
| `Date` | C`r` | `date` |
| `Sens` | D`r` | `"Achat"` if `amount < 0` else `"Vente"` |
| `Prix` | E`r` | `price` |
| `Quantité` | F`r` | `shares` |
| `Frais` | G`r` | `fee` |
| `Total` | H`r` | formula `=E{r}*F{r}` (`price * shares`) |
| `Total TTC` | I`r` | formula `=H{r}+G{r}` (`Total + Frais`) |

**Rationale**: The trader confirmed the sheet's real name and column layout, so no placeholder is needed. `Sens` is derived from the sign of `amount` rather than from the CSV `type` column, because only one `type` value (`INTEREST_PAYMENT`) is confirmed from the sample and the actual values used for buy/sell trades aren't known — deriving from the amount's sign is robust regardless of what `type` string Trade Republic actually uses for a trade row (see §4 for why `type` itself isn't turned into an enum). `Total` (gross, `price * shares`) is distinguished from `Total TTC` (gross plus fees, matching the French accounting convention "TTC" = toutes taxes comprises), per the trader's explicit formula. Consistent with the existing `GSheetClient` pattern (e.g. `_generate_r_v_block`'s `=F{row}+R{row}+S{row}` cell formula), `Total` and `Total TTC` are written as spreadsheet formulas referencing the row's own `Prix`/`Quantité`/`Frais` cells, not as pre-computed values — so the sheet stays self-consistent if a cell is later edited by hand. This method is separate from `_generate_row` (used by the existing Saxo/Binance "Liste d'ordre" journal) since that layout encodes unrelated order semantics (stop/objective/strategy) that don't apply here — reusing it would require awkward workarounds rather than the small, purpose-built append this format actually needs.

**Alternatives considered**:
- Reuse the existing `_generate_row` / "Liste d'ordre" layout: rejected — that layout encodes Saxo/Binance-specific order semantics (stop/objective/strategy columns) that don't map to Trade Republic transactions (interest payments, card fees, etc. have no strategy/signal), and writes to a different sheet than the one the trader named.
- Derive `Sens` from the CSV `type` column instead of `amount`'s sign: rejected — the exact `type` values Trade Republic uses for buy vs. sell trades aren't confirmed from the single sample row available, whereas the sign of `amount` is guaranteed to reflect money in vs. out regardless of the exact type string.

## 7. File upload mechanics

**Decision**: Standard FastAPI `UploadFile` (multipart/form-data) on the new `POST /api/trade-republic/upload` endpoint; parse with Python's built-in `csv` module (via `io.TextIOWrapper`/`csv.DictReader` over the sniffed dialect) rather than adding a new dependency (e.g. pandas).

**Rationale**: This is the first file-upload endpoint in the codebase, so there's no existing pattern to match, but `UploadFile` is FastAPI's standard mechanism and needs no new dependency. The stdlib `csv` module is sufficient for a 23-column, line-oriented format — pulling in pandas for this would be a needless new dependency for a spec that emphasizes reading "line by line".

**Alternatives considered**:
- pandas `read_csv`: rejected — heavier dependency than needed, and DictReader already gives per-row dicts matching the "line by line" requirement (FR-002) directly.
