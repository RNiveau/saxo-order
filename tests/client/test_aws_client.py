import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError

from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import Alert, AlertType


class TestDynamoDBClient:
    @pytest.fixture
    def mock_dynamodb_resource(self):
        """Create a mock async DynamoDB resource."""
        mock_resource = AsyncMock()
        mock_table = AsyncMock()
        mock_resource.Table.return_value = mock_table
        return mock_resource, mock_table

    @pytest.fixture
    def client(self, mock_dynamodb_resource):
        """Create DynamoDBClient with mocked resource."""
        mock_resource, _ = mock_dynamodb_resource
        return DynamoDBClient(dynamodb_resource=mock_resource)

    async def test_store_alerts(self, mock_dynamodb_resource, client):
        _, mock_table = mock_dynamodb_resource
        # Mock get_item for get_alerts (no existing alerts)
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {},
        }

        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2025, 12, 14, 10, 30, 0),
                data={"price": 150.25},
                asset_code="AAPL",
                asset_description="Apple Inc.",
                exchange="saxo",
                country_code="xpar",
            )
        ]

        await client.store_alerts("AAPL", "xpar", alerts)

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args["Key"]["asset_code"] == "AAPL"
        assert call_args["Key"]["country_code"] == "xpar"
        assert ":new_alerts" in call_args["ExpressionAttributeValues"]
        assert len(call_args["ExpressionAttributeValues"][":new_alerts"]) == 1
        assert (
            call_args["ExpressionAttributeValues"][":new_alerts"][0][
                "alert_type"
            ]
            == "combo"
        )
        assert ":ttl" in call_args["ExpressionAttributeValues"]
        assert isinstance(call_args["ExpressionAttributeValues"][":ttl"], int)
        assert "list_append" in call_args["UpdateExpression"]

    async def test_store_alerts_without_country_code(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        # Mock get_item for get_alerts (no existing alerts)
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {},
        }

        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2025, 12, 14, 10, 30, 0),
                data={"price": 150.25},
                asset_code="BTC",
                asset_description="Bitcoin",
                exchange="binance",
                country_code=None,
            )
        ]

        await client.store_alerts("BTC", None, alerts)

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args["Key"]["asset_code"] == "BTC"
        assert call_args["Key"]["country_code"] == "NONE"
        assert ":ttl" in call_args["ExpressionAttributeValues"]
        assert isinstance(call_args["ExpressionAttributeValues"][":ttl"], int)

    async def test_store_alerts_deduplication(
        self, mock_dynamodb_resource, client
    ):
        """Test that duplicate alerts are filtered out."""
        _, mock_table = mock_dynamodb_resource
        # Mock existing alerts
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Item": {
                "alerts": [
                    {
                        "alert_type": "combo",
                        "date": "2025-12-14T10:30:00",
                        "asset_code": "AAPL",
                    }
                ]
            },
        }
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {},
        }

        alerts = [
            # This alert is a duplicate (same type, same day)
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2025, 12, 14, 15, 30, 0),
                data={"price": 150.25},
                asset_code="AAPL",
                asset_description="Apple Inc.",
                exchange="saxo",
                country_code="xpar",
            ),
            # This alert is unique (different type)
            Alert(
                alert_type=AlertType.CONGESTION20,
                date=datetime.datetime(2025, 12, 14, 15, 30, 0),
                data={"price": 150.25},
                asset_code="AAPL",
                asset_description="Apple Inc.",
                exchange="saxo",
                country_code="xpar",
            ),
        ]

        await client.store_alerts("AAPL", "xpar", alerts)

        # Should only store 1 alert (the unique one)
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        stored_alerts = call_args["ExpressionAttributeValues"][":new_alerts"]
        assert len(stored_alerts) == 1
        assert stored_alerts[0]["alert_type"] == "congestion20"

    async def test_store_alerts_all_duplicates(
        self, mock_dynamodb_resource, client
    ):
        """Test that when all alerts are duplicates, no update is made."""
        _, mock_table = mock_dynamodb_resource
        # Mock existing alerts
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Item": {
                "alerts": [
                    {
                        "alert_type": "combo",
                        "date": "2025-12-14T10:30:00",
                        "asset_code": "AAPL",
                    }
                ]
            },
        }

        alerts = [
            # This alert is a duplicate
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2025, 12, 14, 15, 30, 0),
                data={"price": 150.25},
                asset_code="AAPL",
                asset_description="Apple Inc.",
                exchange="saxo",
                country_code="xpar",
            ),
        ]

        result = await client.store_alerts("AAPL", "xpar", alerts)

        # Should not call update_item
        mock_table.update_item.assert_not_called()
        # Should return success response
        assert result["ResponseMetadata"]["HTTPStatusCode"] == 200


class TestDynamoDBErrorHandling:
    @pytest.fixture
    def mock_dynamodb_resource(self):
        mock_resource = AsyncMock()
        mock_table = AsyncMock()
        mock_resource.Table.return_value = mock_table
        return mock_resource, mock_table

    @pytest.fixture
    def client(self, mock_dynamodb_resource):
        mock_resource, _ = mock_dynamodb_resource
        return DynamoDBClient(dynamodb_resource=mock_resource)

    async def test_client_error_raises_dynamodb_operation_error(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Table not found",
                }
            },
            "Scan",
        )

        with pytest.raises(DynamoDBOperationError) as exc_info:
            await client.get_watchlist()

        assert exc_info.value.operation == "get_watchlist"
        assert "ResourceNotFoundException" in exc_info.value.message

    async def test_throughput_exceeded_raises_dynamodb_operation_error(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ProvisionedThroughputExceededException",
                    "Message": "Rate exceeded",
                }
            },
            "Scan",
        )

        with pytest.raises(DynamoDBOperationError) as exc_info:
            await client.get_watchlist()

        assert (
            "ProvisionedThroughputExceededException" in exc_info.value.message
        )

    async def test_connection_error_raises_dynamodb_operation_error(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.side_effect = ConnectionError("Connection refused")

        with pytest.raises(DynamoDBOperationError) as exc_info:
            await client.get_watchlist()

        assert exc_info.value.operation == "get_watchlist"
        assert "Connection error" in exc_info.value.message

    async def test_graceful_degradation_get_all_tradingview_links(
        self, mock_dynamodb_resource, client
    ):
        """Methods with internal try/except should return defaults on ClientError."""
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Not found",
                }
            },
            "Scan",
        )

        result = await client.get_all_tradingview_links()
        assert result == {}

    async def test_graceful_degradation_get_excluded_assets(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Error"}},
            "Scan",
        )

        result = await client.get_excluded_assets()
        assert result == []

    async def test_graceful_degradation_get_workflow_orders(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.query.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Error"}},
            "Query",
        )

        result = await client.get_workflow_orders("some-id")
        assert result == []
