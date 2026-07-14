# Quickstart: Backtest Menu

Manual verification steps once the feature is implemented (per repo convention — no frontend test framework is configured yet; this is the smoke-test path referenced by the Pre-Merge Gate "API endpoints tested with actual frontend calls").

## 1. Start the stack

```bash
poetry run python run_api.py        # backend on :8000
cd frontend && npm run dev          # frontend on :5173
```

## 2. Backend smoke test (curl)

```bash
# List hardcoded backtests
curl -s http://localhost:8000/api/backtest/definitions | jq

# Single-day detail for a known past trading day
curl -s "http://localhost:8000/api/backtest/day?definition=B9H&date=2026-06-02" | jq

# Range run
curl -s "http://localhost:8000/api/backtest/run?definition=B9H&start_date=2026-06-01&end_date=2026-06-30" | jq

# Invalid range should 400
curl -s -o /dev/null -w "%{http_code}\n" \
  "http://localhost:8000/api/backtest/run?definition=B9H&start_date=2026-06-30&end_date=2026-06-01"
```

Expected: `/definitions` returns the one hardcoded "CAC40 Bougie de 9h" entry; `/day` returns either `no_data`, `no_trade`, or `traded` with entry/exit detail matching the FRA40.I chart for that date; `/run` returns the 8-figure summary plus a compact per-day list; the invalid-range call returns `400`.

## 3. Frontend walkthrough

1. Open http://localhost:5173, confirm a new **Backtest** entry appears in the sidebar (FR-001).
2. Click it, select the "CAC40 Bougie de 9h" backtest, pick a single known historical date, run it.
   - Verify the entry price, exit price, exit reason, and points shown match a manual read of the FRA40.I chart for that day (SC-001, SC-002).
3. Switch to range mode, enter a multi-week start/end date, run it.
   - Verify the 8 summary figures (days, trades, wins, losses, BE, avg win, avg loss, final result) are displayed and are internally consistent (wins + losses + BE = trades) (SC-003).
4. From the range result, open the detail view for a day that had a trade.
   - Verify the H1 high/low and 5-minute candles are shown with the entry/exit points marked (SC-004, User Story 3).
5. Try submitting an end date before the start date, or a future date.
   - Verify the UI shows a validation error and does not run the backtest (FR-016).

## 4. Regression checks

```bash
poetry run pytest tests/services/test_candles_service.py tests/api/services/ tests/api/routers/
poetry run mypy .
poetry run flake8
cd frontend && npm run build && npm run lint
```
