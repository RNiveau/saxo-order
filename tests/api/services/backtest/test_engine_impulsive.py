"""The impulsive-candle variant (spec 025 addendum): no fixed stop at all,
only an impulsive candle against the position takes it out (FR-G14/FR-G15).

The H1 range here is 8000-8100 (the variant refuses anything at or under 70
points, FR-G17), so entries open long at 8015 off the 8000 low, the
take-profit sits at 8090 and break-even arms at 8065.
"""

from unittest.mock import MagicMock

from api.services.backtest import BacktestService
from model import UnitTime
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from tests.api.services.backtest.helpers import (
    GER_PARAMS,
    IMPULSIVE_DEFINITION,
    IMPULSIVE_H1_HIGH,
    NO_CACHE_CLIENT,
    TRADING_DATE,
    ger_entry_candles,
    h1_candle,
    m5_candle,
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
