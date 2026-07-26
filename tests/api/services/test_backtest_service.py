import datetime
from unittest.mock import AsyncMock, MagicMock


from api.services.backtest import BacktestService
from api.services.backtest.service import (
    _is_valid_long_entry,
    _is_valid_short_entry,
)
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import BacktestParameters, DayResult, Trade, UnitTime
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from tests.api.services.backtest.helpers import (
    DEFINITION,
    GER_DEFINITION,
    GER_PARAMS,
    H1_HIGH,
    H1_LOW,
    NO_CACHE_CLIENT,
    TIME_CUT_DEFINITION,
    TRADING_DATE,
    WIDE_RANGE_DEFINITION,
    h1_candle,
    m5_candle,
    make_service,
    run_ger,
    uptrend_daily_series,
)
from utils.exception import SaxoException


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


class TestIsValidLongEntry:
    """Direct unit tests for the long entry-validity rule added after PR
    review: a breakout-reversal close only produces a trade when it is
    within MAX_ENTRY_DISTANCE points of the H1 low and still below the
    take-profit level."""

    def test_within_distance_and_below_tp_is_valid(self):
        assert _is_valid_long_entry(8010, 8000, 8040) is True

    def test_exactly_at_max_distance_is_valid(self):
        assert _is_valid_long_entry(8020, 8000, 8040) is True

    def test_beyond_max_distance_is_invalid(self):
        assert _is_valid_long_entry(8021, 8000, 8040) is False

    def test_at_take_profit_level_is_invalid(self):
        assert _is_valid_long_entry(8015, 8005, 8015) is False

    def test_above_take_profit_level_is_invalid(self):
        assert _is_valid_long_entry(8016, 8005, 8015) is False

    def test_just_below_take_profit_level_is_valid(self):
        assert _is_valid_long_entry(8014, 8005, 8015) is True


class TestIsValidShortEntry:
    """Mirror of TestIsValidLongEntry for the short side: a short
    breakdown entry is valid only when it is within MAX_ENTRY_DISTANCE
    points below the H1 high and still above the take-profit level
    (H1 low plus 10)."""

    def test_within_distance_and_above_tp_is_valid(self):
        # h1_high=8050, tp=8010: entry 8040 is 10pts below high, above tp
        assert _is_valid_short_entry(8040, 8050, 8010) is True

    def test_exactly_at_max_distance_is_valid(self):
        assert _is_valid_short_entry(8030, 8050, 8010) is True

    def test_beyond_max_distance_is_invalid(self):
        assert _is_valid_short_entry(8029, 8050, 8010) is False

    def test_at_take_profit_level_is_invalid(self):
        assert _is_valid_short_entry(8010, 8025, 8010) is False

    def test_below_take_profit_level_is_invalid(self):
        assert _is_valid_short_entry(8009, 8025, 8010) is False

    def test_just_above_take_profit_level_is_valid(self):
        assert _is_valid_short_entry(8011, 8025, 8010) is True


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


