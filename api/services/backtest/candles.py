"""Candle helpers shared by the backtest modules."""

import datetime

from model import Candle
from utils.exception import SaxoException


def candle_date(candle: Candle) -> datetime.datetime:
    """Candles from get_candles_in_window always carry a date (it is
    part of that method's window filter); raise rather than assert so
    a violation surfaces as a normal exception instead of silently
    passing through under `-O` or crashing with a bare AssertionError."""
    if candle.date is None:
        raise SaxoException(
            "Candle from get_candles_in_window is missing a date"
        )
    return candle.date
