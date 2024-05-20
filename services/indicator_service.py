from typing import List, Optional

import numpy

from model import BollingerBands, Candle


def double_top(candles: List[Candle], tick=float) -> bool:
    """
    If a double top exist in the list, return true
    The top can be another candle than the first one
    We accept a spread of one tick between two tops
    """
    if len(candles) < 2:
        return False

    tops = []

    if candles[0].higher >= candles[1].higher:
        tops.append(candles[0].higher)

    for i in range(1, len(candles) - 1):
        if (
            candles[i].higher >= candles[i - 1].higher
            and candles[i].higher >= candles[i + 1].higher
        ):
            tops.append(candles[i].higher)

    if candles[-1].higher >= candles[-2].higher:
        tops.append(candles[-1].higher)
    # Check if there are two tops within one tick spread
    for i in range(len(tops)):
        for j in range(i + 1, len(tops)):
            if round(abs(tops[i] - tops[j]), 4) <= tick:
                return True
    return False


def bollinger_bands(candles: List[Candle], multiply_std: float = 2.0) -> BollingerBands:
    closes = list(map(lambda x: x.close, candles))
    std = numpy.std(closes)
    avg = numpy.average(closes)
    return BollingerBands(
        bottom=float(round(avg - multiply_std * std, 4)),
        up=float(round(avg + multiply_std * std, 4)),
        middle=float(round(avg, 4)),
    )
