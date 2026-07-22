# CAC40 "Bougie de 9h" (B9H) — full-stop-loss analysis

Analysis of the `-50.0` point (full stop-loss) trading days for the B9H
backtest strategy (spec `021-backtest-menu-hardcoded`, long+short per PR
#645), based on real Saxo data exported via the backtest CSV feature
(PR #644) covering 2026-01-02 to 2026-06-30.

## 6-month range summary (2026-01-02 → 2026-06-30)

- 125 calendar days, 98 traded, 27 no-trade
- Net result: **+415.68 pts**
- Win/loss/flat days (of 98 traded): 57 win / 36 loss / 5 flat
- Avg win: +27.32, avg loss: -31.72, profit factor: 1.364
- Monthly: Jan +238.4, Feb -46.4, Mar -25.9, Apr +39.0, May -32.0, Jun +242.5
  (Feb-Mar was the roughest stretch)

## The 12 clean single-trade `-50.0` days

Every day below is a single-trade day that hit stop-loss for exactly
-50.0 points. All 12 were hand-traced candle-by-candle against the
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

## Open idea: confirmation-timeout stop

Proposed next strategy variant: if within N candles (e.g. 3-6 M5 candles
/ 15-30 min) after entry, price hasn't moved some minimal amount in the
trade's favor (e.g. +8-10 pts), exit early at a smaller loss instead of
waiting for the full -50 stop.

- Would directly target the 8 "immediate bleed" cases (67% of traced
  losses), which show ~0 pts favorable movement from minute one.
- Would **not** help the 4 "near-miss" cases — those already show real
  early follow-through before reversing; they need the BE-threshold
  fix instead, not a no-follow-through filter.
- **Untested risk**: this analysis only looked at losing trades. If
  winning trades also often sit flat or dip slightly against entry for
  the first 15-30 minutes before eventually working, a confirmation-
  timeout rule would silently cut winners short too. Need to check
  winning-day CSVs (or re-run the backtest with the rule as a flag) for
  contrast before committing to specific parameters.

## Not yet investigated

- The 5 exactly-0.0-point days.
- The two multi-trade days that net exactly -50.0 (2026-03-19, 3 trades;
  2026-03-27, 2 trades).
- Winning trades' early post-entry price behavior, for contrast against
  the confirmation-timeout idea above.
