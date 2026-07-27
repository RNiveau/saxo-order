"""The entry gate in isolation: when the engine may open a position.

Built without candles - the gate only ever sees a candle's start time and
the trades that have closed, so its rules are asserted directly rather
than inferred from a day's result.
"""

import datetime

from api.services.backtest.entry_gate import (
    ALWAYS_OPEN,
    FilteredEntry,
    cutoff_utc,
)
from model import EuCfdMarket, EUMarket
from model.enum import Direction, ExitReason
from tests.api.services.backtest.helpers import closed_trade

SUMMER = datetime.date(2026, 6, 2)
WINTER = datetime.date(2026, 1, 15)
FOUR_PM = datetime.time(16, 0)


def at(hour, minute=0, day=SUMMER):
    return datetime.datetime(day.year, day.month, day.day, hour, minute)


class TestCutoffResolution:
    """16:00 market-local, resolved per date - not a hardcoded UTC hour."""

    def test_summer_is_14h_utc(self):
        assert cutoff_utc(FOUR_PM, EuCfdMarket(), SUMMER) == at(14, 0)

    def test_winter_is_15h_utc(self):
        assert cutoff_utc(FOUR_PM, EuCfdMarket(), WINTER) == at(
            15, 0, day=WINTER
        )

    def test_the_shift_follows_the_timezone_not_the_session(self):
        """EUMarket and EuCfdMarket close at different hours but share a
        timezone, so a 16:00 cut-off lands on the same instant."""
        assert cutoff_utc(FOUR_PM, EUMarket(), SUMMER) == cutoff_utc(
            FOUR_PM, EuCfdMarket(), SUMMER
        )


class TestEntryCutoff:
    def _gate(self):
        return FilteredEntry(cutoff_utc(FOUR_PM, EuCfdMarket(), SUMMER), None)

    def test_the_1555_candle_may_still_open(self):
        assert self._gate().allows(at(13, 55)) is True

    def test_the_1600_candle_may_not(self):
        assert self._gate().allows(at(14, 0)) is False

    def test_nothing_later_may_either(self):
        gate = self._gate()
        assert gate.allows(at(14, 5)) is False
        assert gate.allows(at(19, 55)) is False

    def test_the_morning_is_unaffected(self):
        assert self._gate().allows(at(8, 0)) is True


class TestDailyLossCap:
    def _gate(self):
        return FilteredEntry(None, 2)

    def test_two_losses_close_the_gate(self):
        gate = self._gate()
        assert gate.allows(at(8, 0)) is True

        gate.record(closed_trade(-75, ExitReason.STOP_LOSS))
        assert gate.allows(at(8, 30)) is True

        gate.record(closed_trade(-40, ExitReason.END_OF_DAY))
        assert gate.allows(at(9, 0)) is False

    def test_the_cap_counts_losses_not_trades(self):
        gate = self._gate()
        gate.record(closed_trade(-75, ExitReason.STOP_LOSS))
        gate.record(closed_trade(120, ExitReason.TAKE_PROFIT))
        gate.record(closed_trade(30, ExitReason.TAKE_PROFIT))

        assert gate.allows(at(9, 0)) is True

    def test_any_negative_exit_reason_counts(self):
        """Not just stop-losses: under an impulse stop a day can bleed
        away through end-of-day and gapped break-even closes."""
        for reason in (
            ExitReason.STOP_LOSS,
            ExitReason.END_OF_DAY,
            ExitReason.BREAK_EVEN,
            ExitReason.TAKE_PROFIT,
        ):
            gate = self._gate()
            gate.record(closed_trade(-5, reason))
            gate.record(closed_trade(-5, reason))
            assert gate.allows(at(9, 0)) is False

    def test_a_flat_trade_is_not_a_loss(self):
        gate = self._gate()
        gate.record(closed_trade(0, ExitReason.BREAK_EVEN))
        gate.record(closed_trade(0, ExitReason.END_OF_DAY))
        gate.record(closed_trade(0, ExitReason.TAKE_PROFIT))

        assert gate.allows(at(9, 0)) is True

    def test_shorts_count_the_same_way(self):
        gate = self._gate()
        gate.record(closed_trade(-20, ExitReason.STOP_LOSS, Direction.SELL))
        gate.record(closed_trade(-20, ExitReason.STOP_LOSS, Direction.SELL))

        assert gate.allows(at(9, 0)) is False


class TestFiltersAreIndependent:
    def test_either_alone_refuses(self):
        gate = FilteredEntry(cutoff_utc(FOUR_PM, EuCfdMarket(), SUMMER), 2)

        # The clock alone, with no losses at all.
        assert gate.allows(at(14, 0)) is False
        # The losses alone, in the morning.
        gate.record(closed_trade(-10, ExitReason.STOP_LOSS))
        gate.record(closed_trade(-10, ExitReason.STOP_LOSS))
        assert gate.allows(at(8, 5)) is False


class TestAlwaysOpen:
    """The gate the other five definitions get: no filtering at all."""

    def test_every_candle_is_allowed_whatever_has_closed(self):
        ALWAYS_OPEN.record(closed_trade(-75, ExitReason.STOP_LOSS))
        ALWAYS_OPEN.record(closed_trade(-75, ExitReason.STOP_LOSS))
        ALWAYS_OPEN.record(closed_trade(-75, ExitReason.STOP_LOSS))

        assert ALWAYS_OPEN.allows(at(8, 0)) is True
        assert ALWAYS_OPEN.allows(at(19, 55)) is True
