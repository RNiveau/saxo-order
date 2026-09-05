import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy

from client.saxo_client import SaxoClient
from model import (
    BollingerBands,
    Candle,
    ComboSignal,
    Direction,
    SignalStrength,
    UnitTime,
)
from utils.exception import SaxoException
from utils.logger import Logger


def double_top(candles: List[Candle], tick=float) -> Optional[Candle]:
    """
    If a double top exist in the list, return true
    The top can be another candle than the first one
    We accept a spread of one tick between two tops
    """
    if len(candles) < 2:
        return None

    tops: List[Candle] = []

    if candles[0].higher >= candles[1].higher:
        tops.append(candles[0])

    for i in range(1, len(candles) - 1):
        if (
            candles[i].higher >= candles[i - 1].higher
            and candles[i].higher >= candles[i + 1].higher
        ):
            tops.append(candles[i])

    if candles[-1].higher >= candles[-2].higher:
        tops.append(candles[-1])
    # Check if there are two tops within one tick spread
    for i in range(len(tops)):
        for j in range(i + 1, len(tops)):
            if round(abs(tops[i].higher - tops[j].higher), 4) <= tick:
                return tops[i]
    return None


def double_bottom(candles: List[Candle], tick=float) -> Optional[Candle]:
    """
    If a double bottom exist in the list, return the trough candle
    The bottom can be another candle than the first one
    We accept a spread of one tick between two bottoms
    """
    if len(candles) < 2:
        return None

    bottoms: List[Candle] = []

    if candles[0].lower <= candles[1].lower:
        bottoms.append(candles[0])

    for i in range(1, len(candles) - 1):
        if (
            candles[i].lower <= candles[i - 1].lower
            and candles[i].lower <= candles[i + 1].lower
        ):
            bottoms.append(candles[i])

    if candles[-1].lower <= candles[-2].lower:
        bottoms.append(candles[-1])
    # Check if there are two bottoms within one tick spread
    for i in range(len(bottoms)):
        for j in range(i + 1, len(bottoms)):
            if round(abs(bottoms[i].lower - bottoms[j].lower), 4) <= tick:
                return bottoms[i]
    return None


def bollinger_bands(
    candles: List[Candle], multiply_std: float = 2.0, period: int = 20
) -> BollingerBands:
    candles = candles[:period]
    closes = list(map(lambda x: x.close, candles))
    std = numpy.std(closes)
    avg = numpy.average(closes)
    return BollingerBands(
        bottom=float(round(avg - multiply_std * std, 4)),
        up=float(round(avg + multiply_std * std, 4)),
        middle=float(round(avg, 4)),
    )


def mobile_average(candles: List[Candle], period: int) -> float:
    if len(candles) < period:
        Logger.get_logger("mobile_average").error(
            "Missing candles to calculate" f" the ma {len(candles)}, {period}"
        )
        raise SaxoException("Missing candles to calcule the ma")
    return sum(map(lambda x: x.close, candles[:period])) / period


MM50_TOUCH_PROXIMITY = 0.01
MM50_TOUCH_SLOPE_MIN = 3.0

MM7_PERIOD = 7
# A close that merely grazes the average is not a break: price has to clear it
# by a margin to count.
MM7_BREAK_MIN_DISTANCE = 0.005
# ...and it has to flip a short-term run rather than cross back and forth. A
# raw cross fires on a large share of the universe every day, which would
# drown the daily digest instead of informing it.
MM7_BREAK_MIN_STREAK = 3
MM7_BREAK_MIN_CANDLES = MM7_PERIOD + MM7_BREAK_MIN_STREAK

