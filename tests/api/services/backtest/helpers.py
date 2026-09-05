"""Shared fixtures for the backtest unit tests.

The registered definitions are re-declared here rather than imported
from the registry so a change to a shipped definition's thresholds fails
the registry test (tests/api/services/backtest/test_definitions.py) instead
of silently changing what every other test is asserting against.
"""

import datetime
from unittest.mock import MagicMock

from api.services.backtest import BacktestService
from client.aws_client import DynamoDBClient
from model import (
    BacktestDefinition,
    BacktestParameters,
    Candle,
    EuCfdMarket,
    Trade,
    UnitTime,
)
from model.enum import Direction, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException

TRADING_DATE = datetime.date(2026, 6, 2)

H1_HIGH = 8050.0
H1_LOW = 8000.0

DEFINITION = BacktestDefinition(
    code="B9H",
    name="Bougie de 9h",
    display_name="CAC40 Bougie de 9h",
    instrument="FRA40.I",
)
TIME_CUT_DEFINITION = BacktestDefinition(
    code="B9HTC",
    name="Bougie de 9h (time cut)",
    display_name="CAC40 Bougie de 9h (time cut)",
    instrument="FRA40.I",
    time_cut_minutes=30,
    time_cut_min_favorable_points=5.0,
)
WIDE_RANGE_DEFINITION = BacktestDefinition(
    code="B9HWS",
    name="Bougie de 9h (wide-range structural stop)",
    display_name="CAC40 Bougie de 9h (wide-range structural stop)",
    instrument="FRA40.I",
    min_h1_range_points=40.0,
    structural_stop=True,
)
GER_DEFINITION = BacktestDefinition(
    code="G9H",
    name="Bougie de 9h GER40",
    display_name="GER40 Bougie de 9h",
    instrument="GER40.I",
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    double_take_profit=True,
    first_target_fraction=0.5,
    stop_from_reference_level=True,
)
GER_SINGLE_LOT_DEFINITION = BacktestDefinition(
    code="G9HSL",
    name="Bougie de 9h GER40 (lot unique)",
    display_name="GER40 Bougie de 9h (lot unique)",
    instrument="GER40.I",
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    stop_from_reference_level=True,
)
IMPULSIVE_DEFINITION = BacktestDefinition(
    code="G9HIC",
    name="Bougie de 9h GER40 (bougie impulsive)",
    display_name="GER40 Bougie de 9h (bougie impulsive)",
    instrument="GER40.I",
    market=EuCfdMarket(),
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    min_h1_range_points=70.0,
    impulsive_candle_points=70.0,
    impulsive_close_fraction=0.25,
    last_entry_time=datetime.time(16, 0),
    max_daily_losses=2,
)
IMPULSIVE_DOUBLE_DEFINITION = BacktestDefinition(
    code="G9HICD",
    name="Bougie de 9h GER40 (bougie impulsive, 2 lots)",
    display_name="GER40 Bougie de 9h (bougie impulsive, 2 lots)",
    instrument="GER40.I",
    market=EuCfdMarket(),
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    min_h1_range_points=70.0,
    impulsive_candle_points=70.0,
    impulsive_close_fraction=0.25,
    last_entry_time=datetime.time(16, 0),
    max_daily_losses=2,
    double_take_profit=True,
    runner_extension_points=100.0,
    trail_to_first_target_points=50.0,
)
# The MM50 direction filter (spec 025 addendum 5): G9HIC restricted to
# one direction per day, the pair differing only in the timeframe the
# MA50 is read on.
MM50_H1_DEFINITION = BacktestDefinition(
    code="G9HICMH",
    name="Bougie de 9h GER40 (bougie impulsive, MM50 h1)",
    display_name="GER40 Bougie de 9h (bougie impulsive, MM50 h1)",
    instrument="GER40.I",
    market=EuCfdMarket(),
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    min_h1_range_points=70.0,
    impulsive_candle_points=70.0,
    impulsive_close_fraction=0.25,
    last_entry_time=datetime.time(16, 0),
    max_daily_losses=2,
    ma50_direction_filter=UnitTime.H1,
)
MM50_DAILY_DEFINITION = BacktestDefinition(
    code="G9HICMD",
    name="Bougie de 9h GER40 (bougie impulsive, MM50 daily)",
    display_name="GER40 Bougie de 9h (bougie impulsive, MM50 daily)",
    instrument="GER40.I",
    market=EuCfdMarket(),
    default_parameters=BacktestParameters(
        stop_loss_points=150,
        take_profit_offset_points=10,
        break_even_trigger_points=50,
        max_entry_distance_points=40,
    ),
    min_h1_range_points=70.0,
    impulsive_candle_points=70.0,
    impulsive_close_fraction=0.25,
    last_entry_time=datetime.time(16, 0),
    max_daily_losses=2,
    ma50_direction_filter=UnitTime.D,
)
GER_PARAMS = GER_DEFINITION.default_parameters

