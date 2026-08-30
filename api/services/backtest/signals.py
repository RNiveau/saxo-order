"""Turning combo signals into entries (FR-C02/FR-C03/FR-C04).

The indicator answers "is there a combo here?" per candle. Two things
still have to happen before a position exists: weak signals are dropped,
and an untriggered signal becomes a stop order that a *later* candle has
to trade through. This module is that gap, and nothing else - where the
stop goes and whether the entry is worth taking belong to the strategy.
"""

from dataclasses import dataclass
from typing import List, Optional

from api.services.backtest.side import LONG, SHORT, Side
from model import Candle
from model.enum import Direction
from model.workflow import SignalStrength
from services.indicator_service import combo

# WEAK is a signal that scored zero criteria. It is still a combo, but
# not one this backtest trades (FR-C02).
TRADED_STRENGTHS = (SignalStrength.MEDIUM, SignalStrength.STRONG)


@dataclass(frozen=True)
class PendingEntry:
    """An untriggered signal's stop level, waiting for the next candle.

    `signal_candle` is kept because the stop is measured from the candle
    the indicator fired on, not from the candle that fills the order
    (FR-C06) - and on a pending entry those are never the same candle.
    """

    level: float
    side: Side
    signal_candle: Candle


@dataclass(frozen=True)
class Entry:
    price: float
    side: Side
    signal_candle: Candle


def _side_for(direction: Direction) -> Side:
    return LONG if direction == Direction.BUY else SHORT


class ComboEntrySearch:
    """Carries at most one pending entry between candles.

    Order matters and is the whole content of `feed`: a pending level
    from the previous candle is resolved *before* this candle's own
    signal is evaluated. A candle that fills yesterday's order opens the
    position, and its own signal is then ignored by the one-position rule
    (FR-C09) rather than by anything here.
    """

    def __init__(self) -> None:
        self.pending: Optional[PendingEntry] = None

    def reset(self) -> None:
        self.pending = None

    def feed(self, candle: Candle, window: List[Candle]) -> Optional[Entry]:
        """Advance the search by one candle, `window` being the
        newest-first series ending at it. Returns an entry when this
        candle opens one."""
        filled = self._fill_pending(candle)
        # Whether it filled or not, a pending level lives exactly one
        # candle (FR-C04). A setup that still holds re-emits below with
        # its own updated level.
        self.pending = None
        if filled is not None:
            return filled
        return self._evaluate(candle, window)

    def _fill_pending(self, candle: Candle) -> Optional[Entry]:
        pending = self.pending
        if pending is None:
            return None
        side = pending.side
        if not side.reached(pending.level, candle):
            return None
        # The conservative fill of FR-010: a candle that gapped through
        # the level fills at its open, never at the level it skipped.
        return Entry(
            price=side.worse(pending.level, candle.open),
            side=side,
            signal_candle=pending.signal_candle,
        )

    def _evaluate(
        self, candle: Candle, window: List[Candle]
    ) -> Optional[Entry]:
        signal = combo(window)
        if signal is None or signal.strength not in TRADED_STRENGTHS:
            return None
        side = _side_for(signal.direction)
        if signal.has_been_triggered:
            # The signal candle already closed beyond the previous
            # candle's extreme; combo puts its price at that close.
            return Entry(price=signal.price, side=side, signal_candle=candle)
        self.pending = PendingEntry(
            level=signal.price, side=side, signal_candle=candle
        )
        return None
