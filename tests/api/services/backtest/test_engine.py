"""The core breakout/reversal engine, shared by every backtest variant:
entry detection, the exit conventions, and the one-position-at-a-time
rule. Variant-specific behavior lives in the test_engine_* files.
"""

from model.enum import DayStatus, Direction, ExitReason
from tests.api.services.backtest.helpers import (
    DEFINITION,
    H1_HIGH,
    H1_LOW,
    TRADING_DATE,
    h1_candle,
    m5_candle,
    make_service,
)


class TestEvaluateDayNoData:
    async def test_missing_h1_candle_returns_no_data(self):
        service = make_service(h1_candles=[], m5_candles=[])
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_DATA
        assert result.trades == []
        assert result.h1_high is None
        assert result.h1_low is None

    async def test_h1_fetch_raising_returns_no_data(self):
        service = make_service(h1_candles=[], m5_candles=[], raise_on_h1=True)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_DATA

    async def test_m5_fetch_raising_returns_no_trade(self):
        """If the H1 reference is available but the 5-minute fetch
        fails, the day is a NO_TRADE (not NO_DATA, which is reserved
        for a missing H1 reference per FR-004)."""
        service = make_service([h1_candle()], m5_candles=[], raise_on_m5=True)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW


class TestEvaluateDayNoTrade:
    async def test_no_breakout_below_h1_low(self):
        candles = [
            m5_candle(0, 8010, 8020, 8005, 8015),
            m5_candle(1, 8015, 8025, 8010, 8020),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW

    async def test_breakdown_without_confirmed_reversal(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach, no close-back
            m5_candle(1, 7995, 8000, 7985, 7990),  # still below h1_low
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []


class TestEvaluateDayCandleOrdering:
    async def test_day_result_candles_chronological_even_if_fetched_reversed(
        self,
    ):
        """The real SaxoClient returns candles newest-first (repo-wide
        "index 0 = newest" convention). DayResult.candles must still be
        time-ascending for the detail view's "5-minute candles from
        10:00" table (FR-015), independently of the fetch order -- the
        engine already sorts internally for its own evaluation, but the
        DayResult used to be populated from the raw, unsorted fetch."""
        chronological_candles = [
            m5_candle(0, 8010, 8020, 8005, 8015),
            m5_candle(1, 8015, 8025, 8010, 8020),
            m5_candle(2, 8020, 8030, 8015, 8025),
        ]
        newest_first = list(reversed(chronological_candles))
        service = make_service([h1_candle()], newest_first)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert [c.date for c in result.candles] == [
            c.date for c in chronological_candles
        ]


class TestEvaluateDayExits:
    async def test_stop_loss_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8000, 8005, 7950, 7955),  # SL: low<=7965, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8015
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7965
        assert trade.points == -50

    async def test_stop_loss_exit_with_gap(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 7900, 7910, 7850, 7880),  # gap below 7965
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7900
        assert trade.points == -115

    async def test_take_profit_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8020, 8045, 8015, 8035),  # TP: high>=8040, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
        assert trade.points == 25

    async def test_end_of_day_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8012, 8020, 8005, 8018),  # last candle of the day
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8018
        assert trade.points == 3

    async def test_entry_on_last_candle_produces_zero_point_end_of_day(self):
        """A breakout that only confirms on the session's final
        5-minute candle opens and immediately closes (end of day) on
        that same candle, since there is no further candle to
        evaluate -- the trade never had a chance to move, so points
        is exactly 0."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout, also last
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8015
        assert trade.exit_price == 8015
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.points == 0

    async def test_break_even_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8015, 8039, 8005, 8020),  # arms BE (>=8035), no TP
            m5_candle(4, 8020, 8025, 8005, 8000),  # BE exit: low<=8015
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015
        assert trade.points == 0

    async def test_break_even_exit_with_gap_is_not_exactly_zero(self):
        """FR-010's gap-fill rule applies uniformly to all exit types,
        including break-even (resolved explicitly after PR review):
        a candle that opens below the (now break-even) stop records
        that open price, so the trade's points can be a small
        non-zero value even though it is still labeled BREAK_EVEN."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8015, 8039, 8005, 8020),  # arms BE (>=8035), no TP
            m5_candle(4, 8005, 8008, 7995, 8000),  # gap: open 8005 < 8015
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8005
        assert trade.points == -10

    async def test_multi_trade_day_reentry(self):
        candles = [
            # Trade 1: breach -> candidate -> breakout @8015 -> stop-loss
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),
            m5_candle(2, 8010, 8020, 8005, 8015),
            m5_candle(3, 8000, 8005, 7950, 7955),
            # Trade 2: fresh breach -> candidate -> breakout @8005 -> EOD
            m5_candle(4, 7950, 7960, 7930, 7935),
            m5_candle(5, 7940, 8005, 7935, 8000),
            m5_candle(6, 8000, 8010, 7995, 8005),
            m5_candle(7, 8010, 8020, 8000, 8015),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 2
        assert result.trades[0].entry_price == 8015
        assert result.trades[0].exit_reason == ExitReason.STOP_LOSS
        assert result.trades[0].exit_price == 7965
        assert result.trades[1].entry_price == 8005
        assert result.trades[1].exit_reason == ExitReason.END_OF_DAY
        assert result.trades[1].exit_price == 8015


