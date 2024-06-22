import datetime

import pytest

from model import Candle, UnitTime
from services.workflow_service import *


class TestWorkflowService:

    @pytest.mark.parametrize(
        "file, ut, results, expected_len",
        [
            (
                "dax_15m.obj",
                UnitTime.M15,
                [
                    Candle(
                        lower=18585.53,
                        open=18608.87,
                        close=18593.47,
                        higher=18612.07,
                        ut=UnitTime.D,
                    ),
                    Candle(
                        lower=18574.72,
                        open=18585.02,
                        close=18608.87,
                        higher=18610.76,
                        ut=UnitTime.D,
                    ),
                    Candle(
                        lower=18551.89,
                        open=18554.20,
                        close=18584.75,
                        higher=18588.08,
                        ut=UnitTime.D,
                    ),
                ],
                4,
            ),
            (
                "dax_h1.obj",
                UnitTime.H1,
                [
                    Candle(
                        lower=18428.50,
                        open=18430.63,
                        close=18434.96,
                        higher=18485.49,
                        ut=UnitTime.D,
                    ),
                    Candle(
                        lower=18421.95,
                        open=18423.25,
                        close=18430.63,
                        higher=18454.93,
                        ut=UnitTime.D,
                    ),
                    Candle(
                        lower=18388.02,
                        open=18439.11,
                        close=18423.88,
                        higher=18444.17,
                        ut=UnitTime.D,
                    ),
                ],
                7,
            ),
        ],
    )
    def test_get_candle_per_minutes(
        self, file: str, ut: UnitTime, results: List[Candle], expected_len: int, mocker
    ):
        saxo_client = mocker.Mock()
        mocker.patch.object(
            saxo_client,
            "get_asset",
            return_value={
                "Description": "",
                "AssetType": "Stock",
                "Identifier": 12345,
                "CurrencyCode": "EUR",
            },
        )
        with open(f"tests/services/files/{file}", "r") as f:
            data = eval(f.read(), {"datetime": datetime})

        mocker.patch.object(saxo_client, "get_historical_data", return_value=data)
        worfklow_service = WorkflowService(saxo_client)
        candles = worfklow_service.get_candle_per_minutes("code", len(data), ut)
        for i, result in enumerate(results):
            assert candles[i].close == result.close
            assert candles[i].lower == result.lower
            assert candles[i].higher == result.higher
            assert candles[i].open == result.open

        assert candles[-1].close != -1
        assert candles[-1].open != -1
        assert candles[-1].lower != -1
        assert candles[-1].higher != -1

        assert len(candles) == expected_len

    @pytest.mark.parametrize(
        "file_index, file_cfd, ut, date, expected",
        [
            (
                "ma_dax.obj",
                "ma_cfd_dax.obj",
                UnitTime.H1,
                datetime.datetime(2024, 6, 14, 14, 0),
                18401.5962,
            ),
            (
                "ma_dax.obj",
                "ma_cfd_dax.obj",
                UnitTime.H4,
                datetime.datetime(2024, 6, 14, 14, 0),
                18532.2234,
            ),
            (
                "ma_dax2.obj",
                "",
                UnitTime.H4,
                datetime.datetime(2024, 6, 14, 15, 0),
                18532.2234,
            ),
            (
                "ma_dax2.obj",
                "",
                UnitTime.H1,
                datetime.datetime(2024, 6, 14, 15, 0),
                18391.0818,
            ),
        ],
    )
    def test_calculate_ma(
        self,
        file_index: str,
        file_cfd: str,
        ut: UnitTime,
        date: datetime.datetime,
        expected: float,
        mocker,
    ):
        saxo_client = mocker.Mock()
        mocker.patch.object(
            saxo_client,
            "get_asset",
            return_value={
                "Description": "",
                "AssetType": "Stock",
                "Identifier": 12345,
                "CurrencyCode": "EUR",
            },
        )
        side_effet = []
        with open(f"tests/services/files/{file_index}", "r") as f:
            side_effet.append(eval(f.read(), {"datetime": datetime}))
        if file_cfd != "":
            with open(f"tests/services/files/{file_cfd}", "r") as f:
                side_effet.append(eval(f.read(), {"datetime": datetime}))
        mocker.patch.object(saxo_client, "get_historical_data", side_effect=side_effet)
        mocker.patch("services.workflow_service.get_date_utc0", return_value=date)
        worfklow_service = WorkflowService(saxo_client)
        assert expected == worfklow_service.calculate_ma(
            "dax", "cfd", ut, IndicatorType.MA50, datetime.datetime.now()
        )

    @pytest.mark.parametrize(
        "file_index, file_cfd, open_hour, close_hour, open_minutes, ut, date, expected",
        [
            (
                "cac_30min.obj",
                "",
                7,
                15,
                0,
                UnitTime.H1,
                datetime.datetime(2024, 6, 20, 14, 45),
                [
                    Candle(
                        lower=7626.04,
                        open=7630.49,
                        close=7660.20,
                        higher=7661.60,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 13, 0),
                    ),
                    Candle(
                        lower=7622.46,
                        open=7635.75,
                        close=7630.23,
                        higher=7636.91,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 12, 0),
                    ),
                    Candle(
                        lower=7633.52,
                        open=7634.98,
                        close=7636.61,
                        higher=7650.21,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 11, 0),
                    ),
                ],
            ),
            (
                "cac_30min.obj",
                "cac_cfd_30min.obj",
                7,
                15,
                0,
                UnitTime.H1,
                datetime.datetime(2024, 6, 20, 15, 14),
                [
                    Candle(
                        lower=7646.33,
                        open=7662.12,
                        close=7680.14,
                        higher=7681.68,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 14, 0),
                    ),
                    Candle(
                        lower=7626.04,
                        open=7630.49,
                        close=7660.20,
                        higher=7661.60,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 13, 0),
                    ),
                    Candle(
                        lower=7622.46,
                        open=7635.75,
                        close=7630.23,
                        higher=7636.91,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 12, 0),
                    ),
                    Candle(
                        lower=7633.52,
                        open=7634.98,
                        close=7636.61,
                        higher=7650.21,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 20, 11, 0),
                    ),
                ],
            ),
            (
                "cac_30min_end_of_day.obj",
                "",
                7,
                15,
                0,
                UnitTime.H1,
                datetime.datetime(2024, 6, 19, 18, 1),
                [
                    Candle(
                        lower=7566.09,
                        open=7576.38,
                        close=7570.20,
                        higher=7579.18,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 19, 15, 0),
                    ),
                    Candle(
                        lower=7570.33,
                        open=7582.57,
                        close=7576.03,
                        higher=7588.27,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 19, 14, 0),
                    ),
                    Candle(
                        lower=7577.51,
                        open=7584.03,
                        close=7582.33,
                        higher=7593.09,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 19, 13, 0),
                    ),
                ],
            ),
            (
                "sp500_cfd.obj",
                "",
                13,
                20,
                30,
                UnitTime.H1,
                datetime.datetime(
                    2024,
                    6,
                    18,
                    14,
                ),
                [
                    Candle(
                        lower=5474.7949,
                        open=5475.5649,
                        close=5478.3452,
                        higher=5486.3149,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 13, 30),
                    ),
                    Candle(
                        lower=5470.0449,
                        open=5475.3052,
                        close=5475.5552,
                        higher=5480.6899,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 6, 18, 12, 30),
                    ),
                ],
            ),
        ],
    )
    def test_build_hour_candles(
        self,
        file_index: str,
        file_cfd: str,
        open_hour: int,
        close_hour: int,
        open_minutes: int,
        ut: UnitTime,
        date: datetime.datetime,
        expected: List[Candle],
        mocker,
    ):
        saxo_client = mocker.Mock()
        mocker.patch.object(
            saxo_client,
            "get_asset",
            return_value={
                "Description": "",
                "AssetType": "Stock",
                "Identifier": 12345,
                "CurrencyCode": "EUR",
            },
        )
        side_effet = []
        with open(f"tests/services/files/{file_index}", "r") as f:
            side_effet.append(eval(f.read(), {"datetime": datetime}))
        if file_cfd != "":
            with open(f"tests/services/files/{file_cfd}", "r") as f:
                side_effet.append(eval(f.read(), {"datetime": datetime}))
        mocker.patch.object(saxo_client, "get_historical_data", side_effect=side_effet)
        mocker.patch(
            "services.workflow_service.get_date_utc0",
            return_value=date.replace(tzinfo=datetime.timezone.utc),
        )
        worfklow_service = WorkflowService(saxo_client)
        candles = worfklow_service.build_hour_candles(
            "code", "", ut, open_hour, close_hour, 50, open_minutes, date
        )
        for i in range(0, len(expected)):
            assert expected[i] == candles[i]

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
        ],
    )
    def test_build_h4_candles(
        self, candles: List[Candle], open_hour: int, expected: List[Candle]
    ):
        assert (
            WorkflowService._build_h4_candles(candles=candles, open_hour_utc0=open_hour)
            == expected
        )
