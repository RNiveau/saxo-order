from typing import List

from api.models.workflow import (
    WorkflowCloseInfo,
    WorkflowConditionInfo,
    WorkflowIndicatorInfo,
    WorkflowInfo,
    WorkflowTriggerInfo,
)
from engines.workflow_loader import load_workflows
from model.workflow import Workflow
from utils.logger import Logger

logger = Logger.get_logger("workflow_service")


class WorkflowService:
    def __init__(self, force_from_disk: bool = False):
        self.force_from_disk = force_from_disk

    def get_workflows_by_asset(
        self, code: str, country_code: str = "xpar"
    ) -> List[WorkflowInfo]:
        """
        Get all workflows associated with a specific asset.

        Args:
            code: Asset code (e.g., "itp", "DAX.I")
            country_code: Country code (e.g., "xpar"). Defaults to "xpar".

        Returns:
            List of WorkflowInfo objects matching the asset
        """
        # Construct possible symbol formats
        symbol = f"{code}:{country_code}" if country_code else code

        # Load workflows
        workflows = load_workflows(self.force_from_disk)

        # Filter workflows by index matching the asset
        matching_workflows = [
            w
            for w in workflows
            if w.index.lower() == code.lower()
            or w.index.lower() == symbol.lower()
        ]

        # Transform to API models
        return [
            self._workflow_to_info(workflow) for workflow in matching_workflows
        ]

    def _workflow_to_info(self, workflow: Workflow) -> WorkflowInfo:
        """Convert Workflow domain model to WorkflowInfo API model."""
        return WorkflowInfo(
            name=workflow.name,
            index=workflow.index,
            cfd=workflow.cfd,
            enabled=workflow.enable,
            dry_run=workflow.dry_run,
            end_date=(
                workflow.end_date.strftime("%Y-%m-%d")
                if workflow.end_date
                else None
            ),
            is_us=workflow.is_us,
            conditions=[
                WorkflowConditionInfo(
                    indicator=WorkflowIndicatorInfo(
                        name=cond.indicator.name.value,
                        unit_time=cond.indicator.ut.value,
                        value=cond.indicator.value,
                        zone_value=cond.indicator.zone_value,
                    ),
                    close=WorkflowCloseInfo(
                        direction=cond.close.direction.value,
                        unit_time=cond.close.ut.value,
                        spread=cond.close.spread,
                    ),
                    element=(cond.element.value if cond.element else None),
                )
                for cond in workflow.conditions
            ],
            trigger=WorkflowTriggerInfo(
                unit_time=workflow.trigger.ut.value,
                signal=workflow.trigger.signal.value,
                location=workflow.trigger.location.value,
                order_direction=workflow.trigger.order_direction.value,
                quantity=workflow.trigger.quantity,
            ),
        )
