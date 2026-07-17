import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from api.services.backtest_service import (
    BacktestService,
    is_future_paris_date,
    is_today_not_yet_closed,
    paris_reference_window_utc,
    paris_session_end_utc,
)
from model import BacktestDefinition, Candle, DayResult, Trade, UnitTime
from model.enum import DayStatus, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException

PARIS_TZ = ZoneInfo("Europe/Paris")

DEFINITION = BacktestDefinition(
    code="B9H",
    name="Bougie de 9h",
    display_name="CAC40 Bougie de 9h",
    instrument="FRA40.I",
)
TRADING_DATE = datetime.date(2026, 6, 2)

H1_HIGH = 8050.0
H1_LOW = 8000.0


def h1_candle(higher=H1_HIGH, lower=H1_LOW):
    return Candle(
        lower=lower,
        higher=higher,
        open=8020.0,
        close=8030.0,
        ut=UnitTime.H1,
        date=datetime.datetime(2026, 6, 2, 7, 0),
    )


def m5_candle(minute_offset, open, higher, lower, close):
    return Candle(
        lower=lower,
        higher=higher,
        open=open,
        close=close,
        ut=UnitTime.M5,
        date=datetime.datetime(2026, 6, 2, 8, 0)
        + datetime.timedelta(minutes=5 * minute_offset),
    )


def make_service(h1_candles, m5_candles, raise_on_h1=False, raise_on_m5=False):
    candles_service = MagicMock(spec=CandlesService)

    def side_effect(code, ut, horizon, start, end):
        if ut == UnitTime.H1:
            if raise_on_h1:
                raise SaxoException("boom")
            return h1_candles
        if raise_on_m5:
            raise SaxoException("boom")
        return m5_candles

    candles_service.get_candles_in_window.side_effect = side_effect
    return BacktestService(candles_service)


class TestTimezoneHelpers:
    def test_reference_window_cest_summer(self):
        start, end = paris_reference_window_utc(datetime.date(2026, 6, 2))
        assert start == datetime.datetime(2026, 6, 2, 7, 0)
        assert end == datetime.datetime(2026, 6, 2, 8, 0)

    def test_reference_window_cet_winter(self):
        start, end = paris_reference_window_utc(datetime.date(2026, 1, 15))
        assert start == datetime.datetime(2026, 1, 15, 8, 0)
        assert end == datetime.datetime(2026, 1, 15, 9, 0)

    def test_session_end_cest_summer(self):
        assert paris_session_end_utc(
            datetime.date(2026, 6, 2)
        ) == datetime.datetime(2026, 6, 2, 15, 30)

    def test_session_end_cet_winter(self):
        assert paris_session_end_utc(
            datetime.date(2026, 1, 15)
        ) == datetime.datetime(2026, 1, 15, 16, 30)

    def test_is_future_paris_date(self):
        now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=PARIS_TZ)
        assert is_future_paris_date(datetime.date(2026, 6, 3), now=now)
        assert not is_future_paris_date(datetime.date(2026, 6, 2), now=now)
        assert not is_future_paris_date(datetime.date(2026, 6, 1), now=now)

    def test_today_before_session_close_is_not_yet_closed(self):
        now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=PARIS_TZ)
        assert is_today_not_yet_closed(datetime.date(2026, 6, 2), now=now)

    def test_today_after_session_close_is_closed(self):
        now = datetime.datetime(2026, 6, 2, 18, 0, tzinfo=PARIS_TZ)
        assert not is_today_not_yet_closed(datetime.date(2026, 6, 2), now=now)

    def test_other_day_is_never_not_yet_closed(self):
        now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=PARIS_TZ)
        assert not is_today_not_yet_closed(datetime.date(2026, 6, 1), now=now)
        assert not is_today_not_yet_closed(datetime.date(2026, 6, 3), now=now)


class TestEvaluateDayNoData:
    def test_missing_h1_candle_returns_no_data(self):
        service = make_service(h1_candles=[], m5_candles=[])
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_DATA
        assert result.trades == []
        assert result.h1_high is None
        assert result.h1_low is None

    def test_h1_fetch_raising_returns_no_data(self):
        service = make_service(h1_candles=[], m5_candles=[], raise_on_h1=True)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_DATA

    def test_m5_fetch_raising_returns_no_trade(self):
        """If the H1 reference is available but the 5-minute fetch
        fails, the day is a NO_TRADE (not NO_DATA, which is reserved
        for a missing H1 reference per FR-004)."""
        service = make_service([h1_candle()], m5_candles=[], raise_on_m5=True)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW


class TestListAndGetDefinition:
    def test_list_definitions_returns_the_hardcoded_backtest(self):
        service = make_service([], [])
        definitions = service.list_definitions()
        assert len(definitions) == 1
        assert definitions[0].code == "B9H"
        assert definitions[0].display_name == "CAC40 Bougie de 9h"
        assert definitions[0].instrument == "FRA40.I"

    def test_get_definition_found(self):
        service = make_service([], [])
        assert service.get_definition("B9H") is not None

    def test_get_definition_not_found(self):
        service = make_service([], [])
        assert service.get_definition("NOPE") is None


