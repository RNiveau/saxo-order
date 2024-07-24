import datetime
from typing import List

import pytest

from model import (
    BollingerBands,
    Candle,
    ComboSignal,
    Direction,
    SignalStrength,
    UnitTime,
)
from services.indicator_service import (
    average_true_range,
    bollinger_bands,
    combo,
    containing_candle,
    double_top,
    exponentiel_mobile_average,
    macd0lag,
    slope_percentage,
)


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
                lambda x: Candle(
                    0, x, 0, 0, UnitTime.D, datetime.datetime.now()
                ),
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
                BollingerBands(
                    middle=8182.2755, bottom=8118.8328, up=8245.7182
                ),
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
                BollingerBands(
                    middle=18732.8735, bottom=18636.9720, up=18828.7750
                ),
            ),
        ],
    )
    def test_bollinger_bands(self, candles, std, expected):
        candles = list(
            map(
                lambda x: Candle(
                    0, 0, 0, x, UnitTime.D, datetime.datetime.now()
                ),
                candles,
            )
        )
        assert bollinger_bands(candles, std) == expected

    @pytest.mark.parametrize(
        "candles, expected",
        [
            (
                [
                    Candle(5, 6, 5.5, 6, UnitTime.D),
                    Candle(5, 6, 5.5, 6, UnitTime.D),
                ],
                None,
            ),
            (
                [
                    Candle(4, 8, 5.5, 6, UnitTime.D),
                    Candle(5, 6, 5.5, 6, UnitTime.D),
                ],
                None,
            ),
            (
                [
                    Candle(4, 8, 4.2, 6.2, UnitTime.D),
                    Candle(5, 6, 5.5, 6, UnitTime.D),
                ],
                Candle(4, 8, 4.2, 6.2, UnitTime.D),
            ),
            (
                [
                    Candle(4, 8, 8, 4.9, UnitTime.D),
                    Candle(5, 6, 5.5, 6, UnitTime.D),
                ],
                Candle(4, 8, 8, 4.9, UnitTime.D),
            ),
        ],
    )
    def test_containing_candle(self, candles, expected):
        assert containing_candle(candles) == expected

    @pytest.mark.parametrize(
        "x1, y1, x2, y2, expected",
        [
            (0, 18266, 5, 18313, 5.13297),
            (0, 18295, 12, 18362, 3.0407),
            (0, 44.97, 17, 46.291, 16.78639),
            (0, 37.66, 11, 36.691, -24.00886),
            (0, 7618.46, 7, 7613, -1.02456),
        ],
    )
    def test_slope_percentage(
        self, x1: float, y1: float, x2: float, y2: float, expected: float
    ):
        assert slope_percentage(x1, y1, x2, y2) == expected

    @pytest.mark.parametrize(
        "candles, period, expected",
        [
            (
                [
                    18534.56,
                    18407.22,
                    18236.19,
                    18472.05,
                    18475.45,
                    18450.48,
                    18374.53,
                    18164.06,
                    18290.66,
                    18235.45,
                    18210.55,
                    18155.24,
                    18177.62,
                    18325.58,
                    18163.52,
                    18254.18,
                    18067.91,
                    18131.97,
                    18068.21,
                    18002.02,
                    18265.68,
                    18630.86,
                    18369.94,
                ],
                7,
                18402.44569,
            ),  # DAX D 11/07/2024
            (
                [
                    39.8,
                    39.05,
                    38.2,
                    41,
                    40.32,
                    44.09,
                    44.23,
                    44.18,
                    43.64,
                    43.86,
                    43.27,
                    42.95,
                    44.05,
                    43.41,
                    46.55,
                    47.45,
                ],
                5,
                40.11208,
            ),  # ITP W 08/07/2024
            (
                [
                    7570.05,
                    7632.71,
                    7626.74,
                    7639.13,
                    7651.51,
                    7671.34,
                    7686.06,
                    7693.67,
                    7692.19,
                    7680.64,
                    7724.32,
                    7729.35,
                    7700.19,
                    7686.55,
                    7686.91,
                    7681.62,
                    7670.91,
                    7690.60,
                    7674.06,
                    7627.13,
                    7634.64,
                    7623.62,
                    7608.2,
                    7598.73,
                    7602.2,
                    7616.99,
                    7620.63,
                    7610.96,
                    7573.55,
                    7569.43,
                ],
                10,
                7641.95384,
            ),  # CAC H1 16/07/2024 09:00:00
        ],
    )
    def test_exponentiel_mobile_average(
        self, candles: List[float], period: int, expected: float
    ):
        assert exponentiel_mobile_average(candles, period) == expected

    @pytest.mark.parametrize(
        "file_candles, expected",
        [
            ("macd0lag_cac_h1.obj", (-36.07337, -32.71418)),
            ("macd0lag_dax_daily.obj", (113.46834, 107.26162)),
        ],
    )
    def test_macd0lag(self, file_candles: str, expected: float):
        with open(f"tests/services/files/{file_candles}", "r") as f:
            candles = eval(
                f.read(),
                {"datetime": datetime, "Candle": Candle, "UnitTime": UnitTime},
            )
        assert macd0lag(candles) == expected

    @pytest.mark.parametrize(
        "file_candles, expected",
        [
            (
                "combo_buy_daily_cac.obj",
                ComboSignal(
                    7401.35,
                    True,
                    Direction.BUY,
                    SignalStrength.MEDIUM,
                    {
                        "macd": True,
                        "ma50_over_bb": False,
                        "price_within_bb": True,
                        "strong_ma50": True,
                        "both_bb_flat": False,
                    },
                ),
            ),
            (
                "combo_buy_h4_dax.obj",
                ComboSignal(
                    18640.90,
                    False,
                    Direction.BUY,
                    SignalStrength.MEDIUM,
                    {
                        "macd": True,
                        "ma50_over_bb": True,
                        "price_within_bb": True,
                        "strong_ma50": False,
                        "both_bb_flat": False,
                    },
                ),
            ),
            (
                "no_combo_h4_dax.obj",
                None,
            ),
            (
                "no_combo_h4_dax_2.obj",
                None,
            ),
            ("no_combo_buy_daily_eramet.obj", None),
            (
                "combo_buy_daily_aca.obj",
                None,
            ),
            ("no_combo_sell_h4_dax.obj", None),
            (
                "combo_sell_h1_dax.obj",
                ComboSignal(
                    18140.82,
                    False,
                    Direction.SELL,
                    SignalStrength.MEDIUM,
                    {
                        "macd": False,
                        "ma50_over_bb": False,
                        "price_within_bb": True,
                        "strong_ma50": False,
                        "both_bb_flat": True,
                    },
                ),
            ),
            (
                "combo_sell_h1_cac.obj",
                ComboSignal(
                    7861.23,
                    False,
                    Direction.SELL,
                    SignalStrength.MEDIUM,
                    {
                        "macd": False,
                        "ma50_over_bb": False,
                        "price_within_bb": False,
                        "strong_ma50": False,
                        "both_bb_flat": True,
                    },
                ),
            ),
            (
                "no_combo_daily_stmpa.obj",
                None,
            ),
            (
                "no_combo_daily_vie.obj",
                None,
            ),
            (
                "combo_sell_daily_aca.obj",
                ComboSignal(
                    13.91,
                    False,
                    Direction.SELL,
                    SignalStrength.MEDIUM,
                    {
                        "macd": True,
                        "ma50_over_bb": False,
                        "price_within_bb": False,
                        "strong_ma50": True,
                        "both_bb_flat": False,
                    },
                ),
            ),
        ],
    )
    def test_combo(self, file_candles: str, expected: float):
        with open(f"tests/services/files/{file_candles}", "r") as f:
            candles = eval(
                f.read(),
                {"datetime": datetime, "Candle": Candle, "UnitTime": UnitTime},
            )
        assert combo(candles) == expected

    @pytest.mark.parametrize(
        "file_candles, expected",
        [
            (
                "combo_buy_daily_cac.obj",
                74.95462,
            ),
            ("combo_buy_h4_dax.obj", 79.38263),
            ("atr_aca_daily.obj", 0.29201),
        ],
    )
    def test_average_true_range(self, file_candles: str, expected: float):
        with open(f"tests/services/files/{file_candles}", "r") as f:
            candles = eval(
                f.read(),
                {"datetime": datetime, "Candle": Candle, "UnitTime": UnitTime},
            )
        assert average_true_range(candles) == expected
