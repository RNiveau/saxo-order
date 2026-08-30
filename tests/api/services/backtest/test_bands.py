"""The combo strategy's two moving targets (FR-C07)."""

import datetime

import pytest

from api.services.backtest.bands import (
    MIN_BAND_CANDLES,
    BandLevels,
    levels,
    levels_or_raise,
)
from api.services.backtest.side import LONG, SHORT
from model import Candle, UnitTime
from utils.exception import SaxoException


def series(closes):
    """Newest-first, as every indicator in this codebase expects."""
    return [
        Candle(
            lower=close - 5,
            higher=close + 5,
            open=close,
            close=close,
            ut=UnitTime.M15,
            date=datetime.datetime(2026, 6, 2, 10, 0)
            - datetime.timedelta(minutes=15 * i),
        )
        for i, close in enumerate(closes)
    ]


class TestOpposite:
    LEVELS = BandLevels(mm20=8020.0, upper=8060.0, bottom=7980.0)

    def test_a_long_runs_to_the_upper_band(self):
        assert self.LEVELS.opposite(LONG) == 8060.0

    def test_a_short_runs_to_the_lower_band(self):
        assert self.LEVELS.opposite(SHORT) == 7980.0


class TestLevels:
    def test_the_middle_band_is_the_average_of_the_last_twenty_closes(self):
        closes = [8000.0] * 20
        result = levels(series(closes))
        assert result is not None
        assert result.mm20 == pytest.approx(8000.0)

    def test_the_bands_straddle_the_middle(self):
        result = levels(series([8000.0 + (i % 5) * 10 for i in range(30)]))
        assert result is not None
        assert result.bottom < result.mm20 < result.upper

    def test_a_flat_series_collapses_the_bands_onto_the_middle(self):
        result = levels(series([8000.0] * 25))
        assert result is not None
        assert result.upper == pytest.approx(result.mm20)
        assert result.bottom == pytest.approx(result.mm20)

    def test_the_levels_move_as_the_window_advances(self):
        """The whole point of FR-C07: a target read from candle N is not
        the target read from candle N+1."""
        rising = [8000.0 + i for i in range(40)]
        early = levels(series(rising[10:]))
        late = levels(series(rising))
        assert early is not None and late is not None
        assert early.mm20 != late.mm20

    def test_too_few_candles_is_none_not_an_error(self):
        """The head of a run legitimately has no bands yet - a stretch
        the strategy cannot act on, not a failure."""
        assert levels(series([8000.0] * (MIN_BAND_CANDLES - 1))) is None

    def test_exactly_the_minimum_is_enough(self):
        assert levels(series([8000.0] * MIN_BAND_CANDLES)) is not None


class TestLevelsOrRaise:
    def test_it_returns_the_levels_when_they_exist(self):
        assert levels_or_raise(series([8000.0] * 25)).mm20 == pytest.approx(
            8000.0
        )

    def test_it_raises_when_they_do_not(self):
        """An open position cannot exist over a stretch with no bands, so
        this is an invariant violation rather than a quiet None."""
        with pytest.raises(SaxoException, match="open combo position"):
            levels_or_raise(series([8000.0] * 5))
