import datetime
import json
import logging
import os
from typing import Any, Dict, Optional

import boto3

from utils.json_util import dumps_indicator, hash_indicator
from utils.logger import Logger


class AwsClient:
    @staticmethod
    def is_aws_context() -> bool:
        return (
            "AWS_LAMBDA_FUNCTION_NAME" in os.environ
            or "AWS_PROFILE" in os.environ
        )


class S3Client(AwsClient):

    BUCKET_NAME = "k-order"
    ACCESS_TOKEN = "access_token"
    WORKFLOWS = "workflows.yml"

    def __init__(self) -> None:
        self.s3 = boto3.client("s3")

    def get_access_token(self) -> str:
        response = self.s3.get_object(
            Bucket=S3Client.BUCKET_NAME, Key=S3Client.ACCESS_TOKEN
        )
        return response["Body"].read().decode("utf-8")

    def save_access_token(self, access_token: str, refresh_token: str) -> None:
        self.s3.put_object(
            Bucket=S3Client.BUCKET_NAME,
            Key=S3Client.ACCESS_TOKEN,
            Body=f"{access_token}\n{refresh_token}\n",
        )

    def get_workflows(self) -> str:
        response = self.s3.get_object(
            Bucket=S3Client.BUCKET_NAME, Key=S3Client.WORKFLOWS
        )
        return response["Body"].read().decode("utf-8")

    def save_workflows(self, content: str) -> None:
        self.s3.put_object(
            Bucket=S3Client.BUCKET_NAME,
            Key=S3Client.WORKFLOWS,
            Body=f"{content}\n",
        )


class DynamoDBClient(AwsClient):

    def __init__(self) -> None:
        self.logger = Logger.get_logger("dynamodb_client", logging.INFO)
        self.dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")

    def store_indicator(
        self,
        code: str,
        date: datetime.datetime,
        indicator_type: str,
        indicator: Any,
    ) -> Dict[str, Any]:
        indicator_str = dumps_indicator(indicator)
        md5_hash = hash_indicator(indicator_str)
        response = self.dynamodb.Table("indicators").put_item(
            Item={
                "id": md5_hash,
                "code": code,
                "date": date.isoformat(),
                "indicator_type": indicator_type,
                "json": indicator_str,
            }
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")
        return response

    def get_indicator(self, indicator: Any) -> Optional[Any]:
        indicator_json = dumps_indicator(indicator)
        md5_hash = hash_indicator(indicator_json)
        response = self.dynamodb.Table("indicators").get_item(
            Key={"id": md5_hash}
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None
        if "Item" not in response:
            return None
        return json.loads(response["Item"]["json"])

    def get_indicator_by_id(self, id: str) -> Optional[Any]:
        response = self.dynamodb.Table("indicators").get_item(Key={"id": id})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None
        if "Item" not in response:
            return None
        return json.loads(response["Item"]["json"])

    def add_to_watchlist(
        self,
        asset_id: str,
        asset_symbol: str,
        description: str,
        country_code: str,
        asset_identifier: Optional[int] = None,
        asset_type: Optional[str] = None,
        labels: Optional[list[str]] = None,
        exchange: str = "saxo",
    ) -> Dict[str, Any]:
        """Add an asset to the watchlist with cached metadata and labels."""
        item: Dict[str, Any] = {
            "id": asset_id,
            "asset_symbol": asset_symbol,
            "description": description,
            "country_code": country_code,
            "added_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "labels": labels if labels is not None else [],
            "exchange": exchange,
        }

        # Add cached asset metadata if provided
        if asset_identifier is not None:
            item["asset_identifier"] = asset_identifier
        if asset_type is not None:
            item["asset_type"] = asset_type

        response = self.dynamodb.Table("watchlist").put_item(Item=item)
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")
        return response

    def get_watchlist(self) -> list[Dict[str, Any]]:
        """Get all assets in the watchlist."""
        response = self.dynamodb.Table("watchlist").scan()
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []
        return response.get("Items", [])

    def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
        """Remove an asset from the watchlist."""
        response = self.dynamodb.Table("watchlist").delete_item(
            Key={"id": asset_id}
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB delete_item error: {response}")
        return response

    def is_in_watchlist(self, asset_id: str) -> bool:
        """Check if an asset is in the watchlist."""
        response = self.dynamodb.Table("watchlist").get_item(
            Key={"id": asset_id}
        )
        return "Item" in response

    def update_watchlist_labels(
        self, asset_id: str, labels: list[str]
    ) -> Dict[str, Any]:
        """Update labels for a watchlist item."""
        response = self.dynamodb.Table("watchlist").update_item(
            Key={"id": asset_id},
            UpdateExpression="SET labels = :labels",
            ExpressionAttributeValues={":labels": labels},
            ReturnValues="ALL_NEW",
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB update_item error: {response}")
        return response

    def set_asset_detail(
        self, asset_id: str, tradingview_url: str
    ) -> Dict[str, Any]:
        """Store or update TradingView link for an asset."""
        item = {
            "asset_id": asset_id,
            "tradingview_url": tradingview_url,
            "updated_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }

        response = self.dynamodb.Table("asset_details").put_item(Item=item)
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")
        return response

    def get_asset_detail(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset details including TradingView link."""
        response = self.dynamodb.Table("asset_details").get_item(
            Key={"asset_id": asset_id}
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None
        return response.get("Item")

    def get_tradingview_link(self, asset_id: str) -> Optional[str]:
        """Convenience method to get just the TradingView URL for an asset."""
        detail = self.get_asset_detail(asset_id)
        if detail:
            return detail.get("tradingview_url")
        return None

    def store_alerts(
        self,
        asset_code: str,
        country_code: Optional[str],
        alerts: list,
    ) -> Dict[str, Any]:
        """Append new alerts for a given asset with 7-day TTL."""
        country_code_value = country_code if country_code else ""

        alerts_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type.value,
                "asset_code": alert.asset_code,
                "country_code": (
                    alert.country_code if alert.country_code else ""
                ),
                "date": alert.date.isoformat(),
                "data": alert.data,
            }
            for alert in alerts
        ]

        now = datetime.datetime.now(datetime.timezone.utc)
        ttl_timestamp = int((now + datetime.timedelta(days=7)).timestamp())

        update_expression = (
            "SET alerts = list_append(if_not_exists(alerts, :empty_list), "
            ":new_alerts), last_updated = :last_updated, #ttl = :ttl"
        )

        response = self.dynamodb.Table("alerts").update_item(
            Key={
                "asset_code": asset_code,
                "country_code": country_code_value,
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames={
                "#ttl": "ttl",
            },
            ExpressionAttributeValues={
                ":empty_list": [],
                ":new_alerts": alerts_data,
                ":last_updated": now.isoformat(),
                ":ttl": ttl_timestamp,
            },
            ReturnValues="UPDATED_NEW",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB update_item error: {response}")

        return response

    def get_alerts(self, asset_code: str, country_code: Optional[str]) -> list:
        """Get alerts for a specific asset."""
        country_code_value = country_code if country_code else ""

        response = self.dynamodb.Table("alerts").get_item(
            Key={"asset_code": asset_code, "country_code": country_code_value}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return []

        if "Item" not in response:
            return []

        return response["Item"].get("alerts", [])

    def get_all_alerts(self) -> list[Dict[str, Any]]:
        """Get all alerts from the alerts table."""
        response = self.dynamodb.Table("alerts").scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []

        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            response = self.dynamodb.Table("alerts").scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        return items
