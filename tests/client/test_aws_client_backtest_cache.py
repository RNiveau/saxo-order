from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from client.aws_client import DynamoDBClient, DynamoDBOperationError


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


class TestConditionalStore:
    """`only_if_absent` guards the partial entry a minimum-H1-range
    definition writes on a filtered day. Unlike the one-off migration,
    this path runs on every such day, forever - it is the only thing
    stopping a partial entry from clobbering a complete one."""

    async def test_only_if_absent_sets_the_condition(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        await client.store_backtest_candles(
            "FRA40.I:0900-1730@Europe/Paris:v2",
            "2026-07-14",
            True,
            {"lower": 8000.0, "higher": 8020.0},
            [],
            False,
            only_if_absent=True,
        )

        kwargs = mock_table.put_item.call_args[1]
        assert kwargs["ConditionExpression"] == (
            "attribute_not_exists(definition_code)"
        )
        assert kwargs["Item"]["m5_fetched"] is False

    async def test_default_write_is_unconditional(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        await client.store_backtest_candles(
            "FRA40.I:0900-1730@Europe/Paris:v2", "2026-07-14", False
        )

        assert "ConditionExpression" not in mock_table.put_item.call_args[1]

    async def test_condition_failure_is_not_an_error(
        self, mock_dynamodb_resource, client
    ):
        """Another run cached the day first - which is the point of the
        condition. It must not surface as a failed cache write."""
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )

        result = await client.store_backtest_candles(
            "FRA40.I:0900-1730@Europe/Paris:v2",
            "2026-07-14",
            True,
            {"lower": 8000.0, "higher": 8020.0},
            [],
            False,
            only_if_absent=True,
        )

        assert result == {}

    async def test_other_client_errors_still_propagate(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}},
            "PutItem",
        )

        with pytest.raises(DynamoDBOperationError):
            await client.store_backtest_candles(
                "FRA40.I:0900-1730@Europe/Paris:v2",
                "2026-07-14",
                True,
                {"lower": 8000.0, "higher": 8020.0},
                [],
                False,
                only_if_absent=True,
            )


class TestScanAndDelete:
    """The two primitives the cache migration runs on."""

    async def test_scan_follows_pagination(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.side_effect = [
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Items": [{"definition_code": "B9H:FRA40.I:v1"}],
                "LastEvaluatedKey": {"definition_code": "B9H:FRA40.I:v1"},
            },
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Items": [{"definition_code": "B9HTC:FRA40.I:v1"}],
            },
        ]

        items = await client.scan_backtest_candles()

        assert [i["definition_code"] for i in items] == [
            "B9H:FRA40.I:v1",
            "B9HTC:FRA40.I:v1",
        ]
        second_call = mock_table.scan.call_args_list[1][1]
        assert second_call["ExclusiveStartKey"] == {
            "definition_code": "B9H:FRA40.I:v1"
        }

    async def test_delete_targets_the_composite_key(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.delete_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        await client.delete_backtest_candles("B9H:FRA40.I:v1", "2026-07-14")

        assert mock_table.delete_item.call_args[1]["Key"] == {
            "definition_code": "B9H:FRA40.I:v1",
            "trading_date": "2026-07-14",
        }
