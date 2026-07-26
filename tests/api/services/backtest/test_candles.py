import pytest

from api.services.backtest import candle_date
from tests.api.services.backtest.helpers import m5_candle
from utils.exception import SaxoException


class TestCandleDate:
    def test_returns_the_candle_date(self):
        candle = m5_candle(0, 8005, 8010, 7995, 8000)
        assert candle_date(candle) == candle.date

    def test_raises_saxo_exception_when_date_is_missing(self):
        """get_candles_in_window always filters out dateless candles
        before this is called, so this path shouldn't be reachable in
        practice - but it must not be a bare assert (stripped under -O,
        and an AssertionError is the wrong exception type for a
        data-integrity problem from a Saxo response)."""
        candle = m5_candle(0, 8005, 8010, 7995, 8000)
        candle.date = None
        with pytest.raises(SaxoException):
            candle_date(candle)
