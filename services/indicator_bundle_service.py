"""Every indicator an analysis snapshot can carry, computed in one pass.

The point of this module is the depth table below. The indicators differ
enormously in how much history they need - 7 bars for a short average, 235
for the lag-reduced MACD - so asking for one cheap number should not pay for
the most expensive one's history, and asking for six should not fetch the
series six times.

Nothing here calculates anything. Every entry delegates to
``services/indicator_service.py``, which is what the scheduled scan runs,
so an on-demand answer and a scan answer cannot drift apart.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union

from model import Candle, IndicatorName
from services import indicator_service
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("indicator_bundle_service")

Value = Union[float, Dict[str, float]]

# The scan reads a moving average's slope over this many bars
# (saxo_order/commands/alerting.py), so the same span is used here.
SLOPE_LOOKBACK = 10

BOLLINGER_PERIOD = 20
ATR_PERIOD = 14
ADX_PERIOD = 14


# What the scheduled scan reads for a daily series. Recursive indicators
# are seeded from the oldest bar and smoothed forward, so the number of
# bars changes the answer - fetching one of those at its bare minimum
# returns a warm-up value that disagrees with the scan for the same
# instrument on the same day. They are fetched at this depth instead.
SCAN_DEPTH = 250


@dataclass
class IndicatorOutcome:
    """One indicator's answer: a value, or why there isn't one."""

    name: IndicatorName
    value: Optional[Value] = None
    unavailable_reason: Optional[str] = None


def _ma(period: int) -> Callable[[List[Candle]], Value]:
    return lambda candles: indicator_service.mobile_average(candles, period)


def _ma_slope(period: int) -> Callable[[List[Candle]], Value]:
    def compute(candles: List[Candle]) -> Value:
        latest = indicator_service.mobile_average(candles, period)
        earlier = indicator_service.mobile_average(
            candles[SLOPE_LOOKBACK:], period
        )
        return indicator_service.slope_percentage(
            0, earlier, SLOPE_LOOKBACK, latest
        )

    return compute


def _bollinger(candles: List[Candle]) -> Value:
    bands = indicator_service.bollinger_bands(candles, period=BOLLINGER_PERIOD)
    return {"up": bands.up, "middle": bands.middle, "bottom": bands.bottom}


def _macd0lag(candles: List[Candle]) -> Value:
    macd, signal = indicator_service.macd0lag(candles)
    return {"macd": round(macd, 4), "signal": round(signal, 4)}


@dataclass(frozen=True)
class Spec:
    """What an indicator needs, and what it should be given.

    ``minimum_bars`` is the feasibility floor - below it the calculation
    cannot run at all, and that is what an unavailable answer reports.

    ``fetch_bars`` is what to actually request. For a windowed indicator the
    two are the same: a 7-bar average reads exactly 7 closes and gives the
    same number whether 7 or 250 were fetched. A recursive one is different
    - it is seeded from the oldest bar available and smoothed forward, so
    the depth is part of the answer, and asking at the floor returns a
    warm-up value that disagrees with the scan.
    """

    minimum_bars: int
    fetch_bars: int
    compute: Callable[[List[Candle]], Value]


def _windowed(bars: int, compute: Callable[[List[Candle]], Value]) -> Spec:
    return Spec(minimum_bars=bars, fetch_bars=bars, compute=compute)


def _recursive(bars: int, compute: Callable[[List[Candle]], Value]) -> Spec:
    return Spec(
        minimum_bars=bars, fetch_bars=max(bars, SCAN_DEPTH), compute=compute
    )


# The minimums mirror the guards in indicator_service: a moving average needs
# its period, ATR and ADX need period * 3 for Wilder's double smoothing, and
# macd0lag needs signal * 9 + long * 6 - 2. A slope reads the average twice,
# SLOPE_LOOKBACK bars apart, so it needs that many more than the average.
#
# bollinger_bands is the exception: it slices rather than raising, so with
# too little history it would return a confident band built from a handful
# of closes. Its minimum is enforced here instead.
REGISTRY: Dict[IndicatorName, Spec] = {
    IndicatorName.MM7: _windowed(7, _ma(7)),
    IndicatorName.MM20: _windowed(20, _ma(20)),
    IndicatorName.MM50: _windowed(50, _ma(50)),
    IndicatorName.MM200: _windowed(200, _ma(200)),
    IndicatorName.MM7_SLOPE: _windowed(7 + SLOPE_LOOKBACK, _ma_slope(7)),
    IndicatorName.MM20_SLOPE: _windowed(20 + SLOPE_LOOKBACK, _ma_slope(20)),
    IndicatorName.MM50_SLOPE: _windowed(50 + SLOPE_LOOKBACK, _ma_slope(50)),
    IndicatorName.MM200_SLOPE: _windowed(200 + SLOPE_LOOKBACK, _ma_slope(200)),
    IndicatorName.BOLLINGER: _windowed(BOLLINGER_PERIOD, _bollinger),
    IndicatorName.ATR: _recursive(
        ATR_PERIOD * 3, indicator_service.average_true_range
    ),
    IndicatorName.ADX: _recursive(ADX_PERIOD * 3, indicator_service.adx),
    IndicatorName.MACD0LAG: _recursive(235, _macd0lag),
}

DEFAULT_INDICATORS: List[IndicatorName] = list(REGISTRY)


def required_bars(requested: List[IndicatorName]) -> int:
    """How much history to fetch for exactly these indicators.

    The hungriest one decides, so a request for MM7 alone costs 7 bars
    rather than what the whole set would need. A recursive indicator asks
    for the scan's depth even though it could technically run on less -
    the extra bars are what make its answer the same as the scan's.
    """
    return max(REGISTRY[name].fetch_bars for name in requested)


def compute_bundle(
    candles: List[Candle], requested: List[IndicatorName]
) -> List[IndicatorOutcome]:
    """Compute each requested indicator, isolating the ones that cannot be.

    Every requested indicator comes back, in the order asked for. One that
    cannot be computed carries the reason instead of a value - it is never
    simply missing, because a reader cannot tell an absent key from a flat
    number.

    Raises only when nothing at all could be computed: a series too short
    for even the shallowest indicator is a failed request, while a series
    too short for the deepest is a partial answer.
    """
    outcomes: List[IndicatorOutcome] = []
    for name in requested:
        spec = REGISTRY[name]
        minimum, compute = spec.minimum_bars, spec.compute
        if len(candles) < minimum:
            outcomes.append(
                IndicatorOutcome(
                    name=name,
                    unavailable_reason=(
                        f"needs {minimum} bars, got {len(candles)}"
                    ),
                )
            )
            continue
        try:
            outcomes.append(
                IndicatorOutcome(name=name, value=compute(candles))
            )
        except SaxoException as e:
            logger.warning(f"{name.value} could not be computed: {e}")
            outcomes.append(
                IndicatorOutcome(name=name, unavailable_reason=str(e))
            )

    if outcomes and all(o.value is None for o in outcomes):
        raise SaxoException(
            f"No indicator could be computed from {len(candles)} bars; "
            f"the shallowest requested needs "
            f"{min(REGISTRY[n].minimum_bars for n in requested)}"
        )
    return outcomes
