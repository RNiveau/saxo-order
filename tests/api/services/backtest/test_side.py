"""Side is the primitive every strategy rule is built on, so its
long/short symmetry is asserted directly rather than only through the
engine."""

import datetime

import pytest

from api.services.backtest.side import LONG, SHORT
from model import Candle, UnitTime

MIRROR = 16000.0


def candle(open, higher, lower, close):
    return Candle(
        lower=lower,
        higher=higher,
        open=open,
        close=close,
        ut=UnitTime.M5,
        date=datetime.datetime(2026, 6, 2, 8, 0),
    )


def mirrored(c):
    """The candle reflected through MIRROR - high and low swap."""
    return candle(
        MIRROR - c.open, MIRROR - c.lower, MIRROR - c.higher, MIRROR - c.close
    )


class TestFavorable:
    def test_long_gains_when_price_rises(self):
        assert LONG.favorable(8010, 8000) == 10
        assert LONG.favorable(7990, 8000) == -10

    def test_short_gains_when_price_falls(self):
        assert SHORT.favorable(7990, 8000) == 10
        assert SHORT.favorable(8010, 8000) == -10

    def test_sign_and_is_long(self):
        assert (LONG.sign, LONG.is_long) == (1, True)
        assert (SHORT.sign, SHORT.is_long) == (-1, False)


class TestReferenceLevels:
    def test_long_trades_off_the_low_short_off_the_high(self):
        assert LONG.reference_level(8050, 8000) == 8000
        assert SHORT.reference_level(8050, 8000) == 8050


class TestTouches:
    C = candle(open=8005, higher=8020, lower=7990, close=8010)

    def test_reached_uses_the_favorable_extreme(self):
        assert LONG.reached(8020, self.C) is True
        assert LONG.reached(8021, self.C) is False
        assert SHORT.reached(7990, self.C) is True
        assert SHORT.reached(7989, self.C) is False

    def test_receded_uses_the_adverse_extreme(self):
        assert LONG.receded(7990, self.C) is True
        assert LONG.receded(7989, self.C) is False
        assert SHORT.receded(8020, self.C) is True
        assert SHORT.receded(8021, self.C) is False

    def test_closed_beyond_is_strict_and_uses_the_close(self):
        assert LONG.closed_beyond(8011, self.C) is True
        assert LONG.closed_beyond(8010, self.C) is False
        assert SHORT.closed_beyond(8009, self.C) is True
        assert SHORT.closed_beyond(8010, self.C) is False


class TestClosedNearAdverseExtreme:
    """The impulsive-candle shape test (FR-G14b): the close must sit in
    the quarter of the candle that hurts the position."""

    # range 80: bottom quarter is 7920-7940, top quarter 7980-8000
    WIDE = candle(open=7990, higher=8000, lower=7920, close=7925)

    def test_long_is_hurt_by_a_close_near_the_low(self):
        assert LONG.closed_near_adverse_extreme(self.WIDE, 0.25) is True

    def test_short_is_not_hurt_by_that_same_candle(self):
        assert SHORT.closed_near_adverse_extreme(self.WIDE, 0.25) is False

    def test_a_mid_range_close_hurts_neither(self):
        mid = candle(open=7990, higher=8000, lower=7920, close=7960)
        assert LONG.closed_near_adverse_extreme(mid, 0.25) is False
        assert SHORT.closed_near_adverse_extreme(mid, 0.25) is False

    def test_short_is_hurt_by_a_close_near_the_high(self):
        up = candle(open=7930, higher=8000, lower=7920, close=7995)
        assert SHORT.closed_near_adverse_extreme(up, 0.25) is True
        assert LONG.closed_near_adverse_extreme(up, 0.25) is False

    def test_the_boundary_counts(self):
        """A close exactly at the fraction is inside it: 7940 is 20 points
        up from the low of an 80-point candle, exactly 25%."""
        boundary = candle(open=7990, higher=8000, lower=7920, close=7940)
        assert LONG.closed_near_adverse_extreme(boundary, 0.25) is True
        just_above = candle(open=7990, higher=8000, lower=7920, close=7941)
        assert LONG.closed_near_adverse_extreme(just_above, 0.25) is False

    def test_a_flat_candle_needs_no_zero_range_guard(self):
        flat = candle(open=8000, higher=8000, lower=8000, close=8000)
        assert LONG.closed_near_adverse_extreme(flat, 0.25) is True
        assert SHORT.closed_near_adverse_extreme(flat, 0.25) is True


class TestFills:
    def test_stop_fill_takes_the_open_on_an_adverse_gap(self):
        gapped = candle(open=7950, higher=7960, lower=7940, close=7955)
        assert LONG.stop_fill(7980, gapped) == 7950
        touched = candle(open=8000, higher=8010, lower=7970, close=8005)
        assert LONG.stop_fill(7980, touched) == 7980

    def test_target_fill_takes_the_open_on_a_favorable_gap(self):
        gapped = candle(open=8060, higher=8070, lower=8055, close=8065)
        assert LONG.target_fill(8040, gapped) == 8060
        touched = candle(open=8000, higher=8045, lower=7995, close=8040)
        assert LONG.target_fill(8040, touched) == 8040


class TestMirrorSymmetry:
    """Every predicate must give the same answer for a short setup as for
    the long setup it reflects."""

    CANDLES = [
        candle(8005, 8020, 7990, 8010),
        candle(7950, 7960, 7940, 7955),
        candle(8060, 8070, 8055, 8065),
        candle(8000, 8000, 8000, 8000),
    ]

    @pytest.mark.parametrize("c", CANDLES)
    @pytest.mark.parametrize("level", [7980.0, 8000.0, 8010.0, 8040.0])
    def test_predicates_mirror(self, c, level):
        m, ml = mirrored(c), MIRROR - level
        assert LONG.reached(level, c) == SHORT.reached(ml, m)
        assert LONG.receded(level, c) == SHORT.receded(ml, m)
        assert LONG.closed_beyond(level, c) == SHORT.closed_beyond(ml, m)
        assert LONG.stop_fill(level, c) == MIRROR - SHORT.stop_fill(ml, m)
        assert LONG.target_fill(level, c) == MIRROR - SHORT.target_fill(ml, m)

    @pytest.mark.parametrize("c", CANDLES)
    def test_shape_predicate_mirrors(self, c):
        assert LONG.closed_near_adverse_extreme(
            c, 0.25
        ) == SHORT.closed_near_adverse_extreme(mirrored(c), 0.25)
