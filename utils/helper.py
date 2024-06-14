import datetime
from typing import List, Optional

from model import Candle, UnitTime


def build_daily_candle_from_hours(candles: List[Candle], day: int) -> Optional[Candle]:
    daily_candle = Candle(-1, -1, -1, -1, UnitTime.D, datetime.datetime.now())
    open_candle: List[Candle] = list(
        filter(
            lambda x: x.date is not None and x.date.day == day and x.date.hour == 7,
            candles,
        )
    )
    if len(open_candle) == 1:
        daily_candle.open = open_candle[0].open
    close_candle: List[Candle] = list(
        filter(
            lambda x: x.date is not None and x.date.day == day and x.date.hour == 15,
            candles,
        )
    )
    if len(close_candle) == 1:
        daily_candle.close = close_candle[0].close
    for candle in candles:
        if candle.date is not None and candle.date.day == day:
            if candle.lower < daily_candle.lower or daily_candle.lower == -1:
                daily_candle.lower = candle.lower
            if candle.higher > daily_candle.higher or daily_candle.higher == -1:
                daily_candle.higher = candle.higher
    if (
        daily_candle.open == -1
        or daily_candle.close == -1
        or daily_candle.higher == -1
        or daily_candle.lower == -1
    ):
        return None
    return daily_candle


def get_date_utc0() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)
