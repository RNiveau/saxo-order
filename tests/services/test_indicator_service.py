import datetime

import pytest

from model import Candle, UnitTime
from services.indicator_service import *


class TestIndicatorService:

    @pytest.mark.parametrize(
        "candles, tick, expected",
        [
            (
                [10, 9, 8, 10, 9],
                0.5,
                10,
            ),
            (
                [10, 9, 8, 10.5, 9],
                0.5,
                10,
            ),
            (
                [10, 9, 8, 10.6, 9],
                0.5,
                None,
            ),
            (
                [10, 11, 8, 10.6, 9],
                0.5,
                11,
            ),
            (
                [10, 11, 8, 10.6, 11.2],
                0.2,
                11,
            ),
            (
                [10, 11, 8, 10.6, 12],
                0.5,
                None,
            ),
            (
                [10, 11.1, 8, 10.6, 9, 2, 11.3, 9, 8],
                0.2,
                11.1,
            ),
        ],
    )
    def test_double_top(self, candles, tick, expected):
        candles = list(
            map(
                lambda x: Candle(0, x, 0, 0, UnitTime.D, datetime.datetime.now()),
                candles,
            )
        )
        if expected is None:
            assert double_top(candles, tick) is None
        else:
            assert double_top(candles, tick).higher == expected

    @pytest.mark.parametrize(
        "candles, std, expected",
        [
            (
                [
                    8197.44,
                    8167.5,
                    8168.71,
                    8162.99,
                    8146.62,
                    8149.27,
                    8156.29,
                    8160.68,
                    8150.25,
                    8153.62,
                    8188.49,
                    8196.96,
                    8189.22,
                    8204.56,
                    8208.38,
                    8204.93,
                    8187.71,
                    8200.88,
                    8211.02,
                    8239.99,
                ],
                2.5,
                BollingerBands(middle=8182.2755, bottom=8118.8328, up=8245.7182),
            ),
            (
                [
                    18786.22,
                    18790.23,
                    18779.16,
                    18775.53,
                    18759.0,
                    18766.01,
                    18704.42,
                    18713.9,
                    18699.1,
                    18686.65,
                    18676.17,
                    18664.39,
                    18677.27,
                    18676.48,
                    18664.47,
                    18738.81,
                    18755.95,
                    18740.97,
                    18781.53,
                    18821.21,
                    18821.21,
                    18821.21,
                    18821.21,
                ],
                2,
                BollingerBands(middle=18732.8735, bottom=18636.9720, up=18828.7750),
            ),
        ],
    )
    def test_bollinger_bands(self, candles, std, expected):
        candles = list(
            map(
                lambda x: Candle(0, 0, 0, x, UnitTime.D, datetime.datetime.now()),
                candles,
            )
        )
        assert bollinger_bands(candles, std) == expected

    @pytest.mark.parametrize(
        "candles, expected",
        [
            (
                [Candle(5, 6, 5.5, 6, UnitTime.D), Candle(5, 6, 5.5, 6, UnitTime.D)],
                None,
            ),
            (
                [Candle(4, 8, 5.5, 6, UnitTime.D), Candle(5, 6, 5.5, 6, UnitTime.D)],
                None,
            ),
            (
                [Candle(4, 8, 4.2, 6.2, UnitTime.D), Candle(5, 6, 5.5, 6, UnitTime.D)],
                Candle(4, 8, 4.2, 6.2, UnitTime.D),
            ),
            (
                [Candle(4, 8, 8, 4.9, UnitTime.D), Candle(5, 6, 5.5, 6, UnitTime.D)],
                Candle(4, 8, 8, 4.9, UnitTime.D),
            ),
        ],
    )
    def test_containing_candle(self, candles, expected):
        assert containing_candle(candles) == expected
