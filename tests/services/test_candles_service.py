import datetime
from typing import List

import pytest

from model import Candle, EUMarket, Market, UnitTime, USMarket
from services.candles_service import CandlesService

STOCK_ASSET = {
    "Description": "",
    "AssetType": "Stock",
    "Identifier": 12345,
    "CurrencyCode": "EUR",
}
CFD_INDEX_ASSET = {"Identifier": 123, "AssetType": "CfdOnIndex"}


@pytest.fixture
def make_saxo_client(mocker):
    """A Saxo client stubbed to resolve one asset."""

    def _make(asset):
        client = mocker.Mock()
        client.get_asset.return_value = asset
        return client

    return _make


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
        make_saxo_client,
    ):
        saxo_client = make_saxo_client(STOCK_ASSET)
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
        make_saxo_client,
    ):
        saxo_client = make_saxo_client(STOCK_ASSET)
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

    @pytest.mark.parametrize(
        "market, ut, count, expected_count",
        [
            # EU H1: 9 in-session candles/day -> 1 trading day -> 3 cal days.
            (EUMarket(), UnitTime.H1, 1, 3 * 48),
            # EU H1 count=55 (MA50): ceil(55/9)=7 trading -> 7+2+2=11 days.
            (EUMarket(), UnitTime.H1, 55, 11 * 48),
            # EU H1 count=750 (COMBO): ceil(750/9)=84 -> 84+32+2=118 days.
            (EUMarket(), UnitTime.H1, 750, 118 * 48),
            # EU H4: len(h4_blocks)=3 candles/day -> 1 trading day -> 3 days.
            (EUMarket(), UnitTime.H4, 1, 3 * 48),
            # EU D: 1 candle/day -> ceil(5/1)=5 -> 5+2+2=9 days.
            (EUMarket(), UnitTime.D, 5, 9 * 48),
            # US H1: 6 in-session candles/day -> 1 trading day -> 3 days.
            (USMarket(), UnitTime.H1, 1, 3 * 48),
        ],
    )
    def test_build_candles_fetch_sizing(
        self,
        market: Market,
        ut: UnitTime,
        count: int,
        expected_count: int,
        mocker,
        make_saxo_client,
    ):
        saxo_client = make_saxo_client(
            {"Identifier": 12345, "AssetType": "Stock"}
        )
        # One off-session bar: enough to avoid the empty-data guard while
        # producing no candles, so we can assert only on the fetch arguments.
        mocker.patch.object(
            saxo_client,
            "get_historical_data",
            return_value=[{"Time": datetime.datetime(2024, 6, 21, 3, 0)}],
        )
        candles_service = CandlesService(saxo_client)
        candles_service.build_candles(
            "code",
            ut,
            market,
            count,
            datetime.datetime(
                2024, 6, 21, 19, 56, tzinfo=datetime.timezone.utc
            ),
        )
        kwargs = saxo_client.get_historical_data.call_args.kwargs
        assert kwargs["horizon"] == 30
        assert kwargs["count"] == expected_count

    def test_build_candles_anchors_to_last_session_close(
        self, mocker, make_saxo_client
    ):
        """Off-hours runs anchor the query to the last session close."""
        saxo_client = make_saxo_client(
            {"Identifier": 12345, "AssetType": "Stock"}
        )
        mocker.patch.object(
            saxo_client,
            "get_historical_data",
            return_value=[{"Time": datetime.datetime(2024, 6, 21, 3, 0)}],
        )
        candles_service = CandlesService(saxo_client)
        # Friday 19:56 UTC, after the 15:00 UTC EU summer close.
        candles_service.build_candles(
            "code",
            UnitTime.H1,
            EUMarket(),
            1,
            datetime.datetime(
                2024, 6, 21, 19, 56, tzinfo=datetime.timezone.utc
            ),
        )
        kwargs = saxo_client.get_historical_data.call_args.kwargs
        assert kwargs["date"] == datetime.datetime(
            2024, 6, 21, 15, 0, tzinfo=datetime.timezone.utc
        )


class TestGetCandlesInWindow:
    def test_h1_window_returns_matching_candle(self, mocker, make_saxo_client):
        saxo_client = make_saxo_client(CFD_INDEX_ASSET)
        data = [
            {
                "Time": datetime.datetime(2026, 6, 2, 8, 0),
                "Open": 8020,
                "High": 8050,
                "Low": 8000,
                "Close": 8030,
            },
            {
                "Time": datetime.datetime(2026, 6, 2, 7, 0),
                "Open": 8010,
                "High": 8040,
                "Low": 7990,
                "Close": 8020,
            },
            {
                "Time": datetime.datetime(2026, 6, 2, 6, 0),
                "Open": 8005,
                "High": 8015,
                "Low": 7995,
                "Close": 8010,
            },
        ]
        mocker.patch.object(
            saxo_client, "get_historical_data", return_value=data
        )
        candles_service = CandlesService(saxo_client)
        start = datetime.datetime(2026, 6, 2, 7, 0)
        end = datetime.datetime(2026, 6, 2, 8, 0)

        candles = candles_service.get_candles_in_window(
            "FRA40.I", UnitTime.H1, 60, start, end
        )

        assert len(candles) == 1
        assert candles[0].date == start
        assert candles[0].lower == 7990
        assert candles[0].higher == 8040

    def test_m5_window_filters_to_range(self, mocker, make_saxo_client):
        saxo_client = make_saxo_client(CFD_INDEX_ASSET)
        base = datetime.datetime(2026, 6, 2, 8, 0)
        data = [
            {
                "Time": base + datetime.timedelta(minutes=5 * i),
                "Open": 1,
                "High": 2,
                "Low": 0,
                "Close": 1,
            }
            for i in range(10)
        ][::-1]
        mocker.patch.object(
            saxo_client, "get_historical_data", return_value=data
        )
        candles_service = CandlesService(saxo_client)
        start = base + datetime.timedelta(minutes=15)
        end = base + datetime.timedelta(minutes=35)

        candles = candles_service.get_candles_in_window(
            "FRA40.I", UnitTime.M5, 5, start, end
        )

        assert len(candles) == 4
        assert all(start <= c.date < end for c in candles)  # type: ignore

    def test_empty_result_when_no_data(self, mocker, make_saxo_client):
        saxo_client = make_saxo_client(CFD_INDEX_ASSET)
        mocker.patch.object(
            saxo_client, "get_historical_data", return_value=[]
        )
        candles_service = CandlesService(saxo_client)

        candles = candles_service.get_candles_in_window(
            "FRA40.I",
            UnitTime.H1,
            60,
            datetime.datetime(2026, 6, 2, 7, 0),
            datetime.datetime(2026, 6, 2, 8, 0),
        )

        assert candles == []