COMBO_MA50_SLOPE_MIN = 3.0
COMBO_MA50_SLOPE_STRONG = 10.0
COMBO_BB_FLAT_SLOPE_MAX = 5.0
COMBO_BB_BREACH_TOLERANCE = 0.001
COMBO_BB_TOLERANCE = 0.005
COMBO_ATR_BB_MARGIN = 0.3
COMBO_ATR_MA50_MARGIN = 0.1
COMBO_STRONG_SIGNAL_MIN = 4
# macd0lag feeds one scoring criterion but is the deepest reader here: see its
# docstring for where 235 comes from. Deferring it spares the candle sets that
# never reach it, but a set that does reach it still needs the full history,
# so combo declines up front rather than raising mid-scoring.
COMBO_MIN_CANDLES = 235
COMBO_WEEKLY_MIN_CANDLES = 60
# Weekly values from the calibration pass over the scanned universe, recorded
# in specs/029-combo-weekly-timeframe/calibration.md. They are not the daily
# ones rescaled by taste: every slope here spans a fixed number of candles, so
# on weekly bars it covers five times the calendar period, and the measured
# distribution says the daily floor would admit 95% of assets.
COMBO_WEEKLY_MA50_SLOPE_MIN = 15.0
COMBO_WEEKLY_MA50_SLOPE_STRONG = 50.0
COMBO_WEEKLY_BB_FLAT_SLOPE_MAX = 25.0
# One criterion fewer than daily, so the top band cannot ask for all of them.
COMBO_WEEKLY_STRONG_SIGNAL_MIN = 3


@dataclass(frozen=True)
class ComboSettings:
    """What separates one timeframe's combo from another's.

    The criteria themselves are identical; only these values and the presence
    of the macd criterion differ. macd is what forces the 235-candle history,
    so dropping it on weekly is also what brings the requirement down to 60.
    """

    min_candles: int
    ma50_slope_min: float
    ma50_slope_strong: float
    bb_flat_slope_max: float
    strong_signal_min: int
    use_macd: bool


# Only the timeframes whose thresholds were measured. Every other unit time
# reaches the detector through combo()'s default, which is the daily entry -
# the same constants they scored against before the settings existed, so a
# combo workflow on H1 or H4 is unaffected. Indexing this map with one of them
# raises rather than quietly serving daily values under another timeframe's
# name: an uncalibrated timeframe is a decision to take, not a default to
# inherit.
COMBO_SETTINGS: Dict[UnitTime, ComboSettings] = {
    UnitTime.D: ComboSettings(
        min_candles=COMBO_MIN_CANDLES,
        ma50_slope_min=COMBO_MA50_SLOPE_MIN,
        ma50_slope_strong=COMBO_MA50_SLOPE_STRONG,
        bb_flat_slope_max=COMBO_BB_FLAT_SLOPE_MAX,
        strong_signal_min=COMBO_STRONG_SIGNAL_MIN,
        use_macd=True,
    ),
    UnitTime.W: ComboSettings(
        min_candles=COMBO_WEEKLY_MIN_CANDLES,
        ma50_slope_min=COMBO_WEEKLY_MA50_SLOPE_MIN,
        ma50_slope_strong=COMBO_WEEKLY_MA50_SLOPE_STRONG,
        bb_flat_slope_max=COMBO_WEEKLY_BB_FLAT_SLOPE_MAX,
        strong_signal_min=COMBO_WEEKLY_STRONG_SIGNAL_MIN,
        use_macd=False,
    ),
}


def mm50_touch(candles: List[Candle]) -> Optional[Dict[str, float]]:
    if len(candles) < 60:
        return None
    ma50_last = mobile_average(candles, 50)
    ma50_first = mobile_average(candles[10:], 50)
    slope = slope_percentage(0, ma50_first, 10, ma50_last)
    close = candles[0].close
    if abs(close - ma50_last) / ma50_last > MM50_TOUCH_PROXIMITY:
        return None
    if slope < MM50_TOUCH_SLOPE_MIN:
        return None
    return {
        "close": close,
        "ma50": ma50_last,
        "distance_pct": (close - ma50_last) / ma50_last * 100,
        "slope": slope,
    }


def _mm7_at(candles: List[Candle], offset: int) -> float:
    """
    The MM7 as it stood at candles[offset], i.e. that candle and the 6 older
    ones. Newest is index 0, so dropping the first `offset` entries walks
    backwards in time and `mobile_average` then reads the 7 newest of what
    remains - candles[offset:offset+7]. Same idiom as mm50_touch's
    mobile_average(candles[10:], 50) for the MA50 of 10 candles ago.
    """
    return mobile_average(candles[offset:], MM7_PERIOD)


