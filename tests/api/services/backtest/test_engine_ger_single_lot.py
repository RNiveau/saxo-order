"""G9HSL: the G9H setup with the 150-point stop still measured from the
H1 reference level, but a single lot and a single take-profit.

With H1 8000-8050 and a long entry at 8015: TP = 8040, stop = 7850,
break-even trigger = 8065. The H1 midpoint (8025) has no meaning here -
neither as an exit nor as an entry filter.
"""

from model.enum import DayStatus, Direction, ExitReason
from tests.api.services.backtest.helpers import (
    ger_entry_candles,
    m5_candle,
    run_ger,
    run_ger_single,
)


class TestEvaluateDayGerSingleLot:
    async def test_take_profit_is_a_single_leg(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8020, 8030, 8018, 8028),  # crosses 8025, no exit
            m5_candle(4, 8030, 8045, 8028, 8042),  # TP @8040
        ]
        result = await run_ger_single(candles)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.BUY
        assert trade.entry_price == 8015
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
        assert trade.points == 25  # 8040 - 8015, not 35

    async def test_stop_out_is_a_single_leg_from_the_h1_level(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8010, 8012, 7840, 7845),  # low <= stop 7850
        ]
        result = await run_ger_single(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7850  # h1_low - 150, not entry - 150
        assert trade.points == -165  # 7850 - 8015, half of G9H's -330

    async def test_midpoint_does_not_close_anything(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8020, 8030, 8018, 8028),  # reaches the midpoint 8025
            m5_candle(4, 8026, 8030, 8024, 8028),  # last candle, still open
        ]
        result = await run_ger_single(candles)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8028
        assert trade.points == 13  # 8028 - 8015, one lot, nothing banked

    async def test_break_even_still_armed_by_the_plus_50_trigger(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8020, 8070, 8018, 8065),  # high >= entry+50 -> arm BE
            m5_candle(4, 8060, 8062, 8010, 8012),  # low <= entry -> BE stop
        ]
        result = await run_ger_single(candles, higher=8200.0, lower=8000.0)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8015
        assert trade.points == 0

    async def test_short_mirror_take_profit(self):
        # Short off the H1 high: TP = 8010, stop = 8200 (h1_high + 150).
        candles = [
            m5_candle(0, 8045, 8060, 8040, 8055),  # breach above high
            m5_candle(1, 8050, 8055, 8035, 8040),  # candidate, lower=8035
            m5_candle(2, 8040, 8045, 8030, 8035),  # breakdown -> entry @8035
            m5_candle(3, 8034, 8038, 8020, 8024),  # crosses 8025, no exit
            m5_candle(4, 8020, 8024, 8005, 8008),  # TP @8010
        ]
        result = await run_ger_single(candles)
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8035
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8010
        assert trade.points == 25  # 8035 - 8010, not 35

    async def test_entry_past_the_midpoint_is_accepted_unlike_g9h(self):
        """The TP1 entry filter is a double-take-profit rule (FR-G02).
        Without it, an entry above the H1 midpoint - still within the
        max entry distance and below the take-profit - is valid, so
        G9HSL trades days G9H sits out."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach (close < h1_low)
            m5_candle(1, 8000, 8035, 7995, 8010),  # candidate, higher=8035
            m5_candle(2, 8010, 8036, 8005, 8030),  # breakout -> entry @8035
            m5_candle(3, 8036, 8045, 8034, 8042),  # TP @8040
        ]
        result = await run_ger_single(candles)
        assert result.status == DayStatus.TRADED
        trade = result.trades[0]
        assert trade.entry_price == 8035  # above the midpoint 8025
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.points == 5  # 8040 - 8035

        rejected = await run_ger(candles)
        assert rejected.status == DayStatus.NO_TRADE
