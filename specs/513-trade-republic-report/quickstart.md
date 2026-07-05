# Quickstart: Trade Republic Report

Manual verification steps once implemented (no automated frontend test framework is configured in this repo).

## Prerequisites

```bash
poetry run python run_api.py   # backend on :8000
cd frontend && npm run dev     # frontend on :5173
```

A sample CSV fixture matching the spec's format, e.g. `tests/services/files/trade_republic_sample.csv`:

```csv
datetime,date,account_type,category,type,asset_class,name,symbol,shares,price,amount,fee,tax,currency,original_amount,original_currency,fx_rate,description,transaction_id,counterparty_name,counterparty_iban,payment_reference,mcc_code
2026-03-01T11:31:45.309887Z,2026-03-01,DEFAULT,CASH,INTEREST_PAYMENT,,,,,,-2.97,,,EUR,,,,Interest payment for payout collection 019ca7a8-6f3f-72da-8766-5ad26381f838,019ca92b-2e1d-7a63-831a-88c8927ba850,,,,
```

## Steps

1. Open the app, click **Trade Republic Report** in the sidebar → the section loads with an empty upload prompt (no stale data from a previous session, per FR-010).
2. Upload the sample CSV above.
   - **Expect**: one row appears in the table with date `2026-03-01`, category `CASH`, type `INTEREST_PAYMENT`, amount `-2.97 EUR`, and the description/transaction id visible. Shares/price/name/symbol show as blank, not as errors (spec Acceptance Scenario US1.2).
3. Reload the page.
   - **Expect**: the table is empty again; the CSV must be re-uploaded (FR-010, US1 Acceptance Scenario 4).
4. Re-upload the CSV, select the single transaction row, click **Export**.
   - **Expect**: a success confirmation; the configured Google Sheet's placeholder tab (`trade_republic_sheet_name` in `config.yml`) gains one new row with the transaction's raw field values (US2 Acceptance Scenario 1).
5. Attempt export with no row selected.
   - **Expect**: the export action is disabled/prevented (US2 Acceptance Scenario 3).
6. Upload a non-CSV file (e.g. a `.txt` or `.png`).
   - **Expect**: a clear rejection error, no rows shown (US3 Acceptance Scenario 1).
7. Upload a CSV with only the header row (no data).
   - **Expect**: an explicit "no transactions found" empty state (US3 Acceptance Scenario 2).
8. Upload a CSV where one row is missing a required field (e.g. `amount` blank on a row that isn't a valid empty case).
   - **Expect**: the other valid rows still display; the bad row is flagged separately rather than aborting the whole upload (US3 Acceptance Scenario 3).
9. Temporarily break the Google Sheets credentials/config and repeat step 4.
   - **Expect**: a clear export failure message; the transaction table itself is unaffected (US2 Acceptance Scenario 2).

## Automated coverage (backend)

```bash
poetry run pytest tests/api/services/test_trade_republic_service.py tests/api/routers/test_trade_republic.py -v
```

Should cover: header/delimiter detection, required-field validation producing `ParseError` entries, foreign-currency row parsing (`original_amount`/`original_currency`/`fx_rate`), empty-file handling, and the export endpoint calling `GSheetClient` once per selected transaction (mocked, no real network/Sheets call in tests).
