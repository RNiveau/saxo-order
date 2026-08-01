"""The open position and how it turns into a closed Trade."""

import datetime
from typing import Optional

from api.services.backtest.lots import SINGLE_LOT, LotModel
from api.services.backtest.side import Side
from model import Trade
from model.enum import ExitReason
from utils.exception import SaxoException


class Position:
    """An open position on one side of the market.

    A session-range position is opened off the H1 range and carries it;
    a combo position is opened from an indicator signal and has no
    reference range at all, hence the optional h1_high/h1_low.

    Direction-dependent arithmetic is delegated to `self.side`, so nothing
    here branches on long vs short.
    """

    def __init__(
        self,
        entry_time: datetime.datetime,
        entry_price: float,
        side: Side,
        take_profit_level: float,
        stop_loss_points: float,
        h1_high: Optional[float] = None,
        h1_low: Optional[float] = None,
        lots: LotModel = SINGLE_LOT,
        first_target_level: Optional[float] = None,
        initial_stop_price: Optional[float] = None,
    ):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.side = side
        self.take_profit_level = take_profit_level
        self.stop_loss_points = stop_loss_points
        self.be_armed = False
        # Best favorable excursion so far, tracked by the time-cut policy.
        self.max_favorable_points = 0.0
        # first_target_level is TP1 (the H1 midpoint) for a two-lot
        # position; once the first lot fills, first_target_taken flips and
        # banked_points holds its realised P&L, which self.lots folds into
        # the runner's leg at close.
        self.lots = lots
        self.first_target_level = first_target_level
        self.first_target_taken = False
        self.banked_points = 0.0
        # Set by the TrailToFirstTarget policy once the runner has gained
        # its trigger beyond TP1: from then on TP1 is the runner's stop,
        # which is strictly better than the break-even it replaces.
        self.trailed_to_first_target = False
        # Absolute initial stop level. When set (GER40, stop measured from
        # the H1 reference level) it overrides the entry-relative stop; both
        # lots share it until break-even moves the stop to entry.
        self.initial_stop_price = initial_stop_price
        # The H1 reference levels, which the structural-stop policy
        # measures a close against. None on a combo position, which is
        # opened from an indicator signal and has no reference range.
        self.h1_high = h1_high
        self.h1_low = h1_low

    @property
    def structural_level(self) -> float:
        """The H1 level a structural stop watches for a close beyond: the
        low for a long, the high for a short.

        Raises when the position carries no reference range rather than
        inventing a level: only the structural and impulsive stops read
        this, and neither belongs to a strategy that has no such range.
        """
        if self.h1_high is None or self.h1_low is None:
            raise SaxoException(
                "this position has no H1 reference range, so no "
                "structural level - a close-measured stop cannot apply"
            )
        return self.side.reference_level(self.h1_high, self.h1_low)

    def retarget(
        self, first_target: Optional[float], take_profit: float
    ) -> None:
        """Move the position's two take-profit levels.

        The session-range strategies place their targets once, at entry.
        The combo strategy reads its targets - the mm20 and the opposite
        bollinger band - from the current candle, so it calls this on
        every candle before the exit chain runs, and DoubleTarget then
        works unchanged against levels that move.
        """
        self.first_target_level = first_target
        self.take_profit_level = take_profit

    @property
    def stop_level(self) -> float:
        if (
            self.trailed_to_first_target
            and self.first_target_level is not None
        ):
            return self.first_target_level
        if self.be_armed:
            return self.entry_price
        if self.initial_stop_price is not None:
            return self.initial_stop_price
        return self.entry_price - self.side.sign * self.stop_loss_points

    def break_even_arm_level(self, trigger_points: float) -> float:
        """The price that arms the break-even stop: entry plus the trigger
        in this side's favorable direction."""
        return self.entry_price + self.side.sign * trigger_points

    def close(
        self,
        exit_time: datetime.datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        """Close the position into a Trade.

        The lot model turns the final exit leg into net points, so for a
        two-lot position exit_price/exit_reason describe the runner's exit
        while points cover both lots - they need not agree.
        """
        points = self.lots.total_points(
            self.side.favorable(exit_price, self.entry_price),
            self.banked_points,
            self.first_target_taken,
        )
        return Trade(
            entry_time=self.entry_time,
            entry_price=self.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            direction=self.side.direction,
            points=round(points, 4),
        )
