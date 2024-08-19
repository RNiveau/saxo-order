from typing import List, Optional

import numpy

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


def combo(candles: List[Candle]) -> Optional[ComboSignal]:
    logger = Logger.get_logger("combo")
    logger.debug(
        f"do we have a combo {candles[0].ut} at the date {candles[0].date} ?"
    )
    ma50_last = mobile_average(candles, 50)
    ma50_first = mobile_average(candles[10:], 50)
    bb_last = bollinger_bands(candles, 2.5)
    bb25_1 = bollinger_bands(candles, 2.5)
    bb_first = bollinger_bands(candles[2:], 2.5)
    bb20 = bollinger_bands(candles, 2.0)
    bb20_1 = bollinger_bands(candles[1:], 2.0)
    ma50_slope = slope_percentage(0, ma50_first, 10, ma50_last)
    bbh_slope = slope_percentage(0, bb_first.up, 3, bb_last.up)
    bbb_slope = slope_percentage(0, bb_first.bottom, 3, bb_last.bottom)
    macd_0lag = macd0lag(candles)
    atr = average_true_range(candles)
    margin_variation_bb = atr * 0.3
    margin_variation_ma50 = atr * 0.1

    if (bbh_slope < -5 or bbh_slope > 5) and (bbb_slope < -5 or bbb_slope > 5):
        logger.debug(f"BB bands are not flat bbh={bbh_slope}, bbb={bbb_slope}")
        return None
    if ma50_slope > 3:
        logger.debug(f"testing a buying combo ma50_slope={ma50_slope}")
        signal = 0
        if candles[0].close < ma50_last:
            logger.debug(
                f"close {candles[0].close} is bellow ma50 {ma50_last}"
            )
            return None
        if candles[0].close < bb_last.bottom * 0.999:
            logger.debug(
                f"close {candles[0].close} is bellow bbb 2.5 {bb_last.bottom}"
            )
            return None
        if (
            candles[0].close > bb20.bottom + margin_variation_bb
            and candles[1].close > bb20.bottom + margin_variation_bb
            and candles[0].lower > bb20.bottom + margin_variation_bb
            and candles[1].lower > bb20.bottom + margin_variation_bb
        ):
            if (
                candles[0].close > ma50_last + margin_variation_ma50
                and candles[1].close > ma50_last + margin_variation_ma50
                and candles[0].higher > ma50_last + margin_variation_ma50
                and candles[1].higher > ma50_last + margin_variation_ma50
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
        if 5 > bbh_slope > -5 and 5 > bbb_slope > -5:  # both bb are flat
            signal += 1
            buy_combo.details["both_bb_flat"] = True
        if ma50_last < bb_last.bottom:
            signal += 1
            buy_combo.details["ma50_over_bb"] = True

        if ma50_slope > 10:
            signal += 1
            buy_combo.details["strong_ma50"] = True

        if (
            bb25_1.bottom * 0.9995 < candles[1].close < bb20_1.bottom * 1.005
        ) or (
            bb_last.bottom * 0.9995 < candles[0].close < bb20.bottom * 1.005
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
        elif signal > 3:
            buy_combo.strength = SignalStrength.STRONG
        return buy_combo
    elif ma50_slope < -3:
        logger.debug(f"testing a selling combo ma50_slope={ma50_slope}")
        signal = 0
        if candles[0].close > ma50_last:
            logger.debug(f"close {candles[0].close} is above ma50 {ma50_last}")
            return None
        if candles[0].close > bb_last.up * 1.001:
            logger.debug(
                f"close {candles[0].close} is above bbb 2.5 {bb_last.up}"
            )
            return None
        if (
            candles[0].close < bb20.up - margin_variation_bb
            and candles[1].close < bb20.up - margin_variation_bb
            and candles[0].higher < bb20.up - margin_variation_bb
            and candles[1].higher < bb20.up - margin_variation_bb
        ):
            if (
                candles[0].close < ma50_last - margin_variation_ma50
                and candles[1].close < ma50_last - margin_variation_ma50
                and candles[0].higher < ma50_last - margin_variation_ma50
                and candles[1].higher < ma50_last - margin_variation_ma50
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
        if 5 > bbh_slope > -5 and 5 > bbb_slope > -5:  # both bb are flat
            signal += 1
            sell_combo.details["both_bb_flat"] = True
        if ma50_last > bb_last.up:
            signal += 1
            sell_combo.details["ma50_over_bb"] = True
        if ma50_slope < -10:
            signal += 1
            sell_combo.details["strong_ma50"] = True

        if (bb25_1.up * 1.005 > candles[1].close > bb20_1.up * 0.9995) or (
            bb_last.up * 1.005 > candles[0].close > bb20.up * 0.995
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
        elif signal > 3:
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

    def _macd0lag(
        candles: List[Candle],
        short_term_period: int = 12,
        long_term_period: int = 26,
    ) -> float:
        if len(candles) < long_term_period * 4:
            Logger.get_logger("macd0lag").error(
                f"Missing candles to calculate a macd0lag len={len(candles)}:"
                f"needed {long_term_period * 4}"
            )
            raise SaxoException("Missing candles")
        short_ma = exponentiel_mobile_average(candles, short_term_period)
        long_ma = exponentiel_mobile_average(candles, long_term_period)
        short_ma_list = [short_ma]
        for i in range(1, short_term_period * 3):
            short_ma_list.append(
                exponentiel_mobile_average(candles[i:], short_term_period)
            )
        short_ma_ma = exponentiel_mobile_average(
            short_ma_list,
            short_term_period,
        )
        long_ma_list = [long_ma]
        for i in range(1, long_term_period * 3):
            long_ma_list.append(
                exponentiel_mobile_average(candles[i:], long_term_period)
            )
        long_ma_ma = exponentiel_mobile_average(long_ma_list, long_term_period)
        macd = (2 * short_ma - short_ma_ma) - (2 * long_ma - long_ma_ma)
        return macd

    macd_list = []
    for i in range(0, signal_period * 9):
        macd_list.append(
            _macd0lag(candles[i:], short_term_period, long_term_period)
        )
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
