"""Candle acquisition for the combo backtests: cache behaviour, the
warm-up lead-in, and the failure policy that keeps a bad minute from
poisoning every later run."""

import datetime
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.backtest.combo_candle_source import (
    MAX_WARM_UP_CALENDAR_DAYS,
    WARM_UP_CANDLES,
    ComboCandleSource,
    cache_key,
    horizon_for,
)
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import (
    BacktestDefinition,
    BacktestParameters,
    Candle,
    DaxCfdMarket,
    UnitTime,
)
from services.candles_service import CandlesService
from utils.exception import SaxoException

DEFINITION = BacktestDefinition(
    code="C15M",
    name="Combo GER40 15m",
    display_name="GER40 Combo 15m",
    instrument="GER40.I",
    market=DaxCfdMarket(),
    unit_time=UnitTime.M15,
    combo_entry=True,
    double_take_profit=True,
    default_parameters=BacktestParameters(stop_loss_points=50),
)

MONDAY = datetime.date(2026, 6, 1)
TUESDAY = datetime.date(2026, 6, 2)


def candle(minute=0, day=2):
    return Candle(
        lower=8000,
        higher=8010,
        open=8005,
        close=8008,
        ut=UnitTime.M15,
        date=datetime.datetime(2026, 6, day, 10, minute),
    )


def make_source(cached=None, fetched=None, fetch_error=None):
    candles_service = MagicMock(spec=CandlesService)
    if fetch_error is not None:
        candles_service.get_candles_in_window.side_effect = fetch_error
    else:
        candles_service.get_candles_in_window.return_value = fetched or []
    client = MagicMock(spec=DynamoDBClient)
    client.get_cached_backtest_series = AsyncMock(return_value=cached)
    client.store_backtest_series = AsyncMock()
    return ComboCandleSource(
        candles_service, client, logging.getLogger("test")
    )


class TestCacheKey:
    def test_it_carries_instrument_session_and_timeframe(self):
        assert cache_key(DEFINITION, UnitTime.M15) == (
            "GER40.I:0200-2200@Europe/Paris:15m:v1"
        )

    def test_two_timeframes_do_not_share_an_entry(self):
        assert cache_key(DEFINITION, UnitTime.M5) != cache_key(
            DEFINITION, UnitTime.H1
        )

    def test_it_does_not_carry_the_definition_code(self):
        """Two definitions on the same instrument, session and timeframe
        read identical candles, so they share one entry."""
        other = BacktestDefinition(
            code="OTHER",
            name="other",
            display_name="other",
            instrument="GER40.I",
            market=DaxCfdMarket(),
            unit_time=UnitTime.M15,
            combo_entry=True,
            double_take_profit=True,
        )
        assert cache_key(other, UnitTime.M15) == cache_key(
            DEFINITION, UnitTime.M15
        )


class TestHorizons:
    @pytest.mark.parametrize(
        "ut,minutes",
        [(UnitTime.M5, 5), (UnitTime.M15, 15), (UnitTime.H1, 60)],
    )
    def test_the_three_supported_timeframes(self, ut, minutes):
        assert horizon_for(ut) == minutes

    def test_an_unsupported_timeframe_raises(self):
        with pytest.raises(SaxoException, match="no candle horizon"):
            horizon_for(UnitTime.W)


