import asyncio
import datetime
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import Alert, AlertType, alert_dedup_signature


@pytest.fixture
def mock_dynamodb_resource():
    """Create a mock async DynamoDB resource."""
    mock_resource = AsyncMock()
    mock_table = AsyncMock()
    mock_resource.Table.return_value = mock_table
    return mock_resource, mock_table


@pytest.fixture
def mock_table(mock_dynamodb_resource):
    return mock_dynamodb_resource[1]


@pytest.fixture
def client(mock_dynamodb_resource):
    """Create DynamoDBClient with mocked resource."""
    mock_resource, _ = mock_dynamodb_resource
    return DynamoDBClient(dynamodb_resource=mock_resource)


class TestDynamoDBClient:
    async def test_store_alerts(self, mock_table, client):
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

    async def test_store_alerts_without_country_code(self, mock_table, client):
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

    async def test_store_alerts_deduplication(self, mock_table, client):
        """Test that duplicate alerts are filtered out."""
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

    async def test_store_alerts_all_duplicates(self, mock_table, client):
        """Test that when all alerts are duplicates, no update is made."""
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
    async def test_client_error_raises_dynamodb_operation_error(
        self, mock_table, client
    ):
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
        self, mock_table, client
    ):
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
        self, mock_table, client
    ):
        mock_table.scan.side_effect = ConnectionError("Connection refused")

        with pytest.raises(DynamoDBOperationError) as exc_info:
            await client.get_watchlist()

        assert exc_info.value.operation == "get_watchlist"
        assert "Connection error" in exc_info.value.message

    async def test_graceful_degradation_get_all_tradingview_links(
        self, mock_table, client
    ):
        """Methods with internal try/except return defaults on ClientError."""
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
        self, mock_table, client
    ):
        mock_table.scan.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Error"}},
            "Scan",
        )

        result = await client.get_excluded_assets()
        assert result == []

    async def test_graceful_degradation_get_workflow_orders(
        self, mock_table, client
    ):
        mock_table.query.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Error"}},
            "Query",
        )

        result = await client.get_workflow_orders("some-id")
        assert result == []


class TestAlertDeduplicationSignature:
    """
    Every alert type but one is a repeat when it fires again on the same scan
    date. A weekly combo is a repeat when it describes the same weekly bar in
    the same direction, because the scan runs daily against a bar that lives
    for a week.
    """

    def _weekly(self, bar_date: str, direction: str) -> Alert:
        return Alert(
            alert_type=AlertType.COMBO_WEEKLY,
            date=datetime.datetime(2026, 8, 20, 18, 15, 0),
            data={
                "direction": direction,
                "weekly_bar_date": bar_date,
                "price": 42.0,
            },
            asset_code="SAN",
            asset_description="Sanofi",
            exchange="saxo",
            country_code="xpar",
        )

    def test_other_types_keep_the_scan_date_rule(self):
        for alert_type in AlertType:
            if alert_type == AlertType.COMBO_WEEKLY:
                continue
            alert = Alert(
                alert_type=alert_type,
                date=datetime.datetime(2026, 8, 20, 18, 15, 0),
                data={"price": 1.0},
                asset_code="SAN",
                asset_description="Sanofi",
            )
            assert alert.dedup_signature == (
                alert_type.value,
                "2026-08-20",
            )

    def test_a_stored_row_and_a_fresh_alert_agree(self):
        alert = self._weekly("2026-08-17", "Buy")

        stored = alert_dedup_signature(
            "combo_weekly",
            "2026-08-20T18:15:00",
            {"direction": "Buy", "weekly_bar_date": "2026-08-17"},
        )

        assert alert.dedup_signature == stored

    def test_the_same_bar_on_a_later_scan_is_a_repeat(self):
        monday = self._weekly("2026-08-17", "Buy")
        thursday = self._weekly("2026-08-17", "Buy")
        thursday.date = datetime.datetime(2026, 8, 20, 18, 15, 0)

        assert monday.dedup_signature == thursday.dedup_signature

    def test_a_direction_flip_on_the_same_bar_is_not(self):
        assert (
            self._weekly("2026-08-17", "Buy").dedup_signature
            != self._weekly("2026-08-17", "Sell").dedup_signature
        )

    def test_a_new_bar_is_not(self):
        assert (
            self._weekly("2026-08-17", "Buy").dedup_signature
            != self._weekly("2026-08-24", "Buy").dedup_signature
        )

    def test_a_weekly_row_missing_its_keys_falls_back(self):
        """A row written before this feature is still comparable, just under
        the shared rule - it must not raise."""
        assert alert_dedup_signature(
            "combo_weekly", "2026-08-20T18:15:00", {"price": 1.0}
        ) == ("combo_weekly", "2026-08-20")
        assert alert_dedup_signature(
            "combo_weekly", "2026-08-20T18:15:00", None
        ) == ("combo_weekly", "2026-08-20")


