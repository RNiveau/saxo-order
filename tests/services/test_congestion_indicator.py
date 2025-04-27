import datetime

import pytest

from model import Candle, UnitTime
from services.congestion_indicator import calculate_congestion_indicator

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
        "file, expected",
        [
            (
                "candles_viridien.obj",
                [datetime.datetime(2025, 3, 3), datetime.datetime(2025, 3, 6)],
            ),
            (
                "candles_viridien2.obj",
                [
                    datetime.datetime(2025, 1, 16),
                    datetime.datetime(2025, 1, 17),
                    datetime.datetime(2025, 1, 21),
                    datetime.datetime(2025, 1, 22),
                    datetime.datetime(2025, 1, 27),
                    datetime.datetime(2025, 2, 5),
                    datetime.datetime(2025, 2, 11),
                    datetime.datetime(2025, 2, 12),
                    datetime.datetime(2025, 2, 14),
                    datetime.datetime(2025, 2, 18),
                    datetime.datetime(2025, 2, 19),
                ],
            ),
        ],
    )
    def test_congestion_indicator(self, file: str, expected):
        with open(f"tests/services/files/{file}", "r") as f:
            candles = eval(
                f.read(),
                {"datetime": datetime, "Candle": Candle, "UnitTime": UnitTime},
            )
        touch_points = calculate_congestion_indicator(
            candles=candles,
        )
        # check la position du 27/01
        assert [t.date for t in touch_points] == expected