def _mm7_streak(candles: List[Candle], direction: Direction) -> int:
    """
    Number of consecutive candles before the break that closed on the side the
    price is leaving. Stops as soon as the history runs short of a full MM7.
    """
    streak = 0
    offset = 1
    while len(candles) - offset >= MM7_PERIOD:
        mm7 = _mm7_at(candles, offset)
        close = candles[offset].close
        on_previous_side = (
            close >= mm7 if direction == Direction.SELL else close <= mm7
        )
        if not on_previous_side:
            break
        streak += 1
        offset += 1
    return streak


def mm7_break(candles: List[Candle]) -> Optional[Dict[str, Any]]:
    """
    Detect the last candle closing through the 7-period mobile average.

    A break is a short-term timing signal, not a thesis: it only fires when
    the close clears the average by MM7_BREAK_MIN_DISTANCE and the previous
    MM7_BREAK_MIN_STREAK candles all closed on the other side, so chop around
    a flat average stays silent.
    """
    if len(candles) < MM7_BREAK_MIN_CANDLES:
        return None

    mm7 = _mm7_at(candles, 0)
    close = candles[0].close
    distance = (close - mm7) / mm7

    if distance < -MM7_BREAK_MIN_DISTANCE:
        direction = Direction.SELL
    elif distance > MM7_BREAK_MIN_DISTANCE:
        direction = Direction.BUY
    else:
        return None

    streak = _mm7_streak(candles, direction)
    if streak < MM7_BREAK_MIN_STREAK:
        return None

    return {
        "close": close,
        "mm7": mm7,
        "previous_close": candles[1].close,
        "previous_mm7": _mm7_at(candles, 1),
        "distance_pct": distance * 100,
        "direction": direction.value,
        "streak": streak,
    }


def containing_candle(candles: List[Candle]) -> Optional[Candle]:
    if len(candles) >= 2:
        if (
            candles[0].open <= candles[1].lower
            and candles[0].close >= candles[1].higher
        ):
            return candles[0]
        if (
            candles[0].open >= candles[1].higher
            and candles[0].close <= candles[1].lower
        ):
            return candles[0]
    return None


def is_price_within_bands(
    close: float, *, outer: float, inner: float, direction: Direction
) -> bool:
    """
    True when close sits in the zone between the 2.0 (inner) and the 2.5
    (outer) bollinger band, widened by COMBO_BB_TOLERANCE at both ends.
    Both bands must be read at the same candle offset as the close.
    """
    if direction == Direction.BUY:
        return (
            outer * (1 - COMBO_BB_TOLERANCE)
            < close
            < inner * (1 + COMBO_BB_TOLERANCE)
        )
    return (
        inner * (1 - COMBO_BB_TOLERANCE)
        < close
        < outer * (1 + COMBO_BB_TOLERANCE)
    )


def is_far_from_levels(
    candles: List[Candle],
    band: float,
    ma50: float,
    margin_band: float,
    margin_ma50: float,
    direction: Direction,
) -> bool:
    """
    True when the last two candles sit clear of both the 2.0 bollinger band
    and the ma50: the pullback never came close enough to be tradable.
    The levels are supports for a buy and resistances for a sell.
    The candle extreme facing the level is used - the low for a buy, the
    high for a sell - so a wick reaching the level counts as a touch.
    """
    if len(candles) < 2:
        Logger.get_logger("is_far_from_levels").error(
            "Two candles are needed to measure the distance,"
            f" got {len(candles)}"
        )
        raise SaxoException("Missing candles")
    closes = [candle.close for candle in candles[:2]]
    if direction == Direction.BUY:
        values = closes + [candle.lower for candle in candles[:2]]
        return all(value > band + margin_band for value in values) and all(
            value > ma50 + margin_ma50 for value in values
        )
    values = closes + [candle.higher for candle in candles[:2]]
    return all(value < band - margin_band for value in values) and all(
        value < ma50 - margin_ma50 for value in values
    )


