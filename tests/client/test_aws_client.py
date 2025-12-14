import datetime
from unittest.mock import MagicMock, patch

from client.aws_client import DynamoDBClient
from model import Alert, AlertType


class TestDynamoDBClient:
    @patch("client.aws_client.boto3")
    def test_clear_alerts_empty_table(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        client.clear_alerts()

        mock_table.scan.assert_called_once()

    @patch("client.aws_client.boto3")
    def test_clear_alerts_with_items(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [
                {"asset_code": "AAPL", "country_code": "xpar"},
                {"asset_code": "GOOGL", "country_code": "xnas"},
            ],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_batch_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = (
            mock_batch_writer
        )
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        client.clear_alerts()

        assert mock_batch_writer.delete_item.call_count == 2

    @patch("client.aws_client.boto3")
    def test_store_alerts(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
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

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]
        assert call_args["Item"]["asset_code"] == "AAPL"
        assert call_args["Item"]["country_code"] == "xpar"
        assert len(call_args["Item"]["alerts"]) == 1
        assert call_args["Item"]["alerts"][0]["alert_type"] == "combo"

    @patch("client.aws_client.boto3")
    def test_store_alerts_without_country_code(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
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

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]
        assert call_args["Item"]["asset_code"] == "BTC"
        assert call_args["Item"]["country_code"] == ""

    @patch("client.aws_client.boto3")
    def test_get_alerts(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "asset_code": "AAPL",
                "country_code": "xpar",
                "alerts": [
                    {
                        "id": "AAPL_xpar",
                        "alert_type": "combo",
                        "date": "2025-12-14T10:30:00",
                        "data": {"price": 150.25},
                    }
                ],
            },
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        alerts = client.get_alerts("AAPL", "xpar")

        mock_table.get_item.assert_called_once_with(
            Key={"asset_code": "AAPL", "country_code": "xpar"}
        )
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "combo"

    @patch("client.aws_client.boto3")
    def test_get_alerts_not_found(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        alerts = client.get_alerts("AAPL", "xpar")

        assert alerts == []

    @patch("client.aws_client.boto3")
    def test_get_all_alerts(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "asset_code": "AAPL",
                    "country_code": "xpar",
                    "alerts": [{"alert_type": "combo"}],
                },
                {
                    "asset_code": "GOOGL",
                    "country_code": "xnas",
                    "alerts": [{"alert_type": "double_top"}],
                },
            ],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        all_alerts = client.get_all_alerts()

        assert len(all_alerts) == 2
        assert all_alerts[0]["asset_code"] == "AAPL"
        assert all_alerts[1]["asset_code"] == "GOOGL"

    @patch("client.aws_client.boto3")
    def test_get_all_alerts_with_pagination(self, mock_boto3):
        mock_table = MagicMock()
        mock_table.scan.side_effect = [
            {
                "Items": [{"asset_code": "AAPL", "country_code": "xpar"}],
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "LastEvaluatedKey": {"asset_code": "AAPL"},
            },
            {
                "Items": [{"asset_code": "GOOGL", "country_code": "xnas"}],
                "ResponseMetadata": {"HTTPStatusCode": 200},
            },
        ]
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        client = DynamoDBClient()
        all_alerts = client.get_all_alerts()

        assert len(all_alerts) == 2
        assert mock_table.scan.call_count == 2
