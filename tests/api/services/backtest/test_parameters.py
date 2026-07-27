"""The four strategy thresholds are tunable via BacktestParameters;
omitting them reproduces the original hardcoded behavior."""

from model import BacktestParameters
from model.enum import DayStatus, ExitReason
from tests.api.services.backtest.helpers import (
    DEFINITION,
    TRADING_DATE,
    h1_candle,
    m5_candle,
    make_service,
    stop_loss_candles,
)


class TestBacktestParameters:
    """The four strategy thresholds are tunable via BacktestParameters;
    omitting them (or passing the default instance) reproduces the
    original hardcoded behavior exercised by TestEvaluateDayExits."""

    async def test_explicit_default_params_match_the_hardcoded_result(self):
        service = make_service([h1_candle()], stop_loss_candles())
        result = await service.evaluate_day(
            DEFINITION, TRADING_DATE, BacktestParameters()
        )
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7965
        assert trade.points == -50

    async def test_custom_stop_loss_points_tightens_the_stop(self):
        service = make_service([h1_candle()], stop_loss_candles())
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
        service = make_service([h1_candle()], stop_loss_candles())
        params = BacktestParameters(max_entry_distance_points=10)
        result = await service.evaluate_day(DEFINITION, TRADING_DATE, params)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
