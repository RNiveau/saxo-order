import datetime
from typing import List, Optional

from model import Candle, UnitTime
from utils.logger import Logger


def build_daily_candle_from_hours(
    candles: List[Candle], day: int
) -> Optional[Candle]:
    daily_candle = Candle(-1, -1, -1, -1, UnitTime.D, datetime.datetime.now())
    open_candle: List[Candle] = list(
        filter(
            lambda x: x.date is not None
            and x.date.day == day
            and x.date.hour == 7,
            candles,
        )
    )
    if len(open_candle) == 1:
        daily_candle.open = open_candle[0].open
    close_candle: List[Candle] = list(
        filter(
            lambda x: x.date is not None
            and x.date.day == day
            and x.date.hour == 15,
            candles,
        )
    )
    if len(close_candle) == 1:
        daily_candle.close = close_candle[0].close
    for candle in candles:
        if candle.date is not None and candle.date.day == day:
            if candle.lower < daily_candle.lower or daily_candle.lower == -1:
                daily_candle.lower = candle.lower
            if (
                candle.higher > daily_candle.higher
                or daily_candle.higher == -1
            ):
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


def build_h4_candles_from_h1(
    candles: List[Candle], open_hour_utc0: int
) -> List[Candle]:
    candles_h4 = []
    if open_hour_utc0 == 7:
        i = 0
        while i < len(candles):
            candle_date = candles[i].date
            if candle_date is None:
                i += 1
            elif candle_date.hour == 15:  # included 17h utc+2
                if i + 1 >= len(candles):
                    break
                candles_h4.append(
                    _internal_build_candle(candles, i, 1, UnitTime.H4)
                )
                i += 2
            elif candle_date.hour == 13:  # included 15h utc+2
                if i + 3 >= len(candles):
                    break
                candles_h4.append(
                    _internal_build_candle(candles, i, 3, UnitTime.H4)
                )
                i += 4
            elif candle_date.hour == 9:  # included 11h utc+2
                if i + 2 >= len(candles):
                    break
                candles_h4.append(
                    _internal_build_candle(candles, i, 2, UnitTime.H4)
                )
                i += 3
            else:
                Logger.get_logger("build_h4_candles_from_h1").debug(
                    f"Not a h4 ending {candles[i].date}"
                )
                i += 1
    elif open_hour_utc0 == 13:
        i = 0
        while i < len(candles):
            candle_date = candles[i].date
            if candle_date is None:
                i += 1
            elif candle_date.hour == 16:
                if i + 3 >= len(candles):
                    break
                candles_h4.append(
                    _internal_build_candle(candles, i, 3, UnitTime.H4)
                )
                i += 4
            elif candle_date.hour == 19:
                if i + 2 >= len(candles):
                    break
                candles_h4.append(
                    _internal_build_candle(candles, i, 2, UnitTime.H4)
                )
                i += 3
            else:
                Logger.get_logger("build_h4_candles_from_h1").debug(
                    f"Not a h4 ending {candles[i].date}"
                )
                i += 1
    return candles_h4


def build_daily_candles_from_h1(
    candles: List[Candle], open_hour_utc0: int
) -> List[Candle]:
    candles_daily = []
    if open_hour_utc0 == 7:
        i = 0
        while i < len(candles):
            candle_date = candles[i].date
            if candle_date is None:
                i += 1
            elif candle_date.hour == 15:  # included 17h utc+2
                if i + 7 >= len(candles):
                    break
                candles_daily.append(
                    _internal_build_candle(candles, i, 8, UnitTime.D)
                )
                i += 9
            else:
                Logger.get_logger("build_daily_candles_from_h1").debug(
                    f"Not a daily ending {candles[i].date}"
                )
                i += 1
    elif open_hour_utc0 == 13:
        i = 0
        while i < len(candles):
            candle_date = candles[i].date
            if candle_date is None:
                i += 1
            elif candle_date.hour == 19:
                if i + 6 >= len(candles):
                    break
                candles_daily.append(
                    _internal_build_candle(candles, i, 6, UnitTime.D)
                )
                i += 7
            else:
                Logger.get_logger("build_daily_candles_from_h1").debug(
                    f"Not a daily ending {candles[i].date}"
                )
                i += 1
    return candles_daily


def _internal_build_candle(
    candles: List[Candle], start_index: int, nbr_candles: int, ut: UnitTime
) -> Candle:
    """internal use by build_*_candles_from_h1"""
    candle = Candle(
        lower=candles[start_index].lower,
        higher=candles[start_index].higher,
        close=candles[start_index].close,
        open=-1,
        ut=ut,
    )
    candle.open = candles[start_index + nbr_candles].open
    candle.date = candles[start_index + nbr_candles].date
    for j in range(start_index, start_index + nbr_candles + 1):
        if candles[j].lower < candle.lower:
            candle.lower = candles[j].lower
        if candles[j].higher > candle.higher:
            candle.higher = candles[j].higher
    return candle
