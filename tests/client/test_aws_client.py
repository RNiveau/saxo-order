import datetime
from unittest.mock import MagicMock, patch

from client.aws_client import DynamoDBClient
from model import Alert, AlertType


class TestDynamoDBClient:
    @patch("client.aws_client.boto3")
    def test_store_alerts(self, mock_boto3):
        mock_table = MagicMock()
        # Mock get_item for get_alerts (no existing alerts)
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {},
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
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

        client.store_alerts("AAPL", "xpar", alerts)

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

    @patch("client.aws_client.boto3")
    def test_store_alerts_without_country_code(self, mock_boto3):
        mock_table = MagicMock()
        # Mock get_item for get_alerts (no existing alerts)
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {},
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
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

        client.store_alerts("BTC", None, alerts)

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args["Key"]["asset_code"] == "BTC"
        assert call_args["Key"]["country_code"] == "NONE"
        assert ":ttl" in call_args["ExpressionAttributeValues"]
        assert isinstance(call_args["ExpressionAttributeValues"][":ttl"], int)

    @patch("client.aws_client.boto3")
    def test_store_alerts_deduplication(self, mock_boto3):
        """Test that duplicate alerts are filtered out."""
        mock_table = MagicMock()
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
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
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

        client.store_alerts("AAPL", "xpar", alerts)

        # Should only store 1 alert (the unique one)
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        stored_alerts = call_args["ExpressionAttributeValues"][":new_alerts"]
        assert len(stored_alerts) == 1
        assert stored_alerts[0]["alert_type"] == "congestion20"

    @patch("client.aws_client.boto3")
    def test_store_alerts_all_duplicates(self, mock_boto3):
        """Test that when all alerts are duplicates, no update is made."""
        mock_table = MagicMock()
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
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
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

        result = client.store_alerts("AAPL", "xpar", alerts)

        # Should not call update_item
        mock_table.update_item.assert_not_called()
        # Should return success response
        assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

    @patch("client.aws_client.boto3")
    def test_get_excluded_assets_empty(self, mock_boto3):
        """Test get_excluded_assets returns empty list when no exclusions."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.get_excluded_assets()

        assert result == []
        mock_table.scan.assert_called_once()

    @patch("client.aws_client.boto3")
    def test_get_excluded_assets_with_exclusions(self, mock_boto3):
        """Test get_excluded_assets returns correct list of asset IDs."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [
                {"asset_id": "SAN", "is_excluded": True},
                {"asset_id": "BNP", "is_excluded": True},
            ],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.get_excluded_assets()

        assert len(result) == 2
        assert "SAN" in result
        assert "BNP" in result

    @patch("client.aws_client.boto3")
    def test_get_excluded_assets_with_pagination(self, mock_boto3):
        """Test get_excluded_assets handles pagination correctly."""
        mock_table = MagicMock()
        # First page
        mock_table.scan.side_effect = [
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Items": [
                    {"asset_id": "SAN", "is_excluded": True},
                ],
                "LastEvaluatedKey": {"asset_id": "SAN"},
            },
            # Second page
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Items": [
                    {"asset_id": "BNP", "is_excluded": True},
                ],
            },
        ]
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.get_excluded_assets()

        assert len(result) == 2
        assert "SAN" in result
        assert "BNP" in result
        assert mock_table.scan.call_count == 2

    @patch("client.aws_client.boto3")
    def test_update_asset_exclusion_success(self, mock_boto3):
        """Test update_asset_exclusion successfully updates status."""
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {
                "asset_id": "SAN",
                "is_excluded": True,
            },
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.update_asset_exclusion("SAN", True)

        assert result is True
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args["Key"]["asset_id"] == "SAN"
        assert call_args["ExpressionAttributeValues"][":is_excluded"] is True

    @patch("client.aws_client.boto3")
    def test_update_asset_exclusion_to_false(self, mock_boto3):
        """Test update_asset_exclusion can un-exclude an asset."""
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {
                "asset_id": "SAN",
                "is_excluded": False,
            },
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.update_asset_exclusion("SAN", False)

        assert result is True
        call_args = mock_table.update_item.call_args[1]
        assert call_args["ExpressionAttributeValues"][":is_excluded"] is False

    @patch("client.aws_client.boto3")
    def test_update_asset_exclusion_failure(self, mock_boto3):
        """Test update_asset_exclusion returns False on error."""
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 500},
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.update_asset_exclusion("SAN", True)

        assert result is False

    @patch("client.aws_client.boto3")
    def test_get_all_asset_details_empty(self, mock_boto3):
        """Test get_all_asset_details returns empty list."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.get_all_asset_details()

        assert result == []

    @patch("client.aws_client.boto3")
    def test_get_all_asset_details_with_data(self, mock_boto3):
        """Test get_all_asset_details returns all assets with all fields."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [
                {
                    "asset_id": "SAN",
                    "tradingview_url": "https://tradingview.com/SAN",
                    "updated_at": "2026-01-26T10:00:00Z",
                    "is_excluded": True,
                },
                {
                    "asset_id": "ITP",
                    "tradingview_url": None,
                    "updated_at": "2026-01-25T15:00:00Z",
                    "is_excluded": False,
                },
            ],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.get_all_asset_details()

        assert len(result) == 2
        assert result[0]["asset_id"] == "SAN"
        assert result[0]["is_excluded"] is True
        assert result[1]["asset_id"] == "ITP"
        assert result[1]["is_excluded"] is False

    @patch("client.aws_client.boto3")
    def test_get_all_asset_details_defaults_is_excluded(self, mock_boto3):
        """Test get_all_asset_details defaults is_excluded to False."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [
                {
                    "asset_id": "OLD",
                    "tradingview_url": "https://tradingview.com/OLD",
                    # No is_excluded field
                },
            ],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        result = client.get_all_asset_details()

        assert len(result) == 1
        assert result[0]["asset_id"] == "OLD"
        assert result[0]["is_excluded"] is False
