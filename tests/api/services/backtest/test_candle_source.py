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
    NO_CACHE_CLIENT,
    TIME_CUT_DEFINITION,
    TRADING_DATE,
    h1_candle,
    m5_candle,
)
from utils.exception import SaxoException


class TestBacktestCandleCache:
    """FR-036-FR-040: the raw-candle cache is a capability of
    BacktestService itself, keyed by (definition code, instrument,
    schema version, trading_date) - these tests exercise it directly
    against a mocked DynamoDBClient, independently of the
    CandlesService-fetch tests above."""

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

    async def test_cache_key_covers_code_instrument_and_version(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            f"{DEFINITION.code}:{DEFINITION.instrument}:v1",
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
        assert args[0] == f"{DEFINITION.code}:{DEFINITION.instrument}:v1"
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
            f"{DEFINITION.code}:{DEFINITION.instrument}:v1",
            TRADING_DATE.isoformat(),
            False,
            None,
            None,
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

    async def test_different_definitions_cache_independently(self):
        dynamodb_client = MagicMock(spec=DynamoDBClient)
        dynamodb_client.get_cached_backtest_candles = AsyncMock(
            return_value=None
        )
        dynamodb_client.store_backtest_candles = AsyncMock()
        service, _ = self._service(dynamodb_client)

        await service.evaluate_day(TIME_CUT_DEFINITION, TRADING_DATE)

        dynamodb_client.get_cached_backtest_candles.assert_called_once_with(
            f"{TIME_CUT_DEFINITION.code}:{TIME_CUT_DEFINITION.instrument}:v1",
            TRADING_DATE.isoformat(),
        )