class TestBreakoutConfirmation:
    """Direct tests for the breakout-confirmation step clarified after
    PR review: closing back above the H1 low only produces a
    candidate reversal candle - entry only fires once a later candle's
    high trades above that candidate's high."""

    async def test_reversal_without_breakout_confirmation_produces_no_trade(
        self,
    ):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8014, 8005, 8012),  # never exceeds 8015
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_candidate_rolls_forward_when_breakout_not_yet_confirmed(
        self,
    ):
        """A candle that stays above the H1 low but fails to beat the
        current candidate's high becomes the new candidate itself,
        rather than cancelling the signal."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate1, higher=8015
            m5_candle(2, 8010, 8014, 8005, 8012),  # rolls: new candidate=8014
            m5_candle(3, 8010, 8020, 8005, 8015),  # breaks 8014 -> entry
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        assert result.trades[0].entry_price == 8014

    async def test_candidate_closing_back_below_h1_low_requires_a_fresh_breach(
        self,
    ):
        """While waiting for a breakout, a candle that closes back
        below the H1 low discards the pending candidate entirely - a
        brand new breach and reversal pair is required, not just a
        new candidate."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach 1
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate1, higher=8015
            m5_candle(2, 7995, 8005, 7985, 7990),  # closes below h1_low
            m5_candle(3, 7995, 8020, 7985, 8005),  # candidate2, higher=8020
            m5_candle(4, 8010, 8025, 8000, 8015),  # breaks 8020 -> entry
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        assert result.trades[0].entry_price == 8020

    async def test_breakout_entry_gap_fill(self):
        """A candle that opens above the candidate's high (a gap)
        records the entry at that worse open price, not the exact
        breakout level - same gap-fill convention as the exits."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8020, 8030, 8015, 8025),  # gaps above 8015
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        assert result.trades[0].entry_price == 8020


class TestEvaluateDaySameCandleEdgeCases:
    async def test_stop_loss_priority_over_same_candle_be_arm(self):
        """A candle that would both breach the original stop-loss and
        reach the +20pt break-even-arm threshold resolves as a
        stop-loss using the pre-candle level, not a break-even arm."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            # low breaches original stop (7965) AND high reaches +20 (8035)
            m5_candle(3, 8005, 8035, 7950, 8000),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7965

    async def test_arm_and_breach_round_trip_does_not_exit_same_candle(self):
        """A candle whose high reaches the +20pt arm threshold and whose
        low would also breach the not-yet-armed break-even level (but
        not the original stop) must not itself produce a break-even
        exit -- arming only takes effect on the next candle."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            # high reaches +20 (8035->8039, below TP 8040) AND low dips to
            # 8010 (<=entry 8015, but > original stop 7965 -- no exit)
            m5_candle(3, 8015, 8039, 8010, 8020),
            # now armed: low breaches the new stop (8015)
            m5_candle(4, 8020, 8025, 8005, 8000),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015
        assert trade.exit_time == candles[4].date


class TestEvaluateDayEntryValidityRule:
    async def test_entry_too_far_above_h1_low_is_rejected(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8015, 8026, 8005, 8020),  # candidate, higher=8026
            # breaks 8026 -> entry@8026, but 26pts from h1_low (> 20 max)
            m5_candle(2, 8020, 8030, 8010, 8025),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_entry_at_or_above_take_profit_is_rejected(self):
        h1 = h1_candle(higher=8025, lower=8005)  # take_profit_level = 8015
        candles = [
            m5_candle(0, 8010, 8015, 7995, 8000),  # breach
            m5_candle(1, 8010, 8016, 8000, 8010),  # candidate, higher=8016
            # breaks 8016 -> entry@8016, within 20pts but at/above TP (8015)
            m5_candle(2, 8012, 8020, 8005, 8015),
        ]
        service = make_service([h1], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_rejected_entry_still_allows_a_fresh_signal_afterwards(self):
        """After an invalid entry, the search resets so a later,
        independent breach/candidate/breakout sequence can still
        produce a valid trade the same day."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach 1
            m5_candle(1, 8015, 8026, 8005, 8020),  # candidate1, higher=8026
            m5_candle(2, 8020, 8030, 8010, 8025),  # invalid breakout (26pts)
            m5_candle(3, 8010, 8015, 7995, 7998),  # breach 2
            m5_candle(4, 8000, 8015, 7995, 8010),  # candidate2, higher=8015
            m5_candle(5, 8010, 8020, 8005, 8015),  # breaks 8015 -> entry
            m5_candle(6, 8012, 8020, 8005, 8018),  # end of day
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8015
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8018


