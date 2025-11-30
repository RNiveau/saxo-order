import datetime
from typing import List

import pytest

from model import Candle, UnitTime
from utils.helper import (
    build_current_weekly_candle_from_daily,
    build_daily_candle_from_hours,
    build_daily_candles_from_h1,
    build_h4_candles_from_h1,
    build_weekly_candles_from_daily,
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
    def test_build_h4_candles_from_h1(
        self, candles: List[Candle], open_hour: int, expected: List[Candle]
    ):
        assert (
            build_h4_candles_from_h1(candles=candles, open_hour_utc0=open_hour)
            == expected
        )

    @pytest.mark.parametrize(
        "candles, open_hour, expected",
        [
            (
                [
                    Candle(
                        lower=1.4,
                        higher=4.0,
                        open=1.3,
                        close=5.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 21, 13, 0),
                    )
                ],
                13,
                [],
            ),
            (
                [
                    Candle(
                        lower=7481.67,
                        higher=7491.62,
                        open=7491.62,
                        close=7485.73,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 15, 0),
                    ),
                    Candle(
                        lower=7489.80,
                        higher=7506.71,
                        open=7491.80,
                        close=7506.71,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 14, 0),
                    ),
                    Candle(
                        lower=7490.88,
                        higher=7506.96,
                        open=7496.16,
                        close=7506.96,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 13, 0),
                    ),
                    Candle(
                        lower=7490.88,
                        higher=7511.86,
                        open=7493.84,
                        close=7495.21,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 12, 0),
                    ),
                    Candle(
                        lower=7505.04,
                        higher=7512.21,
                        open=7510.32,
                        close=7510.02,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 11, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7516.10,
                        open=7509.42,
                        close=7511.21,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 10, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7523.55,
                        open=7507.69,
                        close=7508.98,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 9, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7531.70,
                        open=7511.69,
                        close=7519.66,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 8, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7525.48,
                        open=7518.70,
                        close=7525.48,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 7, 0),
                    ),
                ],
                7,
                [
                    Candle(
                        lower=7481.67,
                        higher=7531.70,
                        open=7518.70,
                        close=7485.73,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 8, 20, 7, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=1,
                        higher=2,
                        open=3,
                        close=4,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 21, 7, 0),
                    ),
                    Candle(
                        lower=7481.67,
                        higher=7491.62,
                        open=7491.62,
                        close=7485.73,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 15, 0),
                    ),
                    Candle(
                        lower=7489.80,
                        higher=7506.71,
                        open=7491.80,
                        close=7506.71,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 14, 0),
                    ),
                    Candle(
                        lower=7490.88,
                        higher=7506.96,
                        open=7496.16,
                        close=7506.96,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 13, 0),
                    ),
                    Candle(
                        lower=7490.88,
                        higher=7511.86,
                        open=7493.84,
                        close=7495.21,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 12, 0),
                    ),
                    Candle(
                        lower=7505.04,
                        higher=7512.21,
                        open=7510.32,
                        close=7510.02,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 11, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7516.10,
                        open=7509.42,
                        close=7511.21,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 10, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7523.55,
                        open=7507.69,
                        close=7508.98,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 9, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7531.70,
                        open=7511.69,
                        close=7519.66,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 8, 0),
                    ),
                    Candle(
                        lower=7502.10,
                        higher=7525.48,
                        open=7518.70,
                        close=7525.48,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 20, 7, 0),
                    ),
                    Candle(
                        lower=1,
                        higher=2,
                        open=3,
                        close=4,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 8, 19, 15, 0),
                    ),
                ],
                7,
                [
                    Candle(
                        lower=7481.67,
                        higher=7531.70,
                        open=7518.70,
                        close=7485.73,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 8, 20, 7, 0),
                    )
                ],
            ),
        ],
    )
    def test_build_daily_candle_from_h1(
        self, candles: List[Candle], open_hour: int, expected: List[Candle]
    ):
        assert (
            build_daily_candles_from_h1(
                candles=candles, open_hour_utc0=open_hour
            )
            == expected
        )

    @pytest.mark.parametrize(
        "candles, expected",
        [
            ([], []),
            (
                [
                    Candle(
                        lower=100.0,
                        higher=110.0,
                        open=105.0,
                        close=108.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 5, 15, 0),
                    ),
                    Candle(
                        lower=102.0,
                        higher=112.0,
                        open=104.0,
                        close=106.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 4, 15, 0),
                    ),
                    Candle(
                        lower=98.0,
                        higher=108.0,
                        open=100.0,
                        close=105.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 3, 15, 0),
                    ),
                    Candle(
                        lower=95.0,
                        higher=105.0,
                        open=98.0,
                        close=102.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 2, 15, 0),
                    ),
                    Candle(
                        lower=90.0,
                        higher=100.0,
                        open=92.0,
                        close=99.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 1, 15, 0),
                    ),
                ],
                [
                    Candle(
                        lower=90.0,
                        higher=112.0,
                        open=92.0,
                        close=108.0,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 1, 1, 15, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=115.0,
                        higher=125.0,
                        open=120.0,
                        close=122.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 12, 15, 0),
                    ),
                    Candle(
                        lower=110.0,
                        higher=120.0,
                        open=112.0,
                        close=118.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 11, 15, 0),
                    ),
                    Candle(
                        lower=108.0,
                        higher=118.0,
                        open=110.0,
                        close=115.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 10, 15, 0),
                    ),
                    Candle(
                        lower=105.0,
                        higher=115.0,
                        open=108.0,
                        close=112.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 9, 15, 0),
                    ),
                    Candle(
                        lower=100.0,
                        higher=110.0,
                        open=105.0,
                        close=108.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 8, 15, 0),
                    ),
                    Candle(
                        lower=100.0,
                        higher=110.0,
                        open=105.0,
                        close=108.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 5, 15, 0),
                    ),
                    Candle(
                        lower=102.0,
                        higher=112.0,
                        open=104.0,
                        close=106.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 4, 15, 0),
                    ),
                    Candle(
                        lower=98.0,
                        higher=108.0,
                        open=100.0,
                        close=105.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 3, 15, 0),
                    ),
                    Candle(
                        lower=95.0,
                        higher=105.0,
                        open=98.0,
                        close=102.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 2, 15, 0),
                    ),
                    Candle(
                        lower=90.0,
                        higher=100.0,
                        open=92.0,
                        close=99.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 1, 15, 0),
                    ),
                ],
                [
                    Candle(
                        lower=100.0,
                        higher=125.0,
                        open=105.0,
                        close=122.0,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 1, 8, 15, 0),
                    ),
                    Candle(
                        lower=90.0,
                        higher=112.0,
                        open=92.0,
                        close=108.0,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 1, 1, 15, 0),
                    ),
                ],
            ),
            (
                [
                    Candle(
                        lower=95.0,
                        higher=105.0,
                        open=98.0,
                        close=102.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 2, 15, 0),
                    ),
                    Candle(
                        lower=90.0,
                        higher=100.0,
                        open=92.0,
                        close=99.0,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 1, 1, 15, 0),
                    ),
                ],
                [
                    Candle(
                        lower=90.0,
                        higher=105.0,
                        open=92.0,
                        close=102.0,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 1, 1, 15, 0),
                    )
                ],
            ),
            (
                [
                    Candle(
                        lower=40.53,
                        higher=41.12,
                        open=40.99,
                        close=40.64,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 28, 15, 0),
                    ),
                    Candle(
                        lower=40.60,
                        higher=40.93,
                        open=40.75,
                        close=40.84,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 27, 15, 0),
                    ),
                    Candle(
                        lower=40.39,
                        higher=40.82,
                        open=40.65,
                        close=40.65,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 24, 15, 0),
                    ),
                    Candle(
                        lower=40.45,
                        higher=40.78,
                        open=40.60,
                        close=40.70,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 23, 15, 0),
                    ),
                    Candle(
                        lower=40.30,
                        higher=40.65,
                        open=40.50,
                        close=40.58,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 22, 15, 0),
                    ),
                    Candle(
                        lower=40.25,
                        higher=40.55,
                        open=40.40,
                        close=40.52,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 21, 15, 0),
                    ),
                    Candle(
                        lower=40.20,
                        higher=40.50,
                        open=40.35,
                        close=40.45,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 20, 15, 0),
                    ),
                ],
                [
                    Candle(
                        lower=40.53,
                        higher=41.12,
                        open=40.75,
                        close=40.64,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 5, 27, 15, 0),
                    ),
                    Candle(
                        lower=40.20,
                        higher=40.82,
                        open=40.35,
                        close=40.65,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 5, 20, 15, 0),
                    ),
                ],
            ),
            (
                # week with only tuesday and wednesday
                [
                    Candle(
                        lower=40.25,
                        higher=40.55,
                        open=40.40,
                        close=40.52,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 22, 15, 0),
                    ),
                    Candle(
                        lower=40.20,
                        higher=40.50,
                        open=40.35,
                        close=40.45,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 21, 15, 0),
                    ),
                ],
                [
                    Candle(
                        lower=40.20,
                        higher=40.55,
                        open=40.35,
                        close=40.52,
                        ut=UnitTime.W,
                        date=datetime.datetime(2024, 5, 21, 15, 0),
                    )
                ],
            ),
        ],
    )
    def test_build_weekly_candles_from_daily(
        self, candles: List[Candle], expected: List[Candle]
    ):
        result = build_weekly_candles_from_daily(candles)
        assert len(result) == len(expected)
        for i, (result_candle, expected_candle) in enumerate(
            zip(result, expected)
        ):
            assert (
                result_candle.lower == expected_candle.lower
            ), f"Candle {i}: lower mismatch"
            assert (
                result_candle.higher == expected_candle.higher
            ), f"Candle {i}: higher mismatch"
            assert (
                result_candle.open == expected_candle.open
            ), f"Candle {i}: open mismatch"
            assert (
                result_candle.close == expected_candle.close
            ), f"Candle {i}: close mismatch"
            assert (
                result_candle.ut == expected_candle.ut
            ), f"Candle {i}: ut mismatch"
            assert (
                result_candle.date == expected_candle.date
            ), f"Candle {i}: date mismatch"

    def test_build_current_weekly_candle_from_daily(self):
        """Test building current week's candle from daily candles"""
        today = datetime.datetime.now(datetime.UTC)
        current_iso_year, current_iso_week, current_iso_day = \
            today.isocalendar()

        days_since_monday = current_iso_day - 1
        monday = today - datetime.timedelta(days=days_since_monday)

        num_days = min(days_since_monday + 1, 5)
        daily_candles = [
            Candle(
                open=100 + i,
                close=105 + i,
                lower=95 + i,
                higher=110 + i,
                ut=UnitTime.D,
                date=monday + datetime.timedelta(days=i),
            )
            for i in range(num_days)
        ]
        daily_candles.reverse()

        result = build_current_weekly_candle_from_daily(daily_candles)

        assert result is not None
        assert result.ut == UnitTime.W
        assert result.open == 100
        assert result.close == 105 + (num_days - 1)
        assert result.lower == 95
        assert result.higher == 110 + (num_days - 1)

    def test_build_current_weekly_candle_empty_list(self):
        """Test with empty candle list"""
        result = build_current_weekly_candle_from_daily([])
        assert result is None

    def test_build_current_weekly_candle_no_current_week(self):
        """Test when no candles from current week"""
        last_week = datetime.datetime.now(datetime.UTC) - \
            datetime.timedelta(days=7)
        daily_candles = [
            Candle(
                open=100,
                close=105,
                lower=95,
                higher=110,
                ut=UnitTime.D,
                date=last_week,
            )
        ]
        result = build_current_weekly_candle_from_daily(daily_candles)
        assert result is None
