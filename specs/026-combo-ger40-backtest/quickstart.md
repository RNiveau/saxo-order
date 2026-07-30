# Quickstart: "GER40 Combo" Backtest

How to run, verify and reason about the three combo backtests once
implemented.

## Run it

```bash
# Backend
poetry run python run_api.py          # port 8000

# Frontend
cd frontend && npm run dev            # port 5173
```

Open the **Backtest** menu. Three new entries appear beside the existing
ones: *GER40 Combo 5m*, *GER40 Combo 15m*, *GER40 Combo H1*. Only one
parameter input is offered — **Stop loss (pts)**, default 50 — because
the other three thresholds have no meaning for this strategy (FR-C16).

## The comparison this feature exists for

Run the same range on all three, then read the summaries side by side:

```bash
for code in C5M C15M C1H; do
  curl -s "http://localhost:8000/api/backtest/run?definition=$code\
&start_date=2026-01-01&end_date=2026-06-30" | jq '.summary'
done
```

Expect materially different trade counts: the 5m timeframe fires far more
signals than H1 over the same window. A timeframe with a handful of
trades over six months has not been shown to work or fail — it has not
been measured.

## Verify a single position by hand

```bash
curl -s "http://localhost:8000/api/backtest/day?definition=C15M\
&date=2026-06-02" | jq
```

For a reported long, check each rule against the 15-minute candles:

| Rule | Check |
|---|---|
| FR-C02 | The entry's signal candle produces a MEDIUM/STRONG `combo` — a WEAK signal must never appear as a trade. |
| FR-C03 | Triggered signal → entry at the signal candle's **close**. Untriggered → entry at the signal candle's **high**, filled on the **next** candle. |
| FR-C04 | If that next candle never reached the level, there is **no** trade from that signal. |
| FR-C06 | `stop` = the **signal** candle's low − 50 (not the entry candle's). |
| FR-C07 | TP1 = the MM20 **of the exit candle**, not of the entry candle. TP2 = that candle's upper Bollinger band. |
| FR-C08 | After TP1 fills, the runner's stop is the entry price — nothing else arms it. |
| FR-C10 | If the MM20 was already at or below the entry, there is no trade at all. |
| FR-C14 | A candle reaching both the stop and TP1 closes the whole position at the **stop**. |

## Watch for these while testing

- **A trade that spans days.** `entry_time` on Tuesday and `exit_time` on
  Friday is correct (FR-C11). The trade is attributed to Tuesday.
- **`no_trade` days with an open position running through them.** Also
  correct — the day opened nothing.
- **`end_of_run` exits.** Expected on the last day of any range, and in
  the single-day view for a position that really ran longer (research
  R9). If they dominate a run, the range is too short for the timeframe.
- **A "take-profit" that banks a loss.** If the MM20 crossed below the
  entry, TP1 fills below it. Specified behavior (spec edge case), not a
  bug.

## Regression check — the part that matters most

The existing backtests must be **bit-for-bit unchanged** (SC-C03):

```bash
poetry run pytest tests/api/services/backtest/ -q
```

`test_backtest_golden.py` runs every registered definition against a
fixed synthetic market and diffs a committed snapshot. It must pass
**without being regenerated**. If it fails, the strategy seam changed
existing behavior — fix the seam, do not regenerate the snapshot.

Note the golden suite will need the three new definitions added to its
snapshot once, deliberately, as part of registering them.

## Quality gates

```bash
poetry run black . && poetry run isort .
poetry run mypy . && poetry run flake8
poetry run pytest --cov
cd frontend && npm run lint && npm run build
```

## Performance sanity

A 6-month 5m run evaluates ~20k candles. Time it once:

```bash
time curl -s "http://localhost:8000/api/backtest/run?definition=C5M\
&start_date=2026-01-01&end_date=2026-06-30" > /dev/null
```

Cold (uncached) is dominated by ~130 Saxo fetches; warm should be
computation only. Over ~30s warm, revisit the rolling band computation —
not the strategy rules.
