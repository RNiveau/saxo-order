"""US1d: the wide-range structural-stop variant - a >40pt H1-range entry
filter (FR-033) and a structural stop that fires when a 5-minute candle
closes beyond the H1 level while break-even is unarmed (FR-034/FR-035)."""

from unittest.mock import MagicMock

from api.services.backtest import BacktestService
from model import UnitTime
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from tests.api.services.backtest.helpers import (
    NO_CACHE_CLIENT,
    TRADING_DATE,
    WIDE_RANGE_DEFINITION,
    h1_candle,
    m5_candle,
    make_service,
)


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