class TestBreachRequiresCloseOutsideRange:
    """The initial breach is measured on the candle's close, not an
    intrabar wick: a candle that pierces the H1 range but closes back
    inside it does not arm a breach, so a subsequent reversal/breakout
    sequence produces no trade."""

    async def test_long_wick_below_low_that_closes_inside_is_not_a_breach(
        self,
    ):
        candles = [
            # low 7990 dips below h1_low 8000 but close 8005 is inside
            m5_candle(0, 8005, 8010, 7990, 8005),
            m5_candle(1, 8005, 8015, 8000, 8010),  # would-be candidate
            m5_candle(2, 8010, 8020, 8005, 8015),  # would-be breakout
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_short_wick_above_high_that_closes_inside_is_not_a_breach(
        self,
    ):
        candles = [
            # high 8060 pierces h1_high 8050 but close 8045 is inside
            m5_candle(0, 8045, 8060, 8040, 8045),
            m5_candle(1, 8045, 8050, 8035, 8040),  # would-be candidate
            m5_candle(2, 8040, 8045, 8030, 8035),  # would-be breakdown
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []


class TestEvaluateDayShort:
    """Short side, mirror of the long-side exit tests. H1 high=8050,
    low=8000, so the short take-profit is 8010 (low + 10) and the short
    stop-loss sits 50 points above entry."""

    async def test_short_stop_loss_exit(self):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach above high
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8038, 8042, 8035, 8037),  # breakdown -> short @8038
            m5_candle(3, 8080, 8090, 8075, 8085),  # SL: high>=8088, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8038
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 8088
        assert trade.points == -50

    async def test_short_stop_loss_exit_with_gap(self):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8038, 8042, 8035, 8037),  # short @8038
            m5_candle(3, 8095, 8100, 8090, 8098),  # gap above 8088
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 8095
        assert trade.points == -57

    async def test_short_take_profit_exit(self):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8038, 8042, 8035, 8037),  # short @8038
            m5_candle(3, 8015, 8018, 8005, 8010),  # TP: low<=8010, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8010
        assert trade.points == 28

    async def test_short_end_of_day_exit(self):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8038, 8042, 8035, 8037),  # short @8038
            m5_candle(3, 8036, 8040, 8030, 8035),  # last candle of the day
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8035
        assert trade.points == 3

    async def test_short_break_even_exit(self):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8038, 8042, 8035, 8037),  # short @8038
            m5_candle(3, 8035, 8040, 8016, 8030),  # arms BE (low<=8018), no TP
            m5_candle(4, 8030, 8045, 8025, 8035),  # BE exit: high>=8038
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8038
        assert trade.points == 0

    async def test_short_reversal_without_breakdown_confirmation_no_trade(
        self,
    ):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach above high
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8042, 8048, 8041, 8045),  # never breaks below 8040
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_short_entry_too_far_below_h1_high_is_rejected(self):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach above high
            m5_candle(1, 8050, 8055, 8025, 8045),  # candidate, lower=8025
            # breaks below 8025 -> entry @8025, 25pts from h1_high (> 20 max)
            m5_candle(2, 8028, 8030, 8020, 8025),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_short_breakdown_entry_gap_fill(self):
        """Mirror of the long-side gap-fill entry: a confirming candle
        that opens below the candidate's low records the short entry at
        that worse open price, not the exact breakdown level."""
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach above high
            m5_candle(1, 8050, 8055, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8035, 8038, 8025, 8030),  # gaps below 8040
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        assert result.trades[0].direction == Direction.SELL
        assert result.trades[0].entry_price == 8035

    async def test_short_candidate_closing_above_h1_high_needs_fresh_breach(
        self,
    ):
        """Mirror of the long-side discard rule: while waiting for a
        breakdown, a candle that closes back above the H1 high discards
        the pending short candidate entirely - a brand new breach and
        reversal pair is required, not just a new candidate."""
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach 1 above high
            m5_candle(1, 8050, 8055, 8040, 8045),  # candidate1, lower=8040
            m5_candle(2, 8055, 8065, 8048, 8060),  # closes above h1_high
            m5_candle(3, 8050, 8058, 8035, 8045),  # candidate2, lower=8035
            m5_candle(4, 8038, 8042, 8030, 8035),  # breaks 8035 -> entry
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        assert result.trades[0].direction == Direction.SELL
        assert result.trades[0].entry_price == 8035

    async def test_short_candidate_rolls_forward_when_not_yet_confirmed(self):
        """Mirror of the long-side roll-forward: a candle that stays
        below the H1 high but fails to break the current candidate's
        low becomes the new candidate itself, rather than cancelling
        the signal."""
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach above high
            m5_candle(1, 8050, 8055, 8040, 8045),  # candidate1, lower=8040
            m5_candle(2, 8045, 8048, 8041, 8043),  # rolls: new candidate=8041
            m5_candle(3, 8042, 8044, 8035, 8038),  # breaks 8041 -> entry
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        assert result.trades[0].direction == Direction.SELL
        assert result.trades[0].entry_price == 8041