class TestStoreAlertsWeeklyDeduplication:

    async def test_the_same_weekly_bar_is_stored_once(
        self, mock_table, client
    ):
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Item": {
                "alerts": [
                    {
                        "alert_type": "combo_weekly",
                        "date": "2026-08-17T18:15:00",
                        "data": {
                            "direction": "Buy",
                            "weekly_bar_date": "2026-08-17",
                        },
                    }
                ]
            },
        }

        alerts = [
            Alert(
                alert_type=AlertType.COMBO_WEEKLY,
                date=datetime.datetime(2026, 8, 20, 18, 15, 0),
                data={"direction": "Buy", "weekly_bar_date": "2026-08-17"},
                asset_code="SAN",
                asset_description="Sanofi",
                country_code="xpar",
            )
        ]

        await client.store_alerts("SAN", "xpar", alerts)

        mock_table.update_item.assert_not_called()

    async def test_a_flip_on_that_bar_is_stored(self, mock_table, client):
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Item": {
                "alerts": [
                    {
                        "alert_type": "combo_weekly",
                        "date": "2026-08-17T18:15:00",
                        "data": {
                            "direction": "Buy",
                            "weekly_bar_date": "2026-08-17",
                        },
                    }
                ]
            },
        }
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {},
        }

        alerts = [
            Alert(
                alert_type=AlertType.COMBO_WEEKLY,
                date=datetime.datetime(2026, 8, 20, 18, 15, 0),
                data={"direction": "Sell", "weekly_bar_date": "2026-08-17"},
                asset_code="SAN",
                asset_description="Sanofi",
                country_code="xpar",
            )
        ]

        await client.store_alerts("SAN", "xpar", alerts)

        mock_table.update_item.assert_called_once()

    async def test_a_daily_combo_on_the_same_day_still_de_dupes(
        self, mock_table, client
    ):
        """The change must be inert for every pre-existing type (SC-007)."""
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Item": {
                "alerts": [
                    {
                        "alert_type": "combo",
                        "date": "2026-08-20T09:00:00",
                        "data": {"price": 1.0},
                    }
                ]
            },
        }

        alerts = [
            Alert(
                alert_type=AlertType.COMBO,
                date=datetime.datetime(2026, 8, 20, 18, 15, 0),
                data={"price": 2.0},
                asset_code="SAN",
                asset_description="Sanofi",
                country_code="xpar",
            )
        ]

        await client.store_alerts("SAN", "xpar", alerts)

        mock_table.update_item.assert_not_called()


class TestDynamoDBClientOwnsItsConnection:
    """The client opens the session it has always carried.

    __init__ has built an aioboto3 Session since the class was written; it
    just had no way to open a resource from it, so every caller had to wire
    one up and hand it in. Callers that already own a resource (the API's
    app-wide lifespan) still pass it and are left alone.
    """

    def test_it_opens_and_closes_a_resource_it_created(self, mocker):
        resource = mocker.AsyncMock()
        context = mocker.AsyncMock()
        context.__aenter__.return_value = resource
        client = DynamoDBClient()
        mocker.patch.object(client._session, "resource", return_value=context)

        async def run():
            async with client as opened:
                assert opened._dynamodb is resource
            return client

        closed = asyncio.run(run())

        context.__aexit__.assert_awaited_once()
        assert closed._dynamodb is None

    def test_a_supplied_resource_is_left_alone(self, mocker):
        supplied = mocker.MagicMock()
        client = DynamoDBClient(dynamodb_resource=supplied)
        opening = mocker.patch.object(client._session, "resource")

        async def run():
            async with client:
                pass
            return client

        after = asyncio.run(run())

        opening.assert_not_called()
        assert after._dynamodb is supplied
