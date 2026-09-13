import datetime
from typing import List

from mcp_server.formatters import (
    MAX_BAR_COUNT,
    candle_row,
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
        rows, _ = to_rows(_candles(5))

        dates = [row[0] for row in rows]
        assert dates == sorted(dates, reverse=True)

    def test_asking_for_fewer_bars_is_not_truncation(self):
        """The caller got what it asked for; nothing was overridden."""
        rows, truncated = to_rows(_candles(50), count=10)

        assert len(rows) == 10
        assert truncated is False

    def test_the_hard_cap_is_reported_as_truncation(self):
        rows, truncated = to_rows(_candles(MAX_BAR_COUNT + 10), count=99999)

        assert len(rows) == MAX_BAR_COUNT
        assert truncated is True

    def test_a_cap_that_had_nothing_to_cut_is_not_truncation(self):
        rows, truncated = to_rows(_candles(5), count=99999)

        assert len(rows) == 5
        assert truncated is False

    def test_no_candles_yields_no_rows(self):
        rows, truncated = to_rows([])

        assert rows == []
        assert truncated is False

    def test_a_zero_count_still_returns_a_bar(self):
        rows, _ = to_rows(_candles(5), count=0)

        assert len(rows) == 1


class TestLastBarDate:
    def test_it_reads_the_newest_bar(self):
        candles = _candles(5)

        assert last_bar_date(candles) == candles[0].date

    def test_it_is_none_without_candles(self):
        assert last_bar_date([]) is None
