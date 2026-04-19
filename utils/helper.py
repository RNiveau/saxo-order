import datetime
from typing import List, Optional

from model import Candle, Market, UnitTime
from utils.logger import Logger


def build_current_weekly_candle_from_daily(
    candles: List[Candle],
) -> Optional[Candle]:
    """
    Build the current week's candle from daily candles.

    Args:
        candles: List of daily candles (newest first, index 0)

    Returns:
        Weekly candle for the current incomplete week, or None if not enough
        data
    """
    if not candles:
        return None

    today = datetime.datetime.now(datetime.UTC)
    current_iso_year, current_iso_week, _ = today.isocalendar()

    current_week_candles: List[Candle] = []
    for candle in candles:
        if candle.date is None:
            continue
        candle_iso_year, candle_iso_week, _ = candle.date.isocalendar()
        if (
            candle_iso_year == current_iso_year
            and candle_iso_week == current_iso_week
        ):
            current_week_candles.append(candle)

    if not current_week_candles:
        return None

    current_week_candles.sort(
        key=lambda c: c.date if c.date is not None else datetime.datetime.min,
        reverse=True,
    )

    monday_candle = current_week_candles[-1]
    latest_candle = current_week_candles[0]

    weekly_candle = Candle(
        open=monday_candle.open,
        close=latest_candle.close,
        lower=min(c.lower for c in current_week_candles),
        higher=max(c.higher for c in current_week_candles),
        ut=UnitTime.W,
        date=monday_candle.date,
    )

    return weekly_candle


def get_date_utc0() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


def build_h4_candles_from_h1(
    candles: List[Candle], market: Market
) -> List[Candle]:
    ending_hours = {}
    cumulative = 0
    for block_size in market.h4_blocks:
        cumulative += block_size
        ending_hour = market.open_hour + cumulative - 1
        ending_hours[ending_hour] = block_size

    candles_h4 = []
    i = 0
    while i < len(candles):
        candle_date = candles[i].date
        if candle_date is None:
            i += 1
        elif candle_date.hour in ending_hours:
            block_size = ending_hours[candle_date.hour]
            if i + block_size - 1 >= len(candles):
                break
            candles_h4.append(
                _internal_build_candle(candles, i, block_size - 1, UnitTime.H4)
            )
            i += block_size
        else:
            Logger.get_logger("build_h4_candles_from_h1").debug(
                f"Not a h4 ending {candles[i].date}"
            )
            i += 1
    return candles_h4


def build_daily_candles_from_h1(
    candles: List[Candle], market: Market
) -> List[Candle]:
    ending_hour = market.close_hour - (1 if market.open_minutes == 30 else 0)
    num_h1 = (
        market.close_hour
        - market.open_hour
        + (1 if market.open_minutes == 0 else 0)
    )

    candles_daily = []
    i = 0
    while i < len(candles):
        candle_date = candles[i].date
        if candle_date is None:
            i += 1
        elif candle_date.hour == ending_hour:
            if i + num_h1 - 1 >= len(candles):
                break
            candles_daily.append(
                _internal_build_candle(candles, i, num_h1 - 1, UnitTime.D)
            )
            i += num_h1
        else:
            Logger.get_logger("build_daily_candles_from_h1").debug(
                f"Not a daily ending {candles[i].date}"
            )
            i += 1
    return candles_daily


def build_weekly_candles_from_daily(candles: List[Candle]) -> List[Candle]:
    """
    Build weekly candles from daily candles.

    Args:
        candles: List of daily candles (newest first, index 0)

    Returns:
        List of weekly candles (newest first)
    """
    if not candles:
        return []

    weekly_candles: List[Candle] = []
    weeks_dict: dict[tuple[int, int], List[Candle]] = {}

    for candle in candles:
        if candle.date is None:
            continue

        iso_year, iso_week, iso_day = candle.date.isocalendar()
        week_key = (iso_year, iso_week)

        if week_key not in weeks_dict:
            weeks_dict[week_key] = []
        weeks_dict[week_key].append(candle)

    for week_key in sorted(weeks_dict.keys(), reverse=True):
        week_candles = weeks_dict[week_key]
        week_candles.sort(
            key=lambda c: (
                c.date if c.date is not None else datetime.datetime.min
            ),
            reverse=True,
        )

        monday_candle = week_candles[-1]
        friday_candle = week_candles[0]

        weekly_candle = Candle(
            lower=min(c.lower for c in week_candles),
            higher=max(c.higher for c in week_candles),
            open=monday_candle.open,
            close=friday_candle.close,
            ut=UnitTime.W,
            date=monday_candle.date,
        )

        weekly_candles.append(weekly_candle)

    return weekly_candles


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
