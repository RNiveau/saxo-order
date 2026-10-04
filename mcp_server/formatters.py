"""Turning candles into something economical to read.

A model pays for every token of a tool result, so a bar series is returned
columnar - the field names once in ``columns``, the values as bare rows -
rather than as a list of five-key objects. For a hundred bars that is four
hundred repeated keys saved.
"""

import datetime
from typing import List, Optional, Union

from model import Candle

# Enough to see structure and swing points without spending the context on
# history the indicators have already summarised.
DEFAULT_BAR_COUNT = 100
MAX_BAR_COUNT = 500

PRICE_PRECISION = 4

Row = List[Union[str, float, None]]


def round_price(value: float) -> float:
    return round(value, PRICE_PRECISION)


def candle_row(candle: Candle) -> Row:
    """One bar, in ``mcp_server.models.BAR_COLUMNS`` order."""
    return [
        candle.date.isoformat() if candle.date else None,
        round_price(candle.open),
        round_price(candle.higher),
        round_price(candle.lower),
        round_price(candle.close),
    ]


def to_rows(
    candles: List[Candle], count: int = DEFAULT_BAR_COUNT
) -> List[Row]:
    """Newest-first rows, no more than the caller asked for or the cap allows.

    Whether the cap overrode the caller is ``exceeds_cap``'s question, asked
    where the answer is put on the wire. Returning it from here as well left
    two definitions of "truncated" alive, disagreeing on the same input.

    The newest-first order is the project's convention and is preserved all
    the way to the wire: index 0 is the most recent bar.
    """
    return [candle_row(c) for c in candles[: min(count, MAX_BAR_COUNT)]]


def exceeds_cap(count: int) -> bool:
    """Whether a requested bar count was overridden by the hard cap.

    A property of the request, not of what came back: asking for 20 of 250
    is a request being honoured, while asking for 900 is the server
    overriding you, however much history the instrument turns out to have.
    """
    return count > MAX_BAR_COUNT


def last_bar_date(candles: List[Candle]) -> Optional[datetime.datetime]:
    return candles[0].date if candles else None
