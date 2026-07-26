"""Entry detection: the breakout/reversal search and the entry filter.

Both are written once against `Side` rather than twice, so the short rules
are the long rules with the sign flipped by construction.
"""

from typing import Optional

from api.services.backtest.side import Side
from model import Candle


def is_valid_entry(
    side: Side,
    entry_price: float,
    h1_high: float,
    h1_low: float,
    take_profit_level: float,
    max_entry_distance: float,
    first_target: Optional[float] = None,
) -> bool:
    """A breakout entry only produces a trade when it still leaves room to
    work: within max_entry_distance points of the H1 level it trades off,
    and short of the take-profit level. An entry too far from the level, or
    already at/past take-profit, is not valid - it would exit on the very
    next candle for little or no favorable move despite being labeled a
    take-profit.

    For a double take-profit setup, first_target (the H1 midpoint, TP1)
    must also sit strictly beyond the entry: on a narrow H1 range an
    otherwise-valid entry can open past the midpoint, which would fire TP1
    immediately, bank a loss as a take-profit, and discard the structural
    stop - so such an entry is rejected, mirroring the take-profit guard.
    """
    reference = side.reference_level(h1_high, h1_low)
    if side.favorable(entry_price, reference) > max_entry_distance:
        return False
    if side.favorable(entry_price, take_profit_level) >= 0:
        return False
    if (
        first_target is not None
        and side.favorable(entry_price, first_target) >= 0
    ):
        return False
    return True


class DirectionSearch:
    """Tracks the breakout/reversal candidate search for one direction
    while no position is open.

    A long watches for a candle closing below the H1 low, then a reversal
    candle closing back at/above it, confirmed by a later candle trading
    above that reversal candle's high. A short is the mirror around the H1
    high. The breach is measured on the close (a confirmed candle outside
    the H1 range), not an intrabar wick. Both directions are searched
    independently and concurrently; the engine enforces that only one may
    hold a position at a time.
    """

    def __init__(
        self,
        side: Side,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
        max_entry_distance: float,
        first_target_level: Optional[float] = None,
    ):
        self.side = side
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.take_profit_level = take_profit_level
        self.max_entry_distance = max_entry_distance
        # TP1 (H1 midpoint) for double take-profit definitions; None for
        # single-lot ones. When set, a valid entry must sit on the
        # favorable side of it (see is_valid_entry).
        self.first_target_level = first_target_level
        self.breached = False
        self.candidate: Optional[Candle] = None

    @property
    def reference(self) -> float:
        return self.side.reference_level(self.h1_high, self.h1_low)

    def reset(self) -> None:
        self.breached = False
        self.candidate = None

    def feed(self, candle: Candle) -> Optional[float]:
        """Advance the search by one candle. Returns a valid entry price
        when this candle confirms a tradeable breakout, otherwise None
        (updating the internal breach/candidate state)."""
        side = self.side
        if self.candidate is None:
            if not self.breached:
                if side.closed_beyond(self.reference, candle):
                    self.breached = True
                return None
            if not side.closed_beyond(self.reference, candle):
                self.candidate = candle
                self.breached = False
            return None

        # The candidate is the reversal candle awaiting confirmation: only
        # a later candle trading beyond its favorable extreme confirms the
        # reversal has momentum.
        confirmed = (
            side.favorable(side.extreme(candle), side.extreme(self.candidate))
            > 0
        )
        if confirmed:
            entry_price = side.worse(side.extreme(self.candidate), candle.open)
            self.candidate = None
            if is_valid_entry(
                side,
                entry_price,
                self.h1_high,
                self.h1_low,
                self.take_profit_level,
                self.max_entry_distance,
                self.first_target_level,
            ):
                return entry_price
            return None

        if side.closed_beyond(self.reference, candle):
            self.candidate = None
            self.breached = True
            return None
        self.candidate = candle
        return None
