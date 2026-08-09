# GER40 "Bougie de 9h" impulsive-candle (G9HIC) — analysis

Analysis of the **G9HIC** variant (`api/services/backtest/definitions.py`,
spec `025-ger40-bougie-9h`), based on real Saxo data exported via the
backtest CSV feature over six windows: **2021, 2022, 2023, 2024, 2025 and
2026 H1** — roughly 5.5 years, 693 traded days, 884 positions.

Third analysis in the "bougie de 9h" series, after
`b9h-stop-loss-analysis.md` (CAC40) and `g9h-ger40-analysis.md`
(GER40 double-TP and single-lot).

> **Verdict: no usable edge. Do not deploy.** Over six windows G9HIC nets
> **−3553 pts** on 693 traded days and 884 positions
> (t = −1.28, per-position −4.02), **−4437** after one point of spread.
> Four of six windows are negative.
>
> | | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 H1 |
> |---|---|---|---|---|---|---|
> | Net | −408 | −1029 | **+583** | **+168** | −2035 | −832 |
> | Profit factor | 0.87 | 0.84 | 1.21 | 1.06 | 0.75 | 0.81 |
> | Per position | −3.58 | −5.68 | +5.16 | +1.44 | −8.85 | −6.45 |
> | Median H1 range | 97.1 | 114.8 | 88.8 | 93.7 | 118.0 | 121.5 |
>
> The only two profitable windows are **2023 and 2024 — consecutive
> years**, which is what a lucky run looks like.
>
> **Every candidate edge found in this study has died when a new window
> arrived.** That is now the central result:
>
> | Finding | Looked solid on | Killed by |
> |---|---|---|
> | Four-filter stack | 2025 + 2026 H1 | 2024 (inverted), 2023 (halved) |
> | **Avoid ADX 20–25** | 2023–2026, all four | **2021 (+25.4) and 2022 (+28.6)** |
> | Quiet-year regime | 2023–2026 | 2021: quiet *and* losing |
>
> **Correction to the two previous revisions of this document.** The
> revision written on 2024–2026 said "retire the family"; the revision
> after 2023 softened that to "park it, not a demonstrated loser," and
> called **avoid ADX 20–25** "the single most replicated result in the
> study." 2021 and 2022 falsify that: the ADX 20–25 bucket is *strongly
> positive* in both (+25.4 and +28.6 per day), and the six-window mean
> collapses to −3.4 at t = −0.34. It was coincidence across four windows.
>
> A monotone relationship between volatility and performance does survive
> (Spearman −0.943 across the six windows, §7.2) — but it is **not
> tradeable**: the ex-ante trailing-volatility gate fails at every
> threshold (§7.3), and 2021 shows a quiet year can still lose.
>
> **The target-side fix was built and tested (§10).** `G9HICD` uncaps the
> runner — two lots, the second targeting 100 points beyond the H1 range,
> with a one-step trail. It works mechanically: average win rises from
> +101 to **+162**. But the second lot doubles the pre-TP1 loss, so the
> payoff ratio is unchanged at 0.70 and daily variance doubles. Across the
> same six windows it nets **−5444** (t = −0.97) and is statistically
> **indistinguishable from trading G9HIC at 1.5× size** (residual t =
> −0.05). It is leverage, not edge.
>
> **The entry-side fix has since been built and tested too, with the
> same outcome** — see `g9hicm-ma50-direction-analysis.md` and §11.
> `G9HICMH` / `G9HICMD` restrict each day to one direction using an MA50
> read at 10:00 on H1 / daily candles. MD is indistinguishable from
> trading G9HIC at 0.48× size (+23 points over the size-matched control,
> t = +0.91); MH is 1914 points *worse* than the size-matched control.
> Both are position sizing wearing the costume of selection, the same
> result as G9HICD at the other end of the lever.

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

Six runs, all with SL 150 (unused), TP offset 10, BE 50, max entry
distance 40. Points are raw GER40.I index differences, single lot, no
costs unless stated. 2021 and 2022 arrived in a single export and are
split by calendar year here.

