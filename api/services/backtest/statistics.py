"""Aggregation of a run's trades into a BacktestSummary."""

import datetime
from typing import Dict, List

from api.services.backtest.lots import Outcome
from api.services.backtest.rules import build_lot_model
from model import BacktestDefinition, BacktestSummary, Trade


def build_summary(
    definition: BacktestDefinition,
    start_date: datetime.date,
    end_date: datetime.date,
    trades: List[Trade],
    number_of_days: int,
) -> BacktestSummary:
    """Bucket the run's trades into wins, losses and break-evens. How a
    trade is bucketed depends on the definition's position sizing, not on
    this module - see lots.LotModel.classify."""
    lots = build_lot_model(definition)
    buckets: Dict[Outcome, List[Trade]] = {
        Outcome.WIN: [],
        Outcome.LOSS: [],
        Outcome.BREAK_EVEN: [],
    }
    for trade in trades:
        buckets[lots.classify(trade)].append(trade)

    winning = buckets[Outcome.WIN]
    losing = buckets[Outcome.LOSS]

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

    return BacktestSummary(
        definition_code=definition.code,
        start_date=start_date,
        end_date=end_date,
        number_of_days=number_of_days,
        number_of_trades=len(trades),
        number_of_winning_positions=len(winning),
        number_of_losing_positions=len(losing),
        number_of_be=len(buckets[Outcome.BREAK_EVEN]),
        average_win=average_win,
        average_loss=average_loss,
        final_result=round(sum(t.points for t in trades), 4),
    )
