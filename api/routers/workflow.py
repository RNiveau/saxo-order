from fastapi import APIRouter, HTTPException, Path, Query

from api.models.workflow import AssetWorkflowsResponse
from api.services.workflow_service import (
    WorkflowService as LegacyWorkflowService,
)
from client.aws_client import DynamoDBClient
from model.workflow_api import WorkflowDetail, WorkflowListResponse
from services.workflow_service import WorkflowService
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/workflow", tags=["workflow"])
logger = Logger.get_logger("workflow_router")


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
    force_from_disk: bool = Query(
        False,
        description="Force loading workflows from disk instead of S3",
    ),
):
    """
    Get all workflows associated with a specific asset.

    Returns workflows matching the asset code, including their
    configuration, conditions, and trigger settings.
    """
    try:
        legacy_service = LegacyWorkflowService(force_from_disk=force_from_disk)
        workflows = legacy_service.get_workflows_by_asset(
            code=code, country_code=country_code
        )

        symbol = f"{code}:{country_code}" if country_code else code

        return AssetWorkflowsResponse(
            asset_symbol=symbol,
            total=len(workflows),
            workflows=workflows,
        )

    except SaxoException as e:
        logger.error(f"Saxo error getting workflows for {code}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting workflows for {code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows():
    """
    List all workflows.

    Returns all workflows without server-side filtering or pagination.
    Filtering, sorting, and pagination are handled on the frontend.
    Results are cached for 10 minutes to improve performance.
    """
    try:
        dynamodb_client = DynamoDBClient()
        workflow_service = WorkflowService(dynamodb_client)

        return workflow_service.list_workflows()

    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow_by_id(
    workflow_id: str = Path(
        ..., description="Workflow unique identifier (UUID)"
    ),
):
    """
    Get complete workflow details by ID.

    Returns full workflow configuration including all conditions,
    trigger parameters, and metadata.
    """
    try:
        dynamodb_client = DynamoDBClient()
        workflow_service = WorkflowService(dynamodb_client)

        workflow_data = dynamodb_client.get_workflow_by_id(workflow_id)

        if not workflow_data:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return workflow_service._convert_to_detail(workflow_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
