from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_binance_client,
    get_candles_service,
    get_dynamodb_client_optional,
    get_saxo_client,
)
from api.models.indicator import AssetIndicatorsResponse
from api.services.indicator_service import IndicatorService
from client.aws_client import DynamoDBClient
from client.binance_client import BinanceClient
from client.saxo_client import SaxoClient
from model import UnitTime
from model.enum import Exchange
from services.candles_service import CandlesService
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/indicator", tags=["indicator"])
logger = Logger.get_logger("indicator_router")

# Supported unit times for indicator calculations
SUPPORTED_UNIT_TIMES = [UnitTime.D, UnitTime.W, UnitTime.M]


@router.get("/asset/{code}", response_model=AssetIndicatorsResponse)
async def get_asset_indicators(
    code: str,
    exchange: str = Query(
        Exchange.SAXO.value,
        description="Exchange (saxo or binance)",
    ),
    country_code: Optional[str] = Query(
        "xpar",
        description="Country code (e.g., 'xpar') - required for Saxo",
    ),
    unit_time: str = Query(
        UnitTime.D.value,
        description="Unit time for indicators (daily, weekly, monthly)",
    ),
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    candles_service: CandlesService = Depends(get_candles_service),
    dynamodb_client: Optional[DynamoDBClient] = Depends(
        get_dynamodb_client_optional
    ),
):
    """
    Get indicator data for a specific asset.

    Returns moving averages (7, 20, 50, 200 periods), current price,
    and percentage variation from previous period's close.

    Supports both Saxo Bank and Binance exchanges. The exchange parameter
    determines which data source to use.

    The unit_time parameter determines the period length:
    - daily: Moving averages calculated on daily candles
    - weekly: Moving averages calculated on weekly candles
    - monthly: Moving averages calculated on monthly candles

    Args:
        code: Asset code/symbol
            - Saxo: Asset code (e.g., 'itp', 'DAX.I', 'btc')
            - Binance: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        exchange: Exchange name (default: 'saxo')
            - 'saxo': Saxo Bank exchange
            - 'binance': Binance cryptocurrency exchange
        country_code: Country/market code for Saxo assets (default: 'xpar')
            - Required for most Saxo assets (e.g., 'xpar' for Euronext Paris)
            - Optional for some assets (e.g., indices like 'DAX.I')
            - Ignored for Binance assets
        unit_time: Unit time for calculations (default: 'daily')
            - Supported values: 'daily', 'weekly', 'monthly'

    Returns:
        AssetIndicatorsResponse with all indicator data

    Examples:
        - Saxo stock: /api/indicator/asset/itp?exchange=saxo&country_code=xpar
        - Saxo index: /api/indicator/asset/DAX.I?exchange=saxo
        - Binance crypto: /api/indicator/asset/BTCUSDT?exchange=binance
    """
    try:
        # Validate and convert exchange
        ex = Exchange.get_value(exchange)

        # Validate and convert unit_time
        ut = UnitTime.get_value(unit_time)
        if ut not in SUPPORTED_UNIT_TIMES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported unit_time: {unit_time}. "
                f"Supported values: {[u.value for u in SUPPORTED_UNIT_TIMES]}",
            )

        indicator_service = IndicatorService(
            saxo_client, binance_client, candles_service, dynamodb_client
        )
        return indicator_service.get_asset_indicators(
            code=code, exchange=ex, country_code=country_code, unit_time=ut
        )

    except SaxoException as e:
        logger.error(
            f"Error getting indicators for {code} "
            f"({exchange}, {unit_time}): {e}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error getting indicators for "
            f"{code} ({exchange}, {unit_time}): {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")
