import datetime
import random

from api.services.backtest import (
    ADX_CONVERGENCE_DAILY_CANDLES,
    ADX_MIN_DAILY_CANDLES,
    DAILY_CANDLES_LEAD_IN,
    MM50_MIN_DAILY_CANDLES,
    MM50_SLOPE_LOOKBACK,
    adx_before,
    mm50_slope_before,
    overnight_gap,
)
from model import Candle, UnitTime
from tests.api.services.backtest.helpers import (
    daily_candle,
    uptrend_daily_series,
)

TRADING_DATE = datetime.date(2026, 6, 2)

# Deep enough that adding more candles no longer moves Wilder's ADX.
CONVERGED_DEPTH = 900


def _random_walk_series(count: int, seed: int) -> list:
    """`count` daily candles of a seeded random walk ending the day before
    TRADING_DATE, oldest first - a series with enough direction changes
    for Wilder's smoothing to still be settling after a few dozen bars."""
    rng = random.Random(seed)
    price = 8000.0
    series = []
    for offset in range(count, 0, -1):
        close = price + rng.gauss(0, 20)
        series.append(
            Candle(
                lower=round(min(price, close) - abs(rng.gauss(0, 10)), 2),
                higher=round(max(price, close) + abs(rng.gauss(0, 10)), 2),
                open=round(price, 2),
                close=round(close, 2),
                ut=UnitTime.D,
                date=datetime.datetime.combine(
                    TRADING_DATE - datetime.timedelta(days=offset),
                    datetime.time(),
                ),
            )
        )
        price = close
    return series


def _polluted(series):
    """The series plus candles dated on the trading day and after it -
    values a lookahead-safe measure must ignore."""
    return series + [
        daily_candle(TRADING_DATE, close=0.0),
        daily_candle(TRADING_DATE + datetime.timedelta(days=1), close=99999.0),
    ]


class TestMm50SlopeBefore:
    def test_none_when_fewer_than_60_prior_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 59)
        assert mm50_slope_before(series, TRADING_DATE) is None

    def test_positive_slope_for_uptrend(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        slope = mm50_slope_before(series, TRADING_DATE)
        assert slope is not None and slope > 0

    def test_ignores_today_and_future_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        baseline = mm50_slope_before(series, TRADING_DATE)
        assert mm50_slope_before(_polluted(series), TRADING_DATE) == baseline

    def test_skips_dateless_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        dateless = daily_candle(TRADING_DATE, close=0.0)
        dateless.date = None
        assert mm50_slope_before(
            [dateless] + series, TRADING_DATE
        ) == mm50_slope_before(series, TRADING_DATE)


class TestAdxBefore:
    def test_none_when_fewer_than_42_prior_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 41)
        assert adx_before(series, TRADING_DATE) is None

    def test_high_adx_for_uptrend(self):
        series = uptrend_daily_series(TRADING_DATE, 60)
        value = adx_before(series, TRADING_DATE)
        assert value is not None and value > 40

    def test_ignores_today_and_future_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 60)
        baseline = adx_before(series, TRADING_DATE)
        assert adx_before(_polluted(series), TRADING_DATE) == baseline


class TestOvernightGap:
    def test_gap_is_open_minus_prior_daily_close(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        # latest prior daily close in the series is 8069
        assert overnight_gap(series, TRADING_DATE, h1_open=8100.0) == 31.0

    def test_none_when_no_prior_candle(self):
        assert overnight_gap([], TRADING_DATE, h1_open=8100.0) is None

    def test_none_when_h1_open_missing(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        assert overnight_gap(series, TRADING_DATE, h1_open=None) is None

    def test_ignores_today_and_future_candles(self):
        series = uptrend_daily_series(TRADING_DATE, 70)
        baseline = overnight_gap(series, TRADING_DATE, h1_open=8100.0)
        assert (
            overnight_gap(_polluted(series), TRADING_DATE, h1_open=8100.0)
            == baseline
        )


class TestRegimeDepthConstants:
    """The lead-in is what makes a day's regime measures a property of the
    day rather than of where the run happened to start."""

    def test_lead_in_covers_the_adx_convergence_depth(self):
        assert DAILY_CANDLES_LEAD_IN >= ADX_CONVERGENCE_DAILY_CANDLES

    def test_lead_in_covers_the_mm50_slope_depth(self):
        assert (
            DAILY_CANDLES_LEAD_IN
            >= MM50_MIN_DAILY_CANDLES + MM50_SLOPE_LOOKBACK
        )

    def test_convergence_depth_is_deeper_than_the_feasibility_floor(self):
        assert ADX_CONVERGENCE_DAILY_CANDLES > ADX_MIN_DAILY_CANDLES


class TestAdxConvergence:
    """Wilder's ADX is seeded from the oldest bar and smoothed forward, so
    the value depends on how deep the series runs. These pin the depth the
    lead-in is sized on rather than the depth the indicator tolerates."""

    def test_feasibility_floor_alone_is_not_converged(self):
        """At ADX_MIN_DAILY_CANDLES the value is still visibly warming up -
        the reason the lead-in is not sized on that floor."""
        errors = []
        for seed in range(20):
            series = _random_walk_series(CONVERGED_DEPTH, seed)
            converged = adx_before(series, TRADING_DATE)
            shallow = adx_before(series[-ADX_MIN_DAILY_CANDLES:], TRADING_DATE)
            assert converged is not None and shallow is not None
            errors.append(abs(converged - shallow))
        assert max(errors) > 1.0

    def test_convergence_depth_matches_a_much_deeper_series(self):
        for seed in range(20):
            series = _random_walk_series(CONVERGED_DEPTH, seed)
            converged = adx_before(series, TRADING_DATE)
            at_depth = adx_before(
                series[-ADX_CONVERGENCE_DAILY_CANDLES:], TRADING_DATE
            )
            assert converged is not None and at_depth is not None
            assert abs(converged - at_depth) < 0.05
