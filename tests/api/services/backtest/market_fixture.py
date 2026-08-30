"""Deterministic synthetic market for the backtest golden tests.

Draws one seeded 5-minute price path per (instrument, day) across the
widest session any backtest trades, and serves whatever timeframe and
window a caller asks for by aggregating it. Every series is a pure
function of (instrument, date), so the snapshot is stable regardless of
the order or range a test asks for.

Deliberately knows nothing about strategies. It used to answer in the
shapes the strategies of the day happened to ask for - one H1 reference
candle, a post-10:00 5-minute scan, a separately drawn H1 session series
- which meant a backtest reading a new shape could not be added without
editing the market, and meant two timeframes of the "same" day were
really two unrelated random walks.
"""

import datetime
import math
import random
from functools import lru_cache
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

from api.services.backtest import (
    paris_reference_window_utc,
    paris_session_end_utc,
)
from model import Candle, EuCfdMarket, Market, UnitTime
from services.candles_service import CandlesService
from utils.helper import last_session_close

# (base price, 5-minute step sigma) per instrument. GER40's sigma is scaled
# up so its 150-point stop and 40-point entry window are exercised the same
# way FRA40's 50/20 are.
INSTRUMENT_PROFILE = {
    "FRA40.I": (8000.0, 10.0),
    "GER40.I": (24000.0, 30.0),
}

# Days the synthetic market returns nothing for, so the golden run covers
# the NO_DATA path alongside the traded ones.
NO_DATA_DATES = {datetime.date(2026, 3, 11), datetime.date(2026, 4, 8)}

GOLDEN_START = datetime.date(2026, 3, 2)
GOLDEN_END = datetime.date(2026, 4, 30)

# The widest session any definition trades (09:00-22:00 Paris). The day's
# path is drawn across it once; a definition on a shorter session reads a
# prefix of the same prices rather than a walk of its own.
WIDEST_SESSION: Market = EuCfdMarket()

# Resolution the day's path is drawn at - the finest any backtest asks
# for. Everything coarser is aggregated from it.
BASE_HORIZON = 5

# Minutes per candle for each timeframe a backtest can request.
HORIZONS = {UnitTime.M5: 5, UnitTime.M15: 15, UnitTime.H1: 60}


def _rng(instrument: str, d: datetime.date, tag: str) -> random.Random:
    return random.Random(f"{instrument}:{d.isoformat()}:{tag}")


def _walk(
    rng: random.Random, start_price: float, sigma: float, steps: int
) -> List[Tuple[float, float, float, float]]:
    """A random walk as `steps` (open, higher, lower, close) tuples, each
    opening at the previous close."""
    bars = []
    price = start_price
    for _ in range(steps):
        open_price = price
        close = open_price + rng.gauss(0, sigma)
        higher = max(open_price, close) + abs(rng.gauss(0, sigma * 0.5))
        lower = min(open_price, close) - abs(rng.gauss(0, sigma * 0.5))
        bars.append(
            (
                round(open_price, 2),
                round(higher, 2),
                round(lower, 2),
                round(close, 2),
            )
        )
        price = close
    return bars


def _session_open_price(instrument: str, d: datetime.date) -> float:
    """Opening level for the day, drifting on a slow sine so the daily MA50
    slope and ADX regime measures see a real trend rather than pure noise."""
    base, sigma = INSTRUMENT_PROFILE[instrument]
    drift = 30 * sigma * math.sin(d.toordinal() / 40.0)
    noise = _rng(instrument, d, "open").gauss(0, sigma)
    return base + drift + noise


def session_bounds(
    d: datetime.date, market: Market
) -> Tuple[datetime.datetime, datetime.datetime]:
    """The market's session on `d` as naive UTC bounds. The open comes from
    the reference window because both start at the session open."""
    return (
        paris_reference_window_utc(d, market)[0],
        paris_session_end_utc(d, market),
    )


