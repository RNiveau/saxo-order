from api.services.backtest import build_summary
from model.enum import ExitReason
from tests.api.services.backtest.helpers import (
    DEFINITION,
    GER_DEFINITION,
    TRADING_DATE,
    closed_trade,
)


class TestBuildSummaryDoubleTakeProfit:
    """FR-G08: a two-lot position is classified by the sign of its net
    points, not by the runner's exit mechanism. A TP1-then-break-even
    runner closes BREAK_EVEN yet banks a net gain -> a winning position."""

    TRADES = [
        closed_trade(35, ExitReason.TAKE_PROFIT),  # full winner
        closed_trade(10, ExitReason.BREAK_EVEN),  # TP1 then BE -> win
        closed_trade(-330, ExitReason.STOP_LOSS),  # both lots stop -> loss
        closed_trade(0, ExitReason.BREAK_EVEN),  # genuinely flat -> BE
    ]

    def test_double_tp_classifies_by_net_points_sign(self):
        summary = build_summary(
            GER_DEFINITION,
            TRADING_DATE,
            TRADING_DATE,
            self.TRADES,
            number_of_days=4,
        )
        assert summary.number_of_trades == 4
        assert summary.number_of_winning_positions == 2  # 35 and 10
        assert summary.number_of_losing_positions == 1  # -330
        assert summary.number_of_be == 1  # the flat 0
        assert summary.average_win == 22.5  # (35 + 10) / 2
        assert summary.average_loss == 330.0
        assert summary.final_result == -285.0

    def test_non_double_definition_still_buckets_break_even_by_mechanism(self):
        summary = build_summary(
            DEFINITION,
            TRADING_DATE,
            TRADING_DATE,
            [closed_trade(10, ExitReason.BREAK_EVEN)],
            number_of_days=1,
        )
        assert summary.number_of_be == 1
        assert summary.number_of_winning_positions == 0


class TestBuildSummaryBasics:
    def test_empty_run_has_no_averages(self):
        summary = build_summary(
            DEFINITION, TRADING_DATE, TRADING_DATE, [], number_of_days=0
        )
        assert summary.number_of_trades == 0
        assert summary.average_win is None
        assert summary.average_loss is None
        assert summary.final_result == 0

    def test_definition_code_and_range_are_carried_through(self):
        summary = build_summary(
            DEFINITION,
            TRADING_DATE,
            TRADING_DATE,
            [closed_trade(5, ExitReason.TAKE_PROFIT)],
            number_of_days=1,
        )
        assert summary.definition_code == "B9H"
        assert summary.start_date == TRADING_DATE
        assert summary.end_date == TRADING_DATE
        assert summary.number_of_days == 1
