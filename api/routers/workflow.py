import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel

from api.dependencies import get_saxo_client, get_workflow_service
from api.models.workflow import (
    AllWorkflowOrdersResponse,
    AssetWorkflowsResponse,
    WorkflowCloseInfo,
    WorkflowConditionInfo,
    WorkflowIndicatorInfo,
    WorkflowInfo,
    WorkflowOrderHistoryResponse,
    WorkflowTriggerInfo,
)
from client.saxo_client import SaxoClient
from model.workflow import IndicatorType
from model.workflow_api import (
    IndicatorDetail,
    WorkflowCreateRequest,
    WorkflowDetail,
    WorkflowListResponse,
)
from services.indicator_service import (
    apply_linear_function,
    number_of_day_between_dates,
)
from services.workflow_service import WorkflowService
from utils.helper import get_date_utc0
from utils.logger import Logger

router = APIRouter(prefix="/api/workflow", tags=["workflow"])
logger = Logger.get_logger("workflow_router")

_INDICATOR_LABELS: Dict[IndicatorType, str] = {
    IndicatorType.MA7: "MM7",
    IndicatorType.MA50: "MA50",
    IndicatorType.COMBO: "COMBO",
    IndicatorType.BBB: "BBB",
    IndicatorType.BBH: "BBH",
    IndicatorType.POL: "POL (Polarité)",
    IndicatorType.ZONE: "ZONE",
    IndicatorType.INCLINED: "Inclined (ROB/SOH)",
}


class IndicatorTypeOption(BaseModel):
    value: str
    label: str


@router.get("/indicator-types", response_model=List[IndicatorTypeOption])
def get_indicator_types() -> List[IndicatorTypeOption]:
    return [
        IndicatorTypeOption(
            value=member.value, label=_INDICATOR_LABELS[member]
        )
        for member in IndicatorType
    ]


def _compute_inclined_current_value(
    saxo_client: SaxoClient,
    index_code: str,
    indicator: IndicatorDetail,
) -> Optional[float]:
    """Compute the inclined indicator value projected onto today.

    Mirrors engines.workflows.InclinedWorkflow.init_workflow but returns
    only the line value at today's business-day offset from x1.
    """
    if (
        indicator.x1_date is None
        or indicator.x1_price is None
        or indicator.x2_date is None
        or indicator.x2_price is None
    ):
        return None

    try:
        x1_date = datetime.datetime.strptime(indicator.x1_date, "%Y-%m-%d")
        x2_date = datetime.datetime.strptime(indicator.x2_date, "%Y-%m-%d")
    except ValueError as exc:
        logger.warning(
            f"Invalid inclined date(s) on {index_code}: "
            f"{indicator.x1_date}, {indicator.x2_date} ({exc})"
        )
        return None

    asset = saxo_client.get_asset(index_code)
    saxo_uic = asset["Identifier"]
    asset_type = asset["AssetType"]

    x1_to_x2 = number_of_day_between_dates(
        saxo_client, saxo_uic, asset_type, x1_date, x2_date
    )
    if x1_to_x2 == 0:
        return None

    x1_to_now = number_of_day_between_dates(
        saxo_client, saxo_uic, asset_type, x1_date, get_date_utc0()
    )

    return apply_linear_function(
        0,
        indicator.x1_price,
        x1_to_x2,
        indicator.x2_price,
        x1_to_now,
    )


def _build_indicator_info(
    indicator: IndicatorDetail,
    index_code: str,
    saxo_client: SaxoClient,
) -> WorkflowIndicatorInfo:
    current_value: Optional[float] = None
    if indicator.name == IndicatorType.INCLINED.value:
        try:
            current_value = _compute_inclined_current_value(
                saxo_client, index_code, indicator
            )
        except Exception as exc:
            logger.warning(
                f"Failed to compute inclined value for {index_code}: {exc}"
            )

    return WorkflowIndicatorInfo(
        name=indicator.name,
        unit_time=indicator.ut,
        value=indicator.value,
        zone_value=indicator.zone_value,
        x1_date=indicator.x1_date,
        x1_price=indicator.x1_price,
        x2_date=indicator.x2_date,
        x2_price=indicator.x2_price,
        current_value=current_value,
    )


def _convert_detail_to_info(
    detail: WorkflowDetail,
    saxo_client: SaxoClient,
) -> WorkflowInfo:
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
                indicator=_build_indicator_info(
                    cond.indicator, detail.index, saxo_client
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


@router.get("/orders", response_model=AllWorkflowOrdersResponse)
async def get_all_workflow_orders(
    limit: int = Query(100, ge=1, le=100, description="Max orders to return"),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Get all orders across all workflows, sorted newest first.
    """
    try:
        orders = await workflow_service.get_all_orders(limit=limit)
        return AllWorkflowOrdersResponse(
            orders=orders,
            total_count=len(orders),
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting all workflow orders: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve workflow orders",
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
    saxo_client: SaxoClient = Depends(get_saxo_client),
):
    """
    Get all workflows associated with a specific asset from DynamoDB.

    Returns workflows matching the asset code, including their
    configuration, conditions, and trigger settings.
    For inclined indicators, the line value projected onto today is
    computed and returned alongside the stored reference points.
    Uses the same 10-minute cache as the workflows list endpoint.
    """
    try:
        workflow_details = await workflow_service.get_workflows_by_asset(
            code=code, country_code=country_code
        )

        symbol = f"{code}:{country_code}" if country_code else code

        workflows_info = [
            _convert_detail_to_info(detail, saxo_client)
            for detail in workflow_details
        ]

        return AssetWorkflowsResponse(
            asset_symbol=symbol,
            total=len(workflows_info),
            workflows=workflows_info,
        )

    except Exception as e:
        logger.error(f"Error getting workflows for {code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/workflows", response_model=WorkflowDetail, status_code=201)
async def create_workflow(
    data: WorkflowCreateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Create a new workflow."""
    try:
        return await workflow_service.create_workflow(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create workflow"
        )


@router.put(
    "/workflows/{workflow_id}", response_model=WorkflowDetail, status_code=200
)
async def update_workflow(
    data: WorkflowCreateRequest,
    workflow_id: str = Path(...),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Update an existing workflow."""
    try:
        return await workflow_service.update_workflow(workflow_id, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update workflow"
        )


@router.delete("/workflows/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str = Path(...),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Delete a workflow."""
    try:
        await workflow_service.delete_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete workflow"
        )


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
        return await workflow_service.list_workflows()

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
        workflow = await workflow_service.get_workflow_by_id(workflow_id)

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return workflow

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
        workflow = await workflow_service.get_workflow_by_id(workflow_id)

        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow with id {workflow_id} not found",
            )

        # Get order history from DynamoDB
        orders = await workflow_service.get_workflow_order_history(
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
