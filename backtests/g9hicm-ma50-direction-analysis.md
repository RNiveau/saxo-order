# GER40 "Bougie de 9h" MA50 direction filter (G9HICMH / G9HICMD) — analysis

Analysis of the two **MA50 direction-filter** variants of G9HIC
(`api/services/backtest/definitions.py`,
`api/services/backtest/direction_filter.py`, spec
`025-ger40-bougie-9h` addendum 5), each exported over a single window:
**2021-01-04 → 2026-06-30**, 1400 session days.

Fourth analysis in the "bougie de 9h" series, after
`b9h-stop-loss-analysis.md` (CAC40), `g9h-ger40-analysis.md` (GER40
double-TP and single-lot) and `g9hic-impulsive-candle-analysis.md`
(G9HIC and its uncapped-runner variant G9HICD).

> **Verdict: neither filter is an edge, and neither rescues G9HIC. Do
> not deploy.**
>
> | | G9HIC (control) | **G9HICMH** (H1 MA50) | **G9HICMD** (daily MA50) |
> |---|---|---|---|
> | Traded days | 693 | 399 | 388 |
> | Positions | 884 | 435 | 428 |
> | **Net** | **−3553** | **−3663** | **−1697** |
> | Per position | −4.02 | −8.42 | −3.96 |
> | Profit factor | 0.87 | 0.77 | 0.88 |
> | t-stat | −1.28 | −1.88 | −0.90 |
> | Max drawdown | 4173 | 4086 | 3302 |
> | After 1 pt spread | −4437 | −4098 | −2125 |
>
> Both filters cut position count roughly in half, so the comparison
> that matters is against **the control traded at the same size** (§4):
>
> | | positions | actual | control at same size | edge added |
> |---|---|---|---|---|
> | G9HICMH | 435 (49.2%) | −3663 | −1748 | **−1914** |
> | G9HICMD | 428 (48.4%) | −1697 | −1720 | **+23** |
>
> **G9HICMD is the control at 0.48× size.** It keeps 48.4% of the
> positions and captures 47.8% of the loss; 23 points of difference over
> 5.5 years is nothing. Against a randomised half of the control's
> trades it lands at the **52nd percentile** — coin-flip selection does
> the same thing.
>
> **G9HICMH is the control at half size, minus another ~1900 points.**
> On the days it allows, its own side loses −3663 while the control's
> full two-sided trading on those same days makes **+1033** (§5).
>
> This is the same verdict as `G9HICD` in the previous document, at the
> other end of the lever: that one was leverage up, this one is leverage
> down. Neither adds information.
>
> The MA50-at-10:00 gate carries **no usable directional information**
> on this setup, on either timeframe. G9HIC's problem is the payoff
> ratio — structurally capped upside against an unbounded impulse stop
> (§4 of the previous document) — and choosing *which* side to take does
> not touch it (§6).

## 1. What the variants are

G9HIC with one addition: the day trades in at most one direction. At
10:00 the 9:00–10:00 reference candle's close is compared to an MA50;
above it the day is long-only, below it short-only, exactly on it (or
with no computable MA50) untraded.

| | G9HIC | **G9HICMH** | **G9HICMD** |
|---|---|---|---|
| `ma50_direction_filter` | — | `UnitTime.H1` | `UnitTime.D` |
| MA50 read on | — | cash-session H1 candles | daily candles |

Everything else is identical across all three: `EuCfdMarket` 9:00–22:00,
impulse stop (≥70 pts closing in the last 25% of its range),
`min_h1_range_points=70`, `last_entry_time=16:00`,
`max_daily_losses=2`, TP offset 10, BE 50, max entry distance 40.
`stop_loss_points=150` is carried for shape only.

The filter refuses entries on the wrong side only — both direction
searches keep being fed, so the allowed side sees exactly the candles it
would see without the filter.

## 2. Data and the control

Two exports, one window each, 2021-01-04 → 2026-06-30. The control is
the same six-window G9HIC set used in
`g9hic-impulsive-candle-analysis.md`, rebuilt from the yearly exports:
it reproduces exactly — **693 traded days, 884 positions, −3553**.
Windows below are calendar years, with 2026 covering H1 only.

Points are raw GER40.I index differences, single lot, no costs unless
stated.

**The subset property holds, and it is what makes the rest of this
document exact.** Every MH and MD traded day is also a G9HIC traded day
(0 exceptions), and no day carries more positions in a filtered run than
in the control (0 exceptions). Both runs are therefore strict subsets of
the control's trade list: the filter only ever removes trades. Every
comparison below is a partition of the same 884 positions, not two
independent simulations.

