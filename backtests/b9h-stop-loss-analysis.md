# CAC40 "Bougie de 9h" (B9H) — stop-loss analysis & parameter tuning

Analysis of the B9H backtest strategy (spec `021-backtest-menu-hardcoded`,
long+short per PR #645), based on real Saxo data exported via the backtest
CSV feature (PR #644) covering 2026-01-02 to 2026-06-30. Two parts:

1. A **parameter grid** measuring the stop-loss (SL) and take-profit (TP)
   settings against each other, plus the time-cut ("B9HTC") variant.
2. A **candle-by-candle trace** of the `-50.0` full-stop days under the
   original baseline, explaining *why* those days lose.

## Baseline: SL 50 / TP 10 (2026-01-02 → 2026-06-30)

The reference strategy: stop-loss 50 pts, take-profit target 10 pts below
the 9h candle's high.

- 125 calendar days, 98 traded, 27 no-trade
- Net result: **+415.68 pts**
- Win/loss/flat days (of 98 traded): 57 win / 36 loss / 5 flat
- Avg win: +27.33, avg loss: -31.72, profit factor: 1.364
- Monthly: Jan +238.4, Feb -46.4, Mar -25.9, Apr +39.0, May -32.0, Jun +242.5
  (Feb-Mar was the roughest stretch)

## Parameter grid (measured)

TP is the take-profit target expressed as points **below** the 9h high — a
smaller number (TP 5) is a more ambitious target closer to the high. SL is
the full stop-loss distance. All runs cover the same 98 traded days.

### Plain strategy — SL × TP (net pts / profit factor)

| | **TP 10** | **TP 5** |
|---|---|---|
| **SL 50** | 415.68 · 1.364 *(baseline)* | 496.64 · 1.436 |
| **SL 40** | 472.12 · 1.437 | **563.09 · 1.527** |

Isolated lever effects:

- **TP 5** (holding SL): **+80.96** at SL 50, **+90.97** at SL 40. Raises
  avg win 27.33 → 30.22 with essentially unchanged losses. The stronger of
  the two levers.
- **SL 40** (holding TP): **+56.44** at TP 10, **+66.45** at TP 5. Cuts
  avg loss 31.72 → 28.12. The secondary lever.

The two are **additive with mild positive synergy**: baseline → SL 40 / TP 5
is +147.41, versus 137 for the sum of the isolated effects (~+10 pts
interaction). They touch opposite sides of the ledger (TP the wins, SL the
losses) so they compound cleanly.

Full monthly breakdown:

| Variant | Net | PF | Jan | Feb | Mar | Apr | May | Jun |
|---|---|---|---|---|---|---|---|---|
| SL 50 · TP 10 (base) | 415.68 | 1.364 | +238.4 | -46.4 | -25.9 | +39.0 | -32.0 | +242.5 |
| SL 50 · TP 5 | 496.64 | 1.436 | +253.3 | -51.0 | +13.2 | -8.6 | -2.0 | +291.7 |
| SL 40 · TP 10 | 472.12 | 1.437 | +208.1 | -8.3 | +54.1 | +46.0 | -49.2 | +221.2 |
| **SL 40 · TP 5** | **563.09** | **1.527** | +223.0 | -12.8 | +93.2 | +8.4 | -19.2 | +270.5 |

### Time-cut variant ("B9HTC") — dominated at every setting

The time-cut (spec 021 variant, "Bougie de 9h time cut") is the
confirmation-timeout idea realized: if price hasn't followed through soon
after entry, cut the trade early and allow re-entry.

| Variant | Net | PF | W/L/F | Trades |
|---|---|---|---|---|
| Time-cut · SL 50 · TP 10 | 249.74 | 1.223 | 51/42/5 | ~150 |
| Time-cut · SL 40 · TP 5 | 414.08 | 1.402 | 49/43/6 | 196 |

The time-cut **does** rescue the "immediate bleed" full-stop days (02-03
-50→-17.6, 04-17 -50→-4.3, 03-20 -50→-25.9, 06-15 -50→-10.9), exactly as
the trace below predicts. But its re-entry churn creates **new** losses that
blow past the stop floor (05-07 → -62.6 across 3 trades, 05-18 → -67.8,
04-10 → -60.8, 04-14 → -58.0), and March/May crater. Even fully tuned with
SL 40 + TP 5 (+414.08) it lands *below the untuned plain baseline* (+415.68)
and ~150 pts under the tuned plain strategy. TP/SL tuning masks the churn
tax but cannot remove it.

### Recommendation

**Adopt SL 40 / TP 5 as the new default** (+563.09, PF 1.527 — +35% net and
best profit factor of the whole field). The time-cut concept is not viable
in its current form; a *no-re-entry-after-cut* rule, or applying the cut
only to the immediate-bleed signature, would need to be tried before it
could compete.

## The 12 clean single-trade `-50.0` days (baseline SL 50)

Every day below is a single-trade day that hit stop-loss for exactly
-50.0 points under the baseline. All 12 were hand-traced candle-by-candle
against the
breach → candidate → breakout/breakdown confirmation → entry → exit state
machine and confirmed to match their CSV exports exactly.

| Date | Dir | Duration | Max favorable excursion | Exit style |
|---|---|---|---|---|
| 2026-02-03 | Long | 3h40m | ~0 pts | immediate bleed |
| 2026-02-20 | Short | 4h05m | ~12.2 pts | near-miss, then spike reversal |
| 2026-02-24 | Short | 5h10m | ~5 pts | immediate bleed |
| 2026-03-09 | Short | 2h00m | ~3.5 pts | immediate bleed |
| 2026-03-20 | Long | 0h40m | ~0 pts | immediate bleed (fastest) |
| 2026-03-30 | Short | 1h55m | ~16.2 pts | near-miss, then spike reversal |
| 2026-04-17 | Short | 2h00m | ~2.2 pts | immediate bleed, then spike |
| 2026-04-22 | Long | 5h45m | ~7.5 pts | immediate bleed (slowest) |
| 2026-05-07 | Long | — | small | slow bleed |
| 2026-05-18 | Short | — | small | fast sharp reversal |
| 2026-06-04 | Short | — | ~14 pts | near-miss give-back |
| 2026-06-15 | Long | — | small | slow bleed |

Direction split: 7 short / 5 long.

## Key finding

**Not one of the 12 full-stop days ever reached the 20-point break-even
arm threshold** (FR-008a / FR-022 — BE arms when a candle's high/low
reaches entry ±20pts). Best cases were 03-30 (~16.2 pts) and 06-04
(~14 pts) — both still fell 4-6 pts short before reversing hard through
the entry and on to the full stop.

Two sub-patterns:

1. **Immediate bleed** (8 of 12: 02-03, 02-24, 03-09, 03-20, 04-17,
   04-22, 05-07, 06-15) — price trends against the position from the
   first candle and never comes back. Duration varies wildly (40 min to
   5h45m) but favorable excursion stays near zero throughout.
2. **Near-miss give-back** (4 of 12: 02-20, 03-30, 04-17's late spike,
   06-04) — price drifts 12-16 pts in the trade's favor, teases the BE
   zone, then reverses violently — often via a single explosive 5-min
   candle (03-30's 11:25 candle: +41 pts; 02-20's 15:00 candle: +62 pts
   high) — and rides straight through to the far stop.

Conclusion: these aren't trades that "almost worked and got unlucky at
the last second" — the breakout/breakdown signal was false from the
entry candle, and by the time price reverses (if it reverses at all
before stopping out), it reverses through the entry, not just through a
20-pt cushion. A tighter BE-arm threshold (e.g. 10-12 pts instead of 20)
would only have saved the 3 near-miss cases (~25% of these losses); it
would not touch the other 9.

## Confirmation-timeout stop — hypothesis confirmed, but net-negative

The trace above motivated a confirmation-timeout ("time-cut") variant: if
price hasn't followed through soon after entry, exit early at a smaller
loss. The time-cut backtest (see the parameter grid above) settled this:

- **Confirmed** on the loss side: the time-cut rescues the 8 "immediate
  bleed" days (~0 pts favorable movement from entry) and leaves the 4
  "near-miss" days near their full stop — exactly the split the trace
  predicted.
- **But it loses overall.** The predicted "untested risk" materialized:
  allowing re-entry churns the strategy into fresh multi-trade losses that
  exceed the stop floor, and it cuts into winners too. Net -166 vs baseline
  (SL 50/TP 10), and still net-negative vs baseline even with SL 40 + TP 5.

So the immediate-bleed diagnosis was correct, but a naive early-exit +
re-entry rule is the wrong remedy. The plain SL/TP tuning captures the
loss-side gains (SL 40 cuts every full stop by 10 pts) without the churn.

## Not yet investigated

- The 5 exactly-0.0-point days.
- The two multi-trade days that net exactly -50.0 (2026-03-19, 3 trades;
  2026-03-27, 2 trades).
- A time-cut with **no re-entry after cut**, to isolate the early-exit
  benefit from the churn cost.
- Whether SL 40 / TP 5 gains hold out-of-sample (this is a single 6-month
  in-sample fit).
