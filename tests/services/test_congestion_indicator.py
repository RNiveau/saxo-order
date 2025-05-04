import datetime

import pytest

from model import Candle, UnitTime
from services.congestion_indicator import calculate_congestion_indicator


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
                    datetime.datetime(2025, 1, 27),
                    datetime.datetime(2025, 2, 5),
                    datetime.datetime(2025, 2, 12),
                    datetime.datetime(2025, 2, 14),
                ],
            ),
            (
                "candles_viridien3.obj",
                [
                    datetime.datetime(2025, 4, 11, 0, 0),
                    datetime.datetime(2025, 4, 14, 0, 0),
                    datetime.datetime(2025, 4, 15, 0, 0),
                ],
            ),
            (
                "candles_total.obj",
                [
                    datetime.datetime(2025, 4, 23, 0, 0),
                    datetime.datetime(2025, 4, 25, 0, 0),
                    datetime.datetime(2025, 4, 28, 0, 0),
                    datetime.datetime(2025, 4, 29, 0, 0),
                ],
            ),
            (
                "candles_beneteau.obj",
                [],
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
