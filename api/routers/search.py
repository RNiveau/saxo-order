from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_binance_client, get_saxo_client
from api.models.search import SearchResponse, SearchResultItem
from api.services.search_service import SearchService
from client.binance_client import BinanceClient
from client.saxo_client import SaxoClient
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/search", tags=["search"])
logger = Logger.get_logger("search_router")


@router.get("", response_model=SearchResponse)
async def search_instruments(
    keyword: str = Query(
        ...,
        description="Search keyword for instruments (symbol, name, etc.)",
        min_length=1,
    ),
    asset_type: Optional[str] = Query(
        None,
        description="Filter by asset type (e.g., 'Stock', 'ETF', 'Bond')",
    ),
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
):
    """
    Search for financial instruments by keyword across Saxo and Binance.

    Returns a list of matching instruments with their symbol, description,
    identifier, asset type, and exchange.
    """
    try:
        search_service = SearchService(saxo_client, binance_client)
        results = search_service.search_instruments(
            keyword=keyword, asset_type=asset_type
        )

        result_items = [
            SearchResultItem(
                symbol=asset.symbol,
                description=asset.description,
                identifier=asset.identifier,
                asset_type=asset.asset_type.value,
                exchange=asset.exchange,
            )
            for asset in results
        ]

        return SearchResponse(results=result_items, total=len(result_items))

    except SaxoException as e:
        logger.error(f"Saxo error during search: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
