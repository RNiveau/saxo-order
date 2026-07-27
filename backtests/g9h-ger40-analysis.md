# GER40 "Bougie de 9h" (G9H) — full analysis & verdict

Analysis of the GER40 variants of the "Bougie de 9h" family, based on
real Saxo data exported via the backtest CSV feature:

- **G9H** (spec `025-ger40-bougie-9h`) — double take-profit, two lots,
  150-point stop measured from the H1 reference level.
- **G9HSL** — the single-lot control added to isolate what the double
  take-profit overlay actually contributes.

Companion to `b9h-stop-loss-analysis.md`, which covers the CAC40 base
strategy over four windows.

> **Verdict: no edge, net loser, do not deploy.** G9H nets **+83 pts**
> on 2026 H1 (statistically indistinguishable from zero, t = 0.04) and
> **−4305 pts** on the full year 2025 — **−4222 combined** over 301
> traded days and 500 positions, before any spread. The single-lot
> control settles the causation question: removing the double take-profit
> **halves the loss but makes the negative edge more significant**
> (t = −1.74 → **−2.01**), so the overlay was an *amplifier*, not the
> cause. The base GER40 "bougie de 9h" entry has a genuine negative edge
> of roughly **−9 points per position**. No regime gate rescues it — under
> the single-lot run, *every* MA50-slope bucket and *every* ADX bucket is
> negative. Combined with the CAC40 result (−305 over four windows), the
> conclusion is that **the "bougie de 9h" entry has no edge on an index**,
> on either instrument and under either stop convention.

## Data

| Run | Window | SL | TP off | BE | Max dist |
|---|---|---|---|---|---|
| G9H | 2026-01-02 → 2026-06-30 | 150 | 10 | 50 | 50 |
| G9H | 2025-01-02 → 2025-12-30 | 150 | 10 | 50 | 50 |
| G9HSL | 2025-01-02 → 2025-12-30 | 150 | 10 | 50 | **40** |

All stops measured from the H1 reference level (`stop_from_reference_level`),
not from entry. Points are raw GER40.I index differences, no position
sizing, no costs unless stated.

> **Caveat on the control run**: G9HSL was exported at max entry distance
> **40** (the definition default) while the G9H runs used **50**, so two
> parameters differ, not one. It turned out near-immaterial: the two
> differences push in opposite directions (dropping the TP1 entry filter
> *adds* entries, tightening 50→40 *removes* them) and **193 of 195 days
> are traded by both runs**; the 2 G9H-only days are worth +261 total.
> The comparison holds, but it is not a textbook single-variable test.

## 1. G9H — 2026 H1

| | |
|---|---|
| Traded days / no-trade | 106 / 19 |
| Positions | 191 |
| **Net** | **+83.0 pts** |
| Win days | 64 (60.4%) |
| Avg win / avg loss | +145.3 / −219.4 (payoff **0.66**) |
| Profit factor | **1.009** |
| Expectancy | +0.78 pts/day, sd 212 → **t = 0.04** |
| Max drawdown | **1979 pts** (peak +844, trough −1135) |

+83 points over six months is zero, not a small edge — a two-sigma band
on this sample spans roughly ±400 points. Costs finish it: 191 positions
× 2 lots = 382 fills, so at 1 point of spread per lot the run is **−299**.
Max drawdown to net result is **24:1 against**.

Monthly: Jan −100, Feb −569, Mar +312, Apr +210, May −232, Jun +462.
Remove the top 5 days and the run is **−1976**; three days (10–12 March,
the crash rebound) carry +1485 of the +83 total.

### The structure is mathematically hostile

- **Winners capped small.** TP1 is the H1 midpoint and entry must be
  below it, so on GER40's typical 90–140 point 9h range the first lot has
  40–70 points to work with. The standard win is "half a small target
  plus a break-even runner."
- **Losers doubled.** The 150-point structural stop × 2 lots is a 200–330
  point hit. Median loss on single-position days: **−309**; 15 of 29
  losing days were the full double stop.

Payoff 0.66 means a **60.2% win rate just to break even**. The run
delivered 60.4%. It survives on a hair, and any real friction sinks it.

### `trade_count` is an illusion

The only variable with a real correlation to the day's result
(r = +0.48, t = +5.6), and it splits the sample perfectly:

- 53 **single-position** days: **−4419 pts** (45% win rate)
- 53 **multi-position** days: **+4502 pts** (76% win rate)

This is a tautology, not a filter. With one position at a time, a day
only reaches 3–5 trades if the early positions closed quickly and
cheaply — a day whose first entry stops out for −310 has no time left to
re-enter. Trade count **describes the outcome**; it is unknowable at
10:00. The same split appears in 2025 (single-position days −7802,
multi-position +3498), which is what confirms it as mechanical.

## 2. G9H — 2025 full year (out-of-sample)

| | 2025 | 2026 H1 | **Combined** |
|---|---|---|---|
| Traded days | 195 | 106 | 301 |
| Positions | 309 | 191 | 500 |
| **Net** | **−4305** | +83 | **−4222** |
| Win days | 54.9% | 60.4% | 56.8% |
| Avg win / loss | +105 / −197 | +145 / −219 | — |
| Profit factor | **0.72** | 1.009 | **0.83** |
| Expectancy/day | −22.1 | +0.8 | −14.0 |
| t-stat | −1.74 | +0.04 | −1.28 |
| Max drawdown | 4445 | 1979 | — |

