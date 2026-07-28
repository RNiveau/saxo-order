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

from api.services.backtest.side import Side
from model import Trade
from model.enum import ExitReason


@dataclass(frozen=True)
class Targets:
    """Where a lot model's take-profits sit for one side.

    `first` is TP1, the level the first lot exits at, or None for a single
    lot. `runner` is the level the last lot exits at - the ordinary
    take-profit for every model except the extended one, which sends the
    runner beyond it.
    """

    first: Optional[float]
    runner: float


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

    def targets(
        self,
        side: Side,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
    ) -> Targets:
        """Where this model's take-profits sit for `side`, given the
        strategy's ordinary take-profit level."""
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

    def targets(
        self,
        side: Side,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
    ) -> Targets:
        return Targets(first=None, runner=take_profit_level)


@dataclass(frozen=True)
class TwoLotAccounting:
    """What every two-lot model shares: how a position's points are summed
    and how the closed trade is classified.

    Before TP1 fills both lots exit together, so the leg counts twice -
    the "SL is x2" loss. After it, only the runner's leg is added to what
    the first lot banked (FR-G07). Because points no longer follow from
    the exit price, the trade is classified by the sign of its net points
    rather than by its exit reason (FR-G08).

    Subclasses differ only in where the two targets sit.
    """

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


@dataclass(frozen=True)
class TwoLot(TwoLotAccounting):
    """The GER40 double take-profit: the first lot exits a fraction of the
    way across the H1 range, the runner at the ordinary take-profit."""

    first_target_fraction: float

    def targets(
        self,
        side: Side,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
    ) -> Targets:
        # Direction-independent: the midpoint of the H1 range is the same
        # level for a long and a short, so `side` is ignored here.
        return Targets(
            first=h1_low + self.first_target_fraction * (h1_high - h1_low),
            runner=take_profit_level,
        )


@dataclass(frozen=True)
class ExtendedTwoLot(TwoLotAccounting):
    """Two lots whose first takes the *ordinary* take-profit and whose
    runner targets a fixed distance beyond it (FR-G26).

    The mirror image of TwoLot's split: instead of banking early inside
    the H1 range and running to its far end, this banks at the far end and
    sends the runner outside the range entirely. Points accounting and
    classification are identical, so both models share TwoLotAccounting -
    only where the two targets sit differs.
    """

    extension_points: float

    def targets(
        self,
        side: Side,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
    ) -> Targets:
        return Targets(
            first=take_profit_level,
            runner=take_profit_level + side.sign * self.extension_points,
        )


SINGLE_LOT = SingleLot()
