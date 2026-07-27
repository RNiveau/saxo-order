# GER40 "Bougie de 9h" impulsive-candle (G9HIC) — analysis

Analysis of the **G9HIC** variant (`api/services/backtest/definitions.py`,
spec `025-ger40-bougie-9h`), based on real Saxo data exported via the
backtest CSV feature over three windows: **2024, 2025 and 2026 H1**.

Third analysis in the "bougie de 9h" series, after
`b9h-stop-loss-analysis.md` (CAC40) and `g9h-ger40-analysis.md`
(GER40 double-TP and single-lot).

> **Verdict: no edge. Retire the family.** G9HIC nets **+168 pts** on
> 2024, **−2035** on 2025 and **−832** on 2026 H1 — **−2699 combined**
> over 352 traded days and 476 positions before costs, **−3175** at one
> point of spread. It is the best of the three GER40 variants
> (−5.67 pts/position vs −9.20 for G9HSL and −13.93 for G9H), but "least
> bad" is not an edge.
>
> The diagnosis is structural: replacing the fixed 150-point stop with an
> impulsive-candle exit **removed the floor under losses without raising
> the ceiling on wins**. The take-profit is still `h1_high − 10`, so a win
> is capped near `h1_range − 50` (~80 pts) while losses are unbounded and
> reach −456. In ~77% of single-position losing days the loss exceeded the
> best win that day could possibly have paid.
>
> **The one promising lead is dead.** A four-filter stack fitted on
> 2025+2026 H1 (+1775 combined, positive in both) was tested on 2024 and
> **inverted**: it turned the only non-negative window from **+168 into
> −392**. That is the same failure mode as the CAC40 SL 40 / TP 5 fit.
> With the lead closed, there is nothing left to test — see §9.

## 1. What G9HIC is

The G9HSL single-lot GER40 setup with three changes:

| | G9HSL | **G9HIC** |
|---|---|---|
| Stop | fixed 150 pts from the H1 level | **impulsive candle only** (≥70 pts, closing in the last 25% of its range) |
| Session | Xetra cash, to 17:30 | **CFD, 9:00–22:00** (`EuCfdMarket`) |
| Day filter | none | **min H1 range 70 pts** |
| Entry cut-off | none | 16:00 (`last_entry_time`) |
| Daily loss cap | none | 2 (`max_daily_losses`) |

Take-profit, break-even trigger and max entry distance are unchanged
(10 / 50 / 40). `stop_loss_points=150` is carried for shape only —
nothing reads it under an impulse stop.

All five filters were **active in these exports**, including the 16:00
entry cut-off and the 2-loss daily cap added in #677 (confirmed by the
run's author). The `min_h1_range` filter is independently visible in the
data — **0 traded days have an H1 range ≤ 70** in either window. So the
figures below are the fully-filtered behaviour, not a pre-#677 baseline.

## 2. Data

| Window | Traded days | No-trade | Positions |
|---|---|---|---|
| 2024-01-02 → 2024-12-30 | 95 (37%) | 159 | 117 |
| 2025-01-02 → 2025-12-30 | 169 (67%) | 84 | 230 |
| 2026-01-02 → 2026-06-30 | 88 (70%) | 37 | 129 |

Parameters, all three runs: SL 150 (unused), TP offset 10, BE 50, max
entry distance 40. Points are raw GER40.I index differences, single lot,
no costs unless stated.

**2024 trades far less** — 37% of days vs 67–70% — because the DAX's
9:00–10:00 range was routinely below the 70-point minimum that year. It
is a genuinely different volatility regime, which makes it a good
out-of-sample test and a thin one at the same time.

## 3. Headline results

| | 2024 | 2025 | 2026 H1 | **All three** |
|---|---|---|---|---|
| Traded days | 95 | 169 | 88 | 352 |
| Positions | 117 | 230 | 129 | 476 |
| **Net** | **+168** | **−2035** | **−832** | **−2699** |
| Per day | +1.77 | −12.04 | −9.45 | −7.67 |
| **Per position** | **+1.44** | **−8.85** | **−6.45** | **−5.67** |
| Win / loss / flat days | 47 / 32 / 16 | 59 / 60 / 50 | 37 / 29 / 22 | 143 / 121 / 88 |
| Win rate (excl. flats) | 59.5% | 49.6% | 56.1% | 54.2% |
| Avg win / avg loss | +62 / −86 | +103 / −135 | +98 / −154 | — |
| **Profit factor** | **1.06** | **0.75** | **0.81** | **0.82** |
| t-stat | +0.22 | −1.31 | −0.69 | **−1.28** |
| Max drawdown | 701 | 2458 | 1840 | — |