class TestBothDirectionsOnePositionAtATime:
    async def test_long_then_short_sequential_same_day(self):
        """Both directions are evaluated on the same day but only one
        position is open at a time: a long opens first, and only after
        it closes does the short signal (a break above the H1 high and
        reversal) open a second, opposite-direction position."""
        candles = [
            # Long: breach below low -> candidate -> breakout @8015 -> SL
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # long candidate h=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # long entry @8015
            m5_candle(3, 8000, 8005, 7950, 7955),  # long SL @7965
            # Short: breach above high -> candidate -> breakdown @8038 -> EOD
            m5_candle(4, 8055, 8060, 8050, 8055),  # breach above high
            m5_candle(5, 8050, 8052, 8040, 8045),  # short candidate lower=8040
            m5_candle(6, 8038, 8042, 8035, 8037),  # short entry @8038
            m5_candle(7, 8035, 8045, 8030, 8040),  # end of day
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 2

        first, second = result.trades
        assert first.direction == Direction.BUY
        assert first.entry_price == 8015
        assert first.exit_reason == ExitReason.STOP_LOSS
        assert first.exit_price == 7965
        assert first.points == -50

        assert second.direction == Direction.SELL
        assert second.entry_price == 8038
        assert second.exit_reason == ExitReason.END_OF_DAY
        assert second.exit_price == 8040
        assert second.points == -2

    async def test_high_breach_closing_a_long_does_not_also_open_a_short(self):
        """Because the short reference (H1 high) sits above the long
        take-profit (H1 high - 10), the very candle that breaks above
        the high closes the open long on take-profit. That closing
        candle is not re-evaluated for a new signal, so it cannot also
        open a concurrent short - one position at a time, either side."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # long breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # long candidate h=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # long entry @8015
            # breaks above the high (8055) -> closes the long on TP (8040),
            # and does NOT also spawn a short from the same candle
            m5_candle(3, 8035, 8055, 8030, 8040),
            m5_candle(4, 8045, 8048, 8040, 8043),  # benign, flat
            m5_candle(5, 8042, 8046, 8038, 8040),  # last candle, flat
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.BUY
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
