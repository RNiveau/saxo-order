"""Direction-aware price arithmetic.

Every rule in the strategy has a long form and a short form that differ
only in which way the comparison points: a long is helped by price rising,
a short by price falling. `Side` carries that sign so each rule is written
once instead of twice, which is where most of the engine's duplication -
and most of its scope for a long/short asymmetry bug - used to live.

`favorable(price, reference)` is the single primitive: how many points
`price` sits in this side's favor relative to `reference`. Positive is
good for the position, negative is bad, in both directions.
"""

from dataclasses import dataclass

from model import Candle
from model.enum import Direction


@dataclass(frozen=True)
class Side:
    direction: Direction

    @property
    def is_long(self) -> bool:
        return self.direction == Direction.BUY

    @property
    def sign(self) -> int:
        return 1 if self.is_long else -1

    def favorable(self, price: float, reference: float) -> float:
        """Points `price` sits in this side's favor relative to
        `reference`: price - reference for a long, the negation for a
        short."""
        return (price - reference) * self.sign

    def reference_level(self, h1_high: float, h1_low: float) -> float:
        """The H1 level this side trades off: the low for a long (it buys
        the reversal off the bottom of the range), the high for a short."""
        return h1_low if self.is_long else h1_high

    def extreme(self, candle: Candle) -> float:
        """The candle's furthest price in this side's favor."""
        return candle.higher if self.is_long else candle.lower

    def adverse_extreme(self, candle: Candle) -> float:
        """The candle's furthest price against this side."""
        return candle.lower if self.is_long else candle.higher

    def worse(self, first: float, second: float) -> float:
        """The less favorable of two prices - used to pick a conservative
        entry fill."""
        return max(first, second) if self.is_long else min(first, second)

    def reached(self, level: float, candle: Candle) -> bool:
        """The candle traded at or beyond `level` in this side's favor
        (a take-profit-type touch)."""
        return self.favorable(self.extreme(candle), level) >= 0

    def receded(self, level: float, candle: Candle) -> bool:
        """The candle traded at or beyond `level` against this side (a
        stop-type touch)."""
        return self.favorable(self.adverse_extreme(candle), level) <= 0

    def closed_beyond(self, level: float, candle: Candle) -> bool:
        """The candle *closed* strictly on the losing side of `level` -
        a confirmed break, not an intrabar wick."""
        return self.favorable(candle.close, level) < 0

    def stop_fill(self, level: float, candle: Candle) -> float:
        """Fill for a stop-type exit: the candle open when it gapped
        adversely through the level, else the level itself (FR-010)."""
        if self.favorable(candle.open, level) <= 0:
            return candle.open
        return level

    def target_fill(self, level: float, candle: Candle) -> float:
        """Fill for a take-profit-type exit: the candle open when it
        gapped favorably through the level, else the level (FR-010)."""
        if self.favorable(candle.open, level) >= 0:
            return candle.open
        return level


LONG = Side(Direction.BUY)
SHORT = Side(Direction.SELL)