Monthly: **7 positive months of 12** in 2024, 5 of 12 in 2025, 3 of 6 in
2026 H1. Costs: at 1 point of spread per position the three-window total
is **−3175**.

2024 is the one non-negative window, and it is *flat* rather than
profitable: +168 points over a full year, profit factor 1.06, t = +0.22.
Note also that its wins and losses are much smaller (+62 / −86 vs
+103 / −135) — narrow-range year, smaller everything.

**Flat days are 25% of all traded days** across the three windows — the
break-even stop is doing a lot of work, and the strategy spends a quarter
of its days going nowhere.

## 4. The structural problem: capped win, uncapped loss

This is the finding that matters, and it is specific to the impulse stop.

The take-profit is unchanged at `h1_high − 10`, and entry must be within
40 points of the H1 level, so **a winning day can pay at most about
`h1_range − 50`**. With a median H1 range near 132, that is ~80 points.
The impulse stop, by contrast, has **no fixed distance** — it fires only
when a 70-point candle closes in the last quarter of its range, which can
happen arbitrarily far from entry.

Measured on single-position days (the clean read):

| | 2025 | 2026 H1 |
|---|---|---|
| Mean win | +79.4 | +83.8 |
| Mean theoretical cap (`range − 50`) | +77.7 | +65.2 |
| **Win / cap ratio** | **1.12** | **1.51** |
| Mean loss | −142.0 | −169.4 |
| **Losses exceeding the day's win cap** | **37 of 48 (77%)** | **16 of 22 (73%)** |

Wins land essentially *at* the ceiling — the strategy is already
extracting the maximum the target allows. Losses routinely exceed that
ceiling. Worst losses: **−332** (2025), **−456** (2026 H1). Under the
old fixed-stop design a single-lot loss could not exceed ~190; here
**16 losing days in 2025 and 6 in 2026 H1 went beyond −190**.

That is the whole result. Removing the fixed stop did not let winners
run, because nothing was raised on the winner side. It only let losers
run.

### The 2-loss daily cap cannot reach this

Since #677's daily cap was active in these runs, it is worth stating
plainly why it does not help: **the damage is done by single trades, not
by a run of them.**

| | 2025 | 2026 H1 |
|---|---|---|
| Losing days that are a **single trade** | 48 of 60 (80%) | 22 of 29 (76%) |
| Share of all loss from those days | **−6817 of −8109 (84%)** | **−3727 of −4456 (84%)** |
| Single-trade days among the worst 10 | 9 of 10 | 8 of 10 |
| Days losing > 190 that are one trade | 14 of 16 | 5 of 6 |

A cap of two losses per day is structurally unable to bind on a day that
opens one position and loses 456 points on it. 84% of the total loss, in
both windows independently, arrives on days where the cap was never in
play. The same applies to the 16:00 entry cut-off: it bounds how *late* a
new position opens, not how far the one already open can travel.

Both filters are sensible risk controls, and they are already in these
numbers. They are not the missing piece.

## 5. Regime checks

All eight columns. Bucket means are points per day.

> These tables cover **2025 and 2026 H1** — the two windows available
> when the regime scan was run, and therefore the two the §7 filter stack
> was fitted on. The three-window version, including 2024, is in §7 and
> is the one that decides which of these patterns are real. Read the
> "stable" markers below as *stable across the fitted windows*, not as
> validated.

### H1 range

| Bucket | 2025 | 2026 H1 | Combined | Stable? |
|---|---|---|---|---|
| < 90 | −0.5 (32) | +39.1 (11) | +9.7 (43) | flip |
| 90–120 | +2.7 (56) | −25.5 (33) | −7.8 (89) | flip |
| 120–150 | −16.3 (38) | −15.3 (17) | −16.0 (55) | **same** |
| 150–200 | −11.2 (23) | +11.6 (15) | −2.2 (38) | flip |
| **≥ 200** | **−64.6 (20)** | **−27.7 (12)** | **−50.7 (32), t=−1.99** | **same** |

Wide-range days are the clearest single negative, replicated in both
windows — the same finding as the CAC40 and G9H docs.

### MA50 slope

Signed slope flips in 4 of 6 buckets. On absolute slope, four of five
buckets are same-sign, and **all of the negative ones dominate**:
3–7 (−27.4 combined), 7–12 (−3.5), ≥18 (−31.0). The one stable positive
is **12–18: +31.4/day (n=27, t=+2.34)** — one narrow band out of five,
which is what noise looks like when you scan.

Correlation with day points: 2025 r=−0.024, 2026 r=+0.024. Nothing.

### ADX(14)

