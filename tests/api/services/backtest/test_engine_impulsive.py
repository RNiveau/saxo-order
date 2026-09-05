"""The impulsive-candle variant (spec 025 addendum): no fixed stop at all,
only an impulsive candle against the position takes it out (FR-G14/FR-G15).

The H1 range here is 8000-8100 (the variant refuses anything at or under 70
points, FR-G17), so entries open long at 8015 off the 8000 low, the
take-profit sits at 8090 and break-even arms at 8065.
"""

import datetime
from unittest.mock import MagicMock

from api.services.backtest import BacktestService
from model import UnitTime
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from tests.api.services.backtest.helpers import (
    GER_PARAMS,
    GER_SINGLE_LOT_DEFINITION,
    IMPULSIVE_DEFINITION,
    IMPULSIVE_H1_HIGH,
    NO_CACHE_CLIENT,
    TRADING_DATE,
    ger_entry_candles,
    h1_candle,
    m5_candle,
    make_service,
    run_ger_single,
    run_impulsive,
)


class TestNoFixedStop:
    """FR-G15: the fixed stop-loss distance does not apply at all."""

    # Falls to 7838 - below both a 150-point stop from the 8015 entry
    # (7865) and the G9HSL stop measured from the H1 low (7850) - in
    # candles that are each too narrow to be impulsive.
    DEEP_SLIDE = [
        m5_candle(3, 8010, 8015, 7960, 7965),  # range 55
        m5_candle(4, 7965, 7970, 7910, 7915),  # range 60
        m5_candle(5, 7915, 7920, 7860, 7865),  # range 60
        m5_candle(6, 7865, 7870, 7838, 7845),  # range 32
    ]

    async def test_an_adverse_slide_of_narrow_candles_never_stops_out(self):
        result = await run_impulsive(ger_entry_candles() + self.DEEP_SLIDE)

        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 7845.0
        assert trade.points == -170.0

    async def test_the_single_lot_variant_would_have_stopped_out(self):
        """The same candles under G9HSL, whose 150-point stop sits at the
        H1 low minus 150 - the contrast the variant exists to measure."""
        result = await run_ger_single(
            ger_entry_candles() + self.DEEP_SLIDE,
            higher=IMPULSIVE_H1_HIGH,
        )

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7850.0
        assert trade.points == -165.0


class TestImpulsiveStop:
    """FR-G14: amplitude, shape and a close beyond the H1 level, together."""

    async def test_an_impulsive_candle_closes_at_its_close(self):
        # range 77, closes 5 points off its low (inside the bottom 25% =
        # 19.25) and below the 8000 H1 low.
        impulse = m5_candle(3, 8010, 8012, 7935, 7940)

        result = await run_impulsive(ger_entry_candles() + [impulse])

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        # The candle's close, not a level - a market exit, so the gap-fill
        # convention does not apply.
        assert trade.exit_price == 7940.0
        assert trade.points == -75.0

    async def test_a_wide_candle_closing_mid_range_is_not_impulsive(self):
        # range 82, but the close sits 45 points off the low (the bottom
        # 25% ends at 20.5): a long wick that came back, not an impulse.
        wick = m5_candle(3, 8010, 8012, 7930, 7975)

        result = await run_impulsive(ger_entry_candles() + [wick])

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.points == -40.0

    async def test_a_sixty_nine_point_candle_is_not_impulsive(self):
        narrow = m5_candle(3, 8010, 8012, 7943, 7948)

        result = await run_impulsive(ger_entry_candles() + [narrow])

        assert result.trades[0].exit_reason == ExitReason.END_OF_DAY

    async def test_exactly_seventy_points_is_impulsive(self):
        boundary = m5_candle(3, 8010, 8012, 7942, 7947)

        result = await run_impulsive(ger_entry_candles() + [boundary])

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7947.0

    async def test_a_candle_not_closing_beyond_the_h1_level_is_not_a_stop(
        self,
    ):
        # range 75, closes 3 points off its low - but at 8003, still inside
        # the H1 range, so the break is not confirmed.
        inside = m5_candle(3, 8010, 8075, 8000, 8003)

        result = await run_impulsive(ger_entry_candles() + [inside])

        assert result.trades[0].exit_reason == ExitReason.END_OF_DAY

    async def test_an_impulsive_candle_in_our_favor_does_not_close_a_long(
        self,
    ):
        # range 80 closing 5 points off its high: violent, but upward.
        favorable = m5_candle(3, 8015, 8060, 7980, 8055)

        result = await run_impulsive(ger_entry_candles() + [favorable])

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.points == 40.0


