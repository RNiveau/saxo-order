"""Backtest service package.

`BacktestService` is the entry point used by the API router; the modules
around it hold the pieces it orchestrates:

- `definitions`  the registry of hardcoded backtests and parameter merging
- `calendar`     Paris session windows as naive UTC bounds
- `candles`      candle helpers
- `analytics`    lookahead-safe daily regime measures (MA50 slope, ADX, gap)
- `statistics`   trade aggregation into a BacktestSummary
- `service`      orchestration: fetch/cache, per-day evaluation, range runs
"""

from api.services.backtest.analytics import (
    ADX_MIN_DAILY_CANDLES,
    ADX_PERIOD,
    MM50_MIN_DAILY_CANDLES,
    MM50_SLOPE_LOOKBACK,
    adx_before,
    mm50_slope_before,
    overnight_gap,
)
from api.services.backtest.calendar import (
    PARIS_TZ,
    is_future_paris_date,
    is_today_not_yet_closed,
    paris_reference_window_utc,
    paris_session_end_utc,
)
from api.services.backtest.candles import candle_date
from api.services.backtest.definitions import (
    BACKTEST_DEFINITIONS,
    get_definition,
    list_definitions,
    resolve_parameters,
)
from api.services.backtest.service import BacktestService
from api.services.backtest.statistics import build_summary

__all__ = [
    "ADX_MIN_DAILY_CANDLES",
    "ADX_PERIOD",
    "BACKTEST_DEFINITIONS",
    "BacktestService",
    "MM50_MIN_DAILY_CANDLES",
    "MM50_SLOPE_LOOKBACK",
    "PARIS_TZ",
    "adx_before",
    "build_summary",
    "candle_date",
    "get_definition",
    "is_future_paris_date",
    "is_today_not_yet_closed",
    "list_definitions",
    "mm50_slope_before",
    "overnight_gap",
    "paris_reference_window_utc",
    "paris_session_end_utc",
    "resolve_parameters",
]
