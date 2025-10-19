from fastapi import APIRouter

from model import Signal, Strategy

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/config")
async def get_report_config():
    """Get report configuration including strategies and signals."""
    return {
        "strategies": [{"value": s.name, "label": s.value} for s in Strategy],
        "signals": [{"value": s.name, "label": s.value} for s in Signal],
    }
