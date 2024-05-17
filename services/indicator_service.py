from typing import List

from model import Candle


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
    print(tops)
    # Check if there are two tops within one tick spread
    for i in range(len(tops)):
        for j in range(i + 1, len(tops)):
            print(f"{tops[i]} {tops[j]} {tick} {abs(tops[i] - tops[j]) }  ")
            if round(abs(tops[i] - tops[j]), 4) <= tick:
                return True
    return False