class _ComboContext:
    """
    The indicators a combo is scored against, computed once per candle set.

    macd0lag costs about 80% of a combo call and feeds a single scoring
    criterion, so it is computed on first use. A candle set whose ma50 is
    flat, or whose two bollinger bands both slope, never pays for it - and
    never raises over the 235 candles macd0lag needs, where everything else
    here is satisfied by 60.
    """

    def __init__(
        self,
        candles: List[Candle],
        settings: Optional[ComboSettings] = None,
    ) -> None:
        self.candles = candles
        self.settings = settings or COMBO_SETTINGS[UnitTime.D]
        self.ma50 = mobile_average(candles, 50)
        ma50_first = mobile_average(candles[10:], 50)
        self.ma50_slope = slope_percentage(0, ma50_first, 10, self.ma50)
        self.bb25 = bollinger_bands(candles, 2.5)
        self.bb25_previous = bollinger_bands(candles[1:], 2.5)
        self.bb20 = bollinger_bands(candles, 2.0)
        self.bb20_previous = bollinger_bands(candles[1:], 2.0)
        bb_first = bollinger_bands(candles[3:], 2.5)
        self.bbh_slope = slope_percentage(0, bb_first.up, 3, self.bb25.up)
        self.bbb_slope = slope_percentage(
            0, bb_first.bottom, 3, self.bb25.bottom
        )
        atr = average_true_range(candles)
        self.margin_band = atr * COMBO_ATR_BB_MARGIN
        self.margin_ma50 = atr * COMBO_ATR_MA50_MARGIN
        self._macd0lag: Optional[Tuple[float, float]] = None

    @property
    def both_bb_flat(self) -> bool:
        maximum = self.settings.bb_flat_slope_max
        return abs(self.bbh_slope) < maximum and abs(self.bbb_slope) < maximum

    @property
    def neither_bb_flat(self) -> bool:
        maximum = self.settings.bb_flat_slope_max
        return abs(self.bbh_slope) > maximum and abs(self.bbb_slope) > maximum

    @property
    def macd0lag(self) -> Tuple[float, float]:
        if self._macd0lag is None:
            self._macd0lag = macd0lag(self.candles)
        return self._macd0lag


