# GER40 "Bougie de 9h" impulsive-candle (G9HIC) — analysis

Analysis of the **G9HIC** variant (`api/services/backtest/definitions.py`,
spec `025-ger40-bougie-9h`), based on real Saxo data exported via the
backtest CSV feature over four windows: **2023, 2024, 2025 and 2026 H1**.

Third analysis in the "bougie de 9h" series, after
`b9h-stop-loss-analysis.md` (CAC40) and `g9h-ger40-analysis.md`
(GER40 double-TP and single-lot).

> **Verdict: not deployable, but not dead either — and sharply
> regime-dependent.** Over four windows G9HIC nets **−2116 pts** on 448
> traded days and 589 positions (t = −0.94, per-position −3.59) — a
> result statistically indistinguishable from zero, not the clear loser
> the first two windows suggested.
>
> The windows split cleanly in two:
>
> | | 2023 | 2024 | 2025 | 2026 H1 |
> |---|---|---|---|---|
> | Net | **+583** | **+168** | −2035 | −832 |
> | Profit factor | 1.21 | 1.06 | 0.75 | 0.81 |
> | Median H1 range | 88.8 | 93.7 | 118.0 | 121.5 |
> | Days traded | 38% | 37% | 67% | 70% |
>
> **Two profitable years, two losing ones**, and the split tracks
> volatility almost perfectly: the strategy makes money in quiet years
> where it trades ~38% of days, and loses in volatile years where it
> trades ~68%.
>
> **But that regime cannot be traded.** A trailing-20-day volatility gate
> — the obvious ex-ante way to capture it — was tested directly and
> **fails** (§7.3): the bucket means are non-monotonic, the worst bucket
> is in the middle, and every threshold from 100 upward is net negative.
> The regime is a property of the *year*, visible only in hindsight.
>
> The earlier four-filter stack is separately dead: it inverted on 2024
> and merely degraded 2023. The single replicated finding across all four
> windows is **avoid ADX(14) 20–25** (negative in every window, n = 84).
>
> **Correction to the previous revision of this document**, which was
> written on 2024–2026 only and concluded "no edge, retire the family."
> That was too strong: 2023 is the best window in the set and 2024 is
> also positive. The strategy is closer to break-even than stated. The
> deployment recommendation does not change — nothing here is tradeable
> without a working regime gate, and §7.3 shows the obvious one does not
> work — but "retire" overstated the evidence.

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
| 2023-01-02 → 2023-12-29 | 96 (38%) | 159 | 113 |
| 2024-01-02 → 2024-12-30 | 95 (37%) | 159 | 117 |
| 2025-01-02 → 2025-12-30 | 169 (67%) | 84 | 230 |
| 2026-01-02 → 2026-06-30 | 88 (70%) | 37 | 129 |

Parameters, all four runs: SL 150 (unused), TP offset 10, BE 50, max
entry distance 40. Points are raw GER40.I index differences, single lot,
no costs unless stated.

**2023 and 2024 trade far less** — 37–38% of days vs 67–70% — because the
DAX's 9:00–10:00 range was routinely below the 70-point minimum in those
years. That is not a quirk of the export; it is the `min_h1_range = 70`
filter correctly reflecting two much quieter years.

## 3. Headline results

| | 2023 | 2024 | 2025 | 2026 H1 | **All four** |
|---|---|---|---|---|---|
| Traded days | 96 | 95 | 169 | 88 | 448 |
| Positions | 113 | 117 | 230 | 129 | 589 |
| **Net** | **+583** | **+168** | **−2035** | **−832** | **−2116** |
| Per day | +6.07 | +1.77 | −12.04 | −9.45 | −4.72 |
| **Per position** | **+5.16** | **+1.44** | **−8.85** | **−6.45** | **−3.59** |
| Win / loss / flat | 49 / 36 / 11 | 47 / 32 / 16 | 59 / 60 / 50 | 37 / 29 / 22 | 192 / 157 / 99 |
| Win rate (excl. flats) | 57.6% | 59.5% | 49.6% | 56.1% | 55.0% |
| **Profit factor** | **1.21** | **1.06** | **0.75** | **0.81** | **0.90** |
| t-stat | +0.73 | +0.22 | −1.31 | −0.69 | **−0.94** |
| Max drawdown | 1144 | 701 | 2458 | 1840 | — |
| Median H1 range | 88.8 | 93.7 | 118.0 | 121.5 | — |

Four-window total **−2116 at t = −0.94** — indistinguishable from zero,
not a demonstrated loser. At 1 point of spread per position: **−2705**.

The ordering is the striking part. Sort the windows by median H1 range
and the per-position result falls monotonically: 88.8 → +5.16,
93.7 → +1.44, 118.0 → −8.85, 121.5 → −6.45. Four for four. §7.2 examines
whether that is a real effect or a two-regime coincidence.

**Flat days are 22% of all traded days** — the break-even stop is doing a
lot of work, and the strategy spends a fifth of its days going nowhere.

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
> was fitted on. The four-window version, including 2023 and 2024, is in §7 and
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

### 7.2 The volatility regime — real pattern, unusable

The four-window ordering by median H1 range is perfect (§3), and the
single rule **avoid H1 range ≥ 200** is the best filter in the study:

| | 2023 | 2024 | 2025 | 2026 H1 | **All** |
|---|---|---|---|---|---|
| Baseline | +583 | +168 | −2035 | −832 | −2116 |
| Range < 200 | **+1032** | +85 | −744 | −500 | **−127** |
| Delta | +449 | −83 | +1291 | +332 | **+1989** |