**The 2025 equity curve peaked on the first traded day of the year
(+140) and never saw that level again.** Twelve months, eight negative,
ending −4305. That is a monotonic bleed, not variance around a small
edge. At 1 point of spread per lot the combined figure is **−5222**.

2026 H1 was the friendly window — the same window in which the CAC40
base strategy posted its one profitable result (+416). Its +83 was noise.

### Regime filters do not survive

Three buckets kept the same sign across both windows: wide H1 ranges
(≥180) bad, |MA50 slope| 3–7 bad, ADX 25–30 bad. Applied as avoid-rules:

| Filter | 2025 | 2026 H1 | Combined |
|---|---|---|---|
| Avoid range ≥180 | −2504 | +1083 | −1421 |
| Avoid \|slope\| 3–7 | −2453 | +2292 | −161 |
| Avoid ADX 25–30 | −3768 | +580 | −3188 |
| **All three** | **−436** | **+2281** | **+1846** |

The stacked version reaches +1846 combined, and it is worthless: three
thresholds chosen after looking at both windows, discarding 38% of days,
and 2025 is *still* negative. All the profit sits in 2026 H1. This is the
same trap as the CAC40 SL 40 / TP 5 fit that inverted out-of-sample.
Every other bucket — H1 range, ADX, gap, slope — flips sign between the
two windows.

## 3. G9HSL — the single-lot control (2025)

The question this run answers: *is the double take-profit the problem, or
the strategy?*

| | G9H (double) | G9HSL (single) |
|---|---|---|
| Traded days | 195 | 193 |
| Positions | 309 | 287 |
| **Net** | **−4305** | **−2641** |
| Win / loss / flat days | 107 / 79 / 9 | 76 / 85 / **32** |
| Win rate | 54.9% | **39.4%** |
| Avg win / avg loss | +105 / −197 | +73 / −97 |
| Payoff | 0.53 | 0.76 |
| **Profit factor** | **0.72** | **0.68** |
| Expectancy/day | −22.1 | −13.7 |
| **t-stat** | −1.74 | **−2.01** |
| Per position | −13.9 | **−9.2** |
| Max drawdown | 4445 | 2740 |

### The double TP was an amplifier, not the cause

Removing it halves the bleed **and makes the negative edge more
statistically significant** — t goes from −1.74 to **−2.01**. Halving the
position halves the loss *and* halves the noise (daily sd 212 → 95), so
what remains is a cleaner read of the same underlying negative edge.
Profit factor barely moves (0.72 → 0.68). The 2025 curve peaks on the
**first traded day again** (+94) and bleeds for twelve months; 9 of 12
months negative.

The improvement is purely mechanical, not directional. On the 193 shared
days the single lot is +1925 better in total, but it is better on only
**84 days and worse on 100** — the entire gain comes from the tail, full
stops going from ~−310 to ~−165. It does not win more often; it loses
less when it loses. Mean daily difference +9.97, t = +1.47 — not
significant.

### With the variance halved, every regime is negative

Under the double-lot run the regime buckets flip-flopped and looked like
noise. Strip the doubling and the picture is uniform:

- **All 5 MA50-slope buckets negative** (−12 to −24 pts/day)
- **All 5 ADX buckets negative** (−2 to −30 pts/day)
- **5 of 6 H1-range buckets negative** — the exception, 80–110, is
  +3.7/day over 56 days, i.e. zero

There is no slope, no ADX level, no range regime where this makes money.
Under G9H one could squint at the tables and imagine a filter; here one
cannot.

The outcome distribution explains it: **39% win at +73, 44% lose at −97,
17% flat**. Sixteen percent of days are exact zeros — break-even stops.
The modal outcome is getting nowhere while paying to be there. 35 of the
85 losing days were full stops.

## Conclusion

The base setup — GER40 9h range, 5-minute breakout/reversal, 150-point
structural stop, TP 10 below the high, break-even at +50 — has a genuine
negative edge of roughly **−9 points per position**, significant at
t = −2.01 over a full year and 287 positions. The double take-profit
overlay makes it worse by inverting the payoff ratio (capped winners,
doubled losers), but it is not the reason the strategy loses.

Combined with `b9h-stop-loss-analysis.md`: CAC40 base B9H over four
windows (−305), GER40 double-TP over two windows (−4222), GER40
single-lot over one window (−2641). Every variant, both instruments, both
stop conventions — negative. **The "bougie de 9h" entry has no edge on an
index.** Do not deploy any variant of it.

### Not worth further work

- **A 2026 H1 run of G9HSL.** 2026 H1 is the known-favourable window; a
  positive number there would add nothing after G9H made +83 on it and
  −4305 on 2025.
- **Re-running G9HSL at max entry distance 50.** The 193/195 day overlap
  shows it will not move the conclusion.
- **More regime filters.** Four variables, six windows across the two
  instruments, nothing has replicated out-of-sample yet.
- **Tuning the four thresholds on any single window.** That is exactly
  what produced the overfit CAC40 result.

The one robust, replicated finding across the whole family remains the
CAC40 doc's: these strategies are **anti-trend**, losing on strong-trend
days in every window tested. That is a true fact about a losing strategy,
not a path to profit.
