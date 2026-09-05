# CAC40 "Bougie de 9h" (B9H) — stop-loss analysis & parameter tuning

Analysis of the B9H backtest strategy (spec `021-backtest-menu-hardcoded`,
long+short per PR #645), based on real Saxo data exported via the backtest
CSV feature (PR #644). Three parts:

1. A **parameter grid** (SL × TP + time-cut variant) fitted on
   2026-01-02 → 2026-06-30.
2. An **out-of-sample validation** of the two headline configs on the prior
   window 2025-06-01 → 2025-12-31.
3. A **candle-by-candle trace** of the `-50.0` full-stop days under the
   baseline, explaining *why* those days lose.

> **Definitive result (four windows, ~2 years):** B9H has **no edge and is
> a net loser.** Baseline (SL 50 / TP 10) across 2024, 2025 H1, 2025 H2 and
> 2026 H1 nets **−305 points**. The single profitable window (2026 H1,
> +416) — which the early sections of this doc treat as the reference — is
> **an outlier**, outweighed by 2025 H1 alone (−701). Parameter tuning
> (SL 40 / TP 5) is overfit (inverts out-of-sample), and no regime gate
> rescues it: the best one (ADX-avoid) still leaves the strategy net
> negative outside 2026 H1. The one robust, replicated finding is that B9H
> is **anti-trend** — it loses on strong-trend days in all four windows —
> but that is a true fact about a losing strategy, not a path to profit.
> **Do not deploy.** See "Four-window verdict" below; the sections above it
> are the investigation trail that led here (and some of their interim
> conclusions are corrected there).

## Baseline: SL 50 / TP 10 (2026-01-02 → 2026-06-30)

The reference strategy: stop-loss 50 pts, take-profit target 10 pts below
the 9h candle's high.

- 125 calendar days, 98 traded, 27 no-trade
- Net result: **+415.68 pts**
- Win/loss/flat days (of 98 traded): 57 win / 36 loss / 5 flat
- Avg win: +27.33, avg loss: -31.72, profit factor: 1.364
- Monthly: Jan +238.4, Feb -46.4, Mar -25.9, Apr +39.0, May -32.0, Jun +242.5
  (Feb-Mar was the roughest stretch)

## Parameter grid — IN-SAMPLE ONLY (2026 H1)

**Caveat up front:** every number in this section is fitted on the same
2026 H1 window it is scored on. The out-of-sample section below shows these
results do not generalize. Read this as "what the fit produced," not "what
to trade."

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

### In-sample takeaway (do not act on this alone)

On 2026 H1, SL 40 / TP 5 looked best (+563.09, PF 1.527, +35% over baseline)
and the two levers looked additive. The out-of-sample section below shows
this was an artifact of the fit — kept here only to document what the
in-sample grid produced.

## Out-of-sample validation (2025 H2)

Re-ran the two headline configs, unchanged, on the **prior** six months
(2025-06-01 → 2025-12-31, 126 traded days) — data the parameters were never
fitted to. This is the test that matters.

### Net points (profit factor) — both configs, both windows

| Config | In-sample 2026 H1 | Out-of-sample 2025 H2 |
|---|---|---|
| SL 50 / TP 10 (baseline) | +415.68 (1.364) | **+41.15 (1.034)** |
| SL 40 / TP 5 (tuned) | +563.09 (1.527) | **−114.03 (0.911)** |
| **tuning effect** | **+147** | **−155** |

Two conclusions, both decisive:

1. **The tuning is overfit — it inverts out-of-sample.** The SL 40 / TP 5
   change that added +147 in-sample *subtracts* 155 out-of-sample: it goes
   from beating the baseline to losing to it by the same magnitude, and PF
   drops below 1.0 (0.911 = a losing system). This is the textbook signature
   of fitting to noise. Win rate fell 58.7% → 50.8%, payoff 1.07 → 0.88.
2. **The baseline has no real edge either.** Out-of-sample it nets just +41
   over 7 months (PF 1.034), statistically indistinguishable from zero and
   **negative after any realistic transaction cost** (174 trades × 0.5 pt ≈
   −87). "Safe" config, but not a profitable one on unseen data.

### Regime dependence — the same fingerprint in every run

All four runs (2 configs × 2 windows) make money in only 2–3 trending months
and bleed the rest of the time:

| Run | Winning months | Everything else |
|---|---|---|
| 2026 H1 baseline | Jan +238, Jun +242 | net negative |
| 2026 H1 SL40/TP5 | Jan +223, Mar +93, Jun +270 | ~flat |
| 2025 H2 baseline | Jun +68, Dec +160 | Jul–Nov all red (−187 sum) |
| 2025 H2 SL40/TP5 | Jun +96, Dec +187 | Jul–Nov all red (−397 sum) |

The strategy is not a standalone edge; it is a bet that the index trends
cleanly. In-sample happened to contain enough trend to net positive; H2 2025
(a chop-and-bleed summer/autumn) did not.

### Verdict

**B9H as parameterized here has no validated edge. Do not deploy — and in
particular do not adopt SL 40 / TP 5, which is actively overfit.** Raw
parameter tuning is exhausted (it is how the false positive was produced).
The only forward path the data supports is a **regime filter**: since every
profitable stretch is a trending month, the strategy is worth pursuing only
as a *conditional* system that stands aside in chop — gated on a trend/chop
measure (MM50 slope, ADX, or ATR expansion). Next step is to test whether
such a gate turns the losing months flat while keeping the trending ones.

## Regime filter #1: 9h candle range — tested, rejected as a standalone gate

First filter candidate. Enabled by the `h1_range` column added to the range
CSV export (PR #656): the 9h reference-candle width (`h1_high - h1_low`),
config-independent, exported for the full 13 months (2025-06-01 →
2026-06-30, baseline SL 50 / TP 10, 224 traded days, net +456.8). The
hypothesis: narrow 9h mornings = chop = false breakouts = losses; wide =
trend = profit.

**The signal is real and directionally consistent.** In *both* windows the
narrower-half days underperform the wider-half days (no sign-flip):

| | below-median range | above-median range |
|---|---|---|
| 2025 H2 (choppy) | −138 (63d, −2.2/d) | +179 (63d, +2.8/d) |
| 2026 H1 (trending) | +170 (49d, +3.5/d) | +245 (49d, +5.0/d) |

Pooled it is an inverted-U, not monotonic: the mid-range tercile is best
(+554), the *widest* tercile only +125 — extreme-range mornings are
gap/whipsaw days, not clean trends.

**But it fails as a standalone gate — every threshold helps one window and
hurts the other.** "Trade only if 9h range ≥ T", per window (unfiltered:
H2 +41, H1 +416):

| T | 2025 H2 net | 2026 H1 net |
|---|---|---|
| 30 | +228 | +297 |
| 33 | +316 | +341 |
| 35 | +297 | +386 |
| 40 | +78 | +239 |

Every threshold *improves* the choppy window and *degrades* the trending
one. The cause is decisive: the narrowest-third days **lost −275 in 2025 H2**
(−6.4/day) but **made +75 in 2026 H1** (+2.5/day). Narrow mornings only lose
money once the broader regime is already choppy; in a trending regime they
still win, just less. Any gate that rescues H2 discards real profit in H1 —
exactly the window-inconsistency this analysis pre-committed to rejecting.

**Conclusion.** The 9h range is a *trade-quality / expectancy* axis, not the
*regime* axis. It says "is this a high- or low-conviction morning," not "are
we in a trending or choppy month," and low-conviction mornings are only
dangerous once the regime is already choppy. Range and regime are
orthogonal, and the strategy's problem is regime. Rejected as the fix; it
correctly redirects at a genuine trend/chop measure (below).

## Regime filter #2: daily MM50 slope — tested, rejected (sign-inverts)

The daily trend measure the 9h range was a poor proxy for. Enabled by the
`mm50_slope` column added to the range export (PR #657): the daily MA50
slope (%) as of the close *strictly before* each trading day
(lookahead-safe, reusing `mobile_average`/`slope_percentage`, same formula
as the MM50 alert in spec 019). Config-independent; exported for the full
13 months. Hypothesis: trade only when trending (`|slope| ≥ T`), stand
aside in chop.

**It fails the both-windows bar — worse than the range did.** "Trade only
if `|slope| ≥ T`", vs unfiltered (H2 +41, H1 +416):

| T | 2025 H2 | 2026 H1 |
|---|---|---|
| 1 | +57 | +306 |
| 2 | +86 | +161 |
| 3 | +157 | +92 |
| 4 | +223 | +71 |
| 5 | +245 | −7 |

Every threshold *improves* the choppy window and *degrades* the trending
one — same helps-one-hurts-the-other signature as the range gate.

**And the underlying relationship inverts sign between windows**, which is
the damning part. Per-day expectancy by `|slope|` tercile:

| | flat slope | mid | steep |
|---|---|---|---|
| 2025 H2 | −2.88/d | +1.93/d | +1.93/d |
| 2026 H1 | **+11.40/d** | −1.90/d | +3.44/d |

In 2025 H2 flat MM50 is the *worst* bucket; in 2026 H1 it is by far the
*best* (+365 over 32 days — the single most profitable bucket in the whole
dataset, and exactly what a trend gate discards). The 9h range at least
kept a consistent direction; the MM50 slope is not even directionally
stable, so it is not a usable filter.

**What this tells us (not a dead end).** The "profits come from trending
months" narrative does not survive contact with an actual trend indicator:
the most profitable H1 days had a *flat* 50-day slope — the opposite of
trending. The 50-day MA is too laggy to describe the intraday-relevant
regime, and the real axis is probably not long-trend at all. Evidence so
far:

- SL/TP tuning — overfit, inverts out-of-sample.
- 9h-range gate — window-inconsistent on totals.
- MM50-slope gate — sign-inverts between windows.

The MM50 failure is diagnostic: stop testing slow trailing trend, and try a
measure that (a) reacts on a shorter horizon and (b) captures a *different*
property than a moving-average level.

## Regime filter #3: daily ADX(14) — tested, rejected (same inversion + no shared band)

The direction-agnostic trend/chop classifier (`adx14` column, PR #661),
computed lookahead-safe from daily bars strictly before each day. Gate
tested at the pre-committed ADX ∈ {20, 25, 30}, vs unfiltered
(H2 +41, H1 +416):

| T | 2025 H2 | 2026 H1 |
|---|---|---|
| 20 | 0.0 (drops all 126) | −37 |
| 25 | 0.0 (drops all 126) | −49 |
| 30 | 0.0 (drops all 126) | +70 |

Improves **neither** window at any threshold. Rejected. Two structural
problems:

1. **The windows occupy different ADX bands.** ADX range is 8–34 (median
   14.7), and **2025 H2 never reaches ADX 20**. So an absolute "trend gate"
   doesn't filter H2 — it deletes the entire window (net → 0, worse than the
   +41 it started at). Absolute thresholds are meaningless when one window
   never enters the gated band. General warning for any fixed-cutoff gate on
   only two windows.
2. **Same sign-inversion as MM50.** Expectancy by ADX tercile:

   | | low ADX | mid | high ADX |
   |---|---|---|---|
   | 2025 H2 | −0.33/d | −0.66/d | +1.97/d |
   | 2026 H1 | +9.96/d | +6.96/d | −4.02/d |

   In 2026 H1, *more* trend strength is *worse* (high-ADX loses −4/day,
   low-ADX makes +10/day); in 2025 H2 the opposite. The trend-strength →
   P&L relationship flips sign between windows.

## Four-window verdict (definitive)

The sections above were built on two windows (2026 H1 in-sample, 2025 H2
out-of-sample). Two more full windows were then exported with the same
regime columns — **2024** (full year) and **2025 H1** (Jan–May, the gap
between them) — turning this into a four-window / ~2-year test. That
settles it, and it also **corrects two interim conclusions above.**

### Baseline P&L by window (SL 50 / TP 10)

| Window | Net | Note |
|---|---|---|
| 2024 | −61 | losing |
| 2025 H1 | **−701** | catastrophic (incl. the April tariff crash) |
| 2025 H2 | +41 | break-even |
| 2026 H1 | +416 | the one good window |
| **Total** | **−305** | **net loser over ~2 years** |

**The strategy loses money.** 2026 H1 — the reference window for the whole
early analysis — is a single **outlier**, outweighed by 2025 H1 alone. The
+416 was the false positive; the held-out windows exposed it, which is
exactly what out-of-sample testing is for.

### Correction 1: the strategy is anti-trend, and it *replicates*

Interim sections #2/#3 called the MM50 and ADX relationships "sign-
inverting between windows / not usable." That was **partly a gate-direction
error**: those gates were tested as *"trade only when trending"* (`≥ T`),
which is backwards for an anti-trend strategy. With the correct direction
and four windows, the finding is robust, not inverting:

- In **all four** windows, high trend strength (high ADX / steep MM50 slope)
  is the losing bucket; calm/flat days are least-bad. Cleanest example —
  2024 `|MM50 slope|`: flat +160 net, steep **−327** (monotonic).
- The apparent 2025 H2 "inversion" was an artifact: that window never
  exceeds ADX ~20, so it has no trend-strength range to measure.

B9H reliably gets run over on strong-trend days (the big directional moves
blow through the 9h breakout levels to the far stop). This is a **real,
replicated property** — of a losing strategy.

### Correction 2: the anti-trend gate "loses less", it does not create edge

Gating in the correct direction (**stand aside when ADX ≥ T**) is the only
filter that never *hurts* a window across all four — technically the best
cross-window result in the investigation:

| ADX gate | 2024 | 2025 H1 | 2025 H2 | 2026 H1 | total |
|---|---|---|---|---|---|
| unfiltered | −61 | −701 | +41 | +416 | **−305** |
| ADX < 20 | +64 | −166 | +41 | +453 | +391 |
| ADX < 25 | +185 | −353 | +41 | +465 | +338 |

But this does not make B9H tradeable:

- **2025 H1 stays deeply negative even gated** (−353 to −166). No threshold
  makes it positive — 85 losing trades, not a few bad days.
- Even in 2025 H1 the **calm (low-ADX) tercile still lost** (−2.1/day), so
  "avoid trends and you're fine" is false — the calm days had no edge either.
- The gated total (+338) is **entirely 2026 H1**: strip that one window and
  the *gated* strategy nets **−127** over the other three. The gate
  optimizes a losing system; it does not manufacture an edge.
- The threshold (~25) was still chosen in-sample, and all figures are
  pre-cost.

### Conclusion

**B9H has no validated edge. Do not deploy.** Four windows / ~2 years:
net-negative unfiltered, and net-negative even under the best regime gate
once the single outlier window is excluded. Parameter tuning is overfit;
regime gating only reduces losses. The anti-trend behaviour is a robust,
useful *fact* to carry forward (any future variant should expect to be hurt
by trend strength), but it does not rescue this one.

The intraday **overnight-gap** column was built and merged (PR #664,
`overnight_gap`) as the planned next test, but with the strategy now shown
net-negative across four windows, testing it further would be optimising a
loser — not pursued. The column remains available if a materially different
strategy variant is proposed later.

## Variant: wide-range + structural stop (B9HWS) — tested, rejected

A strategy variant (spec 021 US1d, `B9HWS`, PRs #666/#668/#669) built to
test two ideas together: trade only days whose 9h range > 40 pts, and
replace the fixed 50-pt stop with a structural stop (exit when a 5-minute
candle closes back beyond the H1 level while break-even is unarmed). Run
over 2025 H2 + 2026 H1:

| | 2025 H2 | 2026 H1 | Total |
|---|---|---|---|
| B9HWS | +141 | **−129** | **+11** |
| Base (SL 50 / TP 10) | +41 | +416 | +457 |
| Δ | +100 | **−545** | **−446** |

**It destroys the one profitable window.** 2026 H1 swings from +416 to −129
(−545), while it modestly helps the choppy 2025 H2 (+41 → +141) — the same
helps-the-chop / hurts-the-trend pattern seen throughout, but with a
catastrophic "hurt." Net across both windows: +11 vs the base's +457.

Both rule changes are the wrong sign for the window that actually earns:

1. **The range > 40 filter removes H1's good days.** Consistent with regime
   filter #1 (wide-range gate degrades 2026 H1): H1's profitable days are
   the narrower-range ones, so filtering to > 40 pts throws them away (only
   48 of 98 days traded).
2. **The structural stop craters the win rate.** 2026 H1 win rate collapses
   61% → 28% (2025 H2: 55% → 39%), with more trades on fewer days. Because
   entry sits ≤ 20 pts above the H1 low (FR-006a), a "close below H1 low"
   fires constantly and re-enters — a *tighter, noisier* stop than the fixed
   50, not the "let it breathe" stop intended; it gets whipsawed.

Rejected. Consistent with the four-window verdict — nothing that helps the
choppy tape survives contact with 2026 H1. (Result covers 2 of the 4
windows; the −545 destruction of the sole profitable window cannot be
salvaged by the two losing windows, so the conclusion is already robust.)

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
re-entry rule is the wrong remedy. (Note: the "plain SL/TP tuning" that beats
the time-cut in-sample does not itself survive out-of-sample — see the
out-of-sample section. The time-cut is dominated *in-sample*; that is a
weaker claim than "viable.")

## Not pursued (investigation closed)

The four-window verdict closed the strategy as net-negative, so the
remaining threads below are **not worth pursuing on B9H as-is** — they would
optimise a losing system. Kept only as pointers if a materially different
variant is ever proposed:

- Intraday **overnight-gap** gate (`overnight_gap` column shipped in
  PR #664, unused).
- A time-cut with **no re-entry after cut**.
- The 5 exactly-0.0-point days and the two multi-trade −50.0 days
  (2026-03-19, 2026-03-27).