class TestPrecedence:
    """FR-G16: what wins when an impulse coincides with something else."""

    async def test_the_take_profit_wins_on_the_same_candle(self):
        # Reaches 8090 (the take-profit) intrabar and also closes below the
        # H1 low on a 95-point range - the target is touched first in real
        # time, so it wins.
        both = m5_candle(3, 8015, 8090, 7995, 7998)

        result = await run_impulsive(ger_entry_candles() + [both])

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8090.0
        assert trade.points == 75.0

    async def test_an_armed_break_even_stop_wins_over_an_impulse(self):
        candles = ger_entry_candles() + [
            # High of 8070 reaches entry + 50 (8065) and arms break-even.
            m5_candle(3, 8015, 8070, 8010, 8060),
            # Impulsive and below the H1 low - but the position now has a
            # real stop at entry, which leads the chain.
            m5_candle(4, 8060, 8062, 7985, 7990),
        ]

        result = await run_impulsive(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015.0
        assert trade.points == 0.0


class TestShortMirror:
    """FR-G14 mirrored: a short is stopped by a wide candle closing near
    its *high*, above the H1 high."""

    def _short_entry_candles(self):
        return [
            m5_candle(0, 8095, 8110, 8090, 8105),  # breach above 8100
            m5_candle(1, 8105, 8108, 8085, 8095),  # candidate, lower=8085
            m5_candle(2, 8090, 8095, 8080, 8085),  # breakout -> entry @8085
        ]

    async def test_a_short_is_stopped_by_an_upward_impulse(self):
        # range 77, closes 5 points off its high and above the 8100 H1 high.
        impulse = m5_candle(3, 8090, 8175, 8098, 8170)

        result = await run_impulsive(self._short_entry_candles() + [impulse])

        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8085.0
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 8170.0
        assert trade.points == -85.0

    async def test_a_short_survives_a_downward_impulse(self):
        # The same amplitude in the short's favor: it closes near the low,
        # so it is not adverse - and it reaches the 8010 take-profit.
        favorable = m5_candle(3, 8080, 8082, 8005, 8008)

        result = await run_impulsive(self._short_entry_candles() + [favorable])

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8010.0
        assert trade.points == 75.0


class TestMinimumRange:
    """FR-G17: days whose H1 range is not strictly greater than 70 points
    are not traded, and their 5-minute candles are never fetched."""

    def _service(self, h1_high):
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [h1_candle(higher=h1_high, lower=8000.0)]
            return ger_entry_candles() + [m5_candle(3, 8010, 8012, 7935, 7940)]

        candles_service.get_candles_in_window.side_effect = side_effect
        return candles_service

    async def _run(self, h1_high):
        candles_service = self._service(h1_high)
        service = BacktestService(candles_service, NO_CACHE_CLIENT)
        result = await service.evaluate_day(
            IMPULSIVE_DEFINITION, TRADING_DATE, GER_PARAMS
        )
        return result, candles_service

    async def test_a_seventy_point_range_is_not_traded(self):
        result, candles_service = await self._run(8070.0)

        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
        assert candles_service.get_candles_in_window.call_count == 1

    async def test_a_seventy_one_point_range_is_traded(self):
        result, candles_service = await self._run(8071.0)

        assert result.status == DayStatus.TRADED
        assert candles_service.get_candles_in_window.call_count == 2


class TestCfdSession:
    """FR-G12: the variant scans to 22:00 Paris, not the 17:30 cash close.

    m5_candle(n) is 08:00 UTC + 5n minutes, i.e. 10:00 Paris + 5n in
    summer, so offset 90 is exactly the 17:30 cash close and offset 143 is
    the last 5-minute candle of the CFD session (21:55 Paris).
    """

    CASH_CLOSE_OFFSET = 90
    LAST_CFD_OFFSET = 143

    async def test_a_position_runs_past_the_cash_close_to_a_22h_exit(self):
        candles = ger_entry_candles() + [
            # inside the cash session, then after it
            m5_candle(self.CASH_CLOSE_OFFSET - 30, 8015, 8020, 8010, 8018),
            m5_candle(self.CASH_CLOSE_OFFSET + 10, 8018, 8022, 8012, 8020),
            m5_candle(self.LAST_CFD_OFFSET, 8020, 8026, 8016, 8024),
        ]

        result = await run_impulsive(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8024.0
        # 08:00 UTC + 143 * 5 minutes = 19:55 UTC = 21:55 Paris (summer).
        assert trade.exit_time == datetime.datetime(2026, 6, 2, 19, 55)
        assert trade.points == 9.0

    async def test_an_evening_impulse_still_stops_the_position(self):
        """The candles after the cash close are evaluated, not merely
        carried: an impulse at 20:30 Paris closes the position."""
        candles = ger_entry_candles() + [
            m5_candle(self.CASH_CLOSE_OFFSET - 30, 8015, 8020, 8010, 8018),
            # impulsive, 36 candles past the cash close: 20:30 Paris
            m5_candle(self.CASH_CLOSE_OFFSET + 36, 8010, 8012, 7935, 7940),
            m5_candle(self.LAST_CFD_OFFSET, 7940, 7945, 7935, 7942),
        ]

        result = await run_impulsive(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7940.0
        assert trade.exit_time == datetime.datetime(2026, 6, 2, 18, 30)


class TestSessionFetchWindow:
    """The window actually requested from Saxo - the golden fixture is
    market-agnostic, so without this nothing checks that the definition's
    market reaches the fetch."""

    async def _fetch_bounds(self, definition):
        service = make_service([h1_candle(higher=IMPULSIVE_H1_HIGH)], [])
        await service.evaluate_day(definition, TRADING_DATE, GER_PARAMS)
        fetches = service.candles_service.get_candles_in_window.mock_calls
        m5_call = [call for call in fetches if call.args[1] == UnitTime.M5][0]
        return m5_call.args[3], m5_call.args[4]

    async def test_the_impulsive_variant_scans_to_22h_paris(self):
        start, end = await self._fetch_bounds(IMPULSIVE_DEFINITION)

        assert start == datetime.datetime(2026, 6, 2, 8, 0)
        assert end == datetime.datetime(2026, 6, 2, 20, 0)

    async def test_a_cash_definition_still_stops_at_the_17h30_close(self):
        start, end = await self._fetch_bounds(GER_SINGLE_LOT_DEFINITION)

        assert start == datetime.datetime(2026, 6, 2, 8, 0)
        assert end == datetime.datetime(2026, 6, 2, 15, 30)


def entry_sequence(base):
    """The breach / candidate / breakout trio that opens a long at 8015,
    placed so the *breakout* candle (the one the entry is timed at) starts
    at offset `base`."""
    return [
        m5_candle(base - 2, 8005, 8010, 7990, 7995),
        m5_candle(base - 1, 8000, 8015, 7995, 8010),
        m5_candle(base, 8010, 8020, 8005, 8015),
    ]


class TestEntryCutoff:
    """FR-G19: no position opened at or after 16:00 Paris.

    m5_candle(n) is 08:00 UTC + 5n, and 16:00 Paris is 14:00 UTC in
    summer, so offset 72 is exactly the cut-off and 71 is the last candle
    that may open.
    """

    CUTOFF_OFFSET = 72

    async def test_a_breakout_confirming_at_1555_still_opens(self):
        candles = entry_sequence(self.CUTOFF_OFFSET - 1) + [
            m5_candle(143, 8015, 8030, 8010, 8025),
        ]

        result = await run_impulsive(candles)

        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        assert result.trades[0].entry_time == datetime.datetime(
            2026, 6, 2, 13, 55
        )

    async def test_the_same_breakout_at_1600_does_not(self):
        candles = entry_sequence(self.CUTOFF_OFFSET) + [
            m5_candle(143, 8015, 8030, 8010, 8025),
        ]

        result = await run_impulsive(candles)

        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_nothing_opens_later_in_the_evening_either(self):
        candles = entry_sequence(120) + [
            m5_candle(143, 8015, 8030, 8010, 8025),
        ]

        result = await run_impulsive(candles)

        assert result.trades == []

    async def test_a_position_opened_at_1555_still_runs_to_22h(self):
        """The cut-off blocks opening, never closing (FR-G21)."""
        candles = entry_sequence(self.CUTOFF_OFFSET - 1) + [
            m5_candle(100, 8015, 8020, 8010, 8018),
            m5_candle(143, 8018, 8026, 8016, 8024),
        ]

        result = await run_impulsive(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_time == datetime.datetime(2026, 6, 2, 19, 55)
        assert trade.points == 9.0


class TestDailyLossCap:
    """FR-G20: no new position once two have closed at a loss."""

    def _losing_cycle(self, base):
        """Enter long at 8015 on offset `base`, stopped by an impulsive
        candle on the next one for -75."""
        return entry_sequence(base) + [
            m5_candle(base + 1, 8010, 8012, 7935, 7940)
        ]

    def _winning_cycle(self, base):
        """The same entry, taken to the 8090 take-profit for +75."""
        return entry_sequence(base) + [
            m5_candle(base + 1, 8020, 8090, 8015, 8085)
        ]

    async def test_the_third_setup_after_two_losses_is_refused(self):
        candles = (
            self._losing_cycle(2)
            + self._losing_cycle(6)
            + self._losing_cycle(10)
        )

        result = await run_impulsive(candles)

        assert len(result.trades) == 2
        assert [trade.points for trade in result.trades] == [-75.0, -75.0]

    async def test_a_win_between_two_losses_leaves_the_gate_open(self):
        """Proves the third cycle *would* have traded - the cap counts
        losses, not trades."""
        candles = (
            self._losing_cycle(2)
            + self._winning_cycle(6)
            + self._losing_cycle(10)
        )

        result = await run_impulsive(candles)

        assert len(result.trades) == 3
        assert [trade.points for trade in result.trades] == [
            -75.0,
            75.0,
            -75.0,
        ]

    async def test_the_cap_holds_for_the_rest_of_the_day(self):
        candles = (
            self._losing_cycle(2)
            + self._losing_cycle(6)
            + self._winning_cycle(10)
            + self._winning_cycle(20)
        )

        result = await run_impulsive(candles)

        assert len(result.trades) == 2