## 3. Headline results

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 H1 | **All six** |
|---|---|---|---|---|---|---|---|
| Traded days | 101 | 144 | 96 | 95 | 169 | 88 | **693** |
| % of days | 39% | 56% | 38% | 37% | 67% | 70% | — |
| Positions | 114 | 181 | 113 | 117 | 230 | 129 | **884** |
| **Net** | −408 | −1029 | **+583** | **+168** | −2035 | −832 | **−3553** |
| Per day | −4.04 | −7.14 | +6.07 | +1.77 | −12.04 | −9.45 | −5.13 |
| **Per position** | −3.58 | −5.68 | +5.16 | +1.44 | −8.85 | −6.45 | **−4.02** |
| **Profit factor** | 0.87 | 0.84 | **1.21** | **1.06** | 0.75 | 0.81 | — |
| t-stat | −0.53 | −0.73 | +0.73 | +0.22 | −1.31 | −0.69 | **−1.28** |
| Max drawdown | 1014 | 1620 | 1144 | 701 | 2458 | 1840 | — |
| Median H1 range | 97.1 | 114.8 | 88.8 | 93.7 | 118.0 | 121.5 | — |

Six-window total **−3553 at t = −1.28**. The standard error of that total
is 2768 points, so the result is 1.28 SE below zero — still short of
significance, but now leaning clearly negative rather than sitting on it.
At 1 point of spread per position: **−4437**.

**Four of six windows are negative, and the two positive ones are
consecutive.** 2023 and 2024 being adjacent matters: a two-year good run
inside a six-year losing record is the shape of variance, not of an edge
that switched off.

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
> was fitted on. The six-window version, including 2021–2024, is in §7 and
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

### 7.1 Confirmed on 2023 as well

2023 was then run as a second out-of-sample window. The stack does not
invert there, but it does **destroy more than half the profit**:

| | 2023 (OOS) | 2024 (OOS) | 2025 (fitted) | 2026 H1 (fitted) |
|---|---|---|---|---|
| Baseline | +583 (96d) | +168 (95d) | −2035 (169d) | −832 (88d) |
| With the stack | **+258** (29d) | **−392** (31d) | +1211 (50d) | +565 (33d) |

Zero for two out-of-sample. The rule that broke 2024 (avoid gap
∈ [0, +75)) costs −261 on 2023 as well, and `avoid opos 25–50%` costs
−592 there. **The stack is dead** — it only ever worked on the windows it
was fitted to.

### 7.1b And the "quiet years are good" story breaks on 2021

Sorted by median H1 range, all six windows:

| Window | Median H1 range | % days traded | Per position | |
|---|---|---|---|---|
| 2023 | 88.8 | 38% | **+5.16** | profit |
| 2024 | 93.7 | 37% | **+1.44** | profit |
| **2021** | **97.1** | **39%** | **−3.58** | **loss** |
| 2022 | 114.8 | 56% | −5.68 | loss |
| 2025 | 118.0 | 67% | −8.85 | loss |
| 2026 H1 | 121.5 | 70% | −6.45 | loss |

**2021 is a quiet year that lost money** — median range 97.1, only 39% of
days traded, and −3.58 per position. So "quiet year ⇒ profitable" is
false. Quiet years (median range < 100) go 2 wins, 1 loss; volatile years
go 0 for 3.

### 7.2 The volatility regime — real ordering, unusable

Even with 2021 breaking the level, the *ordering* survives: rank the six
windows by median H1 range and by per-position result and only 2025/2026
swap. **Spearman ρ = −0.943 on n = 6.**

That is nominally significant (the 5% critical value at n = 6 is ≈ 0.886)
and it is the most robust pattern in the study. It is also close to
worthless in practice, for three reasons: six calendar years are not six
independent observations; this is the pattern I went looking for after
seeing it in four windows; and — decisively — it does not survive being
made forward-looking (§7.3).

The single rule **avoid H1 range ≥ 200**, which looked like the best
filter on four windows, also weakens badly:

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 H1 | **All six** |
|---|---|---|---|---|---|---|---|
| Baseline | −408 | −1029 | +583 | +168 | −2035 | −832 | −3553 |
| Range < 200 | −750 | −775 | **+1032** | +85 | −744 | −500 | **−1652** |

It still improves the total (−3553 → −1652) but it **makes 2021 worse**,
remains negative in 4 of 6 windows, and lands at t = −0.64.

**And the within-window evidence is weak.** Correlation of `h1_range`
with day points, computed inside each window separately:

