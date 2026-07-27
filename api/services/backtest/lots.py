"""How many lots a position opens, and what that means downstream.

Position sizing is not just an exit detail: it changes how a closed
position's points are computed *and* how the run summary classifies it. A
two-lot position that banks TP1 and then trails back to break-even closes
with a BREAK_EVEN reason while netting a gain, so classifying it by its
exit mechanism would file a winner as a break-even (FR-G08).

Keeping both rules on the same object is what lets the engine and the
statistics stay ignorant of which backtest they are running.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from model import Trade
from model.enum import ExitReason


class Outcome(Enum):
    WIN = "win"
    LOSS = "loss"
    BREAK_EVEN = "break_even"


class LotModel(Protocol):
    def total_points(
        self, exit_leg: float, banked_points: float, first_target_taken: bool
    ) -> float:
        """The position's net points from its final exit leg (points in
        the position's favor) plus anything already banked."""
        ...

    def classify(self, trade: Trade) -> Outcome:
        """Which bucket this closed trade counts in."""
        ...

    def first_target_level(
        self, h1_high: float, h1_low: float
    ) -> Optional[float]:
        """TP1, where the first lot exits, or None for a single lot."""
        ...


@dataclass(frozen=True)
class SingleLot:
    """One lot in, one lot out: net points are the exit leg, and a
    break-even exit is a break-even by mechanism."""

    def total_points(
        self, exit_leg: float, banked_points: float, first_target_taken: bool
    ) -> float:
        return exit_leg

    def classify(self, trade: Trade) -> Outcome:
        if trade.exit_reason == ExitReason.BREAK_EVEN:
            return Outcome.BREAK_EVEN
        return Outcome.WIN if trade.points > 0 else Outcome.LOSS

    def first_target_level(
        self, h1_high: float, h1_low: float
    ) -> Optional[float]:
        return None


@dataclass(frozen=True)
class TwoLot:
    """Two lots in: the first exits at TP1 (a fraction of the way across
    the H1 range), the runner at the full target or its break-even stop.

    Before TP1 fills both lots exit together, so the leg counts twice -
    the "SL is x2" loss. After it, only the runner's leg is added to what
    the first lot banked (FR-G07). Because points no longer follow from
    the exit price, the trade is classified by the sign of its net points
    rather than by its exit reason (FR-G08).
    """

    first_target_fraction: float

    def total_points(
        self, exit_leg: float, banked_points: float, first_target_taken: bool
    ) -> float:
        if first_target_taken:
            return banked_points + exit_leg
        return 2 * exit_leg

    def classify(self, trade: Trade) -> Outcome:
        if trade.points > 0:
            return Outcome.WIN
        if trade.points < 0:
            return Outcome.LOSS
        return Outcome.BREAK_EVEN

    def first_target_level(
        self, h1_high: float, h1_low: float
    ) -> Optional[float]:
        return h1_low + self.first_target_fraction * (h1_high - h1_low)


SINGLE_LOT = SingleLot()