class TestTimeCutVariant:
    """The "Bougie de 9h (time cut)" definition runs the identical B9H
    scenario but closes a position at market once time_cut_minutes have
    elapsed since entry if it has never moved more than
    time_cut_min_favorable_points in its favor. Entry here confirms on
    the candle at offset 2 (08:10 UTC), so the 30-minute deadline lands
    on the candle at offset 8 (08:40 UTC). Long entry is @8015, so
    "5 points favorable" means a high of 8020."""

    ENTRY_CANDLES = [
        m5_candle(0, 8005, 8010, 7990, 7995),  # breach
        m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
        m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
    ]

    async def test_long_position_is_cut_after_30_min_without_favorable_move(
        self,
    ):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8015, 8018, 8010, 8016),
            m5_candle(4, 8016, 8019, 8011, 8017),
            m5_candle(5, 8017, 8018, 8012, 8015),
            m5_candle(6, 8015, 8019, 8010, 8016),
            m5_candle(7, 8016, 8018, 8011, 8014),
            m5_candle(8, 8014, 8018, 8009, 8012),  # 08:40 -> time cut
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.BUY
        assert trade.entry_price == 8015
        assert trade.exit_reason == ExitReason.TIME_CUT
        assert trade.exit_price == 8012  # close of the 08:40 candle
        assert trade.exit_time == candles[8].date
        assert trade.points == -3

    async def test_position_survives_when_favorable_move_exceeds_threshold(
        self,
    ):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8015, 8030, 8010, 8025),  # +15 favorable
            m5_candle(4, 8020, 8022, 8012, 8018),
            m5_candle(5, 8017, 8020, 8012, 8015),
            m5_candle(6, 8015, 8019, 8010, 8016),
            m5_candle(7, 8016, 8018, 8011, 8014),
            m5_candle(8, 8014, 8018, 8009, 8012),  # 08:40, but not cut
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8012

    async def test_exactly_five_points_favorable_still_cuts(self):
        """ "Never been higher than 5 points" is inclusive: a best move of
        exactly 5 points (a high of 8020) does not spare the position."""
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8015, 8020, 8010, 8016),  # exactly +5 favorable
            m5_candle(4, 8016, 8019, 8011, 8017),
            m5_candle(5, 8017, 8018, 8012, 8015),
            m5_candle(6, 8015, 8019, 8010, 8016),
            m5_candle(7, 8016, 8018, 8011, 8014),
            m5_candle(8, 8014, 8018, 8009, 8012),  # 08:40 -> time cut
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)
        assert result.trades[0].exit_reason == ExitReason.TIME_CUT

    async def test_plain_b9h_definition_is_never_time_cut(self):
        """The same stalling day on the plain B9H definition (no time-cut
        config) holds the position to the end of day - proving the rule
        is isolated to the time-cut variant."""
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8015, 8018, 8010, 8016),
            m5_candle(4, 8016, 8019, 8011, 8017),
            m5_candle(5, 8017, 8018, 8012, 8015),
            m5_candle(6, 8015, 8019, 8010, 8016),
            m5_candle(7, 8016, 8018, 8011, 8014),
            m5_candle(8, 8014, 8018, 8009, 8012),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.trades[0].exit_reason == ExitReason.END_OF_DAY

    async def test_short_position_is_cut_after_30_min_without_favorable_move(
        self,
    ):
        candles = [
            m5_candle(0, 8055, 8060, 8050, 8052),  # breach above high
            m5_candle(1, 8050, 8052, 8040, 8045),  # candidate, lower=8040
            m5_candle(2, 8038, 8042, 8035, 8037),  # breakdown -> short @8038
            m5_candle(3, 8038, 8042, 8034, 8039),
            m5_candle(4, 8039, 8043, 8034, 8040),
            m5_candle(5, 8040, 8044, 8035, 8041),
            m5_candle(6, 8041, 8043, 8034, 8039),
            m5_candle(7, 8039, 8042, 8035, 8038),
            m5_candle(8, 8038, 8041, 8034, 8037),  # 08:40 -> time cut
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8038
        assert trade.exit_reason == ExitReason.TIME_CUT
        assert trade.exit_price == 8037
        assert trade.points == 1


def make_trade(exit_reason, points, entry_price=8010.0):
    return Trade(
        entry_time=datetime.datetime(2026, 6, 3, 8, 5),
        entry_price=entry_price,
        exit_time=datetime.datetime(2026, 6, 3, 9, 0),
        exit_price=entry_price + points,
        exit_reason=exit_reason,
        points=points,
    )


class TestRunRange:
    async def test_aggregates_across_days_and_excludes_no_data(self, mocker):
        service = BacktestService(
            MagicMock(spec=CandlesService), NO_CACHE_CLIENT
        )
        day1 = datetime.date(2026, 6, 1)
        day2 = datetime.date(2026, 6, 2)
        day3 = datetime.date(2026, 6, 3)
        results = {
            day1: DayResult(date=day1, status=DayStatus.NO_DATA),
            day2: DayResult(
                date=day2,
                status=DayStatus.NO_TRADE,
                h1_high=8050,
                h1_low=8000,
            ),
            day3: DayResult(
                date=day3,
                status=DayStatus.TRADED,
                h1_high=8050,
                h1_low=8000,
                trades=[
                    make_trade(ExitReason.STOP_LOSS, -50),
                    make_trade(ExitReason.TAKE_PROFIT, 30),
                    make_trade(ExitReason.BREAK_EVEN, 0),
                ],
            ),
        }
        mocker.patch.object(
            service,
            "evaluate_day",
            side_effect=lambda d, date, params: results[date],
        )

        result = await service.run_range(DEFINITION, day1, day3)

        assert result.summary.number_of_days == 2  # NO_DATA excluded
        assert result.summary.number_of_trades == 3
        assert result.summary.number_of_winning_positions == 1
        assert result.summary.number_of_losing_positions == 1
        assert result.summary.number_of_be == 1
        assert result.summary.average_win == 30
        assert result.summary.average_loss == 50  # positive magnitude
        assert result.summary.final_result == -20
        assert len(result.days) == 2  # NO_DATA day excluded from list too
        assert result.days[0].date == day2
        assert result.days[0].trade_count == 0
        assert result.days[1].date == day3
        assert result.days[1].trade_count == 3
        assert result.days[1].points == -20

    async def test_weekends_are_skipped_without_calling_evaluate_day(
        self, mocker
    ):
        """Saturday/Sunday never trade, so run_range must not spend a
        fetch resolving them to NO_DATA - it should skip evaluate_day
        for those dates entirely."""
        service = BacktestService(
            MagicMock(spec=CandlesService), NO_CACHE_CLIENT
        )
        friday = datetime.date(2026, 6, 5)
        monday = datetime.date(2026, 6, 8)
        evaluate_day = mocker.patch.object(
            service,
            "evaluate_day",
            side_effect=lambda d, date, params: DayResult(
                date=date, status=DayStatus.NO_TRADE, h1_high=8050, h1_low=8000
            ),
        )

        result = await service.run_range(DEFINITION, friday, monday)

        called_dates = [call.args[1] for call in evaluate_day.call_args_list]
        assert called_dates == [friday, monday]
        assert result.summary.number_of_days == 2

    async def test_empty_range_returns_all_zero_summary(self, mocker):
        service = BacktestService(
            MagicMock(spec=CandlesService), NO_CACHE_CLIENT
        )
        day = datetime.date(2026, 6, 2)
        mocker.patch.object(
            service,
            "evaluate_day",
            return_value=DayResult(
                date=day, status=DayStatus.NO_TRADE, h1_high=8050, h1_low=8000
            ),
        )

        result = await service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_days == 1
        assert result.summary.number_of_trades == 0
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 0
        assert result.summary.number_of_be == 0
        assert result.summary.average_win is None
        assert result.summary.average_loss is None
        assert result.summary.final_result == 0

    async def test_zero_point_non_be_trade_counts_as_losing(self, mocker):
        """A trade with points == 0 that did NOT close via the
        break-even mechanism (e.g. an end-of-day close landing exactly
        on the entry price) counts as a losing position, not a win or
        a BE (per spec.md Assumptions)."""
        service = BacktestService(
            MagicMock(spec=CandlesService), NO_CACHE_CLIENT
        )
        day = datetime.date(2026, 6, 2)
        mocker.patch.object(
            service,
            "evaluate_day",
            return_value=DayResult(
                date=day,
                status=DayStatus.TRADED,
                h1_high=8050,
                h1_low=8000,
                trades=[make_trade(ExitReason.END_OF_DAY, 0)],
            ),
        )

        result = await service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_trades == 1
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 1
        assert result.summary.number_of_be == 0

    async def test_gapped_be_trade_stays_be_not_losing(self, mocker):
        """A BREAK_EVEN trade with non-zero points (gap-through, see
        evaluate_day's gap test) is still classified as BE, not as a
        loss, and its points are excluded from average_loss - only
        final_result reflects the actual value (resolved explicitly
        after PR review, see spec.md Assumptions)."""
        service = BacktestService(
            MagicMock(spec=CandlesService), NO_CACHE_CLIENT
        )
        day = datetime.date(2026, 6, 2)
        mocker.patch.object(
            service,
            "evaluate_day",
            return_value=DayResult(
                date=day,
                status=DayStatus.TRADED,
                h1_high=8050,
                h1_low=8000,
                trades=[make_trade(ExitReason.BREAK_EVEN, -5)],
            ),
        )

        result = await service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_trades == 1
        assert result.summary.number_of_be == 1
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 0
        assert result.summary.average_loss is None
        assert result.summary.final_result == -5

    async def test_zero_point_end_of_day_trade_counts_as_losing(self, mocker):
        """A non-BE trade that closes at exactly 0 points (e.g. entry
        confirmed on the session's last candle, see evaluate_day's
        same-candle EOD test) is classified as a losing position, not a
        win or a BE - only break-even-mechanism exits get the "BE"
        label (documented in spec.md Assumptions)."""
        service = BacktestService(
            MagicMock(spec=CandlesService), NO_CACHE_CLIENT
        )
        day = datetime.date(2026, 6, 2)
        mocker.patch.object(
            service,
            "evaluate_day",
            return_value=DayResult(
                date=day,
                status=DayStatus.TRADED,
                h1_high=8050,
                h1_low=8000,
                trades=[make_trade(ExitReason.END_OF_DAY, 0)],
            ),
        )

        result = await service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_trades == 1
        assert result.summary.number_of_be == 0
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 1
        assert result.summary.average_loss == 0
        assert result.summary.final_result == 0


class TestBacktestParameters:
    """The four strategy thresholds are tunable via BacktestParameters;
    omitting them (or passing the default instance) reproduces the
    original hardcoded behavior exercised by TestEvaluateDayExits."""

    STOP_LOSS_CANDLES = [
        m5_candle(0, 8005, 8010, 7990, 7995),  # breach
        m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
        m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
        m5_candle(3, 8000, 8005, 7950, 7955),  # stop hit, no gap
    ]

    async def test_explicit_default_params_match_the_hardcoded_result(self):
        service = make_service([h1_candle()], self.STOP_LOSS_CANDLES)
        result = await service.evaluate_day(
            DEFINITION, TRADING_DATE, BacktestParameters()
        )
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7965
        assert trade.points == -50

    async def test_custom_stop_loss_points_tightens_the_stop(self):
        service = make_service([h1_candle()], self.STOP_LOSS_CANDLES)
        params = BacktestParameters(stop_loss_points=30)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE, params)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7985  # 8015 - 30 instead of - 50
        assert trade.points == -30

    async def test_custom_take_profit_offset_moves_the_target(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8020, 8045, 8015, 8035),  # high>=8030 target
        ]
        service = make_service([h1_candle()], candles)
        params = BacktestParameters(take_profit_offset_points=20)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE, params)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8030  # 8050 - 20 instead of - 10
        assert trade.points == 15

    async def test_custom_max_entry_distance_rejects_a_far_entry(self):
        """With the default 20-point window the breakout at 8015 (15
        points above the 8000 low) is a valid entry; tightening the
        window to 10 points rejects it, so no trade is taken."""
        service = make_service([h1_candle()], self.STOP_LOSS_CANDLES)
        params = BacktestParameters(max_entry_distance_points=10)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE, params)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []


