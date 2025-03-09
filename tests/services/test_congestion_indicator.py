import datetime
from typing import List

import pytest

from model import Candle, UnitTime
from model.enum import LineType
from services.congestion_indicator import calculate_line, calculate_congestion_indicator

# Viridien 02/01/2025 to 10/01/2025
candles_viridien = [
    Candle(
        lower=55.6,
        open=55.60,
        close=58.9,
        higher=61.09,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 10),
    ),
    Candle(
        lower=53.3,
        open=53.58,
        close=54.02,
        higher=55.26,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 9),
    ),
    Candle(
        lower=53.2,
        open=54,
        close=53.80,
        higher=54.84,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 8),
    ),
    Candle(
        lower=54.04,
        open=54.93,
        close=54.41,
        higher=56.22,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 7),
    ),
    Candle(
        lower=52,
        open=55.37,
        close=54.93,
        higher=55.59,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 6),
    ),
    Candle(
        lower=54.66,
        open=56.2,
        close=55.42,
        higher=56.71,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 3),
    ),
    Candle(
        lower=50.95,
        open=50.95,
        close=56.03,
        higher=56.04,
        ut=UnitTime.D,
        date=datetime.datetime(2025, 1, 2),
    ),
]

class TestCandlesService:

    @pytest.mark.parametrize(
        "candles, line_type, expected",
        [
            (candles_viridien, LineType.HIGH, 0),
        ],
    )
    def test_calculate_line(
        self, candles: List[Candle], line_type: LineType, expected
    ):
        assert (
            calculate_line(
                line_type=line_type,
                candles=candles,
                max_len=5,
                which_second_point=0,
            )
            == expected
        )

    @pytest.mark.parametrize(
        "candles, expected",
        [
            (candles_viridien, 1),
        ],
    )
    def test_congestion_indicator(
        self, candles: List[Candle], expected
    ):
        assert (
            calculate_congestion_indicator(
                candles=candles,
            )
            == expected
        )


