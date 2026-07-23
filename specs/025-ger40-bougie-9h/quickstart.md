# Quickstart: GER40 Bougie de 9h (double take-profit) backtest

Prerequisites: the spec 021 Backtest menu is already working (CAC40 Bougie de 9h). This feature adds the `G9H` definition; nothing new to install.

## Run it (once implemented)

Backend:

```bash
poetry install
poetry run python run_api.py      # API on :8000
```

Frontend:

```bash
cd frontend && npm run dev        # Vite on :5173
```

In the app: **Backtest** menu → select **"GER40 Bougie de 9h"** → the threshold inputs pre-fill with the GER40 defaults (stop **150**, take-profit offset **10**, break-even trigger **50**, max entry distance **40**). Pick a past day (single-day, full detail) or a date range (aggregate summary). Export CSV from either view.

Direct API check:

```bash
# Definitions now include G9H with its defaults + double_take_profit: true
curl 'http://localhost:8000/api/backtest/definitions'

# Single day (full detail) — each traded position is one aggregated 2-lot trade
curl 'http://localhost:8000/api/backtest/day?definition=G9H&date=2026-06-02'

# Range summary (counts classified by net-points sign for G9H)
curl 'http://localhost:8000/api/backtest/run?definition=G9H&start_date=2026-06-01&end_date=2026-06-30'

# Override a threshold (omitted ones fall back to the GER40 defaults, not CAC40's)
curl 'http://localhost:8000/api/backtest/run?definition=G9H&start_date=2026-06-01&end_date=2026-06-30&stop_loss_points=120'
```

## What to verify (maps to Success Criteria)

- **SC-G01**: a single `G9H` day returns within a few seconds with a correct result (no data / no trade / one or more two-lot positions).
- **SC-G02** (hand-verified, ≥6 GER40.I days): for each of — both-lots stop-out (`points = 2·(stop−entry)`, `stop_loss`), +50 break-even (net ≈ 0, `break_even`), TP1-then-break-even (net-positive, `break_even`), TP1-then-TP2 full winner (`points = (TP1−entry)+(TP2−entry)`, `take_profit`), end-of-day, and a multi-position day — the reported entry, per-lot exits, net points, and exit reason match manual calc.
- **SC-G03**: a multi-week range summary (days, trades one-per-position, wins/losses/BE by net sign, avg win, avg loss, final result) matches a manual computation from the per-day net points.
- **SC-G04**: the day detail view shows the H1 high/low, the 5-minute candles, and each position's entry/exit against the chart.
- **SC-G05**: running the same range on `B9H` (CAC40) is byte-for-byte unaffected — confirm CAC40 still uses 50/10/20/20, entry-relative stop, single-lot trades.

## Backend test entry points

```bash
poetry run pytest tests/api/services/test_backtest_service.py -k ger40 -q
poetry run pytest tests/api/routers/test_backtest.py -k g9h -q
poetry run black . && poetry run isort . && poetry run flake8 && poetry run mypy .
```

## Key rules (cheat sheet)

- Instrument `GER40.I`; same 9:00–10:00 Paris-local H1 window and 17:30 session close as CAC40 (Xetra ≈ Euronext hours).
- Long: entry off the H1 low reversal; **TP1 = H1 midpoint `(high+low)/2`** (lot A), **TP2 = H1 high − 10** (runner), **stop = H1 low − 150** (both lots), **break-even trigger = +50**, **max entry distance = 40** from the H1 low. Short = mirror around the H1 high.
- Two lots per entry; when **TP1 fills, the runner's stop → entry** (break-even); "SL is x2" = both lots exit the shared stop.
- One aggregated `Trade` per position; `points` = sum of both lots; summary counts by net-points sign.