def _combo_for_direction(
    context: _ComboContext, direction: Direction
) -> Optional[ComboSignal]:
    """
    Score a combo in one direction. The buy and the sell case are exact
    mirrors, so they run through this single body: `sign` flips every
    comparison, `band`/`inner` pick the side of the bollinger bands facing
    the price, `trigger_level` is the previous candle's extreme the close
    must clear to count as triggered, and `pending_price` is where the order
    waits until it does.
    """
    logger = Logger.get_logger("combo")
    candles = context.candles
    close = candles[0].close
    if direction == Direction.BUY:
        sign = 1.0
        band, band_previous = context.bb25.bottom, context.bb25_previous.bottom
        inner, inner_previous = (
            context.bb20.bottom,
            context.bb20_previous.bottom,
        )
        trigger_level, pending_price = candles[1].higher, candles[0].higher
    else:
        sign = -1.0
        band, band_previous = context.bb25.up, context.bb25_previous.up
        inner, inner_previous = context.bb20.up, context.bb20_previous.up
        trigger_level, pending_price = candles[1].lower, candles[0].lower

    if sign * close < sign * context.ma50:
        logger.debug(
            f"close {close} is on the wrong side of the ma50 {context.ma50}"
            f" for a {direction.value} combo"
        )
        return None
    if sign * close < sign * band * (1 - sign * COMBO_BB_BREACH_TOLERANCE):
        logger.debug(f"close {close} has breached the bb 2.5 {band}")
        return None
    if is_far_from_levels(
        candles,
        inner,
        context.ma50,
        context.margin_band,
        context.margin_ma50,
        direction,
    ):
        logger.debug(
            f"candle {candles[0]} is far from the bb 2.0 {inner}"
            f" and from the ma50 {context.ma50}"
        )
        return None

    settings = context.settings
    criteria = {}
    if settings.use_macd:
        criteria["macd"] = (
            sign * context.macd0lag[0] > sign * context.macd0lag[1]
        )
    criteria.update(
        {
            "ma50_over_bb": sign * context.ma50 < sign * band,
            # candle -1 or candle is between bb 2.0 / 2.5
            "price_within_bb": is_price_within_bands(
                candles[1].close,
                outer=band_previous,
                inner=inner_previous,
                direction=direction,
            )
            or is_price_within_bands(
                close, outer=band, inner=inner, direction=direction
            ),
            "strong_ma50": (
                sign * context.ma50_slope > settings.ma50_slope_strong
            ),
            "both_bb_flat": context.both_bb_flat,
        }
    )
    signal = sum(criteria.values())
    if signal == 0:
        # Not a weak combo - no combo. The candle cleared the three
        # structural gates and then met none of the scoring criteria, which
        # says the setup is absent rather than faint. Returning a WEAK signal
        # here made "nothing found" indistinguishable from "found, barely",
        # and every consumer downstream had to guess which it was holding.
        logger.debug(
            f"no {direction.value} combo: none of the {len(criteria)}"
            " criteria are met"
        )
        return None
    combo_signal = ComboSignal(
        price=0,
        direction=direction,
        has_been_triggered=False,
        strength=SignalStrength.MEDIUM,
        details=dict(criteria),
    )

    if sign * close > sign * trigger_level:
        combo_signal.has_been_triggered = True
        combo_signal.price = close
    else:
        combo_signal.price = pending_price
    if signal == 1:
        combo_signal.strength = SignalStrength.WEAK
    elif signal >= settings.strong_signal_min:
        combo_signal.strength = SignalStrength.STRONG
    return combo_signal


def combo_slopes(candles: List[Candle]) -> Dict[str, float]:
    """
    The three slopes a combo is gated on, for the same candles it would score.

    Calibrating a timeframe means looking at what these actually measure on
    that timeframe. Reading them off the context the detector itself builds
    keeps the calibration and the detector from drifting apart when a span
    or a multiplier moves.
    """
    context = _ComboContext(candles)
    return {
        "ma50_slope": context.ma50_slope,
        "bbh_slope": context.bbh_slope,
        "bbb_slope": context.bbb_slope,
    }


def combo(
    candles: List[Candle], settings: Optional[ComboSettings] = None
) -> Optional[ComboSignal]:
    logger = Logger.get_logger("combo")
    settings = settings or COMBO_SETTINGS[UnitTime.D]
    if len(candles) < settings.min_candles:
        logger.debug(
            f"not enough candles for a combo {len(candles)},"
            f" needed {settings.min_candles}"
        )
        return None
    logger.debug(
        f"do we have a combo {candles[0].ut} at the date {candles[0].date} ?"
    )
    context = _ComboContext(candles, settings)
    if context.neither_bb_flat:
        logger.debug(
            f"BB bands are not flat bbh={context.bbh_slope},"
            f" bbb={context.bbb_slope}"
        )
        return None
    if context.ma50_slope > settings.ma50_slope_min:
        logger.debug(f"testing a buying combo ma50_slope={context.ma50_slope}")
        return _combo_for_direction(context, Direction.BUY)
    if context.ma50_slope < -settings.ma50_slope_min:
        logger.debug(
            f"testing a selling combo ma50_slope={context.ma50_slope}"
        )
        return _combo_for_direction(context, Direction.SELL)
    return None


