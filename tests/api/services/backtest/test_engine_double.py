"""GER40 double take-profit / two-lot engine.

With H1 8000-8050: TP1 (midpoint) = 8025, TP2 (long) = 8040, stop (long)
= 7850, break-even trigger = entry + 50."""

from model.enum import DayStatus, Direction, ExitReason
from tests.api.services.backtest.helpers import (
    GER_DEFINITION,
    GER_PARAMS,
    TRADING_DATE,
    m5_candle,
    make_service,
    run_ger,
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
