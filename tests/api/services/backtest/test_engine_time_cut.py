"""The "Bougie de 9h (time cut)" variant: a position that has never moved
more than N points in its favor by M minutes after entry is closed at
market."""

from model.enum import Direction, ExitReason
from tests.api.services.backtest.helpers import (
    DEFINITION,
    TIME_CUT_DEFINITION,
    TRADING_DATE,
    h1_candle,
    m5_candle,
    make_service,
)


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
