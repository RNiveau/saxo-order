import datetime
from typing import Dict, List, Optional, Tuple

import numpy

from client.saxo_client import SaxoClient
from model import (
    BollingerBands,
    Candle,
    ComboSignal,
    Direction,
    SignalStrength,
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

COMBO_MA50_SLOPE_MIN = 3.0
COMBO_MA50_SLOPE_STRONG = 10.0
COMBO_BB_FLAT_SLOPE_MAX = 5.0
COMBO_BB_BREACH_TOLERANCE = 0.001
COMBO_BB_TOLERANCE = 0.005
COMBO_ATR_BB_MARGIN = 0.3
COMBO_ATR_MA50_MARGIN = 0.1
COMBO_STRONG_SIGNAL_MIN = 4


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
    close: float, outer: float, inner: float, direction: Direction
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


def combo(candles: List[Candle]) -> Optional[ComboSignal]:
    logger = Logger.get_logger("combo")
    logger.debug(
        f"do we have a combo {candles[0].ut} at the date {candles[0].date} ?"
    )
    ma50_last = mobile_average(candles, 50)
    ma50_first = mobile_average(candles[10:], 50)
    bb_last = bollinger_bands(candles, 2.5)
    bb25_1 = bollinger_bands(candles[1:], 2.5)
    bb_first = bollinger_bands(candles[2:], 2.5)
    bb20 = bollinger_bands(candles, 2.0)
    bb20_1 = bollinger_bands(candles[1:], 2.0)
    ma50_slope = slope_percentage(0, ma50_first, 10, ma50_last)
    bbh_slope = slope_percentage(0, bb_first.up, 3, bb_last.up)
    bbb_slope = slope_percentage(0, bb_first.bottom, 3, bb_last.bottom)
    macd_0lag = macd0lag(candles)
    atr = average_true_range(candles)
    margin_variation_bb = atr * COMBO_ATR_BB_MARGIN
    margin_variation_ma50 = atr * COMBO_ATR_MA50_MARGIN
    both_bb_flat = (
        abs(bbh_slope) < COMBO_BB_FLAT_SLOPE_MAX
        and abs(bbb_slope) < COMBO_BB_FLAT_SLOPE_MAX
    )

    if (
        abs(bbh_slope) > COMBO_BB_FLAT_SLOPE_MAX
        and abs(bbb_slope) > COMBO_BB_FLAT_SLOPE_MAX
    ):
        logger.debug(f"BB bands are not flat bbh={bbh_slope}, bbb={bbb_slope}")
        return None
    if ma50_slope > COMBO_MA50_SLOPE_MIN:
        logger.debug(f"testing a buying combo ma50_slope={ma50_slope}")
        signal = 0
        if candles[0].close < ma50_last:
            logger.debug(
                f"close {candles[0].close} is bellow ma50 {ma50_last}"
            )
            return None
        if candles[0].close < bb_last.bottom * (1 - COMBO_BB_BREACH_TOLERANCE):
            logger.debug(
                f"close {candles[0].close} is bellow bbb 2.5 {bb_last.bottom}"
            )
            return None
        if is_far_from_levels(
            candles,
            bb20.bottom,
            ma50_last,
            margin_variation_bb,
            margin_variation_ma50,
            Direction.BUY,
        ):
            logger.debug(
                f"candle {candles[0]} is far from the bbb 2.0 "
                f"{bb20.bottom} and from the ma50 {ma50_last}"
            )
            return None
        buy_combo = ComboSignal(
            price=0,
            direction=Direction.BUY,
            has_been_triggered=False,
            strength=SignalStrength.MEDIUM,
            details={
                "macd": False,
                "ma50_over_bb": False,
                "price_within_bb": False,
                "strong_ma50": False,
                "both_bb_flat": False,
            },
        )
        if both_bb_flat:
            signal += 1
            buy_combo.details["both_bb_flat"] = True
        if ma50_last < bb_last.bottom:
            signal += 1
            buy_combo.details["ma50_over_bb"] = True

        if ma50_slope > COMBO_MA50_SLOPE_STRONG:
            signal += 1
            buy_combo.details["strong_ma50"] = True

        if is_price_within_bands(
            candles[1].close, bb25_1.bottom, bb20_1.bottom, Direction.BUY
        ) or is_price_within_bands(
            candles[0].close, bb_last.bottom, bb20.bottom, Direction.BUY
        ):  # candle -1 or candle is between bb 2.0 / 2.5
            signal += 1
            buy_combo.details["price_within_bb"] = True
        if macd_0lag[0] > macd_0lag[1]:
            signal += 1
            buy_combo.details["macd"] = True
        if candles[0].close > candles[1].higher:
            buy_combo.has_been_triggered = True
            buy_combo.price = candles[0].close
        else:
            buy_combo.price = candles[0].higher
        if signal == 0:
            buy_combo.strength = SignalStrength.WEAK
        elif signal >= COMBO_STRONG_SIGNAL_MIN:
            buy_combo.strength = SignalStrength.STRONG
        return buy_combo
    elif ma50_slope < -COMBO_MA50_SLOPE_MIN:
        logger.debug(f"testing a selling combo ma50_slope={ma50_slope}")
        signal = 0
        if candles[0].close > ma50_last:
            logger.debug(f"close {candles[0].close} is above ma50 {ma50_last}")
            return None
        if candles[0].close > bb_last.up * (1 + COMBO_BB_BREACH_TOLERANCE):
            logger.debug(
                f"close {candles[0].close} is above bbb 2.5 {bb_last.up}"
            )
            return None
        if is_far_from_levels(
            candles,
            bb20.up,
            ma50_last,
            margin_variation_bb,
            margin_variation_ma50,
            Direction.SELL,
        ):
            logger.debug(
                f"candle {candles[0]} is far from the bbb 2.0 "
                f"{bb20.up} and from the ma50 {ma50_last}"
            )
            return None
        sell_combo = ComboSignal(
            price=0,
            direction=Direction.SELL,
            has_been_triggered=False,
            strength=SignalStrength.MEDIUM,
            details={
                "macd": False,
                "ma50_over_bb": False,
                "price_within_bb": False,
                "strong_ma50": False,
                "both_bb_flat": False,
            },
        )
        if both_bb_flat:
            signal += 1
            sell_combo.details["both_bb_flat"] = True
        if ma50_last > bb_last.up:
            signal += 1
            sell_combo.details["ma50_over_bb"] = True
        if ma50_slope < -COMBO_MA50_SLOPE_STRONG:
            signal += 1
            sell_combo.details["strong_ma50"] = True

        if is_price_within_bands(
            candles[1].close, bb25_1.up, bb20_1.up, Direction.SELL
        ) or is_price_within_bands(
            candles[0].close, bb_last.up, bb20.up, Direction.SELL
        ):  # candle -1 or candle is between bb 2.0 / 2.5
            signal += 1
            sell_combo.details["price_within_bb"] = True
        if macd_0lag[0] < macd_0lag[1]:
            signal += 1
            sell_combo.details["macd"] = True
        if candles[0].close < candles[1].lower:
            sell_combo.has_been_triggered = True
            sell_combo.price = candles[0].close
        else:
            sell_combo.price = candles[0].lower
        if signal == 0:
            sell_combo.strength = SignalStrength.WEAK
        elif signal >= COMBO_STRONG_SIGNAL_MIN:
            sell_combo.strength = SignalStrength.STRONG
        return sell_combo
    return None


def macd0lag(
    candles: List[Candle],
    short_term_period: int = 12,
    long_term_period: int = 26,
    signal_period: int = 9,
) -> tuple:
    """
    Here is the formula
    https://www.axialfinance.fr/manuel/pagesindicateurs/pageMZLD.html
    return a tuple(last macd0lag, signal)
    """

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
        if len(candles) - offset < long_term_period * 4:
            Logger.get_logger("macd0lag").error(
                "Missing candles to calculate a macd0lag"
                f" len={len(candles) - offset}:"
                f"needed {long_term_period * 4}"
            )
            raise SaxoException("Missing candles")
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
