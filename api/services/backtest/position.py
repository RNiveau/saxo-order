"""The open position and how it turns into a closed Trade."""

import datetime
from typing import Optional

from api.services.backtest.side import Side
from model import Trade
from model.enum import ExitReason


class Position:
    """A position open on one side of the H1 range.

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
        time_cut_minutes: Optional[int] = None,
        time_cut_min_favorable_points: Optional[float] = None,
        double: bool = False,
        first_target_level: Optional[float] = None,
        initial_stop_price: Optional[float] = None,
        h1_high: Optional[float] = None,
        h1_low: Optional[float] = None,
        structural_stop: bool = False,
    ):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.side = side
        self.take_profit_level = take_profit_level
        self.stop_loss_points = stop_loss_points
        self.be_armed = False
        self.time_cut_minutes = time_cut_minutes
        self.time_cut_min_favorable_points = time_cut_min_favorable_points
        self.max_favorable_points = 0.0
        # Double take-profit / two-lot state (GER40). double gates the
        # split-exit path; first_target_level is TP1 (H1 midpoint); once
        # the first lot fills, first_target_taken flips and banked_points
        # holds lot A's realised P&L, added to the runner's leg at close.
        self.double = double
        self.first_target_level = first_target_level
        self.first_target_taken = False
        self.banked_points = 0.0
        # Absolute initial stop level. When set (GER40, stop measured from
        # the H1 reference level) it overrides the entry-relative stop; both
        # lots share it until break-even moves the stop to entry.
        self.initial_stop_price = initial_stop_price
        # Wide-range structural-stop variant (spec 021, US1d): the H1
        # reference levels and the flag enabling the close-beyond-level stop.
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.structural_stop = structural_stop

    @property
    def direction(self):
        return self.side.direction

    @property
    def is_long(self) -> bool:
        return self.side.is_long

    @property
    def time_cut_enabled(self) -> bool:
        return (
            self.time_cut_minutes is not None
            and self.time_cut_min_favorable_points is not None
        )

    @property
    def structural_level(self) -> Optional[float]:
        """The H1 level a structural stop watches for a close beyond: the
        low for a long, the high for a short."""
        if self.h1_high is None or self.h1_low is None:
            return None
        return self.side.reference_level(self.h1_high, self.h1_low)

    @property
    def stop_level(self) -> float:
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

        A two-lot (double take-profit) position aggregates both lots into
        one Trade whose points is their sum (FR-G07): before the first lot
        takes profit both exit at exit_price (2x the leg - the "SL is x2"
        loss); afterwards only the runner remains, added to the first lot's
        banked points. exit_price/exit_reason describe the runner's final
        exit, so points need not equal the exit leg here.
        """
        leg = self.side.favorable(exit_price, self.entry_price)
        if not self.double:
            points = leg
        elif self.first_target_taken:
            points = self.banked_points + leg
        else:
            points = 2 * leg
        return Trade(
            entry_time=self.entry_time,
            entry_price=self.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            direction=self.side.direction,
            points=round(points, 4),
        )
