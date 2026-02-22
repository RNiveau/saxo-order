import logging
from typing import Any, Dict, List, Optional

from cachetools import TTLCache, cachedmethod
from cachetools.keys import hashkey

from client.aws_client import DynamoDBClient
from model.workflow_api import (
    CloseDetail,
    ConditionDetail,
    IndicatorDetail,
    TriggerDetail,
    WorkflowDetail,
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowOrderListItem,
)
from utils.logger import Logger


class WorkflowService:
    """Service for workflow management operations"""

    def __init__(self, dynamodb_client: DynamoDBClient) -> None:
        """
        Initialize WorkflowService with DynamoDB client dependency.

        Args:
            dynamodb_client: DynamoDB client for data access
        """
        self.logger = Logger.get_logger("workflow_service", logging.INFO)
        self.dynamodb_client = dynamodb_client
        # 10-minute TTL cache for workflow data
        self._cache: TTLCache = TTLCache(maxsize=1, ttl=600)

    @cachedmethod(lambda self: self._cache, key=lambda self: hashkey())
    def _get_cached_workflows(self) -> List[Dict[str, Any]]:
        """
        Get all workflows from DynamoDB with 10-minute TTL cache.

        Returns:
            List of workflow data dictionaries
        """
        return self.dynamodb_client.get_all_workflows()

    def list_workflows(self) -> WorkflowListResponse:
        """
        List all workflows without filtering or pagination.
        Filtering and sorting are handled on the frontend.

        Returns:
            WorkflowListResponse with all workflows
        """
        workflows_data = self._get_cached_workflows()

        workflow_items = [
            self._convert_to_list_item(w) for w in workflows_data
        ]

        # Enrich each workflow with last order information
        for workflow_item in workflow_items:
            last_order = self._get_last_order_for_workflow(workflow_item.id)
            if last_order:
                workflow_item.last_order_timestamp = last_order["placed_at"]
                workflow_item.last_order_direction = last_order[
                    "order_direction"
                ]
                workflow_item.last_order_quantity = float(
                    last_order["order_quantity"]
                )

        total = len(workflow_items)

        return WorkflowListResponse(
            workflows=workflow_items,
            total=total,
            page=1,
            per_page=total,
            total_pages=1,
        )

    def get_workflow_by_id(self, workflow_id: str) -> Optional[WorkflowDetail]:
        """
        Get a single workflow by its ID.

        Args:
            workflow_id: UUID of the workflow

        Returns:
            WorkflowDetail if found, None otherwise
        """
        workflow_data = self.dynamodb_client.get_workflow_by_id(workflow_id)
        if not workflow_data:
            return None
        return self._convert_to_detail(workflow_data)

    def get_workflows_by_asset(
        self, code: str, country_code: str = "xpar"
    ) -> List[WorkflowDetail]:
        """
        Get all workflows associated with a specific asset.

        Args:
            code: Asset code (e.g., "itp", "DAX.I")
            country_code: Country code (e.g., "xpar"). Defaults to "xpar".

        Returns:
            List of WorkflowDetail objects matching the asset
        """
        symbol = f"{code}:{country_code}" if country_code else code
        workflows_data = self._get_cached_workflows()

        matching_workflows = [
            w
            for w in workflows_data
            if w.get("index", "").lower() == code.lower()
            or w.get("index", "").lower() == symbol.lower()
        ]

        return [self._convert_to_detail(w) for w in matching_workflows]

    def _convert_to_list_item(
        self, workflow_data: Dict[str, Any]
    ) -> WorkflowListItem:
        """Convert DynamoDB dict to WorkflowListItem"""
        conditions = workflow_data.get("conditions", [])
        primary_indicator = None
        primary_unit_time = None

        if conditions:
            first_condition = conditions[0]
            indicator = first_condition.get("indicator", {})
            primary_indicator = indicator.get("name")
            primary_unit_time = indicator.get("ut")

        return WorkflowListItem(
            id=workflow_data["id"],
            name=workflow_data["name"],
            index=workflow_data["index"],
            cfd=workflow_data["cfd"],
            enable=workflow_data["enable"],
            dry_run=workflow_data.get("dry_run", False),
            is_us=workflow_data.get("is_us", False),
            end_date=workflow_data.get("end_date"),
            primary_indicator=primary_indicator,
            primary_unit_time=primary_unit_time,
            created_at=workflow_data["created_at"],
            updated_at=workflow_data["updated_at"],
            last_order_timestamp=None,
            last_order_direction=None,
            last_order_quantity=None,
        )

    def _convert_to_detail(
        self, workflow_data: Dict[str, Any]
    ) -> WorkflowDetail:
        """Convert DynamoDB dict to WorkflowDetail with nested structures"""
        conditions_data = workflow_data.get("conditions", [])
        conditions = []

        for cond_data in conditions_data:
            indicator_data = cond_data.get("indicator", {})
            indicator = IndicatorDetail(
                name=indicator_data.get("name"),
                ut=indicator_data.get("ut"),
                value=(
                    float(indicator_data["value"])
                    if indicator_data.get("value")
                    else None
                ),
                zone_value=(
                    float(indicator_data["zone_value"])
                    if indicator_data.get("zone_value")
                    else None
                ),
            )

            close_data = cond_data.get("close", {})
            close = CloseDetail(
                direction=close_data.get("direction"),
                ut=close_data.get("ut"),
                spread=float(close_data.get("spread", 0)),
            )

            condition = ConditionDetail(
                indicator=indicator,
                close=close,
                element=cond_data.get("element"),
            )
            conditions.append(condition)

        trigger_data = workflow_data.get("trigger", {})
        trigger = TriggerDetail(
            ut=trigger_data.get("ut"),
            signal=trigger_data.get("signal"),
            location=trigger_data.get("location"),
            order_direction=trigger_data.get("order_direction"),
            quantity=float(trigger_data.get("quantity", 0)),
        )

        return WorkflowDetail(
            id=workflow_data["id"],
            name=workflow_data["name"],
            index=workflow_data["index"],
            cfd=workflow_data["cfd"],
            enable=workflow_data["enable"],
            dry_run=workflow_data.get("dry_run", False),
            is_us=workflow_data.get("is_us", False),
            end_date=workflow_data.get("end_date"),
            conditions=conditions,
            trigger=trigger,
            created_at=workflow_data["created_at"],
            updated_at=workflow_data["updated_at"],
        )

    def get_workflow_order_history(
        self, workflow_id: str, limit: int = 20
    ) -> List[WorkflowOrderListItem]:
        """
        Get order history for a specific workflow.

        Args:
            workflow_id: UUID of the workflow
            limit: Maximum number of orders to return (default 20)

        Returns:
            List of WorkflowOrderListItem objects (newest first)
        """
        orders_data = self.dynamodb_client.get_workflow_orders(
            workflow_id=workflow_id, limit=limit
        )
        return [
            self._convert_order_to_list_item(order) for order in orders_data
        ]

    def _convert_order_to_list_item(
        self, order_data: Dict[str, Any]
    ) -> WorkflowOrderListItem:
        """
        Convert DynamoDB order dict to WorkflowOrderListItem.

        Args:
            order_data: Raw order data from DynamoDB

        Returns:
            WorkflowOrderListItem with converted fields
        """
        from decimal import Decimal

        return WorkflowOrderListItem(
            id=order_data["id"],
            workflow_id=order_data["workflow_id"],
            placed_at=order_data["placed_at"],
            order_code=order_data["order_code"],
            order_price=(
                float(order_data["order_price"])
                if isinstance(order_data["order_price"], Decimal)
                else order_data["order_price"]
            ),
            order_quantity=(
                float(order_data["order_quantity"])
                if isinstance(order_data["order_quantity"], Decimal)
                else order_data["order_quantity"]
            ),
            order_direction=order_data["order_direction"],
        )

    def _get_last_order_for_workflow(
        self, workflow_id: str
    ) -> Dict[str, Any] | None:
        """
        Get the most recent order for a specific workflow.

        Args:
            workflow_id: UUID of the workflow

        Returns:
            Order data dict or None if no orders exist
        """
        try:
            orders = self.dynamodb_client.get_workflow_orders(
                workflow_id=workflow_id, limit=1
            )
            return orders[0] if orders else None
        except Exception as e:
            self.logger.error(
                f"Error fetching last order for workflow {workflow_id}: {e}"
            )
            return None
