"""Deterministic synthetic market for the backtest golden tests.

Builds reproducible H1 / 5-minute / daily candle series from a seeded RNG so
a full BacktestService run can be snapshotted and compared across a
refactor. Every series is a pure function of (instrument, date), so the
snapshot is stable regardless of the order or range a test asks for.
"""

import datetime
import math
import random
from typing import List, Tuple
from unittest.mock import MagicMock

from api.services.backtest import paris_reference_window_utc
from model import Candle, EUMarket, UnitTime
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

H1_STEPS = 12
SESSION_STEPS = 90

# Minutes per candle for the timeframes the combo backtests run on.
COMBO_HORIZONS = {UnitTime.M5: 5, UnitTime.M15: 15, UnitTime.H1: 60}

# Shortest window only a combo backtest asks for. Its 02:00-22:00 day is
# 20 hours; the widest a session backtest asks for is 10:00-22:00 (12).
COMBO_WINDOW_MIN = datetime.timedelta(hours=15)


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


def h1_reference_candle(instrument: str, d: datetime.date) -> Candle:
    """The 9h-10h reference candle, aggregated from the first hour's walk."""
    _, sigma = INSTRUMENT_PROFILE[instrument]
    bars = _walk(
        _rng(instrument, d, "h1"),
        _session_open_price(instrument, d),
        sigma,
        H1_STEPS,
    )
    start, _ = paris_reference_window_utc(d, EUMarket())
    return Candle(
        lower=round(min(bar[2] for bar in bars), 2),
        higher=round(max(bar[1] for bar in bars), 2),
        open=bars[0][0],
        close=bars[-1][3],
        ut=UnitTime.H1,
        date=start,
    )


def m5_session_candles(instrument: str, d: datetime.date) -> List[Candle]:
    """The post-10h session as 5-minute candles, continuing from the
    reference candle's close."""
    _, sigma = INSTRUMENT_PROFILE[instrument]
    reference = h1_reference_candle(instrument, d)
    bars = _walk(
        _rng(instrument, d, "m5"), reference.close, sigma, SESSION_STEPS
    )
    _, session_start = paris_reference_window_utc(d, EUMarket())
    return [
        Candle(
            lower=bar[2],
            higher=bar[1],
            open=bar[0],
            close=bar[3],
            ut=UnitTime.M5,
            date=session_start + datetime.timedelta(minutes=5 * index),
        )
        for index, bar in enumerate(bars)
    ]


H1_SESSION_CANDLES = 9  # a 9:00-17:30 cash session


def h1_session_candles(instrument: str, d: datetime.date) -> List[Candle]:
    """One trading day's cash-session H1 candles, oldest first.

    The first is the 9:00-10:00 reference candle itself - the same object
    the strategy reads - so the MM50 filter's series and the day's
    reference level cannot drift apart; the rest continue its walk hour by
    hour."""
    _, sigma = INSTRUMENT_PROFILE[instrument]
    reference = h1_reference_candle(instrument, d)
    bars = _walk(
        _rng(instrument, d, "h1series"),
        reference.close,
        sigma,
        H1_SESSION_CANDLES - 1,
    )
    start, _ = paris_reference_window_utc(d, EUMarket())
    return [reference] + [
        Candle(
            lower=bar[2],
            higher=bar[1],
            open=bar[0],
            close=bar[3],
            ut=UnitTime.H1,
            date=start + datetime.timedelta(hours=index + 1),
        )
        for index, bar in enumerate(bars)
    ]


def h1_candles(
    instrument: str, end_date: datetime.date, count: int
) -> List[Candle]:
    """`count` cash-session H1 candles ending with end_date's session,
    newest first, skipping weekends - what CandlesService.build_candles
    returns for UnitTime.H1."""
    candles: List[Candle] = []
    current = end_date
    while len(candles) < count:
        if current.weekday() < 5:
            candles.extend(reversed(h1_session_candles(instrument, current)))
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


def timeframe_session_candles(
    instrument: str,
    d: datetime.date,
    ut: UnitTime,
    start: datetime.datetime,
    end: datetime.datetime,
) -> List[Candle]:
    """A session's worth of candles at an arbitrary timeframe, for the
    combo backtests - which read a whole day at 5m, 15m or H1 rather than
    a reference candle plus a 5-minute scan.

    Drifting rather than driftless: a pure random walk almost never
    produces the sloping ma50 the combo indicator requires, so the golden
    market would exercise the strategy's plumbing and none of its rules.
    The drift alternates by day so both directions are covered.
    """
    horizon = COMBO_HORIZONS[ut]
    steps = max(1, int((end - start).total_seconds() // (60 * horizon)))
    base, sigma = INSTRUMENT_PROFILE[instrument]
    rng = _rng(instrument, d, f"combo-{ut.value}")
    drift = (1 if d.toordinal() % 2 else -1) * sigma * 0.35
    price = _session_open_price(instrument, d)
    candles: List[Candle] = []
    for index in range(steps):
        open_price = price
        close = open_price + drift + rng.gauss(0, sigma)
        candles.append(
            Candle(
                lower=round(
                    min(open_price, close) - abs(rng.gauss(0, sigma / 2)), 2
                ),
                higher=round(
                    max(open_price, close) + abs(rng.gauss(0, sigma / 2)), 2
                ),
                open=round(open_price, 2),
                close=round(close, 2),
                ut=ut,
                date=start + datetime.timedelta(minutes=horizon * index),
            )
        )
        price = close
    return candles


def golden_candles_service() -> MagicMock:
    """A CandlesService stub serving the synthetic market."""
    service = MagicMock(spec=CandlesService)

    def get_candles_in_window(code, ut, horizon, start, end):
        trading_date = start.date()
        if trading_date in NO_DATA_DATES:
            return []
        # Only a combo backtest asks for a whole 02:00-22:00 DAX CFD day
        # (20 hours). The session backtests ask for the 1-hour reference
        # window and then a post-10:00 5-minute scan of at most 12 hours,
        # so the width of the window is what separates them - not the
        # timeframe, which M5 shares.
        if end - start >= COMBO_WINDOW_MIN:
            return timeframe_session_candles(
                code, trading_date, ut, start, end
            )
        if ut == UnitTime.H1:
            return [h1_reference_candle(code, trading_date)]
        return m5_session_candles(code, trading_date)

    def build_candles(code, ut, market, count, reference):
        if ut == UnitTime.H1:
            # Anchored like the real builder: the fetch's reference sits
            # past the last day, and last_session_close walks it back to
            # the session actually available.
            return h1_candles(
                code, last_session_close(reference, market).date(), count
            )
        return daily_candles(code, reference.date(), count)

    service.get_candles_in_window.side_effect = get_candles_in_window
    service.build_candles.side_effect = build_candles
    return service
