from typing import List, Optional

import numpy

from model import BollingerBands, Candle
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


def mobile_average(candles: List[Candle], nbr_candles: int) -> float:
    if len(candles) < nbr_candles:
        Logger.get_logger("mobile_average").error(
            f"Missing candles to calculate the ma {len(candles)}, {nbr_candles}"
        )
        raise SaxoException(f"Missing candles to calcule the ma")
    return sum(map(lambda x: x.close, candles[:nbr_candles])) / nbr_candles


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
