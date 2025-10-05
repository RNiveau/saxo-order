from fastapi import APIRouter, HTTPException, Query

from api.models.workflow import AssetWorkflowsResponse
from api.services.workflow_service import WorkflowService
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
        workflow_service = WorkflowService(force_from_disk=force_from_disk)
        workflows = workflow_service.get_workflows_by_asset(
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
