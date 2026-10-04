"""The workflows armed on an asset: what could fire next.

Reads the same DynamoDB table the workflow engine runs from, never the
local workflows.yml - a stale file answered as the live configuration is
the stored-data version of serving simulated candles.
"""

from typing import List, Optional

from mcp.server.mcpserver.exceptions import ToolError

from client.aws_client import DynamoDBClient
from mcp_server.models import ActiveWorkflow, AssetWorkflows
from services.workflow_service import WorkflowService
from utils.helper import get_date_utc0


async def get_workflows(
    code: str, store: Optional[DynamoDBClient]
) -> AssetWorkflows:
    # Checked here rather than left to the boundary: a client with no
    # resource raises a bare RuntimeError, which surfaces as an opaque crash.
    if store is None:
        raise ToolError(
            "The workflow store is unreachable (AWS_PROFILE not set, or the "
            "connection failed at startup), so active workflows cannot be "
            "read. Market-data tools are unaffected."
        )

    active = await WorkflowService(store).get_active_workflows_by_asset(
        code, get_date_utc0().date()
    )
    workflows = [
        ActiveWorkflow(
            id=detail.id,
            name=detail.name,
            index=detail.index,
            cfd=detail.cfd,
            dry_run=detail.dry_run,
            end_date=detail.end_date,
            conditions=detail.conditions,
            trigger=detail.trigger,
        )
        for detail in active.workflows
    ]
    return AssetWorkflows(
        code=code,
        workflows=workflows,
        none_reason=_none_reason(code, workflows, active.unreadable),
        unreadable_workflows=active.unreadable,
    )


def _none_reason(
    code: str, workflows: List[ActiveWorkflow], unreadable: List[str]
) -> Optional[str]:
    if workflows:
        return None
    if unreadable:
        return (
            f"No readable active workflow on {code}; "
            "see unreadable_workflows"
        )
    return f"No enabled, unexpired workflow watches or trades {code}"