class TestDayFetching:
    async def test_a_cache_hit_skips_saxo(self):
        source = make_source(
            cached={"has_data": True, "candles": [candle().to_dict()]}
        )
        result = await source._day(DEFINITION, UnitTime.M15, TUESDAY)
        assert len(result) == 1
        source.candles_service.get_candles_in_window.assert_not_called()

    async def test_a_miss_fetches_and_stores(self):
        source = make_source(fetched=[candle()])
        result = await source._day(DEFINITION, UnitTime.M15, TUESDAY)
        assert len(result) == 1
        source.dynamodb_client.store_backtest_series.assert_awaited_once()

    async def test_an_empty_day_is_cached_as_such(self):
        """A holiday is a real answer and worth remembering."""
        source = make_source(fetched=[])
        assert await source._day(DEFINITION, UnitTime.M15, TUESDAY) == []
        args = source.dynamodb_client.store_backtest_series.await_args.args
        assert args[2] is False

    async def test_a_cached_empty_day_is_not_refetched(self):
        source = make_source(cached={"has_data": False})
        assert await source._day(DEFINITION, UnitTime.M15, TUESDAY) == []
        source.candles_service.get_candles_in_window.assert_not_called()

    async def test_a_fetch_failure_is_never_cached(self):
        """One expired token would otherwise poison every later run over
        that day."""
        source = make_source(fetch_error=SaxoException("token expired"))
        assert await source._day(DEFINITION, UnitTime.M15, TUESDAY) == []
        source.dynamodb_client.store_backtest_series.assert_not_awaited()

    async def test_a_cache_read_failure_falls_back_to_saxo(self):
        source = make_source(fetched=[candle()])
        source.dynamodb_client.get_cached_backtest_series = AsyncMock(
            side_effect=DynamoDBOperationError("get_item", "down")
        )
        assert len(await source._day(DEFINITION, UnitTime.M15, TUESDAY)) == 1

    async def test_a_malformed_item_is_treated_as_a_miss(self):
        source = make_source(cached={"has_data": True, "candles": ["junk"]})
        source.candles_service.get_candles_in_window.return_value = [candle()]
        assert len(await source._day(DEFINITION, UnitTime.M15, TUESDAY)) == 1

    async def test_a_cache_write_failure_does_not_break_the_run(self):
        source = make_source(fetched=[candle()])
        source.dynamodb_client.store_backtest_series = AsyncMock(
            side_effect=DynamoDBOperationError("get_item", "down")
        )
        assert len(await source._day(DEFINITION, UnitTime.M15, TUESDAY)) == 1

    async def test_candles_come_back_chronological(self):
        source = make_source(
            fetched=[candle(minute=30), candle(minute=0), candle(minute=15)]
        )
        result = await source._day(DEFINITION, UnitTime.M15, TUESDAY)
        assert [c.date.minute for c in result] == [0, 15, 30]


class TestSeries:
    async def test_weekends_are_skipped(self):
        """GER40 never trades Saturday or Sunday, so those days must not
        cost a fetch that could only resolve to nothing."""
        source = make_source(fetched=[candle()])
        source._warm_up = AsyncMock(return_value=[])
        source._day = AsyncMock(return_value=[])
        # Friday 5th through Monday 8th June 2026.
        await source.series(
            DEFINITION, datetime.date(2026, 6, 5), datetime.date(2026, 6, 8)
        )
        asked = [call.args[2] for call in source._day.await_args_list]
        assert asked == [
            datetime.date(2026, 6, 5),
            datetime.date(2026, 6, 8),
        ]

    async def test_a_definition_without_a_timeframe_raises(self):
        source = make_source()
        broken = BacktestDefinition(
            code="X", name="x", display_name="x", instrument="GER40.I"
        )
        with pytest.raises(SaxoException, match="unit_time"):
            await source.series(broken, MONDAY, TUESDAY)

    async def test_the_warm_up_precedes_the_run(self):
        source = make_source(fetched=[candle()])
        source._warm_up = AsyncMock(return_value=[candle(day=1)])
        result = await source.series(DEFINITION, TUESDAY, TUESDAY)
        assert result[0].date.day == 1
        assert result[-1].date.day == 2


class TestWarmUp:
    async def test_it_walks_back_until_it_has_enough_candles(self):
        source = make_source()
        day_candles = [candle(minute=i % 60) for i in range(100)]
        source._day = AsyncMock(return_value=day_candles)
        result = await source._warm_up(DEFINITION, UnitTime.M15, TUESDAY)
        # 100 candles per day, so three days clears 250.
        assert len(result) == 300

    async def test_it_stops_at_the_lookback_floor(self):
        """A dead instrument must not walk backwards forever."""
        source = make_source()
        source._day = AsyncMock(return_value=[])
        result = await source._warm_up(DEFINITION, UnitTime.M15, TUESDAY)
        assert result == []
        assert source._day.await_count <= MAX_WARM_UP_CALENDAR_DAYS

    async def test_a_short_warm_up_is_returned_not_raised(self):
        """FR-C13: the strategy simply takes no entry until the window
        fills."""
        source = make_source()
        source._day = AsyncMock(side_effect=[[candle()]] + [[]] * 40)
        result = await source._warm_up(DEFINITION, UnitTime.M15, TUESDAY)
        assert len(result) == 1

    async def test_it_is_returned_oldest_first(self):
        source = make_source()
        source._day = AsyncMock(
            side_effect=[
                [candle(day=5)],
                [candle(day=4)],
                [candle(day=3)],
            ]
            + [[]] * 40
        )
        result = await source._warm_up(DEFINITION, UnitTime.M15, TUESDAY)
        assert [c.date.day for c in result] == [3, 4, 5]

    def test_the_warm_up_clears_what_the_indicator_needs(self):
        """combo raises below COMBO_MIN_CANDLES; the warm-up must be at
        least that, and matches the live path's 250 so the MACD - a
        recursive EMA - is the same one the live engine saw."""
        from services.indicator_service import COMBO_MIN_CANDLES

        assert WARM_UP_CANDLES >= COMBO_MIN_CANDLES
