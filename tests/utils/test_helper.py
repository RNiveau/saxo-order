import datetime
from typing import List

import pytest

from model import Candle, EUMarket, Market, UnitTime, USMarket
from utils.helper import (
    build_current_weekly_candle_from_daily,
    build_daily_candles_from_h1,
    build_h4_candles_from_h1,
    build_weekly_candles_from_daily,
    last_session_close,
    market_in_utc,
)


class TestHelper:

    @pytest.mark.parametrize(
        "candles, market, expected",
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
                EUMarket(),
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
                EUMarket(),
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
                EUMarket(),
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
                EUMarket(),
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
                EUMarket(),
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
                USMarket(),
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
                USMarket(),
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
                USMarket(),
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
        self, candles: List[Candle], market: Market, expected: List[Candle]
    ):
        assert (
            build_h4_candles_from_h1(candles=candles, market=market)
            == expected
        )

    @pytest.mark.parametrize(
        "candles, market, expected",
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
                USMarket(),
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
                EUMarket(),
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
                EUMarket(),
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
            # EU incomplete day - only 2 H1 candles, not enough for a full day
            (
                [
                    Candle(
                        close=40.64,
                        open=40.58,
                        higher=40.64,
                        lower=40.53,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 15, 0),
                    ),
                    Candle(
                        close=40.58,
                        open=40.59,
                        higher=40.62,
                        lower=40.48,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 14, 0),
                    ),
                ],
                EUMarket(),
                [],
            ),
            # EU multi-day: 2 complete days (28th and 27th) + partial 24th
            (
                [
                    Candle(
                        close=40.64,
                        open=40.58,
                        higher=40.64,
                        lower=40.53,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 15, 0),
                    ),
                    Candle(
                        close=40.58,
                        open=40.59,
                        higher=40.62,
                        lower=40.48,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 14, 0),
                    ),
                    Candle(
                        close=40.61,
                        open=40.55,
                        higher=40.64,
                        lower=40.5,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 13, 0),
                    ),
                    Candle(
                        close=40.55,
                        open=40.65,
                        higher=40.65,
                        lower=40.53,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 12, 0),
                    ),
                    Candle(
                        close=40.64,
                        open=40.53,
                        higher=40.72,
                        lower=40.51,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 11, 0),
                    ),
                    Candle(
                        close=40.52,
                        open=40.66,
                        higher=40.72,
                        lower=40.51,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 10, 0),
                    ),
                    Candle(
                        close=40.65,
                        open=40.74,
                        higher=40.77,
                        lower=40.57,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 9, 0),
                    ),
                    Candle(
                        close=40.75,
                        open=40.92,
                        higher=40.99,
                        lower=40.71,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 8, 0),
                    ),
                    Candle(
                        close=40.92,
                        open=40.99,
                        higher=41.12,
                        lower=40.89,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 28, 7, 0),
                    ),
                    Candle(
                        close=40.84,
                        open=40.9,
                        higher=40.93,
                        lower=40.84,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 15, 0),
                    ),
                    Candle(
                        close=40.9,
                        open=40.89,
                        higher=40.94,
                        lower=40.85,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 14, 0),
                    ),
                    Candle(
                        close=40.88,
                        open=40.87,
                        higher=40.94,
                        lower=40.83,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 13, 0),
                    ),
                    Candle(
                        close=40.86,
                        open=40.86,
                        higher=40.9,
                        lower=40.84,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 12, 0),
                    ),
                    Candle(
                        close=40.86,
                        open=40.74,
                        higher=40.87,
                        lower=40.71,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 11, 0),
                    ),
                    Candle(
                        close=40.72,
                        open=40.7,
                        higher=40.77,
                        lower=40.7,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 10, 0),
                    ),
                    Candle(
                        close=40.71,
                        open=40.84,
                        higher=40.85,
                        lower=40.67,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 9, 0),
                    ),
                    Candle(
                        close=40.83,
                        open=40.65,
                        higher=40.83,
                        lower=40.65,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 8, 0),
                    ),
                    Candle(
                        close=40.65,
                        open=40.75,
                        higher=40.93,
                        lower=40.6,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 27, 7, 0),
                    ),
                    Candle(
                        close=40.65,
                        open=40.65,
                        higher=40.82,
                        lower=40.65,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 24, 15, 0),
                    ),
                    Candle(
                        close=40.66,
                        open=40.4,
                        higher=40.72,
                        lower=40.39,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 5, 24, 14, 0),
                    ),
                ],
                EUMarket(),
                [
                    Candle(
                        lower=40.48,
                        higher=41.12,
                        open=40.99,
                        close=40.64,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 28, 7, 0),
                    ),
                    Candle(
                        lower=40.6,
                        higher=40.94,
                        open=40.75,
                        close=40.84,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 5, 27, 7, 0),
                    ),
                ],
            ),
            # US complete day: 7 H1 candles
            (
                [
                    Candle(
                        close=5478.35,
                        open=5475.56,
                        higher=5486.31,
                        lower=5474.79,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 19, 0),
                    ),
                    Candle(
                        close=5475.56,
                        open=5475.31,
                        higher=5480.69,
                        lower=5470.04,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 18, 0),
                    ),
                    Candle(
                        close=5475.31,
                        open=5472.0,
                        higher=5476.0,
                        lower=5468.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 17, 0),
                    ),
                    Candle(
                        close=5472.0,
                        open=5470.0,
                        higher=5475.0,
                        lower=5465.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 16, 0),
                    ),
                    Candle(
                        close=5470.0,
                        open=5468.0,
                        higher=5473.0,
                        lower=5462.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 15, 0),
                    ),
                    Candle(
                        close=5468.0,
                        open=5465.0,
                        higher=5471.0,
                        lower=5460.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 14, 0),
                    ),
                    Candle(
                        close=5465.0,
                        open=5460.0,
                        higher=5467.0,
                        lower=5455.0,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 13, 0),
                    ),
                ],
                USMarket(),
                [
                    Candle(
                        lower=5455.0,
                        higher=5480.69,
                        open=5460.0,
                        close=5475.56,
                        ut=UnitTime.D,
                        date=datetime.datetime(2024, 6, 18, 13, 0),
                    ),
                ],
            ),
        ],
    )
    def test_build_daily_candle_from_h1(
        self, candles: List[Candle], market: Market, expected: List[Candle]
    ):
        assert (
            build_daily_candles_from_h1(candles=candles, market=market)
            == expected
        )

    @pytest.mark.parametrize(
        "market_factory, reference, expected_open, expected_close",
        [
            # Euronext Paris 09:00-17:00 local -> UTC 07:00-15:00 in CEST
            (EUMarket, datetime.datetime(2024, 6, 21), 7, 15),
            # ... and UTC 08:00-16:00 in CET (winter)
            (EUMarket, datetime.datetime(2024, 1, 15), 8, 16),
            # NYSE 09:30-15:00 local -> UTC 13:30-19:00 in EDT
            (USMarket, datetime.datetime(2024, 6, 21), 13, 19),
            # ... and UTC 14:30-20:00 in EST (winter)
            (USMarket, datetime.datetime(2024, 1, 15), 14, 20),
        ],
    )
    def test_market_in_utc(
        self,
        market_factory,
        reference: datetime.datetime,
        expected_open: int,
        expected_close: int,
    ):
        market = market_in_utc(market_factory(), reference)
        assert market.open_hour == expected_open
        assert market.close_hour == expected_close
        assert market.open_minutes == market_factory().open_minutes
        assert market.end_minute == market_factory().end_minute

    def test_build_daily_candle_from_h1_winter_dst(self):
        """In winter (CET) the EU session lands on UTC 08:00-16:00.

        With the hardcoded summer UTC close hour (15) this batch produced
        no daily candle; the DST-aware conversion now recognises the 16:00
        UTC close.
        """
        candles = [
            Candle(
                lower=93 + i,
                higher=118 - i,
                open=97 + i,
                close=99 + i,
                ut=UnitTime.H1,
                date=datetime.datetime(2024, 1, 15, hour, 0),
            )
            for i, hour in enumerate(range(16, 7, -1))
        ]
        expected = [
            Candle(
                lower=min(c.lower for c in candles),
                higher=max(c.higher for c in candles),
                open=candles[-1].open,
                close=candles[0].close,
                ut=UnitTime.D,
                date=datetime.datetime(2024, 1, 15, 8, 0),
            )
        ]
        assert (
            build_daily_candles_from_h1(candles=candles, market=EUMarket())
            == expected
        )

    def test_build_daily_candles_cross_season_batch(self):
        """A single batch spanning a DST transition must build a daily
        candle for both the winter and the summer day.

        Each candle's own date selects its DST regime, so the winter close
        (16:00 UTC) and the summer close (15:00 UTC) are both recognised.
        A single per-batch regime would drop one of the two days.
        """
        winter = [
            Candle(
                lower=200 + i,
                higher=300 - i,
                open=210 + i,
                close=220 + i,
                ut=UnitTime.H1,
                date=datetime.datetime(2025, 1, 15, hour, 0),
            )
            for i, hour in enumerate(range(16, 7, -1))
        ]
        summer = [
            Candle(
                lower=100 + i,
                higher=190 - i,
                open=110 + i,
                close=120 + i,
                ut=UnitTime.H1,
                date=datetime.datetime(2024, 8, 20, hour, 0),
            )
            for i, hour in enumerate(range(15, 6, -1))
        ]

        def daily(day, date):
            return Candle(
                lower=min(c.lower for c in day),
                higher=max(c.higher for c in day),
                open=day[-1].open,
                close=day[0].close,
                ut=UnitTime.D,
                date=date,
            )

        expected = [
            daily(winter, datetime.datetime(2025, 1, 15, 8, 0)),
            daily(summer, datetime.datetime(2024, 8, 20, 7, 0)),
        ]
        assert (
            build_daily_candles_from_h1(
                candles=winter + summer, market=EUMarket()
            )
            == expected
        )

    def test_build_h4_candles_from_h1_winter_dst(self):
        """In winter (CET) the EU session lands on UTC 08:00-16:00, so H4
        blocks end at UTC 10/14/16 instead of the summer 09/13/15."""
        winter = [
            Candle(
                lower=200 + i,
                higher=300 - i,
                open=210 + i,
                close=220 + i,
                ut=UnitTime.H1,
                date=datetime.datetime(2025, 1, 15, hour, 0),
            )
            for i, hour in enumerate(range(16, 7, -1))
        ]

        def h4(day):
            return Candle(
                lower=min(c.lower for c in day),
                higher=max(c.higher for c in day),
                open=day[-1].open,
                close=day[0].close,
                ut=UnitTime.H4,
                date=day[-1].date,
            )

        expected = [h4(winter[0:2]), h4(winter[2:6]), h4(winter[6:9])]
        assert (
            build_h4_candles_from_h1(candles=winter, market=EUMarket())
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
        current_iso_year, current_iso_week, current_iso_day = (
            today.isocalendar()
        )

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
        last_week = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            days=7
        )
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

    @pytest.mark.parametrize(
        "market_factory, reference, expected",
        [
            # 2024-06-21 is a Friday; EU summer session is 07:00-15:00 UTC.
            # During session -> reference is returned unchanged.
            (
                EUMarket,
                datetime.datetime(2024, 6, 21, 10, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 21, 10, 0, tzinfo=datetime.UTC),
            ),
            # After the close -> snap back to today's close.
            (
                EUMarket,
                datetime.datetime(2024, 6, 21, 19, 56, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 21, 15, 0, tzinfo=datetime.UTC),
            ),
            # Before the open -> previous trading day's close.
            (
                EUMarket,
                datetime.datetime(2024, 6, 21, 6, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 20, 15, 0, tzinfo=datetime.UTC),
            ),
            # Saturday -> Friday's close.
            (
                EUMarket,
                datetime.datetime(2024, 6, 22, 12, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 21, 15, 0, tzinfo=datetime.UTC),
            ),
            # Sunday -> Friday's close.
            (
                EUMarket,
                datetime.datetime(2024, 6, 23, 12, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 21, 15, 0, tzinfo=datetime.UTC),
            ),
            # Monday pre-open -> Friday's close (weekend skipped).
            (
                EUMarket,
                datetime.datetime(2024, 6, 24, 5, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 21, 15, 0, tzinfo=datetime.UTC),
            ),
            # Winter DST: EU close lands at 16:00 UTC (2024-01-15 is Monday).
            (
                EUMarket,
                datetime.datetime(2024, 1, 15, 19, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 1, 15, 16, 0, tzinfo=datetime.UTC),
            ),
            # US summer session closes at 19:00 UTC.
            (
                USMarket,
                datetime.datetime(2024, 6, 21, 22, 0, tzinfo=datetime.UTC),
                datetime.datetime(2024, 6, 21, 19, 0, tzinfo=datetime.UTC),
            ),
        ],
    )
    def test_last_session_close(
        self,
        market_factory,
        reference: datetime.datetime,
        expected: datetime.datetime,
    ):
        assert last_session_close(reference, market_factory()) == expected

    def test_last_session_close_naive_reference_is_utc(self):
        """A naive reference is treated as UTC; a tz-aware anchor returns."""
        anchor = last_session_close(
            datetime.datetime(2024, 6, 21, 19, 56), EUMarket()
        )
        assert anchor == datetime.datetime(
            2024, 6, 21, 15, 0, tzinfo=datetime.UTC
        )
        assert anchor.tzinfo is not None
