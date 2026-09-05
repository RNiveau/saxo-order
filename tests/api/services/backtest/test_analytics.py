import datetime

from api.services.backtest import adx_before, mm50_slope_before, overnight_gap
from tests.api.services.backtest.helpers import (
    daily_candle,
    uptrend_daily_series,
)

TRADING_DATE = datetime.date(2026, 6, 2)


def _polluted(series):
    """The series plus candles dated on the trading day and after it -
    values a lookahead-safe measure must ignore."""
    return series + [
        daily_candle(TRADING_DATE, close=0.0),
        daily_candle(TRADING_DATE + datetime.timedelta(days=1), close=99999.0),
    ]


class TestMm50SlopeBefore:
    def test_none_when_fewer_than_60_prior_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 59)
        assert mm50_slope_before(series, TRADING_DATE) is None

    def test_positive_slope_for_uptrend(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        slope = mm50_slope_before(series, TRADING_DATE)
        assert slope is not None and slope > 0

    def test_ignores_today_and_future_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        baseline = mm50_slope_before(series, TRADING_DATE)
        assert mm50_slope_before(_polluted(series), TRADING_DATE) == baseline

    def test_skips_dateless_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        dateless = daily_candle(TRADING_DATE, close=0.0)
        dateless.date = None
        assert mm50_slope_before(
            [dateless] + series, TRADING_DATE
        ) == mm50_slope_before(series, TRADING_DATE)


class TestAdxBefore:
    def test_none_when_fewer_than_42_prior_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 41)
        assert adx_before(series, TRADING_DATE) is None

    def test_high_adx_for_uptrend(self):
        series = uptrend_daily_series(TRADING_DATE, 60)
        value = adx_before(series, TRADING_DATE)
        assert value is not None and value > 40

    def test_ignores_today_and_future_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 60)
        baseline = adx_before(series, TRADING_DATE)
        assert adx_before(_polluted(series), TRADING_DATE) == baseline


class TestOvernightGap:
    def test_gap_is_open_minus_prior_daily_close(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        # latest prior daily close in the series is 8069
        assert overnight_gap(series, TRADING_DATE, h1_open=8100.0) == 31.0

    def test_none_when_no_prior_candle(self):
        assert overnight_gap([], TRADING_DATE, h1_open=8100.0) is None

    def test_none_when_h1_open_missing(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        assert overnight_gap(series, TRADING_DATE, h1_open=None) is None

    def test_ignores_today_and_future_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        baseline = overnight_gap(series, TRADING_DATE, h1_open=8100.0)
        assert (
            overnight_gap(_polluted(series), TRADING_DATE, h1_open=8100.0)
            == baseline
        )
