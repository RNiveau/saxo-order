import datetime
import functools
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Optional

import aioboto3
import boto3
from botocore.exceptions import ClientError

from model import (
    Alert,
    AlertDigest,
    AlertType,
    TriagedAsset,
    alert_dedup_signature,
)
from utils.json_util import dumps_indicator, hash_indicator
from utils.logger import Logger

AWS_REGION = "eu-west-1"


class DynamoDBOperationError(Exception):
    """Raised when a DynamoDB operation fails."""

    def __init__(self, operation: str, message: str):
        self.operation = operation
        self.message = message
        super().__init__(f"DynamoDB '{operation}' failed: {message}")


def _dynamo_operation(func):
    """Decorator for DynamoDB operations with error handling and timing."""

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        operation = func.__name__
        start = time.monotonic()
        try:
            result = await func(self, *args, **kwargs)
            duration_ms = (time.monotonic() - start) * 1000
            self.logger.debug(
                f"dynamodb.{operation} completed in {duration_ms:.1f}ms"
            )
            DynamoDBClient._request_count += 1
            DynamoDBClient._total_duration_ms += duration_ms
            return result
        except ClientError as e:
            duration_ms = (time.monotonic() - start) * 1000
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                self.logger.error(
                    f"dynamodb.{operation} table not found "
                    f"({duration_ms:.1f}ms)"
                )
            elif error_code == "ProvisionedThroughputExceededException":
                self.logger.error(
                    f"dynamodb.{operation} throughput exceeded "
                    f"({duration_ms:.1f}ms)"
                )
            else:
                self.logger.error(
                    f"dynamodb.{operation} ClientError {error_code} "
                    f"({duration_ms:.1f}ms)"
                )
            raise DynamoDBOperationError(operation, error_code) from e
        except (ConnectionError, OSError) as e:
            duration_ms = (time.monotonic() - start) * 1000
            self.logger.error(
                f"dynamodb.{operation} connection error "
                f"({duration_ms:.1f}ms): {type(e).__name__}"
            )
            raise DynamoDBOperationError(operation, "Connection error") from e

    return wrapper


