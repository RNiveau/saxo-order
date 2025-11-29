from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import (
    get_binance_client,
    get_candles_service,
    get_saxo_client,
)
from api.models.watchlist import WatchlistResponse
from api.services.indicator_service import IndicatorService
from api.services.watchlist_service import WatchlistService
from client.binance_client import BinanceClient
from client.saxo_client import SaxoClient
from services.candles_service import CandlesService
from utils.logger import Logger

router = APIRouter(prefix="/api/indexes", tags=["indexes"])
logger = Logger.get_logger("indexes_router")


def get_watchlist_service(
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    candles_service: CandlesService = Depends(get_candles_service),
) -> WatchlistService:
    """
    Create WatchlistService instance for indexes.
    Note: Indexes don't use DynamoDB, so we pass None.
    """
    indicator_service = IndicatorService(
        saxo_client, binance_client, candles_service
    )
    return WatchlistService(None, indicator_service)  # type: ignore[arg-type]


@router.get("", response_model=WatchlistResponse)
async def get_indexes(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """
    Get main market indexes with current prices and variations.
    Returns data for: CAC40, DAX, S&P 500, and GOLD.

    Returns:
        WatchlistResponse with index data
    """
    try:
        return watchlist_service.get_indexes()
    except Exception as e:
        logger.error(f"Unexpected error getting indexes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
