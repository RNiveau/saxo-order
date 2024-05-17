import datetime

import pytest

from model import Candle, UnitTime
from services.indicator_service import double_top


class TestIndicatorService:

    @pytest.mark.parametrize(
        "candles, tick, expected",
        [
            (
                [10, 9, 8, 10, 9],
                0.5,
                True,
            ),
            (
                [10, 9, 8, 10.5, 9],
                0.5,
                True,
            ),
            (
                [10, 9, 8, 10.6, 9],
                0.5,
                False,
            ),
            (
                [10, 11, 8, 10.6, 9],
                0.5,
                True,
            ),
            (
                [10, 11, 8, 10.6, 11.2],
                0.2,
                True,
            ),
            (
                [10, 11, 8, 10.6, 12],
                0.5,
                False,
            ),
            (
                [10, 11.1, 8, 10.6, 9, 2, 11.3, 9, 8],
                0.2,
                True,
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
        assert double_top(candles, tick) == expected
