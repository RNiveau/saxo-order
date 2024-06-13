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
        self, file: str, ut: UnitTime, results: List[Candle], expected_len, mocker
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