| Bucket | 2025 | 2026 H1 | Combined | Stable? |
|---|---|---|---|---|
| < 15 | −14.8 (63) | −27.2 (18) | −17.5 (81) | **same** |
| 15–20 | +7.8 (48) | −3.8 (27) | +3.6 (75) | flip |
| 20–25 | −20.3 (21) | −14.3 (25) | −17.0 (46) | **same** |
| 25–30 | −27.8 (10) | +13.9 (9) | −8.1 (19) | flip |
| ≥ 30 | −28.7 (27) | −0.5 (9) | −21.6 (36) | **same** |

Every stable bucket is negative; the only positive one flips. Correlation
r=−0.042 / +0.068 — no signal. There is no ADX regime where this works.

### Overnight gap

Absolute gap is noise (the 100–200 bucket flips hard: +27.1 vs −58.4).
**Signed** gap has two stable buckets, and they are the interesting ones:

- **gap ∈ [0, +75): −28.1 / −66.8 → −39.0 combined (n=64, t=−2.78)**
- gap < −200: +22.5 / +71.3 → +42.0 combined (n=20)
- gap ≥ +200: −109.8 / −6.4 → −60.6 combined (n=21)

A small positive overnight gap is the single worst signed-gap condition
in both windows. Combined correlation of signed gap with points is
**r=−0.124, t=−2.00** — the only raw feature correlation reaching
significance.

### Where the 9h candle opens within its own range

The most consistent non-tautological pattern found:

| Open position | 2025 | 2026 H1 | Combined | Stable? |
|---|---|---|---|---|
| < 25% | +7.4 (43) | −24.7 (22) | −3.4 (65) | flip |
| 25–50% | −27.2 (36) | −32.1 (18) | −28.8 (54) | **same** |
| **50–75%** | **+24.9 (36)** | **+32.4 (25)** | **+28.0 (61), t=+2.69** | **same** |
| **≥ 75%** | **−42.1 (54)** | **−22.7 (23)** | **−36.3 (77), t=−2.87** | **same** |

Three of four buckets are same-sign across windows, with the two extremes
significant in the combined sample. Days where the 9h candle opens near
its own high are consistently bad; days where it opens in the upper-middle
are consistently good.

### Trade count — the same tautology as before

| Bucket | 2025 | 2026 H1 | Combined |
|---|---|---|---|
| 1 position | −41.3 (115) | −40.4 (57) | **−41.0 (172), t=−4.54** |
| 2 positions | +48.0 (47) | +35.7 (22) | +44.1 (69), t=+3.35 |
| 3+ positions | +65.8 (7) | +76.3 (9) | +71.7 (16), t=+3.19 |

Strongest correlation in the file (r=+0.344, t=+5.84) and still
**unusable**: with one position at a time, a day only reaches 2–3 trades
if the first one closed quickly and cheaply. It describes the outcome,
not a condition you can read at 10:00. Identical to what G9H showed —
worth restating because it is the single most tempting number here.

## 6. Comparison with the other GER40 variants (2025)

| Variant | Stop | Net | Traded days | Positions | Per position |
|---|---|---|---|---|---|
| G9H | fixed 150, **double lot** | −4305 | 195 | 309 | −13.93 |
| G9HSL | fixed 150, single lot | −2641 | 193 | 287 | −9.20 |
| **G9HIC** | **impulse, single lot** | **−2035** | **169** | **230** | **−8.85** |

G9HIC is the best of the three — but the improvement over G9HSL is **not
real**. Paired on the 169 days both traded: IC −2035 vs SL −2145, a
difference of just **+110 points**, better on 53 days and worse on 63,
mean daily difference +0.65 with **t = +0.13**. The impulse stop is
statistically indistinguishable from the fixed stop. Most of G9HIC's
headline improvement comes from the `min_h1_range ≥ 70` filter simply
**trading 24 fewer days**, not from exiting better.

## 7. The filter stack — fitted, then falsified

Four avoid-rules were same-sign across 2025 and 2026 H1. Stacked, they
produced the most promising number in the entire series: **+1775
combined, positive in both windows independently** (+1211 and +564).
That was more than the G9H stack managed, which left 2025 negative.

It was flagged at the time as a hypothesis, not a result — four
thresholds chosen while looking at both windows, 68% of days discarded,
combined t of only +1.60. **2024 was then run as a clean out-of-sample
test.**

### It inverted

| | 2024 (out-of-sample) | 2025 (fitted) | 2026 H1 (fitted) |
|---|---|---|---|
| Baseline | **+168** (95 days) | −2035 (169) | −832 (88) |
| With the four filters | **−392** (31 days) | +1211 (50) | +565 (33) |
| Mean per day | **−12.63** | +24.21 | +17.11 |
| t-stat | −0.90 | +1.56 | +0.71 |

The stack **turned the only non-negative window into a losing one** —
from +1.77 pts/day to −12.63 pts/day, a swing of −560 points on 95 days.
It did not merely fail to help; it destroyed the value that was there.

