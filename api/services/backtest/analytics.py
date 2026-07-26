"""Lookahead-safe daily regime measures attached to each backtest day.

Every measure here is computed from daily candles strictly *before* the
trading day, so a day's row never carries information that was not yet
knowable when the trade was taken. They are also independent of the run's
SL/TP parameters, which makes them usable to segment an exported run.
"""

import datetime
from typing import List, Optional

from api.services.backtest.candles import candle_date
from model import Candle
from services.indicator_service import adx, mobile_average, slope_percentage

# Daily MA50 slope regime measure: MA50 needs 50 daily closes and the
# slope is taken over a 10-candle lookback, so at least 60 prior daily
# candles are required before a day can be scored.
MM50_MIN_DAILY_CANDLES = 60
MM50_SLOPE_LOOKBACK = 10

# Daily ADX regime measure: Wilder's double smoothing needs period * 3
# prior daily candles (matches services.indicator_service.adx).
ADX_PERIOD = 14
ADX_MIN_DAILY_CANDLES = ADX_PERIOD * 3

# Lead-in a run needs before its first day can be scored, plus a small
# margin for holidays.
DAILY_CANDLES_LEAD_IN = MM50_MIN_DAILY_CANDLES + MM50_SLOPE_LOOKBACK + 5


def _prior_candles_newest_first(
    daily_candles: List[Candle], trading_date: datetime.date
) -> List[Candle]:
    """Daily candles strictly before trading_date, newest first - the
    shared lookahead guard and ordering convention for every measure."""
    prior = [
        candle
        for candle in daily_candles
        if candle.date is not None and candle.date.date() < trading_date
    ]
    prior.sort(key=candle_date, reverse=True)
    return prior


def mm50_slope_before(
    daily_candles: List[Candle], trading_date: datetime.date
) -> Optional[float]:
    """Daily MA50 slope (%) as of the last close strictly before
    trading_date. Mirrors the MA50 slope used by the MM50 alert (spec 019).
    Returns None when fewer than MM50_MIN_DAILY_CANDLES prior daily
    candles are available."""
    prior = _prior_candles_newest_first(daily_candles, trading_date)
    if len(prior) < MM50_MIN_DAILY_CANDLES:
        return None
    ma50_last = mobile_average(prior, 50)
    ma50_first = mobile_average(prior[MM50_SLOPE_LOOKBACK:], 50)
    return slope_percentage(0, ma50_first, MM50_SLOPE_LOOKBACK, ma50_last)


def adx_before(
    daily_candles: List[Candle], trading_date: datetime.date
) -> Optional[float]:
    """Daily ADX(14) as of the last close strictly before trading_date.
    Returns None when fewer than ADX_MIN_DAILY_CANDLES prior daily
    candles are available."""
    prior = _prior_candles_newest_first(daily_candles, trading_date)
    if len(prior) < ADX_MIN_DAILY_CANDLES:
        return None
    return adx(prior, ADX_PERIOD)


def overnight_gap(
    daily_candles: List[Candle],
    trading_date: datetime.date,
    h1_open: Optional[float],
) -> Optional[float]:
    """Overnight gap = 9h open - the prior daily close. A same-day,
    pre-trade shock signal (the 9h open is known at 09:00, before any
    entry). None when the 9h open or a prior daily candle is missing."""
    if h1_open is None:
        return None
    prior = _prior_candles_newest_first(daily_candles, trading_date)
    if not prior:
        return None
    return round(h1_open - prior[0].close, 4)
