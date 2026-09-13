import datetime
import math
from typing import List

import pytest

from model import Candle, IndicatorName, UnitTime
from services.indicator_bundle_service import (
    DEFAULT_INDICATORS,
    REGISTRY,
    SCAN_DEPTH,
    compute_bundle,
    required_bars,
)
from utils.exception import SaxoException


def _series(count: int) -> List[Candle]:
    """A gently rising series, newest first."""
    newest = datetime.datetime(2026, 8, 30)
    return [
        Candle(
            lower=100 + (count - i) * 0.5 - 1,
            higher=100 + (count - i) * 0.5 + 1,
            open=100 + (count - i) * 0.5,
            close=100 + (count - i) * 0.5,
            ut=UnitTime.D,
            date=newest - datetime.timedelta(days=i),
        )
        for i in range(count)
    ]


def _wobbly(count: int) -> List[Candle]:
    """A series that changes direction, so path-dependent indicators move."""
    newest = datetime.datetime(2026, 8, 30)
    candles = []
    for i in range(count):
        base = 100 + 10 * math.sin(i / 7.0) + i * 0.05
        candles.append(
            Candle(
                lower=base - 1.5,
                higher=base + 1.5,
                open=base,
                close=base + math.sin(i / 3.0),
                ut=UnitTime.D,
                date=newest - datetime.timedelta(days=i),
            )
        )
    return candles


class TestRequiredBars:
    """The fetch is sized to the request, not to the deepest indicator."""

    def test_a_shallow_request_stays_shallow(self):
        assert required_bars([IndicatorName.MM7]) == 7

    def test_the_hungriest_requested_indicator_decides(self):
        deep = required_bars([IndicatorName.MACD0LAG])

        assert deep >= 235
        assert required_bars([IndicatorName.MM7, IndicatorName.MACD0LAG]) == (
            deep
        )

    def test_a_slope_needs_more_history_than_its_average(self):
        assert required_bars([IndicatorName.MM50_SLOPE]) > required_bars(
            [IndicatorName.MM50]
        )

    def test_every_indicator_name_is_in_the_registry(self):
        assert set(REGISTRY) == set(IndicatorName)


class TestComputeBundle:
    def test_a_full_series_answers_everything(self):
        outcomes = compute_bundle(_series(300), DEFAULT_INDICATORS)

        assert len(outcomes) == len(DEFAULT_INDICATORS)
        assert all(o.value is not None for o in outcomes)
        assert all(o.unavailable_reason is None for o in outcomes)

    def test_a_short_series_answers_what_it_can_and_explains_the_rest(self):
        """SC-003: a partial answer is a success, not an error."""
        requested = [
            IndicatorName.MM7,
            IndicatorName.MM20,
            IndicatorName.MM50,
            IndicatorName.MM200,
            IndicatorName.MACD0LAG,
        ]

        outcomes = compute_bundle(_series(80), requested)

        computed = {o.name for o in outcomes if o.value is not None}
        missing = {o.name for o in outcomes if o.value is None}
        assert computed == {
            IndicatorName.MM7,
            IndicatorName.MM20,
            IndicatorName.MM50,
        }
        assert missing == {IndicatorName.MM200, IndicatorName.MACD0LAG}

    def test_every_requested_indicator_comes_back(self):
        """Absence is stated, never implied by omission."""
        requested = [IndicatorName.MM7, IndicatorName.MACD0LAG]

        outcomes = compute_bundle(_series(80), requested)

        assert [o.name for o in outcomes] == requested

    def test_an_unavailable_indicator_says_what_it_needed(self):
        """Alongside one that worked - a lone unavailable indicator means
        nothing was computable, which is the failure case below."""
        outcomes = compute_bundle(
            _series(80), [IndicatorName.MM7, IndicatorName.MACD0LAG]
        )

        reason = outcomes[1].unavailable_reason
        assert reason is not None
        assert "235" in reason and "80" in reason

    def test_asking_only_for_an_unavailable_indicator_fails(self):
        with pytest.raises(SaxoException, match="235"):
            compute_bundle(_series(80), [IndicatorName.MACD0LAG])

    def test_nothing_computable_is_a_failure(self):
        """Too short for even the shallowest is a failed request."""
        with pytest.raises(SaxoException):
            compute_bundle(_series(3), [IndicatorName.MM7])


class TestFetchDepthProtectsAccuracy:
    """A recursive indicator's answer depends on how far back it was seeded.

    ATR, ADX and macd0lag are smoothed forward from the oldest bar
    available, so computing one at its bare feasibility floor returns a
    warm-up value that disagrees with the scan's for the same instrument on
    the same day. Windowed indicators do not have that problem: a 7-bar
    average reads exactly 7 closes whatever was fetched.
    """

    def test_a_windowed_indicator_fetches_exactly_its_window(self):
        assert required_bars([IndicatorName.MM7]) == 7
        assert required_bars([IndicatorName.MM200]) == 200

    def test_a_recursive_indicator_fetches_the_scan_depth(self):
        for name in (
            IndicatorName.ATR,
            IndicatorName.ADX,
            IndicatorName.MACD0LAG,
        ):
            assert required_bars([name]) >= SCAN_DEPTH

    def test_the_floor_stays_the_floor_for_availability(self):
        """Fetching deeper must not make a short series look unavailable."""
        assert REGISTRY[IndicatorName.ADX].minimum_bars == 42
        assert REGISTRY[IndicatorName.ADX].fetch_bars == SCAN_DEPTH

    def test_adx_on_a_short_series_differs_from_the_scan_depth(self):
        """The reason the distinction exists, measured rather than asserted.

        A steadily rising series saturates ADX at 100 whatever its length,
        which would hide this - so the series here actually turns.
        """
        at_floor = compute_bundle(_wobbly(42), [IndicatorName.ADX])[0].value
        at_depth = compute_bundle(_wobbly(250), [IndicatorName.ADX])[0].value

        assert at_floor != at_depth
