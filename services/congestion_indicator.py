from typing import List

from model.enum import LineType
from model.workflow import Candle, LineFormula


def calculate_line(
    line_type: LineType,
    candles: List[Candle],
    max_len: int,
    which_second_point: int,
) -> tuple[LineFormula, Candle]:
    """
    Calculate the line of the congestion indicator
    Based on the formula https://www.alloprof.qc.ca/fr/eleves/bv/
    mathematiques/l-equation-d-une-droite-a-partir-de-coordonnees-m1319
    Y = mX + b
    """
    tab_high: List[float] = [0, 0, 0]
    tab_index: List[int] = [0, 0, 0]

    first_index = 1
    if line_type == LineType.HIGH:
        first_high = candles[1].higher
    elif line_type == LineType.LOW:
        first_high = candles[1].lower

    for i in range(1, min(max_len, len(candles))):
        if (line_type == LineType.HIGH and candles[i].higher > first_high) or (
            line_type == LineType.LOW and candles[i].lower < first_high
        ):
            tab_high[2], tab_high[1] = tab_high[1], tab_high[0]
            tab_high[0] = first_high
            tab_index[2], tab_index[1] = tab_index[1], tab_index[0]
            tab_index[0] = first_index
            first_high = (
                candles[i].higher
                if line_type == LineType.HIGH
                else candles[i].lower
            )
            first_index = i

    if tab_high[which_second_point] > 0:
        m = (tab_high[which_second_point] - first_high) / (
            tab_index[which_second_point] - first_index
        )
        b = tab_high[which_second_point] - (m * tab_index[which_second_point])
    else:
        first_index = 0
        m = b = 0

    return LineFormula(m=m, b=b, first_x=first_index), candles[first_index]


def calculate_congestion_indicator(candles: List[Candle]) -> int:
    """
    Calculate the congestion indicator
    Go from the oldest (or 50) to the newest candle - 3

    """
    toleration_high = 1.002
    touch_points: List[Candle] = []
    # toleration_low = 0.998
    for back_test in range(min(50, len(candles)), 3, -1):
        # all points are bellow the line ?
        # test several second highest
        lineOk = 0
        touch_points = []
        line_formula, candle = calculate_line(
            LineType.HIGH, candles, back_test, 0
        )
        # drop too small line
        if line_formula.first_x < 3:
            lineOk = 0
            continue
        lineOk = 1
        for tmpX in range(line_formula.first_x, 0, -1):
            y2 = line_formula.m * tmpX + line_formula.b
            if y2 * toleration_high < candles[tmpX].higher:
                lineOk = 0
                break
            # Check if candle touches the line within 0.02% tolerance
            if abs((y2 - candles[tmpX].higher) / y2) < 0.0002:
                touch_points.append(candles[tmpX])
        if lineOk == 1:
            break
    # should return list of points where the candle touches the line
    return touch_points if lineOk else []