@lru_cache(maxsize=None)
def base_bars(instrument: str, d: datetime.date) -> Tuple[Candle, ...]:
    """The day's price path as 5-minute candles across the widest session
    any backtest trades.

    One path per (instrument, day), sampled - never re-drawn - by
    `candles_in_window`. This is what keeps the fixture a *market* rather
    than a set of answers shaped like the questions the current
    strategies happen to ask: a strategy on a new timeframe reads the
    same prices as every existing one, and adding it touches nothing
    here.
    """
    _, sigma = INSTRUMENT_PROFILE[instrument]
    start, end = session_bounds(d, WIDEST_SESSION)
    steps = int((end - start).total_seconds() // 60) // BASE_HORIZON
    bars = _walk(
        _rng(instrument, d, "base"),
        _session_open_price(instrument, d),
        sigma,
        steps,
    )
    return tuple(
        Candle(
            lower=bar[2],
            higher=bar[1],
            open=bar[0],
            close=bar[3],
            ut=UnitTime.M5,
            date=start + datetime.timedelta(minutes=BASE_HORIZON * index),
        )
        for index, bar in enumerate(bars)
    )


def candles_in_window(
    instrument: str,
    d: datetime.date,
    ut: UnitTime,
    start: datetime.datetime,
    end: datetime.datetime,
) -> List[Candle]:
    """The day's base path aggregated to `ut` and cut to [start, end).

    Buckets are anchored to midnight rather than to the window, so the
    same clock minute always falls in the same candle whatever window it
    is asked for - a 09:00-10:00 request and a 09:00-22:00 request agree
    on the 09:00 hourly candle.
    """
    horizon = HORIZONS.get(ut, BASE_HORIZON)
    buckets: Dict[int, List[Candle]] = {}
    for bar in base_bars(instrument, d):
        if bar.date is None or not (start <= bar.date < end):
            continue
        minute_of_day = bar.date.hour * 60 + bar.date.minute
        buckets.setdefault(minute_of_day // horizon, []).append(bar)

    candles: List[Candle] = []
    for key in sorted(buckets):
        group = buckets[key]
        candles.append(
            Candle(
                lower=round(min(bar.lower for bar in group), 2),
                higher=round(max(bar.higher for bar in group), 2),
                open=group[0].open,
                close=group[-1].close,
                ut=ut,
                date=datetime.datetime.combine(d, datetime.time())
                + datetime.timedelta(minutes=key * horizon),
            )
        )
    return candles


def session_candles(
    instrument: str, d: datetime.date, ut: UnitTime, market: Market
) -> List[Candle]:
    """One trading day's session at `ut`, oldest first."""
    start, end = session_bounds(d, market)
    return candles_in_window(instrument, d, ut, start, end)


def h1_candles(
    instrument: str, end_date: datetime.date, count: int, market: Market
) -> List[Candle]:
    """`count` session H1 candles ending with end_date's session, newest
    first, skipping weekends - what CandlesService.build_candles returns
    for UnitTime.H1."""
    candles: List[Candle] = []
    current = end_date
    while len(candles) < count:
        if current.weekday() < 5:
            candles.extend(
                reversed(
                    session_candles(instrument, current, UnitTime.H1, market)
                )
            )
        current -= datetime.timedelta(days=1)
    return candles[:count]


def daily_candles(
    instrument: str, end_date: datetime.date, count: int
) -> List[Candle]:
    """`count` daily candles ending at end_date, newest first (index 0 is
    the most recent), skipping weekends."""
    _, sigma = INSTRUMENT_PROFILE[instrument]
    candles: List[Candle] = []
    current = end_date
    while len(candles) < count:
        if current.weekday() < 5:
            open_price = _session_open_price(instrument, current)
            rng = _rng(instrument, current, "daily")
            close = open_price + rng.gauss(0, sigma * 3)
            candles.append(
                Candle(
                    lower=round(
                        min(open_price, close) - abs(rng.gauss(0, sigma * 2)),
                        2,
                    ),
                    higher=round(
                        max(open_price, close) + abs(rng.gauss(0, sigma * 2)),
                        2,
                    ),
                    open=round(open_price, 2),
                    close=round(close, 2),
                    ut=UnitTime.D,
                    date=datetime.datetime(
                        current.year, current.month, current.day
                    ),
                )
            )
        current -= datetime.timedelta(days=1)
    return candles


def golden_candles_service() -> MagicMock:
    """A CandlesService stub serving the synthetic market."""
    service = MagicMock(spec=CandlesService)

    def get_candles_in_window(code, ut, horizon, start, end):
        """Whatever the caller asks for, sampled from the day's one price
        path. Nothing here branches on which strategy is asking - that
        coupling is what made this fixture need editing every time a
        backtest reading a new shape was added."""
        trading_date = start.date()
        if trading_date in NO_DATA_DATES:
            return []
        return candles_in_window(code, trading_date, ut, start, end)

    def build_candles(code, ut, market, count, reference):
        if ut == UnitTime.H1:
            # Anchored like the real builder: the fetch's reference sits
            # past the last day, and last_session_close walks it back to
            # the session actually available.
            return h1_candles(
                code,
                last_session_close(reference, market).date(),
                count,
                market,
            )
        return daily_candles(code, reference.date(), count)

    service.get_candles_in_window.side_effect = get_candles_in_window
    service.build_candles.side_effect = build_candles
    return service
