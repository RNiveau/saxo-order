# Feature Specification: Trade Republic Report

**Feature Branch**: `513-trade-republic-report`
**Created**: 2026-07-05
**Status**: Draft
**Input**: User description: "I want you to create a new section in the ui « trade republic report » in this section, i can upload a csv, backend read it line by line and then the ui surface these lines, i can export it in the gsheet. Let's specify the gsheet format later. Here is the csv file format: datetime, date, account_type, category, type, asset_class, name, symbol, shares, price, amount, fee, tax, currency, original_amount, original_currency, fx_rate, description, transaction_id, counterparty_name, counterparty_iban, payment_reference, mcc_code"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload a Trade Republic statement and review its transactions (Priority: P1)

As a trader, I want to upload the CSV file exported from Trade Republic into a dedicated "Trade Republic Report" section so I can see every transaction (cash movements, trades, interest, fees, taxes, etc.) in a readable table without opening a spreadsheet myself.

**Why this priority**: This is the foundation of the whole feature — without a reliable upload-and-display step, there is nothing to review or export. It delivers value on its own (a readable view of the statement) even before export exists.

**Independent Test**: Can be fully tested by uploading a sample Trade Republic CSV export and verifying that every row from the file appears in the UI with its fields (date, category, type, name/symbol when applicable, amounts, fees, tax, currency, description, transaction id, etc.) correctly matched to the corresponding CSV columns.

**Acceptance Scenarios**:

1. **Given** the trader is on the "Trade Republic Report" section, **When** they upload a valid Trade Republic CSV export, **Then** the backend parses the file line by line and the UI displays one row per transaction with the values from the CSV.
2. **Given** a CSV containing different transaction types (e.g. a `CASH`/`INTEREST_PAYMENT` row with no shares/price/symbol, and a trade row with shares/price/symbol populated), **When** the file is uploaded, **Then** each row is displayed with only the fields that apply to it populated, and inapplicable fields shown blank rather than as errors.
3. **Given** a row with `original_amount`, `original_currency`, and `fx_rate` populated (a foreign-currency transaction), **When** it is displayed, **Then** both the original-currency amount and the converted amount/currency are visible.
4. **Given** the trader reloads the page or navigates away and back, **When** they return to the section, **Then** the previously uploaded transactions are no longer shown and the trader must upload the CSV again (transactions are not persisted across sessions).

---

### User Story 2 - Export reviewed transactions to Google Sheets (Priority: P1)

As a trader, once I've reviewed the transactions parsed from a Trade Republic statement, I want to export them to my Google Sheets so they become part of my broader financial record without retyping anything.

**Why this priority**: Reviewing data that cannot leave the upload screen has limited standalone value; getting it into the trader's existing Google Sheets record is the actual payoff of digitizing the statement. It is P1 alongside upload because the two together form the minimum viable slice of this feature (the exact sheet layout is deferred, see Assumptions).

**Independent Test**: Can be fully tested by uploading a CSV, triggering the export action, and verifying that the trader receives a clear success confirmation (or a clear error if the export fails) — independent of the final column layout in the sheet, which is specified separately.

**Acceptance Scenarios**:

1. **Given** transactions are displayed after an upload, **When** the trader selects one or more specific rows and triggers the export action, **Then** only the selected transactions are sent to Google Sheets and the trader sees a success confirmation.
2. **Given** the Google Sheets export fails (e.g. connectivity or permission error), **When** the trader triggers export, **Then** a clear error is shown, no rows are marked as exported, and no partial/corrupted state is left in the UI.
3. **Given** no transaction is selected, **When** the trader attempts to trigger the export action, **Then** the system prevents the export (e.g. the action is disabled) rather than sending an empty request.

---

### User Story 3 - Get clear feedback on an invalid or malformed upload (Priority: P3)

As a trader, if I upload a file that isn't a valid Trade Republic CSV export (wrong format, corrupted file, unexpected columns), I want a clear error message so I understand the upload didn't work and why, instead of a blank or broken screen.

**Why this priority**: Important for usability and trust in the feature, but the feature already delivers its core value through US1/US2 when the input is well-formed; malformed input is the exception path.

**Independent Test**: Can be fully tested by uploading a non-CSV file, an empty file, and a CSV missing expected columns, and verifying each produces a distinct, understandable error message and no partial data is shown.

**Acceptance Scenarios**:

1. **Given** the trader uploads a file that is not a CSV, **When** the upload is processed, **Then** the system rejects it with a clear error message and displays no transaction rows.
2. **Given** the trader uploads a CSV with the expected header but zero data rows, **When** the upload is processed, **Then** the system shows an explicit "no transactions found" state rather than an empty table with no explanation.
3. **Given** a CSV where some rows fail to parse (e.g. malformed numeric field), **When** the upload is processed, **Then** the successfully parsed rows are still displayed and the failing rows are flagged to the trader rather than silently dropped or aborting the whole upload.

---

### Edge Cases

