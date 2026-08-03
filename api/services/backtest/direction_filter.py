"""The MM50 direction filter (spec 025 addendum 5, FR-G37-FR-G40).

A definition carrying `ma50_direction_filter` trades in at most one
direction per day. The decision is taken once, at 10:00: the 9:00-10:00
reference candle's close against an MA50 read on H1 or daily candles.
Above it the day is long-only, below it short-only, exactly on it
untradeable.

Kept apart from `analytics.py` even though both average daily candles:
the measures there are *reported* alongside a day and never change what
the strategy does, while this one decides whether a position may open at
all. They also differ on the lookahead boundary - a regime column reads
strictly prior days, the H1 filter includes the reference candle itself,
which has closed by the time the decision is taken.
"""

import datetime
from typing import List, Optional

from api.services.backtest.calendar import paris_reference_window_utc
from api.services.backtest.candles import candle_date
from api.services.backtest.side import LONG, SHORT, Side
from model import BacktestDefinition, Candle, EUMarket, UnitTime
from services.indicator_service import mobile_average
from utils.exception import SaxoException

MA50_PERIOD = 50

# H1 candles the filter's series must hold before the first day of a run
# can be scored: 50 of them, on a 9:00-17:30 session that produces 9 per
# trading day, plus a margin for public holidays.
H1_CANDLES_PER_SESSION = 9
H1_CANDLES_LEAD_IN = MA50_PERIOD + 2 * H1_CANDLES_PER_SESSION


def series_unit_time(
    definition: BacktestDefinition,
) -> Optional[UnitTime]:
    return definition.ma50_direction_filter


def allowed_side(
    definition: BacktestDefinition,
    series: List[Candle],
    trading_date: datetime.date,
    reference_close: float,
) -> Optional[Side]:
    """The only direction this day may open a position in, or None when
    it may open none.

    None covers both "the reference candle closed exactly on the MA50"
    and "the MA50 could not be computed" (FR-G40): in each case the day
    is untradeable, and the caller reports NO_TRADE without distinguishing
    them - a day nobody could have traded either way.

    A definition without the filter never reaches here; the caller keeps
    both sides for it (FR-G45).
    """
    ma50 = _ma50_at_decision(definition, series, trading_date)
    if ma50 is None:
        return None
    if reference_close > ma50:
        return LONG
    if reference_close < ma50:
        return SHORT
    return None


def _ma50_at_decision(
    definition: BacktestDefinition,
    series: List[Candle],
    trading_date: datetime.date,
) -> Optional[float]:
    """The MA50 as of 10:00 on trading_date, or None when the series is
    too short to carry one."""
    ut = definition.ma50_direction_filter
    if ut is None:
        return None
    if ut == UnitTime.D:
        usable = _daily_candles_before(series, trading_date)
    else:
        usable = _h1_candles_through_reference(series, trading_date)
    try:
        return mobile_average(usable, MA50_PERIOD)
    except SaxoException:
        return None


def _daily_candles_before(
    series: List[Candle], trading_date: datetime.date
) -> List[Candle]:
    """Daily candles strictly before trading_date, newest first (FR-G38).
    The day's own daily candle would carry its close - the whole session,
    including everything after 10:00 - so it is excluded."""
    prior = [
        candle
        for candle in series
        if candle.date is not None and candle.date.date() < trading_date
    ]
    prior.sort(key=candle_date, reverse=True)
    return prior


def _h1_candles_through_reference(
    series: List[Candle], trading_date: datetime.date
) -> List[Candle]:
    """H1 candles up to and including the 9:00-10:00 reference candle,
    newest first (FR-G38/FR-G39).

    Inclusive of the reference candle: the decision is taken at 10:00,
    when that candle has closed and is the last one available. Everything
    after it is dropped, so no candle the strategy has not yet reached can
    influence which direction it may trade.

    The window is derived from EUMarket rather than the definition's own
    market, matching the series itself - both markets open at 9:00, so the
    boundary is the same instant either way, but taking it from the series'
    market keeps the two from drifting apart if a session ever moves.
    """
    reference_start, _ = paris_reference_window_utc(trading_date, EUMarket())
    through = [
        candle
        for candle in series
        if candle.date is not None and candle.date <= reference_start
    ]
    through.sort(key=candle_date, reverse=True)
    return through
