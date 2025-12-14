from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import (
    get_binance_client,
    get_candles_service,
    get_dynamodb_client,
    get_saxo_client,
)
from api.models.watchlist import WatchlistTag
from api.services.indicator_service import IndicatorService
from client.aws_client import DynamoDBClient
from client.binance_client import BinanceClient
from client.saxo_client import SaxoClient
from model import Currency
from model.enum import Exchange
from model.workflow import UnitTime
from services.candles_service import CandlesService
from utils.logger import Logger

router = APIRouter(prefix="/api/homepage", tags=["homepage"])
logger = Logger.get_logger("homepage_router")


class HomepageItemResponse(BaseModel):
    id: str = Field(description="Unique identifier for the watchlist item")
    asset_symbol: str = Field(description="Asset symbol (e.g., 'itp:xpar')")
    description: str = Field(description="Asset description/name")
    current_price: float = Field(description="Current price of the asset")
    variation_pct: float = Field(
        description="Percentage variation from previous period"
    )
    currency: Currency = Field(
        description="Currency code (e.g., 'EUR', 'USD')"
    )
    tradingview_url: Optional[str] = Field(
        default=None,
        description="Custom TradingView URL for this asset",
    )
    exchange: str = Field(
        default="saxo",
        description="Exchange (saxo or binance)",
    )
    ma50_value: float = Field(description="50-day moving average value")
    is_above_ma50: bool = Field(
        description="Whether current price is above MA50"
    )


class HomepageResponse(BaseModel):
    items: List[HomepageItemResponse] = Field(
        description="List of homepage items"
    )
    total: int = Field(description="Total number of items on homepage")


def get_indicator_service(
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    candles_service: CandlesService = Depends(get_candles_service),
) -> IndicatorService:
    return IndicatorService(saxo_client, binance_client, candles_service)


@router.get("", response_model=HomepageResponse)
async def get_homepage(
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
    indicator_service: IndicatorService = Depends(get_indicator_service),
):
    """
    Get homepage assets with MA50 data.
    Returns assets tagged with 'homepage' (maximum 6).

    Returns:
        HomepageResponse with homepage items including MA50 data
    """
    try:
        all_items = dynamodb_client.get_watchlist()
        homepage_items = [
            item
            for item in all_items
            if WatchlistTag.HOMEPAGE.value in item.get("labels", [])
        ]

        enriched_items = []
        for item in homepage_items:
            try:
                asset_symbol = item["asset_symbol"]
                parts = asset_symbol.split(":")
                code = parts[0]
                country_code = parts[1] if len(parts) > 1 else ""
                exchange_str = item.get("exchange", "saxo")
                exchange = (
                    Exchange.BINANCE
                    if exchange_str == "binance"
                    else Exchange.SAXO
                )

                indicators = indicator_service.get_asset_indicators(
                    code, exchange, country_code, UnitTime.D
                )

                ma50 = next(
                    (
                        ma
                        for ma in indicators.moving_averages
                        if ma.period == 50
                    ),
                    None,
                )

                if ma50:
                    enriched_items.append(
                        HomepageItemResponse(
                            id=item["id"],
                            asset_symbol=asset_symbol,
                            description=item["description"],
                            current_price=indicators.current_price,
                            variation_pct=indicators.variation_pct,
                            currency=indicators.currency,
                            tradingview_url=item.get("tradingview_url"),
                            exchange=exchange,
                            ma50_value=ma50.value,
                            is_above_ma50=ma50.is_above,
                        )
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to enrich homepage item {item.get('id')}: {e}"
                )
                continue

        enriched_items.sort(key=lambda x: x.description.lower())

        return HomepageResponse(
            items=enriched_items,
            total=len(enriched_items),
        )

    except Exception as e:
        logger.error(f"Unexpected error getting homepage: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