# The impulsive variant needs an H1 range wider than 70 points to trade at
# all (FR-G17), so it cannot reuse the shared 8000-8050 range. Entries
# still open off the same 8000 low, so ger_entry_candles() applies
# unchanged; the far side moves to 8100, putting the take-profit at 8090.
IMPULSIVE_H1_HIGH = 8100.0


# A real DynamoDBClient with no active resource - dynamodb_client is a
# required BacktestService constructor param (not Optional), but calls
# through it still degrade to a cache miss/no-op (RuntimeError, caught in
# the cache layer), the same as in local/dev usage without AWS. Used
# wherever a test doesn't care about caching.
NO_CACHE_CLIENT = DynamoDBClient(dynamodb_resource=None)


def h1_candle(higher=H1_HIGH, lower=H1_LOW, close=8030.0):
    return Candle(
        lower=lower,
        higher=higher,
        open=8020.0,
        close=close,
        ut=UnitTime.H1,
        date=datetime.datetime(2026, 6, 2, 7, 0),
    )


def m5_candle(minute_offset, open, higher, lower, close):
    return Candle(
        lower=lower,
        higher=higher,
        open=open,
        close=close,
        ut=UnitTime.M5,
        date=datetime.datetime(2026, 6, 2, 8, 0)
        + datetime.timedelta(minutes=5 * minute_offset),
    )


def daily_candle(day: datetime.date, close: float) -> Candle:
    return Candle(
        lower=close - 5,
        higher=close + 5,
        open=close,
        close=close,
        ut=UnitTime.D,
        date=datetime.datetime(day.year, day.month, day.day, 0, 0),
    )


def uptrend_daily_series(end_before: datetime.date, count: int) -> list:
    """`count` daily candles ending the day before `end_before`, close
    rising toward the most recent day (an uptrend). Returned oldest-first
    to prove the regime measures do not rely on input ordering."""
    series = []
    for offset in range(1, count + 1):
        day = end_before - datetime.timedelta(days=offset)
        series.append(daily_candle(day, close=8000 + (count - offset)))
    return list(reversed(series))


# The 9:00-10:00 reference candle of TRADING_DATE in naive UTC: 9:00
# Paris on a June day is 07:00 UTC, matching h1_candle()'s date. The
# MM50 H1 series is built backward from it.
REFERENCE_START = datetime.datetime(2026, 6, 2, 7, 0)


def h1_filter_series(close: float, count: int = 60) -> list:
    """`count` H1 candles of constant close ending *with* the 9:00-10:00
    reference candle, so mobile_average over any 50 of them is `close`.

    Returned newest-first, the codebase convention; hourly steps ignore
    session boundaries, which the filter never looks at - it selects on
    "at or before the reference candle" and counts."""
    return [
        Candle(
            lower=close - 5,
            higher=close + 5,
            open=close,
            close=close,
            ut=UnitTime.H1,
            date=REFERENCE_START - datetime.timedelta(hours=offset),
        )
        for offset in range(count)
    ]


def daily_filter_series(close: float, count: int = 60) -> list:
    """`count` daily candles of constant close, all strictly before
    TRADING_DATE, so the daily MA50 is `close`."""
    return [
        daily_candle(TRADING_DATE - datetime.timedelta(days=offset), close)
        for offset in range(1, count + 1)
    ]


async def run_mm50(
    m5_candles,
    definition=MM50_H1_DEFINITION,
    series=None,
    h1_close=8030.0,
    higher=IMPULSIVE_H1_HIGH,
    lower=H1_LOW,
):
    """A single day under one of the MM50-filtered definitions. `series`
    is what the filter's fetch returns - H1 or daily candles depending on
    the definition."""
    service = make_service(
        [h1_candle(higher=higher, lower=lower, close=h1_close)], m5_candles
    )
    service.candles_service.build_candles.return_value = (
        series if series is not None else []
    )
    return await service.evaluate_day(definition, TRADING_DATE, GER_PARAMS)


