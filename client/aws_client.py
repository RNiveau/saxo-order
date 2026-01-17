import datetime
import json
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3

from model import Alert, AlertType
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

    @staticmethod
    def _convert_floats_to_decimal(obj: Any) -> Any:
        """
        Recursively convert float values to Decimal for DynamoDB compatibility.

        Args:
            obj: Object to convert (dict, list, or primitive type)

        Returns:
            Object with all floats converted to Decimal
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {
                k: DynamoDBClient._convert_floats_to_decimal(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [
                DynamoDBClient._convert_floats_to_decimal(item) for item in obj
            ]
        return obj

    @staticmethod
    def _normalize_country_code(country_code: Optional[str]) -> str:
        """
        Normalize country code for DynamoDB storage.

        DynamoDB does not support null values in primary keys,
        so we use "NONE" as a sentinel value for crypto assets.

        Args:
            country_code: Country code string or None

        Returns:
            Country code string or "NONE" if None
        """
        return country_code if country_code else "NONE"

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
        """
        Append new alerts for a given asset with 7-day TTL.

        Deduplicates alerts before storing - alerts with the same
        asset_code, alert_type, and date (same day) are considered
        duplicates.
        """
        country_code_value = self._normalize_country_code(country_code)

        # Get existing alerts to check for duplicates
        existing_alerts = self.get_alerts(asset_code, country_code)

        # Create a set of existing alert signatures for fast lookup
        # Signature: (alert_type, date_day)
        existing_signatures = set()
        for existing in existing_alerts:
            try:
                alert_date = datetime.datetime.fromisoformat(existing["date"])
                signature = (
                    existing["alert_type"],
                    alert_date.date().isoformat(),
                )
                existing_signatures.add(signature)
            except (KeyError, ValueError):
                # Skip malformed alerts
                continue

        # Filter out duplicate alerts
        unique_alerts = []
        for alert in alerts:
            signature = (
                alert.alert_type.value,
                alert.date.date().isoformat(),
            )
            if signature not in existing_signatures:
                unique_alerts.append(alert)
                existing_signatures.add(signature)

        # If no unique alerts, return early
        if not unique_alerts:
            self.logger.info(
                f"No unique alerts to store for {asset_code} "
                f"(all {len(alerts)} alerts are duplicates)"
            )
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

        self.logger.info(
            f"Storing {len(unique_alerts)} unique alerts "
            f"(filtered {len(alerts) - len(unique_alerts)} duplicates) "
            f"for {asset_code}"
        )

        alerts_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type.value,
                "asset_code": alert.asset_code,
                "asset_description": alert.asset_description,
                "exchange": alert.exchange,
                "country_code": (
                    alert.country_code if alert.country_code else "NONE"
                ),
                "date": alert.date.isoformat(),
                "data": self._convert_floats_to_decimal(alert.data),
            }
            for alert in unique_alerts
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
        country_code_value = self._normalize_country_code(country_code)

        response = self.dynamodb.Table("alerts").get_item(
            Key={"asset_code": asset_code, "country_code": country_code_value}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return []

        if "Item" not in response:
            return []

        return response["Item"].get("alerts", [])

    def get_all_alerts(self) -> List[Alert]:
        """
        Get all alerts from the alerts table and convert to Alert objects.
        """
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

        all_alerts: List[Alert] = []
        for item in items:
            alerts_data = item.get("alerts", [])
            for alert_dict in alerts_data:
                country_code = alert_dict.get("country_code")
                if country_code == "NONE":
                    country_code = None

                alert = Alert(
                    alert_type=AlertType(alert_dict["alert_type"]),
                    date=datetime.datetime.fromisoformat(alert_dict["date"]),
                    data=alert_dict["data"],
                    asset_code=alert_dict["asset_code"],
                    asset_description=alert_dict.get(
                        "asset_description", alert_dict["asset_code"]
                    ),
                    exchange=alert_dict.get("exchange", "saxo"),
                    country_code=country_code,
                )
                all_alerts.append(alert)

        return all_alerts

    def get_last_run_at(
        self, asset_code: str, country_code: Optional[str]
    ) -> Optional[datetime.datetime]:
        """
        Get the last execution timestamp for on-demand alerts.

        Args:
            asset_code: Asset identifier
            country_code: Country code (or None for crypto)

        Returns:
            Last execution datetime or None if never executed
        """
        country_code_value = self._normalize_country_code(country_code)

        response = self.dynamodb.Table("alerts").get_item(
            Key={"asset_code": asset_code, "country_code": country_code_value}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None

        if "Item" not in response:
            return None

        last_run_at_str = response["Item"].get("last_run_at")
        if not last_run_at_str:
            return None

        try:
            return datetime.datetime.fromisoformat(last_run_at_str)
        except (ValueError, TypeError):
            self.logger.warning(
                f"Invalid last_run_at format for {asset_code}: "
                f"{last_run_at_str}"
            )
            return None

    def update_last_run_at(
        self, asset_code: str, country_code: Optional[str]
    ) -> None:
        """
        Update the last execution timestamp for on-demand alerts.

        Args:
            asset_code: Asset identifier
            country_code: Country code (or None for crypto)
        """
        country_code_value = self._normalize_country_code(country_code)
        now = datetime.datetime.now()

        response = self.dynamodb.Table("alerts").update_item(
            Key={"asset_code": asset_code, "country_code": country_code_value},
            UpdateExpression="SET last_run_at = :last_run_at",
            ExpressionAttributeValues={":last_run_at": now.isoformat()},
            ReturnValues="UPDATED_NEW",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB update_item error: {response}")