| Window | r | t |
|---|---|---|
| 2023 | −0.418 | **−4.47** |
| 2024 | −0.024 | −0.24 |
| 2025 | −0.032 | −0.41 |
| 2026 H1 | −0.053 | −0.49 |

Only 2023 shows the effect internally; the other three are flat zero. So
"wide range is bad" is largely a **between-year** artifact plus one
strong year — and with only two distinct volatility regimes in the data
(2023–24 quiet, 2025–26 volatile), the across-window correlation of
−0.966 is effectively **n = 2**, not n = 4. It cannot carry the weight it
appears to.

### 7.3 The decisive test: an ex-ante volatility gate fails

If the regime story were tradeable, a **trailing** volatility measure —
knowable at 09:00, no hindsight — should separate good days from bad. I
tested the trailing 20-day median H1 range (`tvol`), computed on prior
days only, across all 442 traded days that have one:

| `tvol` bucket | n | Net | Mean/day | Per-year |
|---|---|---|---|---|
| < 70 | 51 | +162 | +3.18 | 23:+119 24:−57 25:+101 |
| 70–85 | 124 | +771 | +6.22 | 23:+829 24:−145 25:−304 26:+391 |
| **85–100** | 64 | **−1408** | **−21.99** | 23:−367 24:+253 25:−749 26:−545 |
| 100–120 | 100 | −940 | −9.40 | 24:+117 25:−372 26:−686 |
| ≥ 120 | 103 | −703 | −6.82 | 25:−710 26:+7 |

**Non-monotonic — the worst bucket is in the middle**, and the years
disagree inside every bucket. As a gate:

Re-run across all six windows:

| Gate | Days | Positions | Net | Per position | t | After 1 pt | Years positive |
|---|---|---|---|---|---|---|---|
| `tvol` < 85 | 258 | 306 | +734 | +2.40 | +0.57 | +428 | **2 of 6** |
| `tvol` < 95 | 350 | 413 | +183 | +0.44 | +0.11 | −230 | **2 of 6** |
| `tvol` < 100 | 390 | 463 | −759 | −1.64 | −0.42 | −1222 | 2 of 6 |
| `tvol` < 110 | 447 | 535 | −1144 | −2.14 | −0.58 | −1679 | 2 of 6 |
| `tvol` < 120 | 540 | 663 | −2569 | −3.87 | −1.12 | −3232 | 2 of 6 |

Every gate is positive in **exactly the same 2 of 6 years** — 2023 and
2024. The gate is not selecting good *days*; it is just a roundabout way
of keeping more of the two years that happened to work. The best
threshold (`< 85`) discards 63% of days to reach +734 at t = +0.57, and
after costs +428 over 5.5 years is not a strategy.

**The regime effect does not survive being made forward-looking.** It is
a property of the calendar year, visible only in hindsight.

That is the finding that matters most here, and it is the reason the
deployment answer is unchanged despite two profitable years.

### 7.4 ADX 20–25 — the last survivor, falsified

The previous revision of this document called **avoid ADX(14) 20–25**
"the single most replicated result in the study": negative in all four
windows then available, at consistent magnitude. 2021 and 2022 reverse
it outright.

| Window | n | Mean pts/day |
|---|---|---|
| **2021** | 24 | **+25.40** |
| **2022** | 26 | **+28.59** |
| 2023 | 18 | −26.53 |
| 2024 | 20 | −27.23 |
| 2025 | 21 | −20.25 |
| 2026 H1 | 25 | −14.34 |
| **All six** | **134** | **−3.38 (t = −0.34)** |

Not a weakening — a clean sign flip, at magnitude, in both added windows.
Across six windows the bucket is worth −3.4 points/day, indistinguishable
from zero. **Four windows of agreement was coincidence.**

As a rule it is now useless: applying `avoid ADX 20–25` across six
windows gives −3100 (t = −1.28), essentially the baseline. The two-rule
combination that reached +1029 on four windows gives **−1721** on six.

### 7.5 The pattern behind all of this

Three candidate edges, three deaths, each time from data that did not
exist when the claim was made:

