"""Paris trading-calendar helpers for the backtests.

All backtests run on European instruments (FRA40.I, GER40.I), so the
9h reference window and the session end are derived from the definition's
market in Paris local time and returned as naive UTC bounds - the form the
Saxo candle API expects.

The market is a parameter rather than a constant because a definition
chooses its session: the cash-session backtests run EUMarket (9:00-17:30),
the impulsive-candle variant EuCfdMarket (9:00-22:00). Both open at 9:00,
so only the session end actually differs today - but the reference window
is derived from the same market so a future session with a different open
cannot silently keep the 9:00 window.

`market` is required rather than defaulting to EUMarket: every production
call site has a definition to take it from, so a default could only ever
be silently wrong - a call site that forgot it would keep the 9:00-17:30
window and return plausible-but-wrong bounds instead of failing.
"""

import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from model import Market
from utils.helper import market_in_utc

PARIS_TZ = ZoneInfo("Europe/Paris")


def _market_in_utc(trading_date: datetime.date, market: Market) -> Market:
    reference = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        tzinfo=PARIS_TZ,
    )
    return market_in_utc(market, reference)


def paris_reference_window_utc(
    trading_date: datetime.date, market: Market
) -> tuple[datetime.datetime, datetime.datetime]:
    """The market's first trading hour on trading_date (9:00-10:00 Paris
    local for both European markets), as naive UTC bounds."""
    utc_market = _market_in_utc(trading_date, market)
    start = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.open_hour,
        utc_market.open_minutes,
    )
    end = start + datetime.timedelta(hours=1)
    return (start, end)


def paris_session_end_utc(
    trading_date: datetime.date, market: Market
) -> datetime.datetime:
    """End of the market's regular session (17:30 local for EUMarket's
    Euronext Paris close, 22:00 for EuCfdMarket), from
    close_hour/end_minute, as a naive UTC datetime.

    end_minute is added as an offset rather than passed as a minute field
    because it is documented to exceed 59 whenever close_hour labels the
    last full H1 candle rather than the literal close - 60 for both
    USMarket's 16:00 and EuCfdMarket's 22:00."""
    utc_market = _market_in_utc(trading_date, market)
    close_hour_start = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.close_hour,
    )
    return close_hour_start + datetime.timedelta(minutes=utc_market.end_minute)


def session_key(market: Market) -> str:
    """Compact identifier of the market's session window ("0900-1730" for
    EUMarket, "0900-2200" for EuCfdMarket), built from the same fields
    paris_reference_window_utc/paris_session_end_utc derive their bounds
    from. Two markets sharing this string fetch exactly the same candles
    for a given instrument and day, which is what makes it usable as part
    of a cache key."""
    close_minutes = market.close_hour * 60 + market.end_minute
    return (
        f"{market.open_hour:02d}{market.open_minutes:02d}-"
        f"{close_minutes // 60:02d}{close_minutes % 60:02d}"
    )


def is_future_paris_date(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    return d > current.date()


def is_today_not_yet_closed(
    d: datetime.date,
    market: Market,
    *,
    now: Optional[datetime.datetime] = None,
) -> bool:
    """True if d is today (Paris) and the market's regular session hasn't
    ended yet - the backtest only operates on already-closed historical
    days, and Saxo won't return a complete H1/5-minute series for a session
    still in progress."""
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    if d != current.date():
        return False
    session_end_local = datetime.datetime(
        d.year,
        d.month,
        d.day,
        market.close_hour,
        tzinfo=PARIS_TZ,
    ) + datetime.timedelta(minutes=market.end_minute)
    return current < session_end_local
