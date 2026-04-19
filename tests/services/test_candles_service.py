import datetime
from typing import List

import pytest

from model import Candle, EUMarket, Market, UnitTime, USMarket
from services.candles_service import CandlesService


class TestCandlesService:

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
        self,
        file: str,
        ut: UnitTime,
        results: List[Candle],
        expected_len: int,
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
        with open(f"tests/services/files/{file}", "r") as f:
            data = eval(f.read(), {"datetime": datetime})

        mocker.patch.object(
            saxo_client, "get_historical_data", return_value=data
        )
        worfklow_service = CandlesService(saxo_client)
        candles = worfklow_service.get_candles_per_minutes(
            "code", len(data), ut
        )
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
        "file_index, market, ut, date, expected",
        [
            (
                "cac_30min.obj",
                EUMarket(),
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
                EUMarket(),
                UnitTime.H1,
                datetime.datetime(2024, 6, 20, 15, 14),
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
                "cac_30min_end_of_day.obj",
                EUMarket(),
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
                USMarket(),
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
            (
                "bug_switch_day_sp500.obj",
                USMarket(),
                UnitTime.H1,
                datetime.datetime(
                    2024,
                    7,
                    29,
                    14,
                ),
                [
                    Candle(
                        lower=5472.895,
                        higher=5495.665,
                        open=5486.9048,
                        close=5475.415,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 7, 29, 12, 30),
                    ),
                    Candle(
                        lower=5443.7148,
                        higher=5465.4849,
                        open=5464.7148,
                        close=5462.7251,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 7, 26, 19, 30),
                    ),
                    Candle(
                        lower=5447.2749,
                        higher=5467.9951,
                        open=5461.5049,
                        close=5464.7051,
                        ut=UnitTime.H1,
                        date=datetime.datetime(2024, 7, 26, 18, 30),
                    ),
                ],
            ),
            (
                "bug_h4_dax.obj",
                EUMarket(),
                UnitTime.H4,
                datetime.datetime(2024, 7, 2, 15, 2),
                [
                    Candle(
                        lower=18030.49,
                        higher=18126.63,
                        open=18109.3,
                        close=18121.14,
                        ut=UnitTime.H4,
                        date=datetime.datetime(2024, 7, 2, 10, 0),
                    ),
                ],
            ),
        ],
    )
    def test_build_candles(
        self,
        file_index: str,
        market: Market,
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
        with open(f"tests/services/files/{file_index}", "r") as f:
            data = eval(f.read(), {"datetime": datetime})
        mocker.patch.object(
            saxo_client, "get_historical_data", return_value=data
        )
        mocker.patch(
            "services.candles_service.get_date_utc0",
            return_value=date.replace(tzinfo=datetime.timezone.utc),
        )
        candles_service = CandlesService(saxo_client)
        candles = candles_service.build_candles("code", ut, market, 50, date)
        for i in range(0, len(expected)):
            assert expected[i] == candles[i]