def macd0lag(
    candles: List[Candle],
    short_term_period: int = 12,
    long_term_period: int = 26,
    signal_period: int = 9,
) -> Tuple[float, float]:
    """
    Here is the formula
    https://www.axialfinance.fr/manuel/pagesindicateurs/pageMZLD.html
    return a tuple(last macd0lag, signal)

    The nested emas read progressively older suffixes, so the whole call needs
    far more candles than one macd step does. The deepest read is at offset
    (signal_period * 9 - 1) + (long_term_period * 3 - 1) against an ema
    needing long_term_period * 3 values, hence the minimum below - 235 with
    the default periods. The old guard checked only one step's worth
    (long_term_period * 4, i.e. 104) and so reported a requirement less than
    half the real one.
    """
    minimum = signal_period * 9 + long_term_period * 6 - 2
    if len(candles) < minimum:
        Logger.get_logger("macd0lag").error(
            f"Missing candles to calculate a macd0lag {len(candles)},"
            f" needed {minimum}"
        )
        raise SaxoException("Missing candles")

    # The loops below ask for the ema of heavily overlapping suffixes of the
    # same list, so cache each (offset, period) result.
    ema_cache: Dict[Tuple[int, int], float] = {}

    def _ema(offset: int, period: int) -> float:
        key = (offset, period)
        if key not in ema_cache:
            ema_cache[key] = exponentiel_mobile_average(
                candles[offset:], period
            )
        return ema_cache[key]

    def _macd0lag(offset: int) -> float:
        short_ma = _ema(offset, short_term_period)
        long_ma = _ema(offset, long_term_period)
        short_ma_ma = exponentiel_mobile_average(
            [
                _ema(offset + i, short_term_period)
                for i in range(short_term_period * 3)
            ],
            short_term_period,
        )
        long_ma_ma = exponentiel_mobile_average(
            [
                _ema(offset + i, long_term_period)
                for i in range(long_term_period * 3)
            ],
            long_term_period,
        )
        macd = (2 * short_ma - short_ma_ma) - (2 * long_ma - long_ma_ma)
        return macd

    macd_list = []
    for i in range(0, signal_period * 9):
        macd_list.append(_macd0lag(i))
    macd_ma_list = []
    for i in range(0, signal_period * 3):
        macd_ma_list.append(
            exponentiel_mobile_average(macd_list[i:], signal_period)
        )

    signal = (2 * macd_ma_list[0]) - exponentiel_mobile_average(
        macd_ma_list, signal_period
    )
    return (round(macd_list[0], 5), round(signal, 5))


def exponentiel_mobile_average(candles: List, period: int) -> float:
    if len(candles) < period * 3:
        Logger.get_logger("exponentiel_mobile_average").error(
            f"Missing candles to calculate a ema {len(candles)},"
            f" needed {period * 3}"
        )
        raise SaxoException("Missing candles")

    numbers = candles
    if isinstance(candles[0], Candle):
        numbers = list(map(lambda x: x.close, candles))
    alpha = 2.0 / (period + 1.0)

    ema = numbers[-1]
    for i in range(len(candles) - 2, -1, -1):
        ema = (numbers[i] * alpha) + ema * (1 - alpha)
    return round(ema, 5)


def slope_percentage(x1: float, y1: float, x2: float, y2: float) -> float:
    dx = x2 - x1
    coefficient = 100.0 / y2
    dy = 100 - y1 * coefficient
    return round((dy / dx) * 100.0, 5)


def find_linear_function(x0: float, y0: float, x1: float, y1: float) -> tuple:
    a = (y1 - y0) / (x1 - x0)
    b = y0 - a * x0
    return a, b


def apply_linear_function(
    x0: float, y0: float, x1: float, y1: float, x2: float
) -> float:
    a, b = find_linear_function(x0, y0, x1, y1)
    return a * x2 + b


def average_true_range(candles: List[Candle], period=14) -> float:
    """
    Here is the formula
    https://www.abcbourse.com/apprendre/11_average_true_range.html
    """

    if len(candles) < period * 3:
        Logger.get_logger("average_true_range").error(
            f"Missing candles to calculate an atr {len(candles)},"
            f" needed {period * 3}"
        )
        raise SaxoException("Missing candles")
    true_ranges = []
    for i in range(0, len(candles) - 1):
        true_ranges.append(true_range(candles[i:]))
    true_ranges = true_ranges[::-1]
    atr = sum(true_ranges[:period]) / period
    for i in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[i]) / period
    return round(atr, 5)


