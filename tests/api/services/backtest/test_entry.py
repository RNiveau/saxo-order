"""The entry filter and the breakout/reversal search.

Both are written once against Side, so these tests check the long cases,
the mirrored short cases, and - in TestEntryValiditySymmetry - that the
two are genuinely mirror images for arbitrary inputs rather than by
coincidence on the hand-picked numbers.
"""

import pytest

from api.services.backtest.entry import is_valid_entry
from api.services.backtest.side import LONG, SHORT

MAX_DISTANCE = 20


class TestIsValidLongEntry:
    """A breakout-reversal entry only produces a trade when it is within
    MAX_DISTANCE points of the H1 low and still below the take-profit."""

    def _valid(self, entry, h1_low, take_profit):
        return is_valid_entry(
            LONG, entry, 9000, h1_low, take_profit, MAX_DISTANCE
        )

    def test_within_distance_and_below_tp_is_valid(self):
        assert self._valid(8010, 8000, 8040) is True

    def test_exactly_at_max_distance_is_valid(self):
        assert self._valid(8020, 8000, 8040) is True

    def test_beyond_max_distance_is_invalid(self):
        assert self._valid(8021, 8000, 8040) is False

    def test_at_take_profit_level_is_invalid(self):
        assert self._valid(8015, 8005, 8015) is False

    def test_above_take_profit_level_is_invalid(self):
        assert self._valid(8016, 8005, 8015) is False

    def test_just_below_take_profit_level_is_valid(self):
        assert self._valid(8014, 8005, 8015) is True


class TestIsValidShortEntry:
    """Mirror of TestIsValidLongEntry: valid only when within MAX_DISTANCE
    points below the H1 high and still above the take-profit."""

    def _valid(self, entry, h1_high, take_profit):
        return is_valid_entry(
            SHORT, entry, h1_high, 7000, take_profit, MAX_DISTANCE
        )

    def test_within_distance_and_above_tp_is_valid(self):
        assert self._valid(8040, 8050, 8010) is True

    def test_exactly_at_max_distance_is_valid(self):
        assert self._valid(8030, 8050, 8010) is True

    def test_beyond_max_distance_is_invalid(self):
        assert self._valid(8029, 8050, 8010) is False

    def test_at_take_profit_level_is_invalid(self):
        assert self._valid(8010, 8025, 8010) is False

    def test_below_take_profit_level_is_invalid(self):
        assert self._valid(8009, 8025, 8010) is False

    def test_just_above_take_profit_level_is_valid(self):
        assert self._valid(8011, 8025, 8010) is True


class TestFirstTargetGuard:
    """FR-G03: with a double take-profit setup the entry must also sit
    short of TP1, or the first lot would fire immediately."""

    def test_long_entry_past_the_first_target_is_invalid(self):
        assert (
            is_valid_entry(
                LONG, 8026, 8050, 8000, 8040, MAX_DISTANCE, first_target=8025
            )
            is False
        )

    def test_long_entry_at_the_first_target_is_invalid(self):
        assert (
            is_valid_entry(
                LONG, 8025, 8050, 8010, 8040, MAX_DISTANCE, first_target=8025
            )
            is False
        )

    def test_long_entry_short_of_the_first_target_is_valid(self):
        assert (
            is_valid_entry(
                LONG, 8015, 8050, 8000, 8040, MAX_DISTANCE, first_target=8025
            )
            is True
        )

    def test_short_entry_past_the_first_target_is_invalid(self):
        assert (
            is_valid_entry(
                SHORT, 8024, 8040, 8000, 8010, MAX_DISTANCE, first_target=8025
            )
            is False
        )

    def test_short_entry_short_of_the_first_target_is_valid(self):
        assert (
            is_valid_entry(
                SHORT, 8035, 8050, 8000, 8010, MAX_DISTANCE, first_target=8025
            )
            is True
        )


class TestEntryValiditySymmetry:
    """A short setup reflected through a price mirror must produce the
    same verdict as the long setup it reflects."""

    MIRROR = 16000.0

    @pytest.mark.parametrize(
        "entry,h1_low,take_profit,first_target",
        [
            (8010, 8000, 8040, None),
            (8020, 8000, 8040, None),
            (8021, 8000, 8040, None),
            (8015, 8005, 8015, None),
            (8014, 8005, 8015, None),
            (8015, 8000, 8040, 8025),
            (8026, 8000, 8040, 8025),
            (8025, 8000, 8040, 8025),
        ],
    )
    def test_short_mirrors_long(
        self, entry, h1_low, take_profit, first_target
    ):
        long_verdict = is_valid_entry(
            LONG,
            entry,
            h1_low + 500,
            h1_low,
            take_profit,
            MAX_DISTANCE,
            first_target,
        )
        short_verdict = is_valid_entry(
            SHORT,
            self.MIRROR - entry,
            self.MIRROR - h1_low,
            self.MIRROR - h1_low - 500,
            self.MIRROR - take_profit,
            MAX_DISTANCE,
            None if first_target is None else self.MIRROR - first_target,
        )
        assert long_verdict == short_verdict