| Finding | Held on | Died on |
|---|---|---|
| Four-filter stack | 2025, 2026 H1 | 2024 (inverted +168 → −392), 2023 (halved) |
| Quiet-year regime | 2023, 2024, 2025, 2026 | 2021 (quiet *and* losing) |
| Avoid ADX 20–25 | 2023, 2024, 2025, 2026 | 2021 (+25.4), 2022 (+28.6) |

Two of these survived **four** windows before failing. That is the
practical lesson worth keeping from this whole exercise: with ~100
traded days a year and a daily standard deviation of ~107 points, four
windows of agreement is simply not much evidence. Nothing in this study
ever reached |t| > 2 on a rule that was not a tautology.

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

G9HIC has **no usable edge**: −3553 points over 693 traded days and 884
positions across six windows spanning 5.5 years, **t = −1.28**, −4437
after one point of spread. Four of six windows are negative, and the two
positive ones (2023, 2024) are consecutive.

The impulse stop is not the improvement it looks like. Paired against the
fixed-stop variant on the same days it is worth +0.65 points/day
(t = +0.13) — noise. What it *does* change is the loss distribution, in
the wrong direction: it removes the bound on losses while the
`h1_high − 10` target still caps wins near +80. A strategy whose best
possible day is +80 and whose worst realised day is −456 needs a win rate
it does not have. The #677 entry cut-off and 2-loss daily cap were active
throughout and cannot reach this — 84% of all loss arrives on days
holding a single position (§4).

**Every candidate edge has been falsified by data added after the claim
was made** (§7.5). The four-filter stack died on 2023–24; the quiet-year
regime died on 2021; avoid-ADX-20–25 died on 2021–22, flipping from −21
to +27 points/day. Two of the three survived four windows before failing.

The volatility ordering does survive (Spearman −0.943 across six
windows), and it is the only pattern that has not broken. But it is not
tradeable: **2021 was a quiet year that lost money**, and the ex-ante
trailing-volatility gate is positive in exactly the two years that were
already profitable (§7.3) — it selects good *years*, not good *days*.

### Next steps

**Do not deploy, and stop testing this family.** Six windows, 5.5 years,
884 positions, three falsified leads. The question has been answered as
well as this data can answer it.

The deeper constraint is statistical: at ~100 traded days a year and a
daily sd of ~107 points, detecting a +2 points/day edge would take
roughly 33 years of data. **No amount of additional history will settle
a small edge here** — which means any future "promising" filter found on
this dataset should be assumed to be noise until it survives a genuinely
untouched window, and even then treated sceptically given that two rules
survived four.

**Not worth doing:**

- More windows on G9HIC. 2020 and earlier would add two more coin flips,
  not resolution.
- Tuning TP / BE / max-distance — every such fit in this series has
  inverted or degraded out-of-sample.
- More day-level regime variables. Eight were scanned across six windows;
  none survives that is not a tautology.
- A fourth stop variant. Three have been tried; the paired tests show the
  stop is not what costs the money.
- Tightening the daily loss cap or entry cut-off (§4).

**If the idea is revisited**, it should be as a *new* strategy with a
pre-registered hypothesis, not another variant of this entry. The
target-side direction this section previously recommended **has now been
built and tested** — see §10. So has the entry-side direction filter —
see §11.

## 10. G9HICD — the uncapped-runner variant

`G9HICD` (`definitions.py`, spec 025 addenda 3–4) is the fix §4 called
for. Same entries, same impulse stop, same filters as G9HIC, but:

- **Two lots.** The first banks at the ordinary take-profit
  (`h1_high − 10`), where G9HIC exits outright.
- **`runner_extension_points = 100`** — the runner targets 100 points
  *beyond* that, deliberately outside the H1 range that capped every
  earlier variant.
- **`trail_to_first_target_points = 50`** — once the runner is 50 points
  past TP1, its stop moves from break-even up to TP1, locking in at least
  what the first lot banked.

Run over the same six windows (2021-01-04 → 2026-06-30, 693 traded days,
806 positions).

### 10.1 The mechanism works

| | G9HIC | **G9HICD** |
|---|---|---|
| Average win | +101 | **+162.54** |
| Average loss | −141 | −230.66 |
| **Payoff ratio** | 0.72 | **0.70** |
| Win rate (excl. flats) | 55.0% | 56.1% |
| Daily sd | 106.6 | **212.8** |