- **Empty file**: A CSV with headers only (no transaction rows) → explicit empty state, not an error.
- **Non-CSV or corrupted file**: Upload is rejected with a clear message; nothing is displayed.
- **Missing optional fields**: Many columns are legitimately empty for a given transaction type (e.g. `CASH` rows have no `shares`/`price`/`symbol`/`name`) — this is normal, not an error.
- **Foreign currency rows**: `original_amount`/`original_currency`/`fx_rate` populated alongside `amount`/`currency` — both must be shown so the trader can see the conversion.
- **Large statement**: A CSV covering a long period with many transactions must still load and display without the UI becoming unusable.
- **Re-upload / overlapping statements**: The trader uploads a file that overlaps a previously uploaded or previously exported period — the system performs no duplicate detection; it is the trader's responsibility not to re-export the same transaction.
- **Session ends before export**: The trader uploads a CSV but reloads or leaves before exporting — the parsed transactions are lost and the CSV must be re-uploaded (no server-side persistence).
- **Special characters / encoding**: Descriptions, counterparty names, etc. may contain accented characters, quotes, or commas — these must round-trip correctly from CSV to UI to export.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "Trade Republic Report" section in the UI where a trader can upload a CSV file.
- **FR-002**: System MUST parse the uploaded CSV on the backend, line by line, recognizing the columns: `datetime`, `date`, `account_type`, `category`, `type`, `asset_class`, `name`, `symbol`, `shares`, `price`, `amount`, `fee`, `tax`, `currency`, `original_amount`, `original_currency`, `fx_rate`, `description`, `transaction_id`, `counterparty_name`, `counterparty_iban`, `payment_reference`, `mcc_code`.
- **FR-003**: System MUST display every successfully parsed transaction row in the UI, showing the values from all columns applicable to that transaction (blank/empty where the source column is empty).
- **FR-004**: System MUST let the trader trigger an export of the reviewed transactions to Google Sheets.
- **FR-005**: System MUST report a clear success or failure outcome after an export attempt, without leaving the UI in an ambiguous or partially-updated state.
- **FR-006**: System MUST reject files that are not parseable as the expected CSV format with a clear, actionable error message, without displaying partial or garbage rows.
- **FR-007**: System MUST show an explicit empty state when a valid CSV contains no transaction rows.
- **FR-008**: System MUST continue displaying successfully parsed rows even when some individual rows fail to parse, and MUST flag the failing rows to the trader rather than silently discarding them or aborting the whole upload.
- **FR-009**: System MUST preserve the distinction between the transaction's native amount/currency and its original (pre-conversion) amount/currency/fx-rate when both are present on a row.
- **FR-010**: Uploaded transactions MUST be held transiently for the current review session (in-memory / current visit only); the system MUST NOT persist them server-side beyond that session. Re-visiting the section after a reload requires uploading the CSV again.
- **FR-011**: System MUST let the trader select one or more specific transactions from the displayed batch and export only that selection to Google Sheets, rather than forcing an all-or-nothing export of the whole batch (consistent with the row-level journaling pattern used by the existing Saxo/Binance reporting).
- **FR-012**: System MUST NOT perform any duplicate detection on `transaction_id` across uploads or exports; avoiding re-export of an already-exported transaction (e.g. from overlapping statement periods) is the trader's responsibility.
- **FR-013**: The exact column mapping and layout used when writing to Google Sheets is deferred to a follow-up specification; this feature only requires that a defined, reviewable, per-transaction export action exists.

### Key Entities

- **Trade Republic Transaction**: A single row from the uploaded CSV — one of a cash movement, a trade, an interest payment, a fee, etc. Carries: timestamp, date, account type, category, type, asset class, asset name/symbol (when applicable), shares, price, amount, fee, tax, currency, original amount/currency/fx rate (when a currency conversion applies), free-text description, a unique transaction id, and optional counterparty details (name, IBAN, payment reference, merchant category code).
- **Upload Batch**: The set of transactions produced by parsing one uploaded CSV file, reviewed together in the UI before export.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can upload a typical monthly Trade Republic statement and see all of its transactions listed in the UI in under 5 seconds.
- **SC-002**: 100% of columns present in a valid uploaded row are represented (shown or explicitly blank) in the UI without data loss.
- **SC-003**: A trader can go from a freshly uploaded statement to a completed Google Sheets export of a chosen transaction in 3 actions or fewer (upload, select transaction(s), export).
- **SC-004**: Invalid uploads (wrong file type, empty file, malformed rows) are met with a clear, distinct message in 100% of cases — no blank screens or silent failures.
- **SC-005**: Foreign-currency transactions display both the original and converted amounts correctly in 100% of rows where those fields are present in the source file.

## Assumptions

- The Google Sheets column layout/mapping for exported transactions is explicitly out of scope for this spec and will be defined in a follow-up specification, as requested by the trader.
- The CSV format matches the header and structure supplied (23 columns as listed in FR-002); files from other brokers or with a different column set are out of scope.
- The feature is single-user (the trader uploading their own statement); no multi-user sharing or permissions model is introduced.
- Numeric fields use a dot as the decimal separator and ISO-8601 timestamps, consistent with the sample row provided.
- Uploaded transactions are transient: no database or persistent store is introduced for this feature, and nothing survives a page reload.
- No duplicate detection is performed; the trader is responsible for not re-exporting a transaction they already exported in a prior session.

## Out of Scope

- Defining the exact Google Sheets column layout/mapping (explicitly deferred by the requester).
- Server-side persistence of uploaded transactions across sessions/reloads.
- Duplicate detection or prevention across uploads/exports by `transaction_id`.
- Automatic reconciliation between Trade Republic transactions and the existing Saxo/Binance reporting or trading journal.
- Editing transaction values in the UI before export — the review is read-only over what was parsed.
- Scheduled or automatic imports (e.g. via email or API) — upload is manual and file-based only.
- Multi-file / bulk upload in a single action.
