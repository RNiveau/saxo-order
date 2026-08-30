import datetime
from typing import List
from unittest.mock import MagicMock

from model import Candle, EUMarket, UnitTime
from services.candle_source import build_daily_series


def _daily_candles(count: int, newest: datetime.datetime) -> List[Candle]:
    return [
        Candle(
            lower=1.0,
            higher=2.0,
            open=1.5,
            close=1.8,
            ut=UnitTime.D,
            date=newest - datetime.timedelta(days=i),
        )
        for i in range(count)
    ]


class TestBuildDailySeriesWithoutAMarket:
    """market=None is a real choice with a visible consequence.

    An instrument whose session hours cannot be determined must not have its
    forming day assembled against guessed ones. The series then ends at the
    last completed day, and the caller is told so rather than left to notice.
    """

    def _client_returning(self, mocker, candles: List[Candle]):
        client = MagicMock()
        client.get_historical_data.return_value = [{"raw": True}]
        mocker.patch(
            "services.candle_source.client_helper.map_data_to_candles",
            return_value=candles,
        )
        return client

    def _yesterday_weekday(self) -> datetime.datetime:
        day = datetime.datetime.now() - datetime.timedelta(days=1)
        while day.weekday() >= 5:
            day -= datetime.timedelta(days=1)
        return day

    def test_it_leaves_the_forming_day_out_and_says_so(self, mocker):
        if datetime.datetime.now().weekday() >= 5:
            return
        candles = _daily_candles(10, self._yesterday_weekday())
        client = self._client_returning(mocker, candles)
        warn = mocker.patch("services.candle_source.logger.warning")

        result = build_daily_series(client, 42, None)

        assert result == candles
        assert client.get_historical_data.call_count == 1
        warn.assert_called_once()

    def test_a_market_buys_the_hourly_top_up(self, mocker):
        if datetime.datetime.now().weekday() >= 5:
            return
        candles = _daily_candles(10, self._yesterday_weekday())
        client = self._client_returning(mocker, candles)

        build_daily_series(client, 42, EUMarket())

        assert client.get_historical_data.call_count == 2