class TestEvaluateDayNoTrade:
    def test_no_breakout_below_h1_low(self):
        candles = [
            m5_candle(0, 8010, 8020, 8005, 8015),
            m5_candle(1, 8015, 8025, 8010, 8020),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW

    def test_breakdown_without_confirmed_reversal(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach, no close-back
            m5_candle(1, 7995, 8000, 7985, 7990),  # still below h1_low
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []


class TestEvaluateDayCandleOrdering:
    def test_day_result_candles_are_chronological_even_if_fetched_reversed(
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
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert [c.date for c in result.candles] == [
            c.date for c in chronological_candles
        ]


class TestEvaluateDayExits:
    def test_stop_loss_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # confirm -> entry @8010
            m5_candle(2, 8005, 8010, 7950, 7955),  # SL: low<=7960, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8010
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7960
        assert trade.points == -50

    def test_stop_loss_exit_with_gap(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 7900, 7910, 7850, 7880),  # gap below 7960
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7900
        assert trade.points == -110

    def test_take_profit_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8020, 8045, 8015, 8035),  # TP: high>=8040, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
        assert trade.points == 30

    def test_end_of_day_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8012, 8020, 8005, 8015),  # last candle of the day
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8015
        assert trade.points == 5

    def test_entry_on_last_candle_produces_zero_point_end_of_day(self):
        """A signal that only confirms on the session's final 5-minute
        candle opens and immediately closes (end of day) on that same
        candle, since there is no further candle to evaluate -- the
        trade never had a chance to move, so points is exactly 0."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010, also last
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8010
        assert trade.exit_price == 8010
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.points == 0

    def test_break_even_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8015, 8035, 8005, 8020),  # arms BE (>=8030)
            m5_candle(3, 8020, 8025, 8005, 8000),  # BE exit: low<=8010
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8010
        assert trade.points == 0

    def test_break_even_exit_with_gap_is_not_exactly_zero(self):
        """FR-010's gap-fill rule applies uniformly to all exit types,
        including break-even (resolved explicitly after PR review):
        a candle that opens below the (now break-even) stop records
        that open price, so the trade's points can be a small
        non-zero value even though it is still labeled BREAK_EVEN."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8015, 8035, 8005, 8020),  # arms BE (>=8030)
            m5_candle(3, 8005, 8008, 7995, 8000),  # gap: open 8005 < 8010
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8005
        assert trade.points == -5

    def test_multi_trade_day_reentry(self):
        candles = [
            # Trade 1: breach -> entry @8010 -> stop-loss
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),
            m5_candle(2, 8005, 8010, 7950, 7955),
            # Trade 2: fresh breach -> entry -> end of day
            m5_candle(3, 7950, 7960, 7930, 7935),
            m5_candle(4, 7940, 8005, 7935, 8005),
            m5_candle(5, 8010, 8020, 8000, 8015),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 2
        assert result.trades[0].exit_reason == ExitReason.STOP_LOSS
        assert result.trades[1].entry_price == 8005
        assert result.trades[1].exit_reason == ExitReason.END_OF_DAY
        assert result.trades[1].exit_price == 8015


class TestEvaluateDaySameCandleEdgeCases:
    def test_stop_loss_priority_over_same_candle_be_arm(self):
        """A candle that would both breach the original stop-loss and
        reach the +20pt break-even-arm threshold resolves as a
        stop-loss using the pre-candle level, not a break-even arm."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            # low breaches original stop (7960) AND high reaches +20 (8030)
            m5_candle(2, 8005, 8035, 7950, 8000),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7960

    def test_arm_and_breach_round_trip_does_not_exit_same_candle(self):
        """A candle whose high reaches the +20pt arm threshold and whose
        low would also breach the not-yet-armed break-even level (but
        not the original stop) must not itself produce a break-even
        exit -- arming only takes effect on the next candle."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            # high reaches +20 (8030->8035) AND low dips to 8005 (<=entry
            # 8010, but > original stop 7960 -- no exit this candle)
            m5_candle(2, 8015, 8035, 8005, 8020),
            # now armed: low breaches the new stop (8010)
            m5_candle(3, 8020, 8025, 8005, 8000),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8010
        assert trade.exit_time == candles[3].date


class TestIsValidEntry:
    """Direct unit tests for the entry-validity rule added after PR
    review: a breakout-reversal close only produces a trade when it is
    within MAX_ENTRY_DISTANCE_FROM_LOW points of the H1 low and still
    below the take-profit level."""

    def test_within_distance_and_below_tp_is_valid(self):
        assert BacktestService._is_valid_entry(8010, 8000, 8040) is True

    def test_exactly_at_max_distance_is_valid(self):
        assert BacktestService._is_valid_entry(8020, 8000, 8040) is True

    def test_beyond_max_distance_is_invalid(self):
        assert BacktestService._is_valid_entry(8021, 8000, 8040) is False

    def test_at_take_profit_level_is_invalid(self):
        assert BacktestService._is_valid_entry(8015, 8005, 8015) is False

    def test_above_take_profit_level_is_invalid(self):
        assert BacktestService._is_valid_entry(8016, 8005, 8015) is False

    def test_just_below_take_profit_level_is_valid(self):
        assert BacktestService._is_valid_entry(8014, 8005, 8015) is True


class TestEvaluateDayEntryValidityRule:
    def test_entry_too_far_above_h1_low_is_rejected(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            # close back above h1_low, but 25pts away (> 20pt max)
            m5_candle(1, 8015, 8030, 8005, 8025),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    def test_entry_at_or_above_take_profit_is_rejected(self):
        h1 = h1_candle(higher=8025, lower=8005)  # take_profit_level = 8015
        candles = [
            m5_candle(0, 8010, 8015, 7995, 8000),  # breach
            # close back within 20pts of the low, but at/above TP (8018)
            m5_candle(1, 8010, 8020, 8005, 8018),
        ]
        service = make_service([h1], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    def test_rejected_entry_still_allows_a_fresh_signal_afterwards(self):
        """After an invalid entry, the breach flag resets so a later,
        independent breach/close-back pair can still produce a valid
        trade the same day."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach 1
            m5_candle(1, 8015, 8030, 8005, 8025),  # invalid close-back
            m5_candle(2, 8010, 8015, 7995, 7998),  # breach 2
            m5_candle(3, 8000, 8015, 7995, 8010),  # valid close-back @8010
            m5_candle(4, 8012, 8020, 8005, 8015),  # end of day
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8010
        assert trade.exit_reason == ExitReason.END_OF_DAY


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
    def test_aggregates_across_days_and_excludes_no_data(self, mocker):
        service = BacktestService(MagicMock(spec=CandlesService))
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
            service, "evaluate_day", side_effect=lambda d, date: results[date]
        )

        result = service.run_range(DEFINITION, day1, day3)

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

    def test_weekends_are_skipped_without_calling_evaluate_day(self, mocker):
        """Saturday/Sunday never trade, so run_range must not spend a
        fetch resolving them to NO_DATA - it should skip evaluate_day
        for those dates entirely."""
        service = BacktestService(MagicMock(spec=CandlesService))
        friday = datetime.date(2026, 6, 5)
        monday = datetime.date(2026, 6, 8)
        evaluate_day = mocker.patch.object(
            service,
            "evaluate_day",
            side_effect=lambda d, date: DayResult(
                date=date, status=DayStatus.NO_TRADE, h1_high=8050, h1_low=8000
            ),
        )

        result = service.run_range(DEFINITION, friday, monday)

        called_dates = [call.args[1] for call in evaluate_day.call_args_list]
        assert called_dates == [friday, monday]
        assert result.summary.number_of_days == 2

    def test_empty_range_returns_all_zero_summary(self, mocker):
        service = BacktestService(MagicMock(spec=CandlesService))
        day = datetime.date(2026, 6, 2)
        mocker.patch.object(
            service,
            "evaluate_day",
            return_value=DayResult(
                date=day, status=DayStatus.NO_TRADE, h1_high=8050, h1_low=8000
            ),
        )

        result = service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_days == 1
        assert result.summary.number_of_trades == 0
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 0
        assert result.summary.number_of_be == 0
        assert result.summary.average_win is None
        assert result.summary.average_loss is None
        assert result.summary.final_result == 0

    def test_zero_point_non_be_trade_counts_as_losing(self, mocker):
        """A trade with points == 0 that did NOT close via the
        break-even mechanism (e.g. an end-of-day close landing exactly
        on the entry price) counts as a losing position, not a win or
        a BE (per spec.md Assumptions)."""
        service = BacktestService(MagicMock(spec=CandlesService))
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

        result = service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_trades == 1
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 1
        assert result.summary.number_of_be == 0

    def test_gapped_be_trade_stays_be_not_losing(self, mocker):
        """A BREAK_EVEN trade with non-zero points (gap-through, see
        evaluate_day's gap test) is still classified as BE, not as a
        loss, and its points are excluded from average_loss - only
        final_result reflects the actual value (resolved explicitly
        after PR review, see spec.md Assumptions)."""
        service = BacktestService(MagicMock(spec=CandlesService))
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

        result = service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_trades == 1
        assert result.summary.number_of_be == 1
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 0
        assert result.summary.average_loss is None
        assert result.summary.final_result == -5

    def test_zero_point_end_of_day_trade_counts_as_losing(self, mocker):
        """A non-BE trade that closes at exactly 0 points (e.g. entry
        confirmed on the session's last candle, see evaluate_day's
        same-candle EOD test) is classified as a losing position, not a
        win or a BE - only break-even-mechanism exits get the "BE"
        label (documented in spec.md Assumptions)."""
        service = BacktestService(MagicMock(spec=CandlesService))
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

        result = service.run_range(DEFINITION, day, day)

        assert result.summary.number_of_trades == 1
        assert result.summary.number_of_be == 0
        assert result.summary.number_of_winning_positions == 0
        assert result.summary.number_of_losing_positions == 1
        assert result.summary.average_loss == 0
        assert result.summary.final_result == 0
