from unittest.mock import AsyncMock

import pytest

from client.aws_client import DynamoDBClient


@pytest.fixture
def mock_dynamodb_resource():
    mock_resource = AsyncMock()
    mock_table = AsyncMock()
    mock_resource.Table.return_value = mock_table
    return mock_resource, mock_table


@pytest.fixture
def client(mock_dynamodb_resource):
    mock_resource, _ = mock_dynamodb_resource
    return DynamoDBClient(dynamodb_resource=mock_resource)


class TestGetCachedBacktestCandles:
    async def test_returns_item_on_hit(self, mock_dynamodb_resource, client):
        _, mock_table = mock_dynamodb_resource
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Item": {
                "definition_code": "B9H",
                "trading_date": "2026-07-14",
                "has_data": True,
            },
        }

        item = await client.get_cached_backtest_candles("B9H", "2026-07-14")

        mock_table.get_item.assert_called_once_with(
            Key={
                "definition_code": "B9H",
                "trading_date": "2026-07-14",
            }
        )
        assert item is not None
        assert item["has_data"] is True

    async def test_returns_none_on_miss(self, mock_dynamodb_resource, client):
        _, mock_table = mock_dynamodb_resource
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }

        item = await client.get_cached_backtest_candles("B9H", "2026-07-14")

        assert item is None

    async def test_returns_none_on_error_response(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 500},
        }

        item = await client.get_cached_backtest_candles("B9H", "2026-07-14")

        assert item is None


class TestStoreBacktestCandles:
    async def test_stores_candles_and_converts_floats_to_decimal(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        h1_candle = {
            "lower": 8000.0,
            "higher": 8050.0,
            "open": 8020.0,
            "close": 8030.0,
            "ut": "1h",
            "date": "2026-07-14T07:00:00",
        }
        m5_candles = [
            {
                "lower": 8010.0,
                "higher": 8020.0,
                "open": 8012.0,
                "close": 8018.0,
                "ut": "5m",
                "date": "2026-07-14T08:00:00",
            }
        ]

        await client.store_backtest_candles(
            "B9H",
            "2026-07-14",
            True,
            h1_candle,
            m5_candles,
        )

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]["Item"]
        assert item["definition_code"] == "B9H"
        assert item["trading_date"] == "2026-07-14"
        assert item["has_data"] is True
        assert str(item["h1_candle"]["lower"]) == "8000.0"
        assert str(item["m5_candles"][0]["higher"]) == "8020.0"
        assert isinstance(item["cached_at"], int)

    async def test_stores_no_data_marker_without_candles(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        await client.store_backtest_candles(
            "B9H", "2026-07-15", False, None, None
        )

        item = mock_table.put_item.call_args[1]["Item"]
        assert item["has_data"] is False
        assert "h1_candle" not in item
        assert "m5_candles" not in item
