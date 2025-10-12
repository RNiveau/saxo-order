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
        self, asset_id: str, asset_symbol: str, country_code: str
    ) -> Dict[str, Any]:
        """Add an asset to the watchlist."""
        response = self.dynamodb.Table("watchlist").put_item(
            Item={
                "id": asset_id,
                "asset_symbol": asset_symbol,
                "country_code": country_code,
                "added_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
            }
        )
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
