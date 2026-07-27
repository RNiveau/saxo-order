# GER40 "Bougie de 9h" impulsive-candle (G9HIC) — analysis

Analysis of the **G9HIC** variant (`api/services/backtest/definitions.py`,
spec `025-ger40-bougie-9h`), based on real Saxo data exported via the
backtest CSV feature over two windows.

Third analysis in the "bougie de 9h" series, after
`b9h-stop-loss-analysis.md` (CAC40) and `g9h-ger40-analysis.md`
(GER40 double-TP and single-lot).

> **Verdict: still negative, but for a new and more interesting reason.**
> G9HIC nets **−2035 pts** on 2025 and **−832 pts** on 2026 H1 —
> **−2867 combined** over 257 traded days and 359 positions, before
> costs. It is the **best of the three GER40 variants** (−8.85 pts per
> position vs −9.20 for G9HSL and −13.93 for G9H), but "least bad" is
> not an edge. The diagnosis is structural and specific: replacing the
> fixed 150-point stop with an impulsive-candle exit **removed the floor
> under losses without raising the ceiling on wins**. The take-profit is
> still `h1_high − 10`, so a win is capped at roughly `h1_range − 50`
> (~80 pts) — while losses are now unbounded and reach −456. In 77% of
> single-position losing days the loss exceeded what the best possible
> win that day could have paid. **Do not deploy as-is.** One filter
> combination looks genuinely promising and is worth a fresh-window test
> — see §7 — but it is a post-hoc fit on these two windows, not a result.

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

| Window | File | Traded days | No-trade | Positions |
|---|---|---|---|---|
| 2026-01-02 → 2026-06-30 | `backtestG9HIC2026010120260630_1` | 88 | 37 (30%) | 129 |
| 2025-01-02 → 2025-12-30 | `backtestG9HIC2025010120251231` | 169 | 84 (33%) | 230 |

Parameters both runs: SL 150 (unused), TP offset 10, BE 50, max entry
distance 40. Points are raw GER40.I index differences, single lot, no
costs unless stated.

## 3. Headline results

| | 2025 | 2026 H1 | **Combined** |
|---|---|---|---|
| Traded days | 169 | 88 | 257 |
| Positions | 230 | 129 | 359 |
| **Net** | **−2035** | **−832** | **−2867** |
| Per day | −12.04 | −9.45 | −11.15 |
| **Per position** | **−8.85** | **−6.45** | **−7.99** |
| Win / loss / flat days | 59 / 60 / 50 | 37 / 29 / 22 | 96 / 89 / 72 |
| Win rate (excl. flats) | 49.6% | 56.1% | 51.9% |
| Break-even rate needed | 56.8% | 61.1% | 58.3% |
| Avg win / avg loss | +103 / −135 | +98 / −154 | +101 / −141 |
| Payoff | 0.76 | 0.64 | 0.72 |
| **Profit factor** | **0.75** | **0.81** | **0.77** |
| t-stat | −1.31 | −0.69 | −1.46 |
| Max drawdown | 2458 | 1840 | 3627 |
| Longest losing streak | 4 days | 4 days | — |

Monthly: **5 positive months of 12** in 2025, **3 of 6** in 2026 H1.
Costs: at 1 point of spread per position the combined run is **−3226**.

**Flat days are 28% of all traded days** — the break-even stop is doing a
lot of work, and the strategy spends more than a quarter of its days
going nowhere.

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

All eight columns, both windows. Bucket means are points per day.

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

## 7. The one thing worth testing

Four avoid-rules are same-sign across both windows. Stacked:

| Filter | 2025 | 2026 H1 | Combined |
|---|---|---|---|
| Baseline | −2035 (169) | −832 (88) | −2867 (257) |
| Avoid H1 range ≥ 200 | −744 | −500 | −1244 |
| Avoid gap ∈ [0, +75) | −743 | **+371** | −372 |
| Avoid open ≥ 75% of range | **+239** | −311 | −72 |
| Avoid open ∈ 25–50% | −1056 | −254 | −1311 |
| **All four** | **+1211 (50)** | **+564 (33)** | **+1775 (83)** |

This is the first filter stack in the whole series that is **positive in
both windows independently**. That is more than the G9H stack managed
(which left 2025 negative).

**It is still not a result.** Four thresholds were chosen by looking at
both windows; it discards 68% of traded days, leaving 83 days
(~55 trades/year); and the combined t-stat is only **+1.60**, short of
significance. This is precisely the shape of the CAC40 SL 40 / TP 5 fit
that inverted out-of-sample.

The honest status: **a hypothesis, testable on a window neither of us has
looked at.** 2024 is the obvious candidate. If it holds there at similar
magnitude, it becomes interesting; if it inverts, the series is closed.

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

G9HIC does not have an edge: −2867 points over 257 traded days and 359
positions across two windows, negative in both, profit factor 0.77,
28% of days flat.

The impulse stop is not the improvement it looks like. Paired against the
fixed-stop variant on the same days it is worth +0.65 points/day
(t = +0.13) — noise. What it *does* change is the loss distribution, and
in the wrong direction: it removes the bound on losses while leaving the
`h1_high − 10` target capping wins at ~80 points. A strategy whose best
possible day is +80 and whose worst realised day is −456 needs a win rate
it does not have.

Three variants, two instruments, three stop conventions, five windows.
The entry is the problem, not the exit — every attempt to fix the exit
has produced the same answer.

### Next steps

**Worth doing:** run the §7 four-filter stack on **2024** (and 2023 if
available). It is one export and it is the only open question left.

**Worth considering:** if the family survives the 2024 test, the natural
structural fix is on the **target**, not the stop — the §4 asymmetry is
caused by a capped take-profit sitting opposite an uncapped exit. A
trailing or measured-move target would be a genuinely different
experiment, unlike the three stop variants already tried.

**Not worth doing:** tuning TP/BE/max-distance on these windows; further
regime variables (eight scanned, one survives and it is a tautology);
a fourth stop variant; tightening the daily loss cap or the entry
cut-off (§4 shows neither reaches the loss that matters). If the §7 test
fails on 2024, retire the family.
