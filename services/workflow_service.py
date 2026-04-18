import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from client.aws_client import DynamoDBClient
from model.workflow import IndicatorType, WorkflowSignal
from model.workflow_api import (
    AllWorkflowOrderItem,
    CloseDetail,
    ConditionDetail,
    IndicatorDetail,
    TriggerDetail,
    WorkflowCreateRequest,
    WorkflowDetail,
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowOrderListItem,
)
from utils.logger import Logger


class WorkflowService:
    """Service for workflow management operations"""

    def __init__(self, dynamodb_client: DynamoDBClient) -> None:
        self.logger = Logger.get_logger("workflow_service", logging.INFO)
        self.dynamodb_client = dynamodb_client

    async def list_workflows(self) -> WorkflowListResponse:
        workflows_data = await self.dynamodb_client.get_all_workflows()

        workflow_items = [
            self._convert_to_list_item(w) for w in workflows_data
        ]

        for workflow_item in workflow_items:
            last_order = await self._get_last_order_for_workflow(
                workflow_item.id
            )
            if last_order:
                workflow_item.last_order_timestamp = int(
                    last_order["placed_at"]
                )
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

    async def create_workflow(
        self, data: WorkflowCreateRequest
    ) -> WorkflowDetail:
        self._validate_request(data)
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        workflow_dict = self._build_workflow_dict(data, str(uuid.uuid4()), now)
        converted = self.dynamodb_client._convert_floats_to_decimal(
            workflow_dict
        )
        await self.dynamodb_client.put_workflow(converted)
        return self._convert_to_detail(workflow_dict)

    def _validate_request(self, data: WorkflowCreateRequest) -> None:
        if data.end_date is not None:
            try:
                end_dt = datetime.fromisoformat(data.end_date)
            except ValueError:
                raise ValueError(
                    f"Invalid end_date format: {data.end_date!r}. "
                    "Expected YYYY-MM-DD."
                )
            if end_dt.date() < datetime.utcnow().date():
                raise ValueError(
                    f"end_date must be a future date, got {data.end_date!r}"
                )

        indicator = data.conditions[0].indicator
        pol_or_zone = (IndicatorType.POL.value, IndicatorType.ZONE.value)
        if indicator.name in pol_or_zone:
            if indicator.value is None:
                raise ValueError(
                    f"indicator.value is required when indicator name is "
                    f"{indicator.name!r}"
                )
        if indicator.name == IndicatorType.ZONE.value:
            if indicator.zone_value is None:
                raise ValueError(
                    "indicator.zone_value is required when indicator name "
                    f"is {IndicatorType.ZONE.value!r}"
                )

    def _build_workflow_dict(
        self, data: WorkflowCreateRequest, workflow_id: str, created_at: str
    ) -> Dict[str, Any]:
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "id": workflow_id,
            "name": data.name,
            "index": data.index,
            "cfd": data.cfd,
            "enable": data.enable,
            "dry_run": data.dry_run,
            "is_us": data.is_us,
            "end_date": data.end_date,
            "conditions": [
                {
                    "indicator": {
                        "name": c.indicator.name,
                        "ut": c.indicator.ut,
                        "value": c.indicator.value,
                        "zone_value": c.indicator.zone_value,
                    },
                    "close": {
                        "direction": c.close.direction,
                        "ut": c.close.ut,
                        "spread": c.close.spread,
                    },
                    "element": c.element,
                }
                for c in data.conditions
            ],
            "trigger": {
                "ut": data.trigger.ut,
                "signal": WorkflowSignal.BREAKOUT.value,
                "location": data.trigger.location,
                "order_direction": data.trigger.order_direction,
                "quantity": data.trigger.quantity,
            },
            "created_at": created_at,
            "updated_at": now,
        }

    async def update_workflow(
        self, workflow_id: str, data: WorkflowCreateRequest
    ) -> WorkflowDetail:
        existing = await self.dynamodb_client.get_workflow_by_id(workflow_id)
        if existing is None:
            raise ValueError(f"Workflow not found: {workflow_id!r}")

        self._validate_request(data)

        created_at = str(existing.get("created_at", ""))
        workflow_dict = self._build_workflow_dict(
            data, workflow_id, created_at
        )
        converted = self.dynamodb_client._convert_floats_to_decimal(
            workflow_dict
        )
        await self.dynamodb_client.put_workflow(converted)
        return self._convert_to_detail(workflow_dict)

    async def delete_workflow(self, workflow_id: str) -> None:
        existing = await self.dynamodb_client.get_workflow_by_id(workflow_id)
        if existing is None:
            raise ValueError(f"Workflow not found: {workflow_id!r}")
        await self.dynamodb_client.delete_workflow(workflow_id)

    async def get_workflow_by_id(
        self, workflow_id: str
    ) -> Optional[WorkflowDetail]:
        workflow_data = await self.dynamodb_client.get_workflow_by_id(
            workflow_id
        )
        if not workflow_data:
            return None
        return self._convert_to_detail(workflow_data)

    async def get_workflows_by_asset(
        self, code: str, country_code: str = "xpar"
    ) -> List[WorkflowDetail]:
        symbol = f"{code}:{country_code}" if country_code else code
        workflows_data = await self.dynamodb_client.get_all_workflows()

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

    async def get_workflow_order_history(
        self, workflow_id: str, limit: int = 20
    ) -> List[WorkflowOrderListItem]:
        orders_data = await self.dynamodb_client.get_workflow_orders(
            workflow_id=workflow_id, limit=limit
        )
        return [
            self._convert_order_to_list_item(order) for order in orders_data
        ]

    async def get_all_orders(
        self, limit: int = 100
    ) -> List[AllWorkflowOrderItem]:
        orders_data = await self.dynamodb_client.get_all_workflow_orders(
            limit=limit
        )
        return [
            self._convert_all_order_to_item(order) for order in orders_data
        ]

    def _convert_all_order_to_item(
        self, order_data: Dict[str, Any]
    ) -> AllWorkflowOrderItem:
        from decimal import Decimal

        return AllWorkflowOrderItem(
            id=order_data["id"],
            workflow_id=order_data["workflow_id"],
            workflow_name=order_data["workflow_name"],
            placed_at=int(order_data["placed_at"]),
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

    def _convert_order_to_list_item(
        self, order_data: Dict[str, Any]
    ) -> WorkflowOrderListItem:
        from decimal import Decimal

        return WorkflowOrderListItem(
            id=order_data["id"],
            workflow_id=order_data["workflow_id"],
            placed_at=int(order_data["placed_at"]),
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

    async def _get_last_order_for_workflow(
        self, workflow_id: str
    ) -> Dict[str, Any] | None:
        try:
            orders = await self.dynamodb_client.get_workflow_orders(
                workflow_id=workflow_id, limit=1
            )
            return orders[0] if orders else None
        except Exception as e:
            self.logger.error(
                f"Error fetching last order for workflow {workflow_id}: {e}"
            )
            return None
