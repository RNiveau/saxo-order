"""Paris trading-calendar helpers for the backtests.

All backtests run on European instruments (FRA40.I, GER40.I), so the
9h reference window and the session end are derived from EUMarket in
Paris local time and returned as naive UTC bounds - the form the Saxo
candle API expects.
"""

import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from model import EUMarket, Market
from utils.helper import market_in_utc

PARIS_TZ = ZoneInfo("Europe/Paris")


def _eu_market_in_utc(trading_date: datetime.date) -> Market:
    reference = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        tzinfo=PARIS_TZ,
    )
    return market_in_utc(EUMarket(), reference)


def paris_reference_window_utc(
    trading_date: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """9:00-10:00 Paris local time for trading_date, as naive UTC bounds."""
    utc_market = _eu_market_in_utc(trading_date)
    start = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.open_hour,
        utc_market.open_minutes,
    )
    end = start + datetime.timedelta(hours=1)
    return (start, end)


def paris_session_end_utc(trading_date: datetime.date) -> datetime.datetime:
    """End of the regular European trading session (Euronext Paris close,
    17:30 local, from EUMarket.close_hour/end_minute), as a naive UTC
    datetime."""
    utc_market = _eu_market_in_utc(trading_date)
    return datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.close_hour,
        utc_market.end_minute,
    )


def is_future_paris_date(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    return d > current.date()


def is_today_not_yet_closed(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    """True if d is today (Paris) and the regular session hasn't ended
    yet - the backtest only operates on already-closed historical days,
    and Saxo won't return a complete H1/5-minute series for a session
    still in progress."""
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    if d != current.date():
        return False
    market = EUMarket()
    session_end_local = datetime.datetime(
        d.year,
        d.month,
        d.day,
        market.close_hour,
        market.end_minute,
        tzinfo=PARIS_TZ,
    )
    return current < session_end_local
