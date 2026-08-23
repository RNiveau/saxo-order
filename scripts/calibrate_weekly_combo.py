#!/usr/bin/env python3
"""
Calibrate the weekly combo thresholds against real weekly bars.

The daily thresholds do not transfer: every slope in the combo is measured
over a fixed number of candles, so on weekly bars it spans roughly five
times the calendar period the daily constants were fitted on. This script
reports what those slopes actually look like on the universe the scanner
covers, so COMBO_SETTINGS[UnitTime.W] can be set from measurement rather
than from the daily values.

It also reports the share of sampled assets holding enough weekly history
to be eligible at all, which answers SC-004.

Raw provider responses are cached to disk, so re-running costs nothing.

Usage:
    poetry run python scripts/calibrate_weekly_combo.py
    poetry run python scripts/calibrate_weekly_combo.py --sample 80
    poetry run python scripts/calibrate_weekly_combo.py --refresh
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent.parent))

from client import client_helper  # noqa: E402
from client.saxo_client import SaxoClient  # noqa: E402
from model import AssetType, Candle, UnitTime  # noqa: E402
from services.indicator_service import (  # noqa: E402
    bollinger_bands,
    mobile_average,
    slope_percentage,
)
from utils.configuration import Configuration  # noqa: E402

WEEKLY_HORIZON = 10080
WEEKLY_COUNT = 70
MIN_WEEKLY_CANDLES = 60
DEFAULT_SAMPLE_SIZE = 40
SAMPLE_SEED = 29
CACHE_FILE = "weekly_calibration_cache.json"
PERCENTILES = (5, 10, 25, 50, 75, 90, 95)


def load_sample(sample_size: int) -> List[Dict[str, Any]]:
    with open("stocks.json", "r") as f:
        stocks = json.load(f)
    if sample_size >= len(stocks):
        return stocks
    return random.Random(SAMPLE_SEED).sample(stocks, sample_size)


def load_cache(refresh: bool) -> Dict[str, Any]:
    if refresh or not Path(CACHE_FILE).is_file():
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def save_cache(cache: Dict[str, Any]) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, default=str)


def fetch_weekly_data(
    saxo_client: SaxoClient,
    asset: Dict[str, Any],
    cache: Dict[str, Any],
) -> List[Dict[str, Any]]:
    key = str(asset["saxo_uic"])
    if key in cache:
        return cache[key]
    data = saxo_client.get_historical_data(
        asset_type=AssetType.STOCK,
        saxo_uic=asset["saxo_uic"],
        horizon=WEEKLY_HORIZON,
        count=WEEKLY_COUNT,
    )
    cache[key] = data
    return data


def measure(candles: List[Candle]) -> Optional[Dict[str, float]]:
    if len(candles) < MIN_WEEKLY_CANDLES:
        return None
    ma50 = mobile_average(candles, 50)
    ma50_first = mobile_average(candles[10:], 50)
    bb25 = bollinger_bands(candles, 2.5)
    bb_first = bollinger_bands(candles[3:], 2.5)
    return {
        "ma50_slope": slope_percentage(0, ma50_first, 10, ma50),
        "bbh_slope": slope_percentage(0, bb_first.up, 3, bb25.up),
        "bbb_slope": slope_percentage(0, bb_first.bottom, 3, bb25.bottom),
    }


def percentiles(values: List[float]) -> List[Tuple[int, float]]:
    ordered = sorted(values)
    last = len(ordered) - 1
    return [
        (p, ordered[min(last, int(round(p / 100 * last)))])
        for p in PERCENTILES
    ]


def report(
    measurements: List[Dict[str, float]], eligible: int, total: int
) -> None:
    print()
    print(f"Sampled assets:  {total}")
    print(
        f"Eligible assets: {eligible} "
        f"({eligible / total:.0%} with at least "
        f"{MIN_WEEKLY_CANDLES} weekly bars) [SC-004]"
    )
    if not measurements:
        print("No eligible asset in the sample - nothing to calibrate.")
        return

    for metric in ("ma50_slope", "bbh_slope", "bbb_slope"):
        raw = [m[metric] for m in measurements]
        magnitude = [abs(value) for value in raw]
        print()
        print(f"{metric} over {len(raw)} assets")
        print("  signed percentiles:")
        for level, value in percentiles(raw):
            print(f"    p{level:<3} {value:>10.2f}")
        print("  absolute percentiles:")
        for level, value in percentiles(magnitude):
            print(f"    p{level:<3} {value:>10.2f}")

    print()
    print(
        "Read ma50_slope to pick the direction floor and the strong level, "
        "and the absolute band slopes to pick the flatness ceiling. A floor "
        "admitting nearly every asset, or a ceiling admitting almost none, "
        "is the daily value showing through."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calibrate the weekly combo thresholds"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"assets to sample (default {DEFAULT_SAMPLE_SIZE})",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignore the cached responses and fetch again",
    )
    args = parser.parse_args()

    sample = load_sample(args.sample)
    cache = load_cache(args.refresh)
    saxo_client = SaxoClient(Configuration("config.yml"))

    measurements: List[Dict[str, float]] = []
    eligible = 0
    for asset in sample:
        try:
            data = fetch_weekly_data(saxo_client, asset, cache)
        except Exception as e:
            print(f"skipped {asset['name']}: {e}")
            continue
        candles = client_helper.map_data_to_candles(data, ut=UnitTime.W)
        measurement = measure(candles)
        if measurement is None:
            print(f"{asset['name']}: {len(candles)} weekly bars, ineligible")
            continue
        eligible += 1
        measurements.append(measurement)

    save_cache(cache)
    report(measurements, eligible, len(sample))


if __name__ == "__main__":
    main()
