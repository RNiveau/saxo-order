# Weekly Combo Calibration (T002)

**Feature**: 029-combo-weekly-timeframe | **Run**: 2026-08-23 | **Config**: `prod_config.yml`
**Command**: `poetry run python scripts/calibrate_weekly_combo.py --config prod_config.yml`

Measured over the whole scanned universe, on completed weekly bars
(`horizon=10080`, `count=70`). Slopes read through `combo_slopes()`, so these are
the values the detector itself scores against.

## Coverage — SC-004

| | |
|---|---|
| Measured assets | 123 |
| Unreachable | 2 (Neoen, Plastic Omnium — empty provider response) |
| Fetched | 121 |
| **Eligible (≥60 weekly bars)** | **121 — 100% of fetched** |

**SC-004 passes**, against a bar of 80%. Dropping the `macd` criterion brings the
history requirement from 235 bars to 60, and at 60 the entire reachable universe
qualifies. Had the full criteria set been kept, the requirement would have been
~4.5 years of weekly history per asset.

The two unreachable names are counted as unreachable rather than as holding no
history, so they do not depress the ratio.

## Distributions (121 assets)

Absolute percentiles — the ones the thresholds are read from.

| percentile | \|ma50_slope\| | \|bbh_slope\| | \|bbb_slope\| |
|---|---|---|---|
| p5 | 3.36 | 1.82 | 2.51 |
| p10 | 6.48 | 5.23 | 5.88 |
| p25 | 14.59 | 19.63 | 44.13 |
| p50 | 36.07 | 64.49 | 99.53 |
| p75 | 61.17 | 144.88 | 216.99 |
| p90 | 91.07 | 240.69 | 446.87 |
| p95 | 130.95 | 327.02 | 668.27 |

Signed medians: `ma50_slope` −0.37, `bbh_slope` +1.34, `bbb_slope` +50.68.

## What the daily constants would have done

This is the measurement the feature existed to take, and it confirms the premise:

| Daily constant | Effect on weekly bars |
|---|---|
| `ma50_slope_min = 3.0` | p5 of \|ma50_slope\| is **3.36** → admits ~95% of assets. Not a filter |
| `ma50_slope_strong = 10.0` | p10 is **6.48** → ~88% would score `strong_ma50`. The top band becomes the default |
| `bb_flat_slope_max = 5.0` | ~10% of upper bands and ~9% of lower bands qualify as flat; `both_bb_flat` falls to ~1%. The criterion dies |

## Chosen values

| Setting | Value | Time-scaling check | Empirical position |
|---|---|---|---|
| `ma50_slope_min` | **15.0** | 3.0 × 5 = 15.0 | p25 of \|ma50_slope\| = 14.59 |
| `ma50_slope_strong` | **50.0** | 10.0 × 5 = 50.0 | between p50 (36.07) and p75 (61.17) |
| `bb_flat_slope_max` | **25.0** | 5.0 × 5 = 25.0 | ≈p28 of \|bbh\|, ≈p18 of \|bbb\| |
| `strong_signal_min` | **3** | — | 3 of 4 criteria; 4 would demand a perfect score |
| `min_candles` | **60** | — | the reduced criteria set's floor |

**Why two methods agree.** The daily detector measures the MA50 slope over 10
daily candles — about two weeks — so 3% there is 1.5% per week. The weekly
detector measures over 10 weekly candles, so 15% is *also* 1.5% per week: the
same economic statement re-expressed on a longer bar. That this lands within 3%
of the measured p25 is the corroboration, not the derivation.

At `bb_flat_slope_max = 25.0`, roughly 40% of assets have at least one flat band
(clearing the gate that rejects when neither is flat) and under 10% have both, so
`both_bb_flat` stays a genuine bonus rather than a free point.

## Judgement call recorded

`ma50_slope_strong` could be **61.0** instead of 50.0 if "strong" should mean
strictly the top quartile of trends rather than the time-scaled equivalent of the
daily level. 50.0 was chosen for consistency with the daily semantics; the two
differ by roughly one decile of the population.

## Emission rate — SC-005

Measured 2026-08-30 from the cached responses, so on the same weekly bars as the
distributions above (the percentiles reproduce exactly, which is how the cache
hit is visible).

```
Would emit a weekly combo: 2 (2% of eligible) [SC-005]
    strong     1
    weak       1
```

**Two assets out of 121.** SC-005 caps weekly combos at 15% of the asset-days a
digest surfaces; at 2% of eligible assets on a bar there is no plausible way to
reach that ceiling, so the thresholds need no tightening before the trial. The
criterion is still formally open — it asks for a share of digest asset-days over
a two-week window, which only production can answer — but the direction of the
risk is settled: the signal is scarce, not floody.

The gap between what the thresholds admit and what actually emits is the point
worth recording. Roughly 40% of assets clear the band gate and ~72% clear the
direction floor, yet 2% emit. The three price-position gates in
`_combo_for_direction` — wrong side of the MA50, a breached 2.5 band, too far
from both the inner band and the MA50 — do nearly all of the filtering, and they
are ATR-scaled, so they self-adjusted to the weekly timeframe without being
recalibrated. The zero-criteria rule cuts again after that.

**The residual risk is now the opposite one.** At this rate a weekly combo is a
rare event — on the order of one or two names a week, and only on the weeks the
setup appears at all. If a trial period passes with no weekly alert whatsoever,
that is not a bug to hunt: it is this number, and the lever is `ma50_slope_min`
(15.0 sits at p25) or `bb_flat_slope_max` (25.0 admits one flat band for ~40% of
assets), loosened deliberately rather than by accident.

## Reproducing

```bash
poetry run python scripts/calibrate_weekly_combo.py --config prod_config.yml
```

Raw responses are cached in `weekly_calibration_cache.json` (gitignored), so a
re-run costs no provider requests. `--refresh` re-fetches. The config file must
match the environment the tokens were minted for — a mismatch returns 401 on
every asset.