Dropping 37 days out of 448 (8%) removes 94% of the total loss. But it
lands at −127, still not positive, t = −0.06.

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

| Gate | Days | Net | Per-position | t | Years positive |
|---|---|---|---|---|---|
| `tvol` < 85 | 175 | +933 | +4.42 | +0.88 | 2 of 4 |
| `tvol` < 100 | 239 | −475 | −1.63 | −0.34 | 2 of 4 |
| `tvol` < 110 | 276 | −414 | −1.22 | −0.27 | 2 of 4 |
| `tvol` < 120 | 339 | −1415 | −3.31 | −0.79 | 2 of 4 |

Every threshold from 100 up is net negative, and even the best one
(`< 85`, which keeps only 39% of days) is positive in just 2 of 4 years
at t = +0.88. **The regime effect does not survive being made
forward-looking.** It is a property of the calendar year, not a signal.

That is the finding that matters most here, and it is the reason the
deployment answer is unchanged despite two profitable years.

### 7.4 What survives all four windows

Re-running every bucket across all four windows, exactly **one**
non-tautological bucket keeps its sign everywhere:

| Bucket | 2023 | 2024 | 2025 | 2026 H1 | All |
|---|---|---|---|---|---|
| **ADX 20–25** | −26.5 | −27.2 | −20.3 | −14.3 | −21.5/day, n=84, t=−1.56 |

(Plus the `trade_count` buckets, which are the tautology described above.)

The `|slope|` and `open-position` buckets that looked stable on three
windows do **not** survive 2023. ADX 20–25 does, at consistent magnitude
in all four — the single most replicated result in the study. It is an
**avoid** rule, and avoiding it is not enough on its own.

Best honest combination — the two rules with genuine cross-window support
(`range < 200` and `avoid ADX 20–25`):

| 2023 | 2024 | 2025 | 2026 H1 | **All** |
|---|---|---|---|---|
| +1220 | +630 | −318 | −502 | **+1029** (+2.33/position, t = +0.59) |

Positive overall and **+588 after 1 point of spread** — but still
negative in 2 of 4 windows and far from significant. Two rules chosen
with all four windows visible is a milder fit than the four-rule stack,
not a clean one.

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

G9HIC is **not deployable, and not demonstrably a loser either**: −2116
points over 448 traded days and 589 positions across four windows,
profit factor 0.90, **t = −0.94** — indistinguishable from zero. Two
windows are profitable (2023 +583 at PF 1.21, 2024 +168 at PF 1.06) and
two are clearly negative (2025, 2026 H1).

The impulse stop is not the improvement it looks like. Paired against the
fixed-stop variant on the same days it is worth +0.65 points/day
(t = +0.13) — noise. What it *does* change is the loss distribution, in
the wrong direction: it removes the bound on losses while the
`h1_high − 10` target still caps wins near +80. A strategy whose best
possible day is +80 and whose worst realised day is −456 needs a win rate
it does not have. The #677 entry cut-off and 2-loss daily cap were active
throughout and cannot reach this — 84% of all loss arrives on days
holding a single position (§4).

**The results are strongly regime-dependent, and the regime is not
tradeable.** Profitability tracks volatility with a perfect four-window
ordering (§3), but the effect is essentially a between-year one — only
2023 shows it within a window — and the obvious ex-ante capture, a
trailing-volatility gate, **fails outright** (§7.3): non-monotonic
buckets, disagreement between years inside every bucket, and net-negative
results at every threshold from 100 up. Knowing that quiet years suit
this strategy is not the same as knowing, on any given morning, whether
today belongs to a quiet year.

**Both filter leads are exhausted.** The four-rule stack inverted on 2024
and halved 2023's profit. The two-rule combination (`range < 200`,
`avoid ADX 20–25`) does reach +1029 across four windows and +588 after
costs — the only positive aggregate in the study — but it is still
negative in 2 of 4 windows, sits at t = +0.59, and was chosen with all
four windows visible.

### Next steps

**Do not deploy.** Nothing here clears the bar: the unfiltered strategy
is at zero, and the best filtered version is a weak positive selected in
hindsight.

**Do not retire it outright either.** An earlier revision of this
document said "retire the family" on 2024–2026 evidence; 2023 shows that
was too strong. What is warranted is *parking* it: the four-window record
is break-even, not a demonstrated loser, and two of four years were
genuinely profitable.

**The one test that would settle it** is 2022 and 2021 — specifically
whether the quiet-year/volatile-year split repeats, or whether 2023–24
were simply two good years in a row. Two exports. If quiet years are
reliably profitable across six windows, a regime gate becomes worth
designing properly (on realised volatility measured over months, not the
20-day window that failed here). If not, the family is finished.

**Not worth doing:**

- Tuning TP / BE / max-distance on any of these windows — every such fit
  in this series has inverted or degraded out-of-sample.
- More day-level regime variables. Eight were scanned across four
  windows; one non-tautological bucket (ADX 20–25) replicates.
- A fourth stop variant. Three have been tried; the paired tests show the
  stop is not what costs the money.
- Tightening the daily loss cap or entry cut-off (§4).

**If it is revisited structurally**, the untried direction remains the
**target**, not the stop: §4's asymmetry comes from a capped take-profit
facing an uncapped exit, and a trailing or measured-move target would be
a genuinely different experiment.
