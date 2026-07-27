"""Range runs: day iteration, weekend skipping, summary aggregation and
the regime columns threaded onto each day."""

import datetime
from unittest.mock import MagicMock

from api.services.backtest import BacktestService
from model import DayResult, Trade
from model.enum import DayStatus, ExitReason
from services.candles_service import CandlesService
from tests.api.services.backtest.helpers import (
    DEFINITION,
    NO_CACHE_CLIENT,
    TRADING_DATE,
    h1_candle,
    make_service,
    stop_loss_candles,
    uptrend_daily_series,
)


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


class TestRunRangeThreadsRegime:
    async def test_mm50_slope_populated_on_summary(self):
        trading_date = datetime.date(2026, 6, 2)
        service = make_service([h1_candle()], stop_loss_candles())
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


class TestParameterFallback:
    """Omitting params must fall back to the *definition's* defaults, not
    to the BacktestParameters class defaults - a direct service call for
    GER40 would otherwise silently run on CAC40's 50/10/20/20."""

    async def test_evaluate_day_without_params_uses_definition_defaults(self):
        from tests.api.services.backtest.helpers import (
            GER_DEFINITION,
            stop_loss_candles,
        )

        service = make_service([h1_candle()], stop_loss_candles())
        result = await service.evaluate_day(GER_DEFINITION, TRADING_DATE)
        # GER40's 40pt entry window admits the 8015 entry that CAC40's
        # 20pt window also admits, but its 150pt stop is measured from the
        # H1 low (7850), so the 7950 candle does not stop it out.
        assert result.status == DayStatus.TRADED
        assert result.trades[0].exit_reason != ExitReason.STOP_LOSS

    async def test_run_range_without_params_uses_definition_defaults(self):
        from tests.api.services.backtest.helpers import GER_DEFINITION

        service = make_service([h1_candle()], [])
        explicit = await service.run_range(
            GER_DEFINITION,
            TRADING_DATE,
            TRADING_DATE,
            GER_DEFINITION.default_parameters,
        )
        implicit = await service.run_range(
            GER_DEFINITION, TRADING_DATE, TRADING_DATE
        )
        assert implicit == explicit
