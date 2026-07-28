"""FR-036-FR-040: the raw-candle cache fronting the Saxo fetches.

Exercised through BacktestService.evaluate_day (the cache is transparent
to callers) against a mocked DynamoDBClient.
"""

from unittest.mock import AsyncMock, MagicMock

from api.services.backtest import BacktestService
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import UnitTime
from model.enum import DayStatus
from services.candles_service import CandlesService
from tests.api.services.backtest.helpers import (
    DEFINITION,
    H1_HIGH,
    H1_LOW,
    IMPULSIVE_DEFINITION,
    NO_CACHE_CLIENT,
    TIME_CUT_DEFINITION,
    TRADING_DATE,
    WIDE_RANGE_DEFINITION,
    h1_candle,
    m5_candle,
)
from utils.exception import SaxoException

# The v2 key for the FRA40.I cash-session definitions: instrument and
# session window only, no definition code.
FRA40_KEY = "FRA40.I:0900-1730:v2"


class TestBacktestCandleCache:
    """FR-036-FR-040: the raw-candle cache is a capability of
    BacktestService itself, keyed by (instrument, session window, schema
    version, trading_date) - these tests exercise it directly against a
    mocked DynamoDBClient, independently of the CandlesService-fetch
    tests above."""

    def _service(self, dynamodb_client):
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [h1_candle()]
            return [m5_candle(0, 8005, 8010, 7995, 8000)]

        candles_service.get_candles_in_window.side_effect = side_effect
        return BacktestService(candles_service, dynamodb_client), (
            candles_service
        )

    async def test_cache_hit_skips_saxo_and_uses_cached_candles(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={
                "has_data": True,
                "h1_candle": h1_candle().to_dict(),
                "m5_candles": [m5_candle(0, 8005, 8010, 7995, 8000).to_dict()],
            }
        )
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_not_called()
        dynamodb_client.store_backtest_candles.assert_not_called()
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW
        assert len(result.candles) == 1

    async def test_cache_hit_no_data_skips_saxo(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={"has_data": False}
        )
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_not_called()
        assert result.status == DayStatus.NO_DATA

    async def test_cache_key_covers_instrument_session_and_version(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            FRA40_KEY,
            TRADING_DATE.isoformat(),
        )

    async def test_cache_miss_fetches_and_stores(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, candles_service = self._service(dynamodb_client)

        await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        dynamodb_client.store_backtest_candles.assert_called_once()
        args = dynamodb_client.store_backtest_candles.call_args[0]
        assert args[0] == FRA40_KEY
        assert args[1] == TRADING_DATE.isoformat()
        assert args[2] is True

    async def test_cache_miss_with_no_h1_data_stores_no_data_marker(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)
        candles_service.get_candles_in_window.return_value = []
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_DATA
        dynamodb_client.store_backtest_candles.assert_called_once_with(
            FRA40_KEY,
            TRADING_DATE.isoformat(),
            False,
            None,
            None,
            True,
        )

    async def test_h1_fetch_failure_is_not_cached(self):
        """A transient Saxo failure (expired token, rate limit, network
        blip) must never be persisted as a permanent NO_DATA - only a
        genuine empty result from Saxo is cacheable."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)
        candles_service.get_candles_in_window.side_effect = SaxoException(
            "boom"
        )
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_DATA
        dynamodb_client.store_backtest_candles.assert_not_called()

    async def test_m5_fetch_failure_is_not_cached(self):
        """Mirror of the H1 case: a transient failure on the 5-minute
        fetch must not be persisted as a permanent has_data=True/empty
        NO_TRADE - only a genuine empty Saxo result is cacheable."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [h1_candle()]
            raise SaxoException("boom")

        candles_service.get_candles_in_window.side_effect = side_effect
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_TRADE
        assert result.h1_high == H1_HIGH
        dynamodb_client.store_backtest_candles.assert_not_called()

    async def test_malformed_cache_item_falls_back_to_saxo(self):
        """An item written under an earlier/different schema (missing
        the expected keys) must be treated as a miss, not raise - a
        cache problem must never break a backtest."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={"has_data": True}
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        dynamodb_client.store_backtest_candles.assert_called_once()
        assert result.h1_high == H1_HIGH

    async def test_no_active_resource_falls_back_to_saxo_every_time(self):
        """dynamodb_client is a required parameter (not Optional), but a
        DynamoDBClient with no active resource - local/dev usage
        without AWS, see get_dynamodb_client_best_effort - degrades to
        a cache miss/no-op every time, exactly like a DynamoDB failure."""
        service, candles_service = self._service(NO_CACHE_CLIENT)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        assert result.h1_high == H1_HIGH

    async def test_cache_lookup_failure_falls_back_to_saxo(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            side_effect=DynamoDBOperationError("get_item", "boom")
        )
        dynamodb_client.store_backtest_candles = AsyncMock(
            side_effect=DynamoDBOperationError("put_item", "boom")
        )
        service, candles_service = self._service(dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        candles_service.get_candles_in_window.assert_called()
        assert result.h1_high == H1_HIGH

    async def test_definitions_on_same_instrument_share_one_entry(self):
        """The cached bytes are raw Saxo candles, identical for every
        strategy on the same instrument and session - so the second
        definition reads the first one's entry instead of re-fetching."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            FRA40_KEY,
            TRADING_DATE.isoformat(),
        )

    async def test_different_sessions_cache_independently(self):
        """The one thing that does still split the cache: a definition on
        the 9:00-22:00 CFD session fetches a longer 5-minute range than
        the cash-session ones, so it cannot share their entry."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(IMPULSIVE_DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            "GER40.I:0900-2200:v2",
            TRADING_DATE.isoformat(),
        )


class TestPartialCacheEntries:
    """A definition with a minimum H1 range skips the 5-minute fetch on a
    day that fails the filter (FR-033). Under a shared cache key that
    entry must be marked partial, so the strategies without the filter
    complete it instead of reading its empty 5-minute list as real data."""

    def _service(self, dynamodb_client, h1_high, h1_low):
        candles_service = MagicMock(spec=CandlesService)

        def side_effect(code, ut, horizon, start, end):
            if ut == UnitTime.H1:
                return [h1_candle(higher=h1_high, lower=h1_low)]
            return [m5_candle(0, 8005, 8010, 7995, 8000)]

        candles_service.get_candles_in_window.side_effect = side_effect
        return BacktestService(candles_service, dynamodb_client), (
            candles_service
        )

    async def test_below_min_range_day_is_stored_as_partial(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        # 20-point range, below WIDE_RANGE_DEFINITION's 40-point minimum.
        service, candles_service = self._service(
            dynamodb_client, 8020.0, 8000.0
        )

        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )

        assert result.status == DayStatus.NO_TRADE
        assert candles_service.get_candles_in_window.call_count == 1
        args = dynamodb_client.store_backtest_candles.call_args[0]
        assert args[0] == FRA40_KEY
        assert args[5] is False

    async def test_partial_entry_is_completed_for_other_definitions(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={
                "has_data": True,
                "h1_candle": h1_candle().to_dict(),
                "m5_candles": [],
                "m5_fetched": False,
            }
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, candles_service = self._service(
            dynamodb_client, H1_HIGH, H1_LOW
        )

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        # Only the 5-minute fetch is paid for; the cached H1 is reused.
        assert candles_service.get_candles_in_window.call_count == 1
        assert (
            candles_service.get_candles_in_window.call_args[0][1]
            == UnitTime.M5
        )
        assert len(result.candles) == 1
        args = dynamodb_client.store_backtest_candles.call_args[0]
        assert args[5] is True

    async def test_partial_entry_serves_the_min_range_definition_as_is(self):
        """The definition that wrote the partial entry doesn't need the
        5-minute candles for that day, so it must not trigger a fetch."""
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={
                "has_data": True,
                "h1_candle": h1_candle(higher=8020.0, lower=8000.0).to_dict(),
                "m5_candles": [],
                "m5_fetched": False,
            }
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, candles_service = self._service(
            dynamodb_client, 8020.0, 8000.0
        )

        result = await service.evaluate_day(
            WIDE_RANGE_DEFINITION, TRADING_DATE
        )

        assert result.status == DayStatus.NO_TRADE
        candles_service.get_candles_in_window.assert_not_called()
        dynamodb_client.store_backtest_candles.assert_not_called()

    async def test_completion_fetch_failure_is_not_cached(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value={
                "has_data": True,
                "h1_candle": h1_candle().to_dict(),
                "m5_candles": [],
                "m5_fetched": False,
            }
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        candles_service = MagicMock(spec=CandlesService)
        candles_service.get_candles_in_window.side_effect = SaxoException(
            "boom"
        )
        service = BacktestService(candles_service, dynamodb_client)

        result = await service.evaluate_day(DEFINITION, TRADING_DATE)

        assert result.status == DayStatus.NO_TRADE
        assert result.h1_high == H1_HIGH
        dynamodb_client.store_backtest_candles.assert_not_called()
