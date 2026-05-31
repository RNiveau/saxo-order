# Quickstart: Saxo Order Reporting

How to exercise the existing Saxo reporting feature end-to-end, from both the CLI and the web UI. Useful as a smoke-test checklist after touching `ReportService`, `SaxoClient.get_report`, `GSheetClient`, or the React `Report.tsx` page.

## Prerequisites

- Working `config.yml` with Saxo credentials, Google Sheets credentials path, spreadsheet id, and `currencies_rate`.
- A Saxo account with at least one executed order in the chosen window.
- Access to the target Google Sheets journal.

```bash
poetry install                  # backend deps
cd frontend && npm install      # frontend deps
```

## CLI flow

Run the report from a terminal:

```bash
poetry run k-order get-report --from-date 2025/04/01 --update-gsheet true
```

You should see:

1. An account selection prompt (skipped when a single Saxo account exists).
2. A numbered list of executed orders since the start date, with prices shown in original currency and EUR for non-EUR orders.
3. Per-row interactive prompts to either **create** a new journal row (asks for stop / objective / strategy / signal / comment) or **update** an existing row (asks for the row number and whether the position is being closed, stopped, or BE-stopped).

Smoke-test sequence:

- [ ] Run with an empty period → "No order to report" then exits cleanly.
- [ ] Create one row in Google Sheets → row appears at the bottom of the sheet with all mandatory fields populated.
- [ ] Update the row's stop/objective → only that row changes.
- [ ] Update the row as closed with `stopped=true` → closure cells populated, taxes computed (if the asset is a stock).

## Web UI flow

Start the backend and frontend in two terminals:

```bash
poetry run python run_api.py    # http://localhost:8000
cd frontend && npm run dev      # http://localhost:5173
```

Then in the browser:

1. Open the **Report** page from the sidebar.
2. Select the Saxo account in the dropdown (Binance is also listed but routes to the Binance service — out of scope here).
3. Enter the start date and load.
4. Confirm the summary cards (`total_orders`, `total_volume_eur`, `total_fees_eur`, buy/sell breakdown) match the per-row data.
5. Click **Manage** on an order to open the `OrderModal`:
   - **Open position**: fill stop / objective / strategy / signal, optionally a comment, save. A new row appears in Google Sheets.
   - **Update / Close**: enter the existing row number, either adjust the stop/objective or tick `stopped` / `be_stopped` to close.
6. Reload the page → results come back instantly (cache hit), and remain consistent for ~5 minutes.

Smoke-test checklist:

- [ ] Account selector lists all Saxo accounts from the user's profile.
- [ ] EUR conversion matches `config.yml` rates within ±0.01 EUR.
- [ ] Summary totals reconcile with the table rows.
- [ ] Create / update / close flows each succeed against Google Sheets.
- [ ] Reloading within 5 minutes returns results in <500 ms (cache hit).

## CLI ↔ UI parity check

Run both surfaces against the same account and start date:

| Check | Expected |
|---|---|
| Same number of orders listed | Identical |
| Same per-order EUR prices | Identical |
| Same summary totals | Identical |
| Same row layout after create | Identical |

Any divergence is a bug — both surfaces share `SaxoClient.get_report`, `calculate_currency`, `calculate_taxes`, and `GSheetClient`.

## Verify US5 — strategy → signal auto-fill (frontend)

Manual smoke test in `npm run dev` (port 5173):

1. Open the Report page, fetch orders for an account, click an opening order to open the create modal.
2. **Mapped strategies fire the default**:
   - Select strategy "Bougie de 9h" → signal becomes "Breakout 5m".
   - Select strategy "Intraday" → signal becomes "Breakout h1".
   - Select strategy "Congestion" → signal becomes "Breakout daily".
3. **Manual override is preserved**: after step 2 with any mapped strategy, change the signal to a different value (e.g. "Polarité"); submit the form; verify the journal row in Google Sheets carries the manually chosen signal, not the default.
4. **Non-mapped strategy leaves signal alone**: pre-select a signal manually, then change the strategy to one *not* in the map (e.g. "Bougie impulsive"); verify the signal field keeps the previously chosen value.
5. **Switching between mapped strategies updates the default**: select "Bougie de 9h" → signal = "Breakout 5m"; without touching the signal, switch to "Intraday" → signal becomes "Breakout h1".
6. **Update flow has the same behaviour**: switch the modal to "update" mode, repeat step 2 on the update form's strategy `<select>`; same defaults fire.

## Troubleshooting

- **"Account not found"**: the supplied `account_id` is not on the Saxo profile that the API is authenticated against. Re-run the OAuth flow.
- **Empty orders list with non-empty period**: check the date format (`YYYY/MM/DD` for the CLI; the API also accepts `YYYY-MM-DD`).
- **EUR conversion off / missing**: confirm `currencies_rate` exists for the order's currency in `config.yml`.
- **Google Sheets write failure**: check `gsheet_creds_path` and that the sheet is shared with the service account.
- **Stale results in the UI**: TTL cache is 5 minutes; reload after waiting, or restart the API for an immediate refresh.