## 3. Headline results by window

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 H1 | **All** |
|---|---|---|---|---|---|---|---|
| **G9HIC** (control) | | | | | | | |
| Traded days | 101 | 144 | 96 | 95 | 169 | 88 | 693 |
| Positions | 114 | 181 | 113 | 117 | 230 | 129 | 884 |
| Net | −408 | −1029 | **+583** | **+168** | −2035 | −832 | **−3553** |
| **G9HICMH** | | | | | | | |
| Traded days | 55 | 80 | 50 | 58 | 94 | 62 | 399 |
| Positions | 58 | 87 | 52 | 62 | 105 | 71 | 435 |
| Net | −1062 | −897 | **+264** | −57 | −969 | −942 | **−3663** |
| Per position | −18.31 | −10.31 | +5.08 | −0.91 | −9.23 | −13.27 | −8.42 |
| Profit factor | 0.52 | 0.72 | 1.20 | 0.97 | 0.75 | 0.72 | 0.77 |
| **G9HICMD** | | | | | | | |
| Traded days | 54 | 85 | 44 | 49 | 99 | 57 | 388 |
| Positions | 58 | 89 | 45 | 53 | 116 | 67 | 428 |
| Net | **+288** | −258 | **+686** | **+323** | −1885 | −851 | **−1697** |
| Per position | +4.97 | −2.90 | +15.25 | +6.09 | −16.25 | −12.70 | −3.96 |
| Profit factor | 1.21 | 0.92 | 1.68 | 1.27 | 0.59 | 0.68 | 0.88 |

MD's 2021–2024 run (+1039 over four consecutive windows) is the shape
that makes a filter look like it works. 2025 and 2026 H1 give back
−2736.

## 4. The decisive test: size-match the control

Both filters trade about half as often. A halved loss is not an
improvement — it is a smaller bet. The question is whether the filter
beats **the control traded at the same position count**.

| Window | control net | control pos | MH net | MH pos | scaled control | **MH edge** | MD net | MD pos | scaled control | **MD edge** |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | −408 | 114 | −1062 | 58 | −208 | **−854** | +288 | 58 | −208 | +496 |
| 2022 | −1029 | 181 | −897 | 87 | −494 | −402 | −258 | 89 | −506 | +247 |
| 2023 | +583 | 113 | +264 | 52 | +268 | −4 | +686 | 45 | +232 | +454 |
| 2024 | +168 | 117 | −57 | 62 | +89 | −146 | +323 | 53 | +76 | +246 |
| 2025 | −2035 | 230 | −969 | 105 | −929 | −40 | −1885 | 116 | −1026 | **−858** |
| 2026 H1 | −832 | 129 | −942 | 71 | −458 | −484 | −851 | 67 | −432 | **−419** |
| **All** | **−3553** | **884** | **−3663** | **435** | **−1748** | **−1914** | **−1697** | **428** | **−1720** | **+23** |

**G9HICMD adds 23 points over 5.5 years.** It keeps 48.4% of the
positions and takes 47.8% of the loss. That is not a filter; that is a
lot size.

**G9HICMH gives back 1914 points** relative to the same size-matched
control, and its per-window edge is negative in five windows of six.

MD's edge column is also the clearest instance of the pattern this
series keeps producing: **+496 / +247 / +454 / +246** across 2021–2024,
then **−858 / −419** in the two most recent windows — sign flip exactly
where the control loses most.

### 4.1 Paired daily differences

The same test day by day, differencing the filtered run against the
control over all 1400 days (0 on untraded days):

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 H1 | **All** |
|---|---|---|---|---|---|---|---|
| **MH** | −654 | +132 | −318 | −225 | +1066 | −110 | **−110** |
| t | −1.16 | +0.12 | −0.52 | −0.43 | +0.92 | −0.16 | **−0.06** |
| **MD** | +696 | +770 | +104 | +154 | +150 | −19 | **+1856** |
| t | +1.14 | +0.76 | +0.17 | +0.25 | +0.13 | −0.02 | **+0.91** |

Not one window reaches significance in either direction, and neither
aggregate does. MH's total effect on the strategy is **−110 points at
t = −0.06** — it is, in aggregate, doing nothing at all, by cancelling
two large opposite errors (§5).

### 4.2 Randomised halving

Keeping a random ~half of each day's control trades, 4000 draws, matched
to each filter's position count:

| | observed | random-half mean | sd | percentile |
|---|---|---|---|---|
| **G9HICMD** | −1697 | −1762 | 1370 | **52%** |
| **G9HICMH** | −3663 | −1749 | 1360 | **8%** |

MD is indistinguishable from a coin flip. MH is worse than a coin flip,
though at p ≈ 0.08 with two variants tested that is suggestive rather
than established.

## 5. Where the filtered trades come from

Splitting the control's 884 positions into the ones each filter kept
(MA50-aligned) and the ones it dropped, in points per position:

| | kept | dropped |
|---|---|---|
| **MH** | 435 pos @ **−8.42** | 449 pos @ **+0.24** |
| **MD** | 428 pos @ −3.96 | 456 pos @ −4.07 |