def short_entry_candles():
    """The mirror of ger_entry_candles(): a breach above the 8100 H1
    high, a candle closing back inside, and a confirmation trading below
    it - a short entry at 8085."""
    return [
        m5_candle(0, 8095, 8115, 8090, 8110),  # breach (close > h1_high)
        m5_candle(1, 8110, 8112, 8085, 8095),  # candidate, lower=8085
        m5_candle(2, 8090, 8092, 8080, 8082),  # breakout -> entry @8085
    ]


def closed_trade(points, exit_reason, direction=Direction.BUY) -> Trade:
    return Trade(
        entry_time=datetime.datetime(2026, 6, 2, 8, 20),
        entry_price=8015.0,
        exit_time=datetime.datetime(2026, 6, 2, 9, 0),
        exit_price=8015.0 + points,
        exit_reason=exit_reason,
        direction=direction,
        points=points,
    )


def ger_entry_candles():
    """The breach / candidate / breakout sequence that opens a long at
    8015 against the 8000-8050 H1 range, shared by both GER40 variants."""
    return [
        m5_candle(0, 8005, 8010, 7990, 7995),  # breach (close < h1_low)
        m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
        m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
    ]


def stop_loss_candles():
    """A breach / candidate / breakout sequence that enters long at 8015
    and stops out on the next candle - the shared "one plain losing
    trade" fixture."""
    return [
        m5_candle(0, 8005, 8010, 7990, 7995),  # breach
        m5_candle(1, 8000, 8015, 7995, 8010),  # candidate, higher=8015
        m5_candle(2, 8010, 8020, 8005, 8015),  # breakout -> entry @8015
        m5_candle(3, 8000, 8005, 7950, 7955),  # stop hit, no gap
    ]


def make_service(h1_candles, m5_candles, raise_on_h1=False, raise_on_m5=False):
    candles_service = MagicMock(spec=CandlesService)

    def side_effect(code, ut, horizon, start, end):
        if ut == UnitTime.H1:
            if raise_on_h1:
                raise SaxoException("boom")
            return h1_candles
        if raise_on_m5:
            raise SaxoException("boom")
        return m5_candles

    candles_service.get_candles_in_window.side_effect = side_effect
    return BacktestService(candles_service, NO_CACHE_CLIENT)


async def run_ger(m5_candles, higher=H1_HIGH, lower=H1_LOW):
    service = make_service([h1_candle(higher=higher, lower=lower)], m5_candles)
    return await service.evaluate_day(GER_DEFINITION, TRADING_DATE, GER_PARAMS)


async def run_ger_single(m5_candles, higher=H1_HIGH, lower=H1_LOW):
    service = make_service([h1_candle(higher=higher, lower=lower)], m5_candles)
    return await service.evaluate_day(
        GER_SINGLE_LOT_DEFINITION, TRADING_DATE, GER_PARAMS
    )


async def run_impulsive(m5_candles, higher=IMPULSIVE_H1_HIGH, lower=H1_LOW):
    service = make_service([h1_candle(higher=higher, lower=lower)], m5_candles)
    return await service.evaluate_day(
        IMPULSIVE_DEFINITION, TRADING_DATE, GER_PARAMS
    )


async def run_impulsive_double(
    m5_candles, higher=IMPULSIVE_H1_HIGH, lower=H1_LOW
):
    service = make_service([h1_candle(higher=higher, lower=lower)], m5_candles)
    return await service.evaluate_day(
        IMPULSIVE_DOUBLE_DEFINITION, TRADING_DATE, GER_PARAMS
    )


__all__ = [
    "DEFINITION",
    "GER_DEFINITION",
    "GER_PARAMS",
    "GER_SINGLE_LOT_DEFINITION",
    "H1_HIGH",
    "IMPULSIVE_DEFINITION",
    "IMPULSIVE_DOUBLE_DEFINITION",
    "IMPULSIVE_H1_HIGH",
    "MM50_DAILY_DEFINITION",
    "MM50_H1_DEFINITION",
    "REFERENCE_START",
    "H1_LOW",
    "NO_CACHE_CLIENT",
    "TIME_CUT_DEFINITION",
    "TRADING_DATE",
    "WIDE_RANGE_DEFINITION",
    "closed_trade",
    "daily_candle",
    "daily_filter_series",
    "h1_filter_series",
    "run_mm50",
    "short_entry_candles",
    "ger_entry_candles",
    "h1_candle",
    "m5_candle",
    "make_service",
    "stop_loss_candles",
    "run_ger",
    "run_ger_single",
    "run_impulsive",
    "run_impulsive_double",
    "uptrend_daily_series",
    "ExitReason",
    "Direction",
]
