"""The synthetic market's own coherence.

The golden snapshot can only mean something if the market underneath it
is one market: the same day read at two timeframes, or over two windows,
has to be the same prices. It used to not be - the H1 series and the
5-minute scan were separate random walks - and the only thing that
noticed was a strategy reading both and producing nonsense.
"""

import datetime

from model import EuCfdMarket, EUMarket, UnitTime
from tests.api.services.backtest.market_fixture import (
    BASE_HORIZON,
    WIDEST_SESSION,
    base_bars,
    candles_in_window,
    session_bounds,
    session_candles,
)

INSTRUMENT = "GER40.I"
DAY = datetime.date(2026, 3, 3)


def test_the_day_is_drawn_once():
    assert base_bars(INSTRUMENT, DAY) == base_bars(INSTRUMENT, DAY)


def test_the_base_path_spans_the_widest_session():
    start, end = session_bounds(DAY, WIDEST_SESSION)
    bars = base_bars(INSTRUMENT, DAY)
    assert bars[0].date == start
    assert bars[-1].date == end - datetime.timedelta(minutes=BASE_HORIZON)


def test_a_narrow_window_agrees_with_a_wide_one():
    """The reference hour a "bougie de 9h" backtest asks for is the same
    candle a whole-session read sees at 09:00 - buckets are anchored to
    midnight, not to the window."""
    reference_start, reference_end = session_bounds(DAY, EUMarket())
    reference_end = reference_start + datetime.timedelta(hours=1)
    narrow = candles_in_window(
        INSTRUMENT, DAY, UnitTime.H1, reference_start, reference_end
    )
    wide = session_candles(INSTRUMENT, DAY, UnitTime.H1, EuCfdMarket())
    assert len(narrow) == 1
    assert narrow[0] == wide[0]


def test_an_hourly_candle_is_its_five_minute_candles():
    start, end = session_bounds(DAY, EuCfdMarket())
    hourly = session_candles(INSTRUMENT, DAY, UnitTime.H1, EuCfdMarket())[0]
    five = candles_in_window(
        INSTRUMENT,
        DAY,
        UnitTime.M5,
        start,
        start + datetime.timedelta(hours=1),
    )
    assert hourly.open == five[0].open
    assert hourly.close == five[-1].close
    assert hourly.higher == round(max(bar.higher for bar in five), 2)
    assert hourly.lower == round(min(bar.lower for bar in five), 2)


def test_a_shorter_session_reads_a_prefix_of_the_longer_one():
    """The cash session's hours are the CFD session's first hours - the
    same prices, not a second walk. Only the last one differs: EUMarket
    closes at 17:30, so its 17:00 candle is the half hour it actually
    traded, exactly as the real API would return it."""
    cash = session_candles(INSTRUMENT, DAY, UnitTime.H1, EUMarket())
    cfd = session_candles(INSTRUMENT, DAY, UnitTime.H1, EuCfdMarket())
    assert len(cash) < len(cfd)
    assert cash[:-1] == cfd[: len(cash) - 1]
    assert cash[-1].date == cfd[len(cash) - 1].date
    assert cash[-1].open == cfd[len(cash) - 1].open
