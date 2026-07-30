"""The combo signal -> entry state machine (FR-C02/FR-C03/FR-C04).

`combo` is mocked throughout: what is under test is what the search does
with a signal, not whether the indicator produces one. The indicator has
its own tests in tests/services/test_indicator_service.py.
"""

import datetime

from api.services.backtest.side import LONG, SHORT
from api.services.backtest.signals import ComboEntrySearch
from model import Candle, ComboSignal, UnitTime
from model.enum import Direction
from model.workflow import SignalStrength

SIGNALS = "api.services.backtest.signals.combo"


def candle(lower, higher, open_, close, minute=0):
    return Candle(
        lower=lower,
        higher=higher,
        open=open_,
        close=close,
        ut=UnitTime.M15,
        date=datetime.datetime(2026, 6, 2, 10, minute),
    )


def signal(direction, price, triggered, strength=SignalStrength.MEDIUM):
    return ComboSignal(
        price=price,
        has_been_triggered=triggered,
        direction=direction,
        strength=strength,
        details={},
    )


class TestStrengthFilter:
    def test_a_weak_signal_opens_nothing(self, mocker):
        """FR-C02: a WEAK signal scored zero criteria. It is still a
        combo, just not one this backtest trades."""
        mocker.patch(
            SIGNALS,
            return_value=signal(
                Direction.BUY, 8020.0, True, SignalStrength.WEAK
            ),
        )
        search = ComboEntrySearch()
        assert search.feed(candle(8000, 8020, 8005, 8020), []) is None
        assert search.pending is None

    def test_no_signal_opens_nothing(self, mocker):
        mocker.patch(SIGNALS, return_value=None)
        search = ComboEntrySearch()
        assert search.feed(candle(8000, 8020, 8005, 8020), []) is None

    def test_medium_and_strong_are_both_traded(self, mocker):
        for strength in (SignalStrength.MEDIUM, SignalStrength.STRONG):
            mocker.patch(
                SIGNALS,
                return_value=signal(Direction.BUY, 8020.0, True, strength),
            )
            entry = ComboEntrySearch().feed(candle(8000, 8020, 8005, 8020), [])
            assert entry is not None
            assert entry.price == 8020.0


class TestTriggeredEntry:
    def test_a_triggered_signal_enters_at_the_signal_price(self, mocker):
        """FR-C03: the signal candle already closed beyond the previous
        candle's extreme, and combo puts its price at that close."""
        mocker.patch(SIGNALS, return_value=signal(Direction.BUY, 8020.0, True))
        signal_candle = candle(8000, 8020, 8005, 8020)
        entry = ComboEntrySearch().feed(signal_candle, [])
        assert entry is not None
        assert entry.price == 8020.0
        assert entry.side is LONG
        assert entry.signal_candle is signal_candle

    def test_a_triggered_sell_signal_is_a_short(self, mocker):
        mocker.patch(
            SIGNALS, return_value=signal(Direction.SELL, 8000.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8015, 8002), [])
        assert search.pending is not None
        assert search.pending.side is SHORT


class TestPendingEntry:
    def test_an_untriggered_signal_arms_a_level_and_opens_nothing(
        self, mocker
    ):
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        assert search.feed(candle(8000, 8020, 8005, 8015), []) is None
        assert search.pending is not None
        assert search.pending.level == 8020.0

    def test_the_next_candle_trading_through_it_fills(self, mocker):
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8005, 8015), [])

        mocker.patch(SIGNALS, return_value=None)
        entry = search.feed(candle(8010, 8030, 8015, 8025, minute=15), [])
        assert entry is not None
        assert entry.price == 8020.0

    def test_a_gap_through_the_level_fills_at_the_open(self, mocker):
        """The conservative fill convention: a candle that opened past
        the level never traded at it."""
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8005, 8015), [])

        mocker.patch(SIGNALS, return_value=None)
        entry = search.feed(candle(8030, 8050, 8035, 8045, minute=15), [])
        assert entry is not None
        assert entry.price == 8035.0

    def test_a_level_not_reached_next_candle_is_dropped(self, mocker):
        """FR-C04: one candle of validity. A setup that still holds
        re-emits with its own updated level, so nothing is lost by
        dropping this one."""
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8005, 8015), [])

        mocker.patch(SIGNALS, return_value=None)
        assert (
            search.feed(candle(7990, 8010, 8005, 8000, minute=15), []) is None
        )
        assert search.pending is None

    def test_a_candle_two_later_cannot_fill_the_stale_level(self, mocker):
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8005, 8015), [])

        mocker.patch(SIGNALS, return_value=None)
        search.feed(candle(7990, 8010, 8005, 8000, minute=15), [])
        assert (
            search.feed(candle(8010, 8040, 8015, 8035, minute=30), []) is None
        )

    def test_the_fill_keeps_the_signal_candle_not_the_fill_candle(
        self, mocker
    ):
        """FR-C06 measures the stop from the candle the indicator fired
        on, which on a pending entry is never the candle that filled."""
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        signal_candle = candle(8000, 8020, 8005, 8015)
        search.feed(signal_candle, [])

        mocker.patch(SIGNALS, return_value=None)
        entry = search.feed(candle(8010, 8030, 8015, 8025, minute=15), [])
        assert entry is not None
        assert entry.signal_candle is signal_candle

    def test_a_short_pending_level_fills_on_a_break_below(self, mocker):
        mocker.patch(
            SIGNALS, return_value=signal(Direction.SELL, 8000.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8015, 8002), [])

        mocker.patch(SIGNALS, return_value=None)
        entry = search.feed(candle(7980, 8010, 8005, 7985, minute=15), [])
        assert entry is not None
        assert entry.price == 8000.0
        assert entry.side is SHORT

    def test_a_fill_wins_over_the_same_candle_own_signal(self, mocker):
        """A pending level is resolved before this candle's signal is
        even asked for, so the fill opens the position and the new signal
        is left to the engine's one-position rule to ignore."""
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        first = candle(8000, 8020, 8005, 8015)
        search.feed(first, [])

        mocker.patch(
            SIGNALS, return_value=signal(Direction.SELL, 7990.0, True)
        )
        entry = search.feed(candle(8010, 8030, 8015, 8025, minute=15), [])
        assert entry is not None
        assert entry.side is LONG
        assert entry.signal_candle is first

    def test_reset_clears_a_pending_level(self, mocker):
        mocker.patch(
            SIGNALS, return_value=signal(Direction.BUY, 8020.0, False)
        )
        search = ComboEntrySearch()
        search.feed(candle(8000, 8020, 8005, 8015), [])
        search.reset()
        assert search.pending is None
