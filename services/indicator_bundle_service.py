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


# name -> (minimum bars, how to compute it)
#
# The minimums mirror the guards in indicator_service: a moving average needs
# its period, ATR and ADX need period * 3 for Wilder's double smoothing, and
# macd0lag needs signal * 9 + long * 6 - 2. A slope reads the average twice,
# SLOPE_LOOKBACK bars apart, so it needs that many more than the average.
#
# bollinger_bands is the exception: it slices rather than raising, so with
# too little history it would return a confident band built from a handful
# of closes. Its minimum is enforced here instead.
REGISTRY: Dict[IndicatorName, tuple] = {
    IndicatorName.MM7: (7, _ma(7)),
    IndicatorName.MM20: (20, _ma(20)),
    IndicatorName.MM50: (50, _ma(50)),
    IndicatorName.MM200: (200, _ma(200)),
    IndicatorName.MM7_SLOPE: (7 + SLOPE_LOOKBACK, _ma_slope(7)),
    IndicatorName.MM20_SLOPE: (20 + SLOPE_LOOKBACK, _ma_slope(20)),
    IndicatorName.MM50_SLOPE: (50 + SLOPE_LOOKBACK, _ma_slope(50)),
    IndicatorName.MM200_SLOPE: (200 + SLOPE_LOOKBACK, _ma_slope(200)),
    IndicatorName.BOLLINGER: (BOLLINGER_PERIOD, _bollinger),
    IndicatorName.ATR: (ATR_PERIOD * 3, indicator_service.average_true_range),
    IndicatorName.ADX: (ADX_PERIOD * 3, indicator_service.adx),
    IndicatorName.MACD0LAG: (235, _macd0lag),
}

DEFAULT_INDICATORS: List[IndicatorName] = list(REGISTRY)


def required_bars(requested: List[IndicatorName]) -> int:
    """How much history to fetch for exactly these indicators.

    The deepest one decides, so a request for MM7 alone costs 7 bars rather
    than the 235 the whole set would need.
    """
    return max(REGISTRY[name][0] for name in requested)


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
        minimum, compute = REGISTRY[name]
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
            f"{min(REGISTRY[n][0] for n in requested)}"
        )
    return outcomes