### Which rule broke it

| Rule applied alone to 2024 | Net | vs baseline +168 |
|---|---|---|
| Avoid H1 range ≥ 200 | +85 | −83 |
| **Avoid gap ∈ [0, +75)** | **−496** | **−664** |
| Avoid open ≥ 75% of range | +291 | +123 |
| Avoid open ∈ 25–50% | +124 | −45 |

The gap rule is the culprit, and it was the *strongest* in-sample signal
— combined t = −2.78, the only raw feature correlation reaching
significance. In 2024 that same bucket is **+18.5 pts/day** versus −28.1
and −66.8 in the fitted windows. A complete sign reversal on the single
variable the fit leaned on hardest.

This is the exact failure mode documented in `b9h-stop-loss-analysis.md`
for the CAC40 SL 40 / TP 5 grid. Two independent windows agreeing is not
evidence when the thresholds were chosen after seeing both.

### What survives three windows

Re-running every bucket across 2024, 2025 and 2026 H1, only four
non-tautological buckets keep the same sign in all three — and none is
usable:

| Bucket | 2024 | 2025 | 2026 H1 | Verdict |
|---|---|---|---|---|
| \|slope\| 7–12 | −25.0 | −6.5 | −0.9 | decays to zero |
| \|slope\| 12–18 | +9.3 | +32.2 | +31.1 | n = 9 / 9 / 18, too thin |
| **ADX 20–25** | **−27.2** | **−20.3** | **−14.3** | the most consistent finding |
| open ≥ 75% | −3.6 | −42.1 | −22.7 | 2024 is ~zero |

Plus the three `trade_count` buckets, which are the tautology described
above and are same-signed in all three windows for that reason.

ADX 20–25 is the only genuinely replicated non-tautological result: 66
days, negative in all three windows at meaningful magnitude. It is an
**avoid** rule, not an edge — and avoiding it does not make the rest
positive.

## 8. Tails and concentration

| | 2025 | 2026 H1 |
|---|---|---|
| Total | −2035 | −832 |
| Top 5 days | +1259 | +813 |
| Bottom 5 days | −1499 | −1782 |
| Total without top 5 | −3294 | −1645 |

Less top-heavy than G9H (removing the top 5 does not swing the sign,
because the sign is already negative). The 2025 best day, +434.8 on
2025-04-09, is the tariff-crash rebound with a 456-point H1 range — the
one day the win cap was wide enough to pay properly, which is itself
evidence for §4.

## 9. Conclusion

G9HIC does not have an edge: **−2699 points over 352 traded days and 476
positions across three windows**, profit factor 0.82, a quarter of days
flat, and −3175 after one point of spread. One window (2024) is flat-
positive at +168; the other two are clearly negative.

The impulse stop is not the improvement it looks like. Paired against the
fixed-stop variant on the same days it is worth +0.65 points/day
(t = +0.13) — noise. What it *does* change is the loss distribution, in
the wrong direction: it removes the bound on losses while the
`h1_high − 10` target still caps wins near +80. A strategy whose best
possible day is +80 and whose worst realised day is −456 needs a win rate
it does not have. The #677 entry cut-off and 2-loss daily cap were active
throughout and cannot reach this — 84% of all loss arrives on days
holding a single position (§4).

**The last open lead is closed.** The four-filter stack was the one
result in the series that looked like it might generalise, and 2024
falsified it decisively: the only non-negative window went from +168 to
−392, driven by a full sign reversal in the variable the fit relied on
most.

Running total across the family: three variants, two instruments, three
stop conventions, **six windows**. The entry is the problem, not the
exit — every attempt to fix the exit has produced the same answer.

### Next steps

**Retire the "bougie de 9h" family.** There is no remaining untested
hypothesis. The G9H/G9HSL/G9HIC definitions can stay in the Backtest menu
as reference implementations, but none should be deployed and none merits
further parameter work.

**Not worth doing:**

- Tuning TP / BE / max-distance on any of these windows — every such fit
  in this series has inverted out-of-sample.
- More regime variables. Eight were scanned across three windows; one
  non-tautological bucket (ADX 20–25) replicates, and it is an avoid rule
  that does not make the remainder positive.
- A fourth stop variant. Three have now been tried; the paired tests show
  the stop is not what is costing the money.
- Tightening the daily loss cap or entry cut-off (§4).

**If the idea is ever revisited**, the one untried direction is the
**target**, not the stop: the §4 asymmetry comes from a capped
take-profit sitting opposite an uncapped exit, and a trailing or
measured-move target would be a genuinely different experiment. That is
a new strategy, though, not a variant of this one — and on the evidence
of six windows it should start from a fresh hypothesis rather than from
this entry.
