import datetime

import pytest

from model import Candle, UnitTime
from utils.helper import *


class TestIndicatorService:

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
