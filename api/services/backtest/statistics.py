"""Aggregation of a run's trades into a BacktestSummary."""

import datetime
from typing import List

from model import BacktestDefinition, BacktestSummary, Trade
from model.enum import ExitReason


def build_summary(
    definition: BacktestDefinition,
    start_date: datetime.date,
    end_date: datetime.date,
    trades: List[Trade],
    number_of_days: int,
) -> BacktestSummary:
    winning: List[Trade] = []
    losing: List[Trade] = []
    be_trades: List[Trade] = []
    for trade in trades:
        if definition.double_take_profit:
            # Two-lot positions are classified by the sign of their
            # net points (FR-G08): a TP1-then-break-even runner closes
            # BREAK_EVEN but banks a net gain, so it counts as a win;
            # only a genuinely flat position (net 0) is a break-even.
            if trade.points > 0:
                winning.append(trade)
            elif trade.points < 0:
                losing.append(trade)
            else:
                be_trades.append(trade)
        elif trade.exit_reason == ExitReason.BREAK_EVEN:
            be_trades.append(trade)
        elif trade.points > 0:
            winning.append(trade)
        else:
            losing.append(trade)

    average_win = (
        round(sum(t.points for t in winning) / len(winning), 4)
        if winning
        else None
    )
    average_loss = (
        round(-sum(t.points for t in losing) / len(losing), 4)
        if losing
        else None
    )
    final_result = round(sum(t.points for t in trades), 4)

    return BacktestSummary(
        definition_code=definition.code,
        start_date=start_date,
        end_date=end_date,
        number_of_days=number_of_days,
        number_of_trades=len(trades),
        number_of_winning_positions=len(winning),
        number_of_losing_positions=len(losing),
        number_of_be=len(be_trades),
        average_win=average_win,
        average_loss=average_loss,
        final_result=final_result,
    )
