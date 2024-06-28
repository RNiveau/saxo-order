import datetime
from typing import List

import pytest

from model import Candle, UnitTime
from utils.helper import (
    build_daily_candle_from_hours,
    build_h4_candles_from_h1,
)


class TestHelper:

    @pytest.mark.parametrize(
        "candles, expected",
        [
            (
                [
                    Candle(
                        close=40.64,
                        open=40.58,
                        higher=40.64,
                        lower=40.53,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.58,
                        open=40.59,
                        higher=40.62,
                        lower=40.48,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.61,
                        open=40.55,
                        higher=40.64,
                        lower=40.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 13:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.55,
                        open=40.65,
                        higher=40.65,
                        lower=40.53,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 12:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.64,
                        open=40.53,
                        higher=40.72,
                        lower=40.51,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 11:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.52,
                        open=40.66,
                        higher=40.72,
                        lower=40.51,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 10:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.65,
                        open=40.74,
                        higher=40.77,
                        lower=40.57,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 09:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.75,
                        open=40.92,
                        higher=40.99,
                        lower=40.71,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 08:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.92,
                        open=40.99,
                        higher=41.12,
                        lower=40.89,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 07:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.84,
                        open=40.9,
                        higher=40.93,
                        lower=40.84,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.9,
                        open=40.89,
                        higher=40.94,
                        lower=40.85,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.88,
                        open=40.87,
                        higher=40.94,
                        lower=40.83,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 13:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.86,
                        open=40.86,
                        higher=40.9,
                        lower=40.84,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 12:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.86,
                        open=40.74,
                        higher=40.87,
                        lower=40.71,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 11:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.72,
                        open=40.7,
                        higher=40.77,
                        lower=40.7,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 10:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.71,
                        open=40.84,
                        higher=40.85,
                        lower=40.67,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 09:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.83,
                        open=40.65,
                        higher=40.83,
                        lower=40.65,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 08:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.65,
                        open=40.75,
                        higher=40.93,
                        lower=40.6,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 07:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.65,
                        open=40.65,
                        higher=40.82,
                        lower=40.65,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-24 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.66,
                        open=40.4,
                        higher=40.72,
                        lower=40.39,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-24 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                ],
                Candle(
                    lower=40.48,
                    higher=41.12,
                    open=40.99,
                    close=40.64,
                    ut=UnitTime.D,
                    date=datetime.datetime.now(),
                ),
            ),
            (
                [
                    Candle(
                        close=18677.87,
                        open=18667.25,
                        higher=18687.14,
                        lower=18656.34,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18666.8,
                        open=18670.16,
                        higher=18682.99,
                        lower=18635.04,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18668.16,
                        open=18712.23,
                        higher=18732.2,
                        lower=18665.85,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 13:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18712.23,
                        open=18764.36,
                        higher=18765.23,
                        lower=18703.22,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 12:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18764.36,
                        open=18773.41,
                        higher=18785.26,
                        lower=18755.49,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 11:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18772.76,
                        open=18813.1,
                        higher=18813.1,
                        lower=18754.23,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 10:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18813.1,
                        open=18844.71,
                        higher=18849.99,
                        lower=18813.1,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 09:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18844.65,
                        open=18809.92,
                        higher=18855.05,
                        lower=18809.92,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 08:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18809.92,
                        open=18775.55,
                        higher=18836.02,
                        lower=18775.07,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 07:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18774.71,
                        open=18763.68,
                        higher=18775.13,
                        lower=18757.62,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18763.68,
                        open=18742.24,
                        higher=18767.16,
                        lower=18742.18,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18742.17,
                        open=18748.27,
                        higher=18767.46,
                        lower=18726.98,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 13:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18748.27,
                        open=18721.07,
                        higher=18751.52,
                        lower=18720.91,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 12:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18721.07,
                        open=18711.84,
                        higher=18722.46,
                        lower=18699.95,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 11:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18712.53,
                        open=18706.91,
                        higher=18718.85,
                        lower=18697.87,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 10:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18706.91,
                        open=18713.59,
                        higher=18726.74,
                        lower=18704.23,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 09:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18713.59,
                        open=18712.47,
                        higher=18731.2,
                        lower=18705.9,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 08:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18712.35,
                        open=18703.13,
                        higher=18735.46,
                        lower=18680.81,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-27 07:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18693.37,
                        open=18654.72,
                        higher=18706.65,
                        lower=18652.88,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-24 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=18653.26,
                        open=18600.64,
                        higher=18659.0,
                        lower=18600.64,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-24 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                ],
                Candle(
                    lower=18635.04,
                    higher=18855.05,
                    open=18775.55,
                    close=18677.87,
                    ut=UnitTime.D,
                    date=datetime.datetime.now(),
                ),
            ),
            (
                [
                    Candle(
                        close=40.64,
                        open=40.58,
                        higher=40.64,
                        lower=40.53,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 15:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                    Candle(
                        close=40.58,
                        open=40.59,
                        higher=40.62,
                        lower=40.48,
                        ut=UnitTime.H1,
                        date=datetime.datetime.strptime(
                            "2024-05-28 14:00:00", "%Y-%m-%d %H:%M:%S"
                        ),
                    ),
                ],
                None,
            ),
        ],
    )
    def test_build_daily_candle_from_hours(
        self, candles: List[Candle], expected: Candle
    ):
        candle = build_daily_candle_from_hours(candles, 28)
        if expected is None:
            assert candle is None
        else:
            assert candle is not None
            assert candle.close == expected.close
            assert candle.open == expected.open
            assert candle.lower == expected.lower
            assert candle.higher == expected.higher

    @pytest.mark.parametrize(
        "candles, open_hour, expected",
        [
            (
                [
                    Candle(
                        lower=7628.57,
                        higher=7653.31,
                        open=7651.63,
                        close=7628.57,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 15, 0),
                    )
                ],
                7,
                [],
            ),
            (
                [
                    Candle(
                        lower=7628.57,
                        higher=7653.31,
                        open=7651.63,
                        close=7628.57,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 15, 0),
                    ),
                    Candle(
                        lower=7621.83,
                        higher=7656.40,
                        open=7621.83,
                        close=7654.36,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 14, 0),
                    ),
                    Candle(
                        lower=7601.82,
                        higher=7633.59,
                        open=7632,
                        close=7621.16,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    ),
                ],
                7,
                [
                    Candle(
                        lower=7621.83,
                        higher=7656.40,
                        open=7621.83,
                        close=7628.57,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 21, 14, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=7621.83,
                        higher=7656.40,
                        open=7621.83,
                        close=7654.36,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 14, 0),
                    ),
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    ),
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 12, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 11, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 10, 0),
                    ),
                    Candle(
                        lower=0.9,
                        higher=10.0,
                        open=0.9,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 9, 0),
                    ),
                ],
                7,
                [
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 21, 10, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 9, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 8, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 7, 0),
                    ),
                    Candle(
                        lower=0.9,
                        higher=10.0,
                        open=0.9,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 15, 0),
                    ),
                ],
                7,
                [
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 21, 7, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 8, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 7, 0),
                    ),
                    Candle(
                        lower=15.0,
                        higher=15.5,
                        open=15.1,
                        close=15.4,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 15, 0),
                    ),
                    Candle(
                        lower=16.0,
                        higher=16.6,
                        open=16.1,
                        close=16.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 14, 0),
                    ),
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 13, 0),
                    ),
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 12, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 11, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 10, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 9, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=12.0,
                        open=1.2,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 8, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 7, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.3,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 19, 15, 0),
                    ),
                ],
                7,
                [
                    Candle(
                        lower=15.0,
                        higher=16.6,
                        open=16.1,
                        close=15.4,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 20, 14, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=11.0,
                        open=1.1,
                        close=9.0,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 20, 10, 0),
                    ),
                    Candle(
                        lower=1.0,
                        higher=12.0,
                        open=1.1,
                        close=3.5,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 20, 7, 0),
                    ),
                ],
            ),
            (
                [
                    Candle(
                        lower=2.0,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 16, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 15, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 14, 0),
                    ),
                    Candle(
                        lower=1.4,
                        higher=4.0,
                        open=1.3,
                        close=5.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.1,
                        open=1.3,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 19, 0),
                    ),
                ],
                13,
                [
                    Candle(
                        lower=1.1,
                        higher=10.0,
                        open=1.3,
                        close=9.0,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=1.1,
                        higher=10.0,
                        open=3.0,
                        close=9.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 16, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.1,
                        open=3.1,
                        close=3.6,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 15, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.0,
                        open=3.0,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 14, 0),
                    ),
                    Candle(
                        lower=1.4,
                        higher=4.0,
                        open=1.3,
                        close=5.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.1,
                        open=1.3,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 19, 0),
                    ),
                    Candle(
                        lower=1.3,
                        higher=4.2,
                        open=1.2,
                        close=3.3,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 18, 0),
                    ),
                    Candle(
                        lower=1.42,
                        higher=4.8,
                        open=1.1,
                        close=3.2,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 17, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.1,
                        open=1.1,
                        close=3.1,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 16, 0),
                    ),
                ],
                13,
                [
                    Candle(
                        lower=1.1,
                        higher=10.0,
                        open=1.3,
                        close=9.0,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.8,
                        open=1.1,
                        close=3.5,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 20, 17, 0),
                    ),
                ],
            ),
            (
                [
                    Candle(
                        lower=1.4,
                        higher=4.0,
                        open=1.3,
                        close=5.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    ),
                    Candle(
                        lower=1.2,
                        higher=4.1,
                        open=1.3,
                        close=3.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 19, 0),
                    ),
                    Candle(
                        lower=1.3,
                        higher=4.2,
                        open=1.2,
                        close=3.3,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 18, 0),
                    ),
                    Candle(
                        lower=1.42,
                        higher=4.8,
                        open=1.1,
                        close=3.2,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 17, 0),
                    ),
                    Candle(
                        lower=1.1,
                        higher=4.1,
                        open=1.1,
                        close=3.1,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 16, 0),
                    ),
                ],
                13,
                [
                    Candle(
                        lower=1.2,
                        higher=4.8,
                        open=1.1,
                        close=3.5,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 6, 20, 17, 0),
                    ),
                ],
            ),
        ],
    )
    def test_build_h4_candles(
        self, candles: List[Candle], open_hour: int, expected: List[Candle]
    ):
        assert (
            build_h4_candles_from_h1(candles=candles, open_hour_utc0=open_hour)
            == expected
        )
