"""Exit rules as an ordered chain of independent policies.

Each policy answers one question about one open position on one candle:
"does this rule close the position here?" The engine walks a definition's
chain in order and stops at the first policy that returns a Trade.

Ordering *is* the rule. "Stop before take-profit on the same candle"
(FR-009, the conservative convention) is expressed by putting the stop
policy ahead of the target policy, once, instead of by the order of two
statements repeated in every exit resolver. A policy that measures on the
candle's close rather than intrabar - the structural stop - sits after the
target for the same reason, because a target touched intrabar happens
first in real time.

Break-even arming is a policy too (it never closes anything, so it goes
last) rather than a line duplicated at the tail of every resolver.
"""

import datetime
from typing import List, Optional, Protocol

from api.services.backtest.position import Position
from model import Candle, Trade
from model.enum import ExitReason


class ExitPolicy(Protocol):
    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        """The closed Trade when this rule fires on this candle, else
        None. May mutate the position's state (arming break-even, banking
        a first-lot fill) before returning None."""
        ...


def _stop_exit(
    position: Position, candle: Candle, candle_time: datetime.datetime
) -> Trade:
    """Close at the stop with the FR-010 gap-fill convention. An armed
    break-even stop is reported as a break-even rather than a stop-loss."""
    exit_price = position.side.stop_fill(position.stop_level, candle)
    reason = (
        ExitReason.BREAK_EVEN if position.be_armed else ExitReason.STOP_LOSS
    )
    return position.close(candle_time, exit_price, reason)


def _target_exit(
    position: Position,
    candle: Candle,
    candle_time: datetime.datetime,
    level: float,
) -> Trade:
    """Close at a target level with the FR-010 gap-fill convention."""
    exit_price = position.side.target_fill(level, candle)
    return position.close(candle_time, exit_price, ExitReason.TAKE_PROFIT)


class Stop:
    """The intrabar stop: the candle traded through the stop level.

    `only_when_armed` is what the wide-range structural variant needs: it
    has no fixed stop distance at all until break-even arms, at which
    point the break-even stop is an ordinary intrabar stop again.
    """

    def __init__(self, only_when_armed: bool = False):
        self.only_when_armed = only_when_armed

    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        if self.only_when_armed and not position.be_armed:
            return None
        if position.side.receded(position.stop_level, candle):
            return _stop_exit(position, candle, candle_time)
        return None


class StructuralStop:
    """A stop that fires when a candle *closes* beyond the position's H1
    reference level on the losing side (FR-034/FR-035), filling at that
    close - a market exit, so no gap-fill applies.

    Only meaningful while break-even is unarmed; once armed the ordinary
    break-even stop (see Stop(only_when_armed=True)) takes over, and it
    sits ahead of the target in the chain because it is an intrabar touch.
    """

    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        if position.be_armed:
            return None
        if not position.side.closed_beyond(position.structural_level, candle):
            return None
        return position.close(candle_time, candle.close, ExitReason.STOP_LOSS)


class Target:
    """The single-lot take-profit."""

    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        if position.side.reached(position.take_profit_level, candle):
            return _target_exit(
                position, candle, candle_time, position.take_profit_level
            )
        return None


class DoubleTarget:
    """The two-lot take-profit (GER40).

    The first lot exits at TP1 (the H1 midpoint); that fill is banked and
    the runner's stop moves to break-even. The runner then exits at the
    full take-profit (TP2), or at its break-even stop via the Stop policy.
    When one candle reaches both targets, both fill on it.
    """

    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        side = position.side
        tp2_hit = side.reached(position.take_profit_level, candle)
        first_target = position.first_target_level

        if (
            not position.first_target_taken
            and first_target is not None
            and side.reached(first_target, candle)
        ):
            tp1_fill = side.target_fill(first_target, candle)
            position.banked_points += side.favorable(
                tp1_fill, position.entry_price
            )
            position.first_target_taken = True
            position.be_armed = True
            if tp2_hit:
                return _target_exit(
                    position, candle, candle_time, position.take_profit_level
                )
            return None

        if position.first_target_taken and tp2_hit:
            return _target_exit(
                position, candle, candle_time, position.take_profit_level
            )
        return None


class TimeCut:
    """The time-based cut for the "Bougie de 9h (time cut)" variant.

    Tracks the position's max favorable excursion candle by candle. Once
    `minutes` have elapsed since entry, a trade that has never moved more
    than `min_favorable_points` in its favor is closed at market (this
    candle's close). "Never been higher than N points" includes a best
    move of exactly N, hence the <= comparison.
    """

    def __init__(self, minutes: int, min_favorable_points: float):
        self.minutes = minutes
        self.min_favorable_points = min_favorable_points

    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        favorable = position.side.favorable(
            position.side.extreme(candle), position.entry_price
        )
        if favorable > position.max_favorable_points:
            position.max_favorable_points = favorable

        deadline = position.entry_time + datetime.timedelta(
            minutes=self.minutes
        )
        if (
            candle_time >= deadline
            and position.max_favorable_points <= self.min_favorable_points
        ):
            return position.close(
                candle_time, candle.close, ExitReason.TIME_CUT
            )
        return None


class ArmBreakEven:
    """Arms the break-even stop the first time a candle reaches entry plus
    the trigger in the position's favor (FR-008a). Never closes a position,
    and takes effect on later candles - so it goes last in the chain, and
    only runs on a candle no other policy claimed."""

    def __init__(self, trigger_points: float):
        self.trigger_points = trigger_points

    def resolve(
        self,
        position: Position,
        candle: Candle,
        candle_time: datetime.datetime,
    ) -> Optional[Trade]:
        if position.be_armed:
            return None
        arm_level = position.break_even_arm_level(self.trigger_points)
        if position.side.reached(arm_level, candle):
            position.be_armed = True
        return None


def resolve_exit(
    chain: List[ExitPolicy],
    position: Position,
    candle: Candle,
    candle_time: datetime.datetime,
) -> Optional[Trade]:
    """Walk the chain, returning the first policy's Trade, or None when
    the position stays open."""
    for policy in chain:
        closed = policy.resolve(position, candle, candle_time)
        if closed is not None:
            return closed
    return None
