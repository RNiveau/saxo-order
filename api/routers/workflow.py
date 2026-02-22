from fastapi import APIRouter, Depends, HTTPException, Path, Query

from api.dependencies import get_workflow_service
from api.models.workflow import (
    AssetWorkflowsResponse,
    WorkflowCloseInfo,
    WorkflowConditionInfo,
    WorkflowIndicatorInfo,
    WorkflowInfo,
    WorkflowOrderHistoryResponse,
    WorkflowTriggerInfo,
)
from model.workflow_api import WorkflowDetail, WorkflowListResponse
from services.workflow_service import WorkflowService
from utils.logger import Logger

router = APIRouter(prefix="/api/workflow", tags=["workflow"])
logger = Logger.get_logger("workflow_router")


def _convert_detail_to_info(detail: WorkflowDetail) -> WorkflowInfo:
    """Convert WorkflowDetail to WorkflowInfo format."""
    return WorkflowInfo(
        name=detail.name,
        index=detail.index,
        cfd=detail.cfd,
        enabled=detail.enable,
        dry_run=detail.dry_run,
        end_date=detail.end_date,
        is_us=detail.is_us,
        conditions=[
            WorkflowConditionInfo(
                indicator=WorkflowIndicatorInfo(
                    name=cond.indicator.name,
                    unit_time=cond.indicator.ut,
                    value=cond.indicator.value,
                    zone_value=cond.indicator.zone_value,
                ),
                close=WorkflowCloseInfo(
                    direction=cond.close.direction,
                    unit_time=cond.close.ut,
                    spread=cond.close.spread,
                ),
                element=cond.element,
            )
            for cond in detail.conditions
        ],
        trigger=WorkflowTriggerInfo(
            unit_time=detail.trigger.ut,
            signal=detail.trigger.signal,
            location=detail.trigger.location,
            order_direction=detail.trigger.order_direction,
            quantity=detail.trigger.quantity,
        ),
    )


@router.get("/asset", response_model=AssetWorkflowsResponse)
async def get_asset_workflows(
    code: str = Query(
        ...,
        description="Asset code (e.g., 'itp', 'DAX.I')",
        min_length=1,
    ),
    country_code: str = Query(
        "xpar",
        description="Country code of the asset (e.g., 'xpar')",
    ),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Get all workflows associated with a specific asset from DynamoDB.

    Returns workflows matching the asset code, including their
    configuration, conditions, and trigger settings.
    Uses the same 10-minute cache as the workflows list endpoint.
    """
    try:
        workflow_details = workflow_service.get_workflows_by_asset(
            code=code, country_code=country_code
        )

        symbol = f"{code}:{country_code}" if country_code else code

        workflows_info = [
            _convert_detail_to_info(detail) for detail in workflow_details
        ]

        return AssetWorkflowsResponse(
            asset_symbol=symbol,
            total=len(workflows_info),
            workflows=workflows_info,
        )

    except Exception as e:
        logger.error(f"Error getting workflows for {code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    List all workflows.

    Returns all workflows without server-side filtering or pagination.
    Filtering, sorting, and pagination are handled on the frontend.
    Results are cached for 10 minutes to improve performance.
    """
    try:
        return workflow_service.list_workflows()

    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow_by_id(
    workflow_id: str = Path(
        ..., description="Workflow unique identifier (UUID)"
    ),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Get complete workflow details by ID.

    Returns full workflow configuration including all conditions,
    trigger parameters, and metadata.
    """
    try:
        workflow_data = workflow_service.dynamodb_client.get_workflow_by_id(
            workflow_id
        )

        if not workflow_data:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return workflow_service._convert_to_detail(workflow_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/workflows/{workflow_id}/orders",
    response_model=WorkflowOrderHistoryResponse,
)
async def get_workflow_order_history(
    workflow_id: str = Path(
        ..., description="Workflow unique identifier (UUID)"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of orders to return (1-100)",
    ),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Get order history for a specific workflow.

    Returns the most recent orders placed by this workflow,
    sorted by placement time (newest first).
    Orders are retained for 7 days via DynamoDB TTL.
    """
    try:
        # Verify workflow exists before querying orders
        workflow_data = workflow_service.dynamodb_client.get_workflow_by_id(
            workflow_id
        )

        if not workflow_data:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow with id {workflow_id} not found",
            )

        # Get order history from DynamoDB
        orders = workflow_service.get_workflow_order_history(
            workflow_id=workflow_id, limit=limit
        )

        return WorkflowOrderHistoryResponse(
            workflow_id=workflow_id,
            orders=orders,
            total_count=len(orders),
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting order history for workflow {workflow_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve order history",
        )