**For MD the two halves are statistically the same** (−3.96 vs −4.07).
The daily MA50 splits the trade population into two indistinguishable
piles. That is the direct statement that it carries no directional
information.

**For MH the kept half is the worse one.** By window:

| MH | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 H1 |
|---|---|---|---|---|---|---|
| kept, pts/pos | −18.31 | −10.31 | +5.08 | −0.91 | −9.23 | −13.27 |
| dropped, pts/pos | +11.67 | −1.40 | +5.22 | +4.09 | −8.52 | +1.90 |

The dropped side is better in five windows of six. And MH's aggregate
only reaches the control's level through cancellation:

| MH | days | positions | net |
|---|---|---|---|
| On the 399 days it allowed — **control, both sides** | 399 | 555 | **+1033** |
| On the 399 days it allowed — **MH, allowed side only** | 399 | 435 | **−3663** |
| ⇒ the 120 refused positions on those days | — | 120 | **+4696** |
| On the 294 control days it skipped entirely | 294 | 329 | **−4586** |

MH refuses +4696 points of counter-side trades and avoids −4586 points
of skipped days. Two large errors of opposite sign, netting −110. It is
not filtering; it is churning.

The equivalent split for MD: +4880 refused on its 388 allowed days,
−6735 avoided on the 305 it skipped, netting +1856 — the same structure,
with the skip side happening to be larger this time.

## 6. The mechanism is untouched

The previous document's §4 — capped win against uncapped loss — is not
addressed by a direction filter, and both variants make the ratio
slightly worse:

| | win % | avg win | avg loss | **payoff** | multi-trade days |
|---|---|---|---|---|---|
| G9HIC | 54.4 | +82.7 | −113.2 | **0.73** | 169 |
| G9HICMH | 54.5 | +71.0 | −110.8 | **0.64** | 35 |
| G9HICMD | 58.8 | +70.8 | −114.8 | **0.62** | 40 |

- **MH does not move the win rate at all** — 54.5% against the control's
  54.4%. A direction filter that leaves the hit rate untouched while
  halving the sample is, by definition, uninformative.
- **MD does lift the win rate**, 54.4% → 58.8%, the one genuinely
  positive signal in this study. It is cancelled by the payoff ratio
  falling 0.73 → 0.62, and the net result is §4's +23 points.
- **Both lower the average win by ~12 points** while leaving the average
  loss intact. The reason is visible in the last column: multi-trade
  days collapse from 169 to 35/40. A day that broke both ways and paid
  on the second break now keeps only the first. The filter removes
  winners from the right tail without removing anything from the left —
  the stop distance on the allowed side is unchanged.

## 7. The two MA50s barely differ, and that is the problem

| | days |
|---|---|
| Traded by both | 282 (239 with identical outcomes, 43 differing) |
| MH only | 117 |
| MD only | 106 |
| Traded by neither | 895 |

On the 266 disagreement days, MH nets **−1142** and MD **+823**. The
entire ~1970-point gap between the two variants comes from 19% of
trading days, on which two near-identical rules happen to pick opposite
sides.

That spread is larger than the control's whole 5.5-year loss. Two
plausible readings of "the MA50 at 10:00", differing only in the
timeframe the average is read on, separate by more than the total
quantity under study. This is a measurement of how much noise a marginal
parameter choice injects here — and it is the reason MD's +1856 should
not be read as an effect.

## 8. Conclusion

**Answered and closed, like the target-side experiment before it.**

- **G9HICMD** is position sizing, not selection. Statistically
  indistinguishable from trading G9HIC at 0.48× (edge +23, t = +0.91,
  52nd percentile of random halving). Its better headline is the
  control's loss scaled down, and its 3302-point drawdown scales down
  with it.
- **G9HICMH** is worse than the size-matched control by ~1900 points,
  worse than random halving, and its allowed side loses money on days
  where two-sided trading made money.
- **The MA50-at-10:00 direction gate carries no usable directional
  information** on this setup, at H1 or daily. The one real signal — MD
  lifting the win rate to 58.8% — is fully consumed by the payoff ratio
  it costs.
- **G9HIC remains the control and remains unusable.** Both the
  target-side fix (`G9HICD`, previous document §10) and now the
  entry-side direction fix leave the payoff ratio where it was. Two
  independent attempts at the same structural flaw have both come back
  as pure position-sizing changes.

### What this does not close

The filter was tested at one decision time (10:00) and one period (50).
Nothing here rules out a different regime measure working; what it does
establish is that the specific reading of trend used by the workflow
engine adds nothing to this setup, and that the noise floor between
neighbouring parameter choices (§7, ~1970 points) is wider than any
effect this data could resolve. Any further variant on G9HIC needs to
clear that floor before it means anything.
