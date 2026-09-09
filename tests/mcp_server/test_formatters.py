import datetime
from typing import List

from mcp_server.formatters import (
    MAX_BAR_COUNT,
    candle_row,
    exceeds_cap,
    last_bar_date,
    to_rows,
)
from mcp_server.models import BAR_COLUMNS
from model import Candle, UnitTime


def _candles(count: int) -> List[Candle]:
    newest = datetime.datetime(2026, 8, 30)
    return [
        Candle(
            lower=1.111111,
            higher=2.222222,
            open=1.555555,
            close=1.888888,
            ut=UnitTime.D,
            date=newest - datetime.timedelta(days=i),
        )
        for i in range(count)
    ]


class TestCandleRow:
    def test_the_row_follows_the_declared_column_order(self):
        candle = _candles(1)[0]
        row = candle_row(candle)

        assert len(row) == len(BAR_COLUMNS)
        assert row[BAR_COLUMNS.index("open")] == round(candle.open, 4)
        assert row[BAR_COLUMNS.index("high")] == round(candle.higher, 4)
        assert row[BAR_COLUMNS.index("low")] == round(candle.lower, 4)
        assert row[BAR_COLUMNS.index("close")] == round(candle.close, 4)

    def test_prices_are_rounded_to_four_places(self):
        row = candle_row(_candles(1)[0])

        assert row[1:] == [1.5556, 2.2222, 1.1111, 1.8889]

    def test_a_dateless_candle_yields_a_null_rather_than_failing(self):
        candle = Candle(
            lower=1.0, higher=2.0, open=1.5, close=1.8, ut=UnitTime.D
        )

        assert candle_row(candle)[0] is None


class TestToRows:
    def test_the_newest_bar_stays_first(self):
        rows = to_rows(_candles(5))

        dates = [row[0] for row in rows]
        assert dates == sorted(dates, reverse=True)

    def test_it_returns_what_was_asked_for(self):
        assert len(to_rows(_candles(50), count=10)) == 10

    def test_it_never_returns_more_than_the_hard_cap(self):
        assert len(to_rows(_candles(MAX_BAR_COUNT + 10), count=99999)) == (
            MAX_BAR_COUNT
        )

    def test_it_returns_what_exists_when_that_is_less(self):
        assert len(to_rows(_candles(5), count=99999)) == 5

    def test_no_candles_yields_no_rows(self):
        assert to_rows([]) == []

    def test_a_zero_count_returns_nothing(self):
        """No silent floor: the schema forbids 0, and if one ever reaches
        here the honest answer is no bars, not a bar nobody asked for."""
        assert to_rows(_candles(5), count=0) == []


class TestExceedsCap:
    """Truncation is a property of the request, asked in one place.

    Returning it from to_rows as well left two definitions alive that
    disagreed on the same input, both asserted by passing tests.
    """

    def test_a_request_beyond_the_cap_was_overridden(self):
        assert exceeds_cap(MAX_BAR_COUNT + 1) is True

    def test_a_request_within_the_cap_was_honoured(self):
        assert exceeds_cap(MAX_BAR_COUNT) is False
        assert exceeds_cap(1) is False

    def test_it_does_not_depend_on_how_much_history_exists(self):
        """The disputed case: 900 asked for, 10 bars in the instrument.

        The fetch was capped at 500 regardless, so the tool cannot claim
        those 10 were all there was.
        """
        assert exceeds_cap(900) is True


class TestLastBarDate:
    def test_it_reads_the_newest_bar(self):
        candles = _candles(5)

        assert last_bar_date(candles) == candles[0].date

    def test_it_is_none_without_candles(self):
        assert last_bar_date([]) is None