Uncapping the target does raise the ceiling — average win is up 61%, and
the §4 diagnosis was right about where the constraint sat. But the second
lot doubles the loss before TP1 fills, so **the payoff ratio does not
improve at all**, and daily variance exactly doubles.

### 10.2 Which means it is leverage, not edge

| Year | G9HIC | G9HICD | Delta |
|---|---|---|---|
| 2021 | −408 | **+493** | +901 |
| 2022 | −1029 | −1883 | −855 |
| 2023 | +583 | **+1676** | +1094 |
| 2024 | +168 | **+1382** | +1214 |
| 2025 | −2035 | −5137 | −3102 |
| 2026 H1 | −832 | −1974 | −1142 |
| **All six** | **−3553** | **−5444** | −1891 |

Every window moves further from zero in the direction it was already
going. Three improve, three worsen, and the aggregate gets worse because
the losing windows were larger to begin with.

The daily results correlate at **r = 0.936**. Subtracting a scaled G9HIC
from G9HICD leaves nothing:

| Residual | Sum | Mean/day | t |
|---|---|---|---|
| **G9HICD − 1.5 × G9HIC** | **−115** | **−0.17** | **−0.05** |
| G9HICD − 1.8 × G9HIC | +951 | +1.37 | +0.48 |
| G9HICD − 2.0 × G9HIC | +1662 | +2.40 | +0.83 |

**G9HICD is statistically indistinguishable from trading G9HIC at 1.5×
size.** The runner extension and the trail add no independent
information — they are a position-sizing change wearing the costume of a
strategy change.

### 10.3 Headline

| | |
|---|---|
| Traded days / positions | 693 / 806 |
| **Net** | **−5444** |
| Per day / per position | −7.86 / −6.75 |
| Profit factor | 0.900 |
| t-stat | **−0.97** |
| **Max drawdown** | **9872** |
| After 1 pt spread | **−6250** |

Two windows in six are positive (2021, 2023, 2024 — three, but 2021 only
just). A 9872-point drawdown against a −5444 result is unusable on its
own terms, before any question of edge.

**Verdict: the target-side experiment is answered and closed.** The
capped take-profit really was the structural flaw §4 identified, and
removing it really does produce bigger wins — but not bigger *relative*
to the losses it also unlocks. There is no edge underneath to leverage.

## 11. G9HICMH / G9HICMD — the MA50 direction filter

Full analysis in **`g9hicm-ma50-direction-analysis.md`**. Summary of the
result, over the same six windows:

| | G9HIC | G9HICMH (H1 MA50) | G9HICMD (daily MA50) |
|---|---|---|---|
| Traded days / positions | 693 / 884 | 399 / 435 | 388 / 428 |
| **Net** | **−3553** | **−3663** | **−1697** |
| Profit factor | 0.87 | 0.77 | 0.88 |
| t-stat | −1.28 | −1.88 | −0.90 |
| **Edge over size-matched G9HIC** | — | **−1914** | **+23** |

Both variants are strict subsets of this document's trade list — the
filter only removes trades — so the comparison is a partition of the
same 884 positions. Halving the position count halves the loss; the
question is whether the *selection* beats trading fewer lots, and it
does not. G9HICMD keeps 48.4% of the positions and takes 47.8% of the
loss (52nd percentile of a randomised half). G9HICMH gives back 1914
points against the same size-matched control, and on the days it allows,
its own side loses −3663 where two-sided trading made +1033.

Two points connect back to this document:

- **§4's structural flaw is untouched.** Payoff ratio goes 0.73 → 0.64
  (MH) / 0.62 (MD): both variants strip ~12 points off the average win —
  multi-trade days fall from 169 to 35/40 — while the average loss is
  unchanged, because the stop on the allowed side is unchanged.
- **§7.5's pattern repeats.** MD's edge over the size-matched control
  runs +496 / +247 / +454 / +246 across 2021–2024, then −858 / −419 in
  2025 and 2026 H1. Four good windows, then a sign flip — for the fourth
  time in this study.

A third observation is new and worth carrying forward: the two variants
differ *only* in the timeframe the MA50 is read on, and they separate by
~1970 points, driven entirely by the 266 days (19% of trading days) on
which they pick opposite sides. **The noise floor between neighbouring
parameter choices is wider than the total quantity under study.** Any
future variant on this entry has to clear that floor before its number
means anything.