class TestRunRangeThreadsRegime:
    async def test_mm50_slope_populated_on_summary(self):
        trading_date = datetime.date(2026, 6, 2)
        service = make_service(
            [h1_candle()], TestBacktestParameters.STOP_LOSS_CANDLES
        )
        service.candles_service.build_candles.return_value = (
            uptrend_daily_series(trading_date, 70)
        )
        result = await service.run_range(
            DEFINITION, trading_date, trading_date
        )
        assert len(result.days) == 1
        assert result.days[0].mm50_slope is not None
        assert result.days[0].mm50_slope > 0
        assert result.days[0].adx14 is not None
        assert result.days[0].adx14 > 0
        # h1_candle() opens at 8020; latest prior daily close is 8069
        assert result.days[0].h1_open == 8020.0
        assert result.days[0].overnight_gap == round(8020.0 - 8069.0, 4)


class TestWideRangeStructuralStop:
    """US1d: the "CAC40 Bougie de 9h (wide-range structural stop)" variant -
    a >40pt H1-range entry filter (FR-033) and a structural stop that fires
    when a 5-minute candle closes beyond the H1 level while break-even is
    unarmed (FR-034/FR-035)."""

    # Base long setup: breach, reversal candidate (high 8015), breakout
    # confirmation -> entry @8015. h1 defaults are 8000/8050 (range 50).
    ENTRY_CANDLES = [
        m5_candle(0, 8005, 8010, 7990, 7995),  # breach (close < 8000)
        m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
        m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
    ]

    async def test_narrow_range_day_takes_no_trades(self):
        narrow = h1_candle(higher=8030.0, lower=8000.0)  # range 30 <= 40
        service = make_service([narrow], self.ENTRY_CANDLES)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
        assert result.h1_high == 8030.0 and result.h1_low == 8000.0

    async def test_range_exactly_at_threshold_takes_no_trades(self):
        # strictly greater than 40 required -> a range of exactly 40 is out
        at_threshold = h1_candle(higher=8040.0, lower=8000.0)
        service = make_service([at_threshold], self.ENTRY_CANDLES)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        assert result.status == DayStatus.NO_TRADE

    async def test_narrow_range_day_skips_the_five_minute_fetch(self):
        """The range filter must run before the m5 fetch (FR-033), both
        to avoid the wasted Saxo call and so a re-run of the same day
        stays NO_TRADE from the cached H1 candle alone."""
        narrow = h1_candle(higher=8030.0, lower=8000.0)  # range 30 <= 40
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [narrow]
            raise AssertionError("m5 candles must not be fetched")

        candles_service.get_candles_in_window.side_effect = side_effect
        service = BacktestService(candles_service, NO_CACHE_CLIENT)

        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )

        assert result.status == DayStatus.NO_TRADE

    async def test_wide_range_long_structural_stop_exits_at_close(self):
        candles = self.ENTRY_CANDLES + [
            # unarmed; closes below h1 low 8000 -> structural stop at close
            m5_candle(3, 8000, 8005, 7950, 7955),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        assert result.status == DayStatus.TRADED
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7955.0  # the candle's close, not h1 low
        assert trade.points == round(7955.0 - 8015.0, 4)

    async def test_wide_range_short_structural_stop_exits_at_close(self):
        short_candles = [
            m5_candle(0, 8045, 8060, 8040, 8055),  # breach above h1 high
            m5_candle(1, 8050, 8055, 8035, 8040),  # candidate, lower=8035
            m5_candle(2, 8040, 8045, 8030, 8035),  # breakdown -> entry @8035
            # unarmed; closes above h1 high 8050 -> structural stop at close
            m5_candle(3, 8090, 8110, 8085, 8095),
        ]
        service = make_service([h1_candle()], short_candles)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 8095.0
        assert trade.points == round(8035.0 - 8095.0, 4)

    async def test_break_even_supersedes_structural_stop(self):
        candles = self.ENTRY_CANDLES + [
            # high 8036 >= entry+20 (8035) arms break-even, no TP (8040)
            m5_candle(3, 8016, 8036, 8015, 8030),
            # low 7990 <= entry 8015 -> break-even at entry, even though the
            # close (7995) is below the h1 low: structural no longer applies
            m5_candle(4, 8020, 8022, 7990, 7995),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015.0

    async def test_take_profit_wins_over_structural_in_same_candle(self):
        candles = self.ENTRY_CANDLES + [
            # high 8045 reaches TP (8040) AND close 7995 is below h1 low:
            # TP is reached intrabar (earlier), so it wins
            m5_candle(3, 8016, 8045, 7990, 7995),
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040.0

    async def test_take_profit_still_exits_normally(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8016, 8045, 8014, 8042),  # high 8045 >= TP 8040
        ]
        service = make_service([h1_candle()], candles)
        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040.0


class TestBacktestCandleCache:
    """FR-036-FR-040: the raw-candle cache is a capability of
    BacktestService itself, keyed by (definition code, instrument,
    schema version, trading_date) - these tests exercise it directly
    against a mocked DynamoDBClient, independently of the
    CandlesService-fetch tests above."""

    def _service(self, dynamodb_client):
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [h1_candle()]
            return [m5_candle(0, 8005, 8010, 7995, 8000)]

        candles_service.get_candles_in_window.side_effect = side_effect
        return BacktestService(candles_service, dynamodb_client), (
            candles_service
        )

    async def test_cache_hit_skips_saxo_and_uses_cached_candles(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={
                "has_data": True,
                "h1_candle": h1_candle().to_dict(),
                "m5_candles": [m5_candle(0, 8005, 8010, 7995, 8000).to_dict()],
            }
        )
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_not_called()
        dynamodb_client.store_backtest_candles.assert_not_called()
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW
        assert len(result.candles) == 1

    async def test_cache_hit_no_data_skips_saxo(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={"has_data": False}
        )
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_not_called()
        assert result.status == DayStatus.NO_DATA

    async def test_cache_key_covers_code_instrument_and_version(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            f"{DEFINITION.code}:{DEFINITION.instrument}:v1",
            TRADING_DATE.isoformat(),
        )

    async def test_cache_miss_fetches_and_stores(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, candles_service = self._service(dynamodb_client)

        await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        dynamodb_client.store_backtest_candles.assert_called_once()
        args = dynamodb_client.store_backtest_candles.call_args[0]
        assert args[0] == f"{DEFINITION.code}:{DEFINITION.instrument}:v1"
        assert args[1] == TRADING_DATE.isoformat()
        assert args[2] is True

    async def test_cache_miss_with_no_h1_data_stores_no_data_marker(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)
        candles_service.get_candles_in_window.return_value = []
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_DATA
        dynamodb_client.store_backtest_candles.assert_called_once_with(
            f"{DEFINITION.code}:{DEFINITION.instrument}:v1",
            TRADING_DATE.isoformat(),
            False,
            None,
            None,
        )

    async def test_h1_fetch_failure_is_not_cached(self):
        """A transient Saxo failure (expired token, rate limit, network
        blip) must never be persisted as a permanent NO_DATA - only a
        genuine empty result from Saxo is cacheable."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)
        candles_service.get_candles_in_window.side_effect = SaxoException(
            "boom"
        )
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_DATA
        dynamodb_client.store_backtest_candles.assert_not_called()

    async def test_m5_fetch_failure_is_not_cached(self):
        """Mirror of the H1 case: a transient failure on the 5-minute
        fetch must not be persisted as a permanent has_data=True/empty
        NO_TRADE - only a genuine empty Saxo result is cacheable."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [h1_candle()]
            raise SaxoException("boom")

        candles_service.get_candles_in_window.side_effect = side_effect
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_TRADE
        assert result.h1_high == H1_HIGH
        dynamodb_client.store_backtest_candles.assert_not_called()

    async def test_malformed_cache_item_falls_back_to_saxo(self):
        """An item written under an earlier/different schema (missing
        the expected keys) must be treated as a miss, not raise - a
        cache problem must never break a backtest."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={"has_data": True}
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        dynamodb_client.store_backtest_candles.assert_called_once()
        assert result.h1_high == H1_HIGH

    async def test_no_active_resource_falls_back_to_saxo_every_time(self):
        """dynamodb_client is a required parameter (not Optional), but a
        DynamoDBClient with no active resource - local/dev usage
        without AWS, see get_dynamodb_client_best_effort - degrades to
        a cache miss/no-op every time, exactly like a DynamoDB failure."""
        service, candles_service = self._service(NO_CACHE_CLIENT)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        assert result.h1_high == H1_HIGH

    async def test_cache_lookup_failure_falls_back_to_saxo(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            side_effect=DynamoDBOperationError("get_item", "boom")
        )
        dynamodb_client.store_backtest_candles = AsyncMock(
            side_effect=DynamoDBOperationError("put_item", "boom")
        )
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        assert result.h1_high == H1_HIGH

    async def test_different_definitions_cache_independently(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            f"{TIME_CUT_DEFINITION.code}:{TIME_CUT_DEFINITION.instrument}:v1",
            TRADING_DATE.isoformat(),
        )


class TestEvaluateDayDoubleTakeProfit:
    """GER40 double take-profit / two-lot engine. With H1 8000-8050:
    TP1 (midpoint) = 8025, TP2 (long) = 8040, stop (long) = 7850,
    break-even trigger = entry + 50. A long entry at 8015 is formed by
    the breach/candidate/breakout candles 0-2 (same as the CAC40 tests)."""

    ENTRY_CANDLES = [
        m5_candle(0, 8005, 8010, 7990, 7995),  # breach (close < h1_low)
        m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
        m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
    ]

    async def test_tp1_then_tp2_full_winner(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8020, 8030, 8018, 8028),  # TP1 @8025 (lot A)
            m5_candle(4, 8030, 8045, 8028, 8042),  # TP2 @8040 (runner)
        ]
        result = await run_ger(candles)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.BUY
        assert trade.entry_price == 8015
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
        assert trade.points == 35  # (8025-8015) + (8040-8015)

    async def test_both_lots_stop_out_before_tp1_is_double_loss(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8010, 8012, 7840, 7845),  # low <= stop 7850
        ]
        result = await run_ger(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7850
        assert trade.points == -330  # 2 * (7850 - 8015)

    async def test_tp1_then_runner_returns_to_break_even(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8020, 8030, 8018, 8028),  # TP1 @8025, runner -> BE
            m5_candle(4, 8020, 8022, 8010, 8012),  # runner low <= entry 8015
        ]
        result = await run_ger(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015
        assert trade.points == 10  # banked 10 + runner 0

    async def test_tp1_and_tp2_on_the_same_candle(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8020, 8045, 8018, 8042),  # reaches both 8025 and 8040
        ]
        result = await run_ger(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
        assert trade.points == 35

    async def test_break_even_armed_by_plus_50_then_flat_stop_is_zero(self):
        # Wide H1 range so the midpoint (TP1) sits above the +50 trigger:
        # H1 8000-8200 -> TP1 = 8100, TP2 = 8190, +50 trigger = 8065.
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8020, 8070, 8018, 8065),  # high >= entry+50 -> arm BE
            m5_candle(4, 8060, 8062, 8010, 8012),  # low <= entry -> BE stop
        ]
        result = await run_ger(candles, higher=8200.0, lower=8000.0)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015
        assert trade.points == 0  # both lots at break-even, no TP filled

    async def test_end_of_day_with_both_lots_open(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8016, 8020, 8014, 8018),  # last candle, no TP/stop
        ]
        result = await run_ger(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8018
        assert trade.points == 6  # 2 * (8018 - 8015)

    async def test_end_of_day_after_tp1_closes_only_the_runner(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8020, 8030, 8018, 8028),  # TP1 @8025
            m5_candle(4, 8026, 8030, 8024, 8028),  # last candle, runner open
        ]
        result = await run_ger(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8028
        assert trade.points == 23  # banked 10 + (8028 - 8015)

    async def test_short_mirror_tp1_then_tp2(self):
        # Short off the H1 high: TP1 = 8025, TP2 = 8010, stop = 8200.
        candles = [
            m5_candle(0, 8045, 8060, 8040, 8055),  # breach above high
            m5_candle(1, 8050, 8055, 8035, 8040),  # candidate, lower=8035
            m5_candle(2, 8040, 8045, 8030, 8035),  # breakdown -> entry @8035
            m5_candle(3, 8034, 8038, 8020, 8024),  # TP1 @8025 (lot A)
            m5_candle(4, 8020, 8024, 8005, 8008),  # TP2 @8010 (runner)
        ]
        result = await run_ger(candles)
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8035
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8010
        assert trade.points == 35  # (8035-8025) + (8035-8010)

    async def test_no_data_day(self):
        service = make_service(h1_candles=[], m5_candles=[])
        result = await service.evaluate_day(
            GER_DEFINITION, TRADING_DATE, GER_PARAMS
        )
        assert result.status == DayStatus.NO_DATA

    async def test_two_sequential_positions_same_day(self):
        candles = self.ENTRY_CANDLES + [
            m5_candle(3, 8010, 8012, 7840, 7845),  # first: both lots stop out
            m5_candle(4, 7900, 7905, 7880, 7895),  # breach again
            m5_candle(5, 7900, 8016, 7895, 8012),  # candidate, higher=8016
            m5_candle(6, 8012, 8020, 8008, 8016),  # breakout -> entry @8016
            m5_candle(7, 8020, 8030, 8018, 8028),  # TP1 @8025
            m5_candle(8, 8030, 8045, 8028, 8042),  # TP2 @8040
        ]
        result = await run_ger(candles)
        assert len(result.trades) == 2
        assert result.trades[0].exit_reason == ExitReason.STOP_LOSS
        assert result.trades[0].points == -330
        assert result.trades[1].exit_reason == ExitReason.TAKE_PROFIT
        assert result.trades[1].points == 33  # (8025-8016) + (8040-8016)


class TestDoubleTakeProfitEntryValidity:
    """FR-G03 regression (PR #659 review #1): on a narrow H1 range an entry
    within max_entry_distance of the reference level can land past the TP1
    midpoint. Such an entry must be rejected. With H1 8000-8050 TP1 = 8025."""

    async def test_long_entry_past_the_midpoint_is_rejected(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8030, 7995, 8010),  # candidate, higher=8030
            m5_candle(2, 8020, 8035, 8015, 8025),  # breakout -> entry @8030
        ]
        result = await run_ger(candles)  # entry 8030 > TP1 8025 -> rejected
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_long_entry_below_the_midpoint_still_trades(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
            m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
            m5_candle(3, 8020, 8030, 8018, 8028),  # TP1 @8025
        ]
        result = await run_ger(candles)  # entry 8015 < TP1 8025 -> valid
        assert result.status == DayStatus.TRADED
        assert result.trades[0].entry_price == 8015

    async def test_short_entry_past_the_midpoint_is_rejected(self):
        candles = [
            m5_candle(0, 8045, 8060, 8040, 8055),  # breach above high
            m5_candle(1, 8050, 8055, 8020, 8040),  # candidate, lower=8020
            m5_candle(2, 8030, 8035, 8015, 8020),  # breakdown -> entry @8020
        ]
        result = await run_ger(candles)  # entry 8020 < TP1 8025 (past mid)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
