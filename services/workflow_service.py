import logging
import math
from typing import Any, Dict, List, Optional

from client.aws_client import DynamoDBClient
from model.workflow_api import (
    CloseDetail,
    ConditionDetail,
    IndicatorDetail,
    TriggerDetail,
    WorkflowDetail,
    WorkflowListItem,
    WorkflowListResponse,
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

    def list_workflows(
        self,
        page: int = 1,
        per_page: int = 20,
        enabled: Optional[bool] = None,
        index: Optional[str] = None,
        indicator_type: Optional[str] = None,
        dry_run: Optional[bool] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> WorkflowListResponse:
        """
        List all workflows with filtering, sorting, and pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            enabled: Filter by enabled status
            index: Filter by index (case-insensitive partial match)
            indicator_type: Filter by indicator type in conditions
            dry_run: Filter by dry run mode
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            WorkflowListResponse with paginated results
        """
        workflows_data = self.dynamodb_client.get_all_workflows()

        filtered = self._apply_filters(
            workflows_data, enabled, index, indicator_type, dry_run
        )

        sorted_workflows = self._apply_sorting(filtered, sort_by, sort_order)

        workflow_items = [
            self._convert_to_list_item(w) for w in sorted_workflows
        ]

        total = len(workflow_items)
        total_pages = math.ceil(total / per_page) if total > 0 else 1

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated = workflow_items[start_idx:end_idx]

        return WorkflowListResponse(
            workflows=paginated,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    def _apply_filters(
        self,
        workflows: List[Dict[str, Any]],
        enabled: Optional[bool],
        index: Optional[str],
        indicator_type: Optional[str],
        dry_run: Optional[bool],
    ) -> List[Dict[str, Any]]:
        """Apply filters to workflow list"""
        filtered = workflows

        if enabled is not None:
            filtered = [w for w in filtered if w.get("enable") == enabled]

        if index:
            index_lower = index.lower()
            filtered = [
                w
                for w in filtered
                if index_lower in w.get("index", "").lower()
            ]

        if indicator_type:
            filtered = [
                w
                for w in filtered
                if any(
                    c.get("indicator", {}).get("name") == indicator_type
                    for c in w.get("conditions", [])
                )
            ]

        if dry_run is not None:
            filtered = [w for w in filtered if w.get("dry_run") == dry_run]

        return filtered

    def _apply_sorting(
        self, workflows: List[Dict[str, Any]], sort_by: str, sort_order: str
    ) -> List[Dict[str, Any]]:
        """Apply sorting to workflow list"""
        reverse = sort_order == "desc"

        def get_sort_key(w: Dict[str, Any]) -> Any:
            if sort_by == "end_date":
                return w.get("end_date") or ""
            return w.get(sort_by, "")

        return sorted(workflows, key=get_sort_key, reverse=reverse)

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
