import datetime
from unittest.mock import MagicMock, patch

from client.aws_client import DynamoDBClient
from model import Alert, AlertType


class TestDynamoDBClient:
    @patch("client.aws_client.boto3")
    def test_store_alerts(self, mock_boto3):
        mock_table = MagicMock()
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
                country_code=None,
            )
        ]

        client.store_alerts("BTC", None, alerts)

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args["Key"]["asset_code"] == "BTC"
        assert call_args["Key"]["country_code"] == ""
        assert ":ttl" in call_args["ExpressionAttributeValues"]
        assert isinstance(call_args["ExpressionAttributeValues"][":ttl"], int)