def _serialize_triaged_asset(asset: TriagedAsset) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "asset_code": asset.asset_code,
        "asset_description": asset.asset_description,
        "exchange": asset.exchange,
        "conviction": asset.conviction.value,
        "rationale": asset.rationale,
        "patterns": [p.value for p in asset.patterns],
        "ma50_slope": asset.ma50_slope,
        "rank": asset.rank,
        "country_code": asset.country_code,
    }
    if asset.workflow_triggers:
        item["workflow_triggers"] = [
            {
                "workflow_name": trigger.workflow_name,
                "direction": trigger.direction.name,
                "order_price": trigger.order_price,
                "trigger_close": trigger.trigger_close,
                "placed_at": trigger.placed_at,
                "dry_run": trigger.dry_run,
            }
            for trigger in asset.workflow_triggers
        ]
    return item


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

    _request_count: int = 0
    _total_duration_ms: float = 0.0

    def __init__(self, dynamodb_resource: Any = None) -> None:
        self.logger = Logger.get_logger("dynamodb_client", logging.INFO)
        self._dynamodb = dynamodb_resource
        self._session = aioboto3.Session()

    async def _get_table(self, table_name: str) -> Any:
        if self._dynamodb is None:
            raise RuntimeError(
                "DynamoDBClient requires an active dynamodb resource. "
                "Use it within a FastAPI lifespan or via run_async."
            )
        return await self._dynamodb.Table(table_name)

    @staticmethod
    def _convert_floats_to_decimal(obj: Any) -> Any:
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
        return country_code if country_code else "NONE"

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        avg_ms = (
            cls._total_duration_ms / cls._request_count
            if cls._request_count > 0
            else 0.0
        )
        return {
            "total_requests": cls._request_count,
            "total_duration_ms": round(cls._total_duration_ms, 1),
            "avg_latency_ms": round(avg_ms, 1),
        }

    @_dynamo_operation
    async def store_indicator(
        self,
        code: str,
        date: datetime.datetime,
        indicator_type: str,
        indicator: Any,
    ) -> Dict[str, Any]:
        indicator_str = dumps_indicator(indicator)
        md5_hash = hash_indicator(indicator_str)
        table = await self._get_table("indicators")
        response = await table.put_item(
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

    @_dynamo_operation
    async def get_indicator(self, indicator: Any) -> Optional[Any]:
        indicator_json = dumps_indicator(indicator)
        md5_hash = hash_indicator(indicator_json)
        table = await self._get_table("indicators")
        response = await table.get_item(Key={"id": md5_hash})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None
        if "Item" not in response:
            return None
        return json.loads(response["Item"]["json"])

    @_dynamo_operation
    async def get_indicator_by_id(self, id: str) -> Optional[Any]:
        table = await self._get_table("indicators")
        response = await table.get_item(Key={"id": id})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None
        if "Item" not in response:
            return None
        return json.loads(response["Item"]["json"])

    @_dynamo_operation
    async def add_to_watchlist(
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

        if asset_identifier is not None:
            item["asset_identifier"] = asset_identifier
        if asset_type is not None:
            item["asset_type"] = asset_type

        table = await self._get_table("watchlist")
        response = await table.put_item(Item=item)
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")
        return response

    @_dynamo_operation
    async def get_watchlist(self) -> list[Dict[str, Any]]:
        table = await self._get_table("watchlist")
        response = await table.scan()
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []
        return response.get("Items", [])

    @_dynamo_operation
    async def remove_from_watchlist(self, asset_id: str) -> Dict[str, Any]:
        table = await self._get_table("watchlist")
        response = await table.delete_item(Key={"id": asset_id})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB delete_item error: {response}")
        return response

    @_dynamo_operation
    async def is_in_watchlist(self, asset_id: str) -> bool:
        table = await self._get_table("watchlist")
        response = await table.get_item(Key={"id": asset_id})
        return "Item" in response

    @_dynamo_operation
    async def get_watchlist_item(
        self, asset_id: str
    ) -> tuple[bool, list[str]]:
        table = await self._get_table("watchlist")
        response = await table.get_item(Key={"id": asset_id})
        in_watchlist = "Item" in response
        labels = (
            response.get("Item", {}).get("labels", []) if in_watchlist else []
        )
        return in_watchlist, labels

    @_dynamo_operation
    async def update_watchlist_labels(
        self, asset_id: str, labels: list[str]
    ) -> Dict[str, Any]:
        table = await self._get_table("watchlist")
        response = await table.update_item(
            Key={"id": asset_id},
            UpdateExpression="SET labels = :labels",
            ExpressionAttributeValues={":labels": labels},
            ReturnValues="ALL_NEW",
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB update_item error: {response}")
        return response

    @_dynamo_operation
    async def set_asset_detail(
        self, asset_id: str, tradingview_url: str
    ) -> Dict[str, Any]:
        item = {
            "asset_id": asset_id,
            "tradingview_url": tradingview_url,
            "updated_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }

        table = await self._get_table("asset_details")
        response = await table.put_item(Item=item)
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")
        return response

    @_dynamo_operation
    async def get_asset_detail(
        self, asset_id: str
    ) -> Optional[Dict[str, Any]]:
        table = await self._get_table("asset_details")
        response = await table.get_item(Key={"asset_id": asset_id})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None
        return response.get("Item")

    @_dynamo_operation
    async def get_tradingview_link(self, asset_id: str) -> Optional[str]:
        detail = await self.get_asset_detail(asset_id)
        if detail:
            return detail.get("tradingview_url")
        return None

    @_dynamo_operation
    async def get_all_tradingview_links(self) -> Dict[str, str]:
        try:
            table = await self._get_table("asset_details")
            response = await table.scan(
                ProjectionExpression="asset_id, tradingview_url",
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                return {}

            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = await table.scan(
                    ProjectionExpression="asset_id, tradingview_url",
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            links = {
                item["asset_id"]: item["tradingview_url"]
                for item in items
                if "tradingview_url" in item and item["tradingview_url"]
            }

            self.logger.info(
                f"Loaded {len(links)} TradingView links from asset_details"
            )
            return links

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"DynamoDB ClientError fetching TradingView links: "
                f"{error_code}"
            )
            return {}
        except Exception as e:
            self.logger.error(f"Failed to fetch TradingView links: {e}")
            return {}

    @_dynamo_operation
    async def get_excluded_assets(self) -> List[str]:
        try:
            table = await self._get_table("asset_details")
            response = await table.scan(
                FilterExpression="is_excluded = :true_val",
                ExpressionAttributeValues={":true_val": True},
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                return []

            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = await table.scan(
                    FilterExpression="is_excluded = :true_val",
                    ExpressionAttributeValues={":true_val": True},
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            excluded_ids = [item["asset_id"] for item in items]
            self.logger.info(f"Found {len(excluded_ids)} excluded assets")
            return excluded_ids

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"DynamoDB ClientError getting excluded assets: {error_code}"
            )
            return []
        except Exception as e:
            self.logger.error(f"Error getting excluded assets: {e}")
            return []

    @_dynamo_operation
    async def update_asset_exclusion(
        self, asset_id: str, is_excluded: bool
    ) -> bool:
        try:
            updated_at = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()

            table = await self._get_table("asset_details")
            response = await table.update_item(
                Key={"asset_id": asset_id},
                UpdateExpression=(
                    "SET is_excluded = :is_excluded, updated_at = :updated_at"
                ),
                ExpressionAttributeValues={
                    ":is_excluded": is_excluded,
                    ":updated_at": updated_at,
                },
                ReturnValues="ALL_NEW",
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB update_item error: {response}")
                return False

            self.logger.info(
                f"Updated exclusion for {asset_id}: is_excluded={is_excluded}"
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"DynamoDB ClientError updating exclusion for "
                f"{asset_id}: {error_code}"
            )
            return False
        except Exception as e:
            self.logger.error(f"Error updating exclusion for {asset_id}: {e}")
            return False

    @_dynamo_operation
    async def get_all_asset_details(self) -> List[Dict[str, Any]]:
        try:
            table = await self._get_table("asset_details")
            response = await table.scan()

            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                return []

            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = await table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            for item in items:
                if "is_excluded" not in item:
                    item["is_excluded"] = False

            self.logger.info(f"Retrieved {len(items)} asset details")
            return items

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"DynamoDB ClientError getting asset details: {error_code}"
            )
            return []
        except Exception as e:
            self.logger.error(f"Error getting all asset details: {e}")
            return []

    @_dynamo_operation
    async def store_alerts(
        self,
        asset_code: str,
        country_code: Optional[str],
        alerts: list,
    ) -> Dict[str, Any]:
        country_code_value = self._normalize_country_code(country_code)

        existing_alerts = await self.get_alerts(asset_code, country_code)

        existing_signatures = set()
        for existing in existing_alerts:
            try:
                existing_signatures.add(
                    alert_dedup_signature(
                        existing["alert_type"],
                        existing["date"],
                        existing.get("data"),
                    )
                )
            except (KeyError, ValueError):
                continue

        unique_alerts = []
        for alert in alerts:
            signature = alert.dedup_signature
            if signature not in existing_signatures:
                unique_alerts.append(alert)
                existing_signatures.add(signature)

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

        table = await self._get_table("alerts")
        response = await table.update_item(
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

    @_dynamo_operation
    async def get_alerts(
        self, asset_code: str, country_code: Optional[str]
    ) -> list:
        country_code_value = self._normalize_country_code(country_code)

        table = await self._get_table("alerts")
        response = await table.get_item(
            Key={"asset_code": asset_code, "country_code": country_code_value}
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return []

        if "Item" not in response:
            return []

        return response["Item"].get("alerts", [])

    @_dynamo_operation
    async def get_all_alerts(self) -> List[Alert]:
        table = await self._get_table("alerts")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []

        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            response = await table.scan(
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

    @_dynamo_operation
    async def get_last_run_at(
        self, asset_code: str, country_code: Optional[str]
    ) -> Optional[datetime.datetime]:
        country_code_value = self._normalize_country_code(country_code)

        table = await self._get_table("alerts")
        response = await table.get_item(
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

    @_dynamo_operation
    async def update_last_run_at(
        self, asset_code: str, country_code: Optional[str]
    ) -> None:
        country_code_value = self._normalize_country_code(country_code)
        now = datetime.datetime.now()

        table = await self._get_table("alerts")
        response = await table.update_item(
            Key={"asset_code": asset_code, "country_code": country_code_value},
            UpdateExpression="SET last_run_at = :last_run_at",
            ExpressionAttributeValues={":last_run_at": now.isoformat()},
            ReturnValues="UPDATED_NEW",
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB update_item error: {response}")

    @_dynamo_operation
    async def get_all_workflows(self) -> List[Dict[str, Any]]:
        workflows: List[Dict[str, Any]] = []
        table = await self._get_table("workflows")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return workflows

        workflows.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                break
            workflows.extend(response.get("Items", []))

        return workflows

    @_dynamo_operation
    async def get_workflow_by_id(
        self, workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        table = await self._get_table("workflows")
        response = await table.get_item(Key={"id": workflow_id})

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None

        return response.get("Item")

    @_dynamo_operation
    async def batch_put_workflows(
        self, workflows: List[Dict[str, Any]]
    ) -> None:
        table = await self._get_table("workflows")

        async with table.batch_writer() as batch:
            for workflow in workflows:
                converted_workflow = self._convert_floats_to_decimal(workflow)
                await batch.put_item(Item=converted_workflow)

        self.logger.info(f"Batch inserted {len(workflows)} workflows")

    @_dynamo_operation
    async def put_workflow(self, workflow: Dict[str, Any]) -> None:
        table = await self._get_table("workflows")
        response = await table.put_item(Item=workflow)
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")
            raise RuntimeError("Failed to persist workflow")

    @_dynamo_operation
    async def delete_workflow(self, workflow_id: str) -> None:
        table = await self._get_table("workflows")
        response = await table.delete_item(Key={"id": workflow_id})
        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(
                f"DynamoDB delete_item error for workflow {workflow_id}: "
                f"{response}"
            )
            raise RuntimeError("Failed to delete workflow")

    @_dynamo_operation
    async def record_workflow_order(
        self,
        workflow_id: str,
        workflow_name: str,
        order_code: str,
        order_price: float,
        order_quantity: float,
        order_direction: str,
        order_type: str,
        asset_type: Optional[str] = None,
        trigger_close: Optional[float] = None,
        execution_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc)
        placed_at = int(now.timestamp())
        ttl = placed_at + (7 * 24 * 60 * 60)

        item = {
            "id": str(uuid.uuid4()),
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "placed_at": placed_at,
            "order_code": order_code,
            "order_price": order_price,
            "order_quantity": order_quantity,
            "order_direction": order_direction,
            "order_type": order_type,
            "ttl": ttl,
        }

        if asset_type:
            item["asset_type"] = asset_type
        if trigger_close is not None:
            item["trigger_close"] = trigger_close
        if execution_context:
            item["execution_context"] = execution_context

        item = self._convert_floats_to_decimal(item)

        table = await self._get_table("workflow_orders")
        response = await table.put_item(Item=item)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")

        return response

    @_dynamo_operation
    async def get_all_workflow_orders(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        orders: List[Dict[str, Any]] = []
        table = await self._get_table("workflow_orders")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return orders

        orders.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                break
            orders.extend(response.get("Items", []))

        orders.sort(key=lambda o: int(o.get("placed_at", 0)), reverse=True)

        if limit is not None:
            orders = orders[:limit]

        return orders

    @_dynamo_operation
    async def get_workflow_orders(
        self, workflow_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        try:
            query_params = {
                "KeyConditionExpression": "workflow_id = :wf_id",
                "ExpressionAttributeValues": {":wf_id": workflow_id},
                "ScanIndexForward": False,
            }

            if limit:
                query_params["Limit"] = limit

            table = await self._get_table("workflow_orders")
            response = await table.query(**query_params)

            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB query error: {response}")
                return []

            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                query_params["ExclusiveStartKey"] = response[
                    "LastEvaluatedKey"
                ]
                response = await table.query(**query_params)
                items.extend(response.get("Items", []))

            return items

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"DynamoDB ClientError querying orders for "
                f"workflow {workflow_id}: {error_code}"
            )
            return []
        except Exception as e:
            self.logger.error(
                f"Error querying orders for workflow {workflow_id}: {e}"
            )
            return []

    @_dynamo_operation
    async def store_alert_digest(self, digest: AlertDigest) -> Dict[str, Any]:
        item = {
            "run_date": digest.run_date,
            "created_at": digest.created_at,
            "summary": digest.summary,
            "counts": digest.counts,
            "triaged_assets": [
                _serialize_triaged_asset(asset)
                for asset in digest.triaged_assets
            ],
            "fallback_used": digest.fallback_used,
            "model": digest.model,
        }
        item = self._convert_floats_to_decimal(item)

        table = await self._get_table("alert_digests")
        response = await table.put_item(Item=item)

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")

        return response

    @_dynamo_operation
    async def get_alert_digests(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        digests: List[Dict[str, Any]] = []
        table = await self._get_table("alert_digests")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return digests

        digests.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                break
            digests.extend(response.get("Items", []))

        digests.sort(key=lambda d: int(d.get("created_at", 0)), reverse=True)

        if limit is not None:
            digests = digests[:limit]

        return digests

    @_dynamo_operation
    async def get_alert_digest(
        self, run_date: str
    ) -> Optional[Dict[str, Any]]:
        table = await self._get_table("alert_digests")
        response = await table.query(
            KeyConditionExpression="run_date = :run_date",
            ExpressionAttributeValues={":run_date": run_date},
            ScanIndexForward=False,
            Limit=1,
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB query error: {response}")
            return None

        items = response.get("Items", [])
        return items[0] if items else None

    # The table's hash key attribute is named "definition_code" for
    # historical reasons: it held a per-definition key until the cache was
    # re-keyed on (instrument, session). Renaming a DynamoDB key attribute
    # means replacing the table, so the attribute keeps its name while the
    # value it carries is now whatever cache key the caller computed.
    @_dynamo_operation
    async def get_cached_backtest_candles(
        self, cache_key: str, trading_date: str
    ) -> Optional[Dict[str, Any]]:
        table = await self._get_table("backtest_candle_cache")
        response = await table.get_item(
            Key={
                "definition_code": cache_key,
                "trading_date": trading_date,
            }
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB get_item error: {response}")
            return None

        return response.get("Item")

    @_dynamo_operation
    async def store_backtest_candles(
        self,
        cache_key: str,
        trading_date: str,
        has_data: bool,
        h1_candle: Optional[Dict[str, Any]] = None,
        m5_candles: Optional[List[Dict[str, Any]]] = None,
        m5_fetched: bool = True,
        only_if_absent: bool = False,
    ) -> Dict[str, Any]:
        """only_if_absent makes the write conditional on nothing being
        cached for this key yet. Used for a partial entry, which must
        never overwrite the richer entry another concurrent run may have
        just written for the same day."""
        item: Dict[str, Any] = {
            "definition_code": cache_key,
            "trading_date": trading_date,
            "has_data": has_data,
            "cached_at": int(time.time()),
        }
        if has_data:
            item["h1_candle"] = h1_candle
            item["m5_candles"] = m5_candles or []
            item["m5_fetched"] = m5_fetched
        item = self._convert_floats_to_decimal(item)

        kwargs: Dict[str, Any] = {"Item": item}
        if only_if_absent:
            kwargs["ConditionExpression"] = (
                "attribute_not_exists(definition_code)"
            )

        table = await self._get_table("backtest_candle_cache")
        try:
            response = await table.put_item(**kwargs)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code != "ConditionalCheckFailedException":
                raise
            # Someone else cached this day first, which is the whole point
            # of the condition - not an error.
            self.logger.debug(
                f"Skipped conditional write for {cache_key}/{trading_date}: "
                "an entry already exists"
            )
            return {}

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB put_item error: {response}")

        return response

    @_dynamo_operation
    async def scan_backtest_candles(self) -> List[Dict[str, Any]]:
        """Every item in the raw-candle cache. Only the cache migration
        needs this - the backtests themselves always read a single
        (cache key, trading date) item."""
        table = await self._get_table("backtest_candle_cache")
        response = await table.scan()

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB scan error: {response}")
            return []

        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                self.logger.error(f"DynamoDB scan error: {response}")
                break
            items.extend(response.get("Items", []))

        return items

    @_dynamo_operation
    async def delete_backtest_candles(
        self, cache_key: str, trading_date: str
    ) -> Dict[str, Any]:
        table = await self._get_table("backtest_candle_cache")
        response = await table.delete_item(
            Key={
                "definition_code": cache_key,
                "trading_date": trading_date,
            }
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
            self.logger.error(f"DynamoDB delete_item error: {response}")

        return response


_store: Optional[DynamoDBClient] = None


@asynccontextmanager
async def dynamodb_session(
    region_name: str = AWS_REGION,
) -> AsyncIterator[None]:
    """Hold the DynamoDB connection open for the life of the context.

    Nothing is yielded on purpose. The client, its aioboto3 session and its
    resource stay inside this module; callers ask this module for the data
    they want instead of being handed a client to drive. A layer that only
    needs yesterday's alerts should not have to know that DynamoDB is what
    is underneath, nor be able to reach past the methods it is offered.

    Long-lived by design - a server holds this open for its whole run,
    rather than opening a connection per request.
    """
    global _store
    session = aioboto3.Session()
    async with session.resource(
        "dynamodb", region_name=region_name
    ) as resource:
        _store = DynamoDBClient(dynamodb_resource=resource)
        try:
            yield
        finally:
            _store = None


def is_dynamodb_available() -> bool:
    """Whether a connection is currently open.

    Callers check this to answer "unavailable" in their own vocabulary
    rather than letting a missing connection surface as a crash.
    """
    return _store is not None
