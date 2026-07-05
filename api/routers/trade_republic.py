from fastapi import APIRouter, Depends, HTTPException, UploadFile

from api.dependencies import get_trade_republic_service
from api.models.trade_republic import (
    ParseErrorResponse,
    TradeRepublicTransactionResponse,
    UploadTradeRepublicResponse,
)
from api.services.trade_republic_service import TradeRepublicService
from utils.logger import Logger

router = APIRouter(prefix="/api/trade-republic", tags=["trade_republic"])
logger = Logger.get_logger("trade_republic_router")


@router.post("/upload", response_model=UploadTradeRepublicResponse)
async def upload_trade_republic_csv(
    file: UploadFile,
    trade_republic_service: TradeRepublicService = Depends(
        get_trade_republic_service
    ),
):
    """Parse an uploaded Trade Republic CSV export and return the
    resulting transactions and any per-row parse errors."""
    try:
        content = (await file.read()).decode("utf-8")
        transactions, errors = trade_republic_service.parse_csv(content)

        return UploadTradeRepublicResponse(
            transactions=[
                TradeRepublicTransactionResponse.from_transaction(t)
                for t in transactions
            ],
            errors=[ParseErrorResponse.from_parse_error(e) for e in errors],
            total_rows=len(transactions) + len(errors),
        )
    except Exception as e:
        logger.error(f"Error parsing Trade Republic CSV: {e}")
        raise HTTPException(status_code=400, detail=str(e))