def true_range(candles: List[Candle]) -> float:
    tr = candles[0].higher - candles[0].lower
    tr2 = abs(candles[0].higher - candles[1].close)
    tr3 = abs(candles[0].lower - candles[1].close)
    return max(tr, tr2, tr3)


def _directional_index(atr: float, plus_sm: float, minus_sm: float) -> float:
    """DX from Wilder-smoothed TR/+DM/-DM sums (guards zero denominators)."""
    if atr == 0:
        return 0.0
    plus_di = 100 * plus_sm / atr
    minus_di = 100 * minus_sm / atr
    denominator = plus_di + minus_di
    if denominator == 0:
        return 0.0
    return 100 * abs(plus_di - minus_di) / denominator


def adx(candles: List[Candle], period: int = 14) -> float:
    """Wilder's Average Directional Index - a direction-agnostic trend/chop
    strength measure (high = trending, low = chopping).

    Candles are newest-first (index 0 is the most recent), matching the rest
    of this module. Returns the latest ADX value. Needs period * 3 candles
    for the double Wilder smoothing (the same minimum as average_true_range).
    """
    if len(candles) < period * 3:
        Logger.get_logger("adx").error(
            f"Missing candles to calculate an adx {len(candles)},"
            f" needed {period * 3}"
        )
        raise SaxoException("Missing candles")
    true_ranges: List[float] = []
    plus_dms: List[float] = []
    minus_dms: List[float] = []
    for i in range(0, len(candles) - 1):
        current = candles[i]
        previous = candles[i + 1]
        up_move = current.higher - previous.higher
        down_move = previous.lower - current.lower
        plus_dms.append(
            up_move if up_move > down_move and up_move > 0 else 0.0
        )
        minus_dms.append(
            down_move if down_move > up_move and down_move > 0 else 0.0
        )
        true_ranges.append(true_range(candles[i:]))
    # reverse to chronological (oldest-first) for forward Wilder smoothing
    true_ranges.reverse()
    plus_dms.reverse()
    minus_dms.reverse()

    atr = sum(true_ranges[:period])
    plus_sm = sum(plus_dms[:period])
    minus_sm = sum(minus_dms[:period])
    directional_indices: List[float] = [
        _directional_index(atr, plus_sm, minus_sm)
    ]
    for i in range(period, len(true_ranges)):
        atr = atr - atr / period + true_ranges[i]
        plus_sm = plus_sm - plus_sm / period + plus_dms[i]
        minus_sm = minus_sm - minus_sm / period + minus_dms[i]
        directional_indices.append(_directional_index(atr, plus_sm, minus_sm))

    adx_value = sum(directional_indices[:period]) / period
    for i in range(period, len(directional_indices)):
        adx_value = (
            adx_value * (period - 1) + directional_indices[i]
        ) / period
    return round(adx_value, 5)


def inside_bar(candles: List[Candle]) -> bool:
    if len(candles) < 2:
        Logger.get_logger("inside_bar").error(
            f"Missing candles to calculate an inside_bar {len(candles)}"
        )
        raise SaxoException("Missing candles")
    return (
        candles[0].lower > candles[1].lower
        and candles[0].higher < candles[1].higher
    )


def double_inside_bar(candles: List[Candle]) -> bool:
    if len(candles) < 3:
        Logger.get_logger("double_inside_bar").error(
            f"Missing candles to calculate a double_inside_bar {len(candles)}"
        )
        raise SaxoException("Missing candles")
    return inside_bar(candles) and inside_bar(candles[1:])


def number_of_day_between_dates(
    saxo_client: SaxoClient,
    saxo_uic: str,
    asset_type: str,
    date1: datetime.datetime,
    date2: datetime.datetime,
) -> int:
    diff = 0
    if date1 > date2:
        return 0
    while date1 < date2:
        date1 += datetime.timedelta(days=1)
        if date1.weekday() < 5 and saxo_client.is_day_open(
            saxo_uic=saxo_uic, asset_type=asset_type, date=date1
        ):
            diff += 1
    return diff
