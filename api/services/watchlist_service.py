from typing import List

from api.models.watchlist import WatchlistItem, WatchlistResponse
from api.services.indicator_service import IndicatorService
from client.aws_client import DynamoDBClient
from model import UnitTime
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("watchlist_api_service")


class WatchlistService:
    """Service for managing watchlist via API."""

    def __init__(
        self,
        dynamodb_client: DynamoDBClient,
        indicator_service: IndicatorService,
    ):
        self.dynamodb_client = dynamodb_client
        self.indicator_service = indicator_service

    def get_watchlist(self) -> WatchlistResponse:
        """
        Get all watchlist items with current prices and variations.

        Returns:
            WatchlistResponse with enriched watchlist data
        """
        # Get watchlist from DynamoDB
        watchlist_items = self.dynamodb_client.get_watchlist()

        # Enrich with current prices and variations
        enriched_items: List[WatchlistItem] = []
        for item in watchlist_items:
            try:
                asset_symbol = item["asset_symbol"]
                country_code = item.get("country_code", "xpar")

                # Extract code from symbol (e.g., "itp:xpar" -> "itp")
                if ":" in asset_symbol:
                    code = asset_symbol.split(":")[0]
                else:
                    code = asset_symbol

                # Get current price and variation using IndicatorService
                current_price, variation_pct = (
                    self.indicator_service.get_price_and_variation(
                        code=code,
                        country_code=country_code,
                        unit_time=UnitTime.D,
                    )
                )

                enriched_items.append(
                    WatchlistItem(
                        id=item["id"],
                        asset_symbol=asset_symbol,
                        country_code=country_code,
                        current_price=round(current_price, 4),
                        variation_pct=variation_pct,
                        added_at=item.get("added_at", ""),
                    )
                )
            except SaxoException as e:
                logger.warning(
                    f"Failed to get price for {item['asset_symbol']}: {e}"
                )
                # Still include the item but without price data
                enriched_items.append(
                    WatchlistItem(
                        id=item["id"],
                        asset_symbol=item.get("asset_symbol", ""),
                        country_code=item.get("country_code", "xpar"),
                        current_price=0.0,
                        variation_pct=0.0,
                        added_at=item.get("added_at", ""),
                    )
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing "
                    f"{item.get('asset_symbol', 'unknown')}: {e}"
                )

        return WatchlistResponse(
            items=enriched_items, total=len(enriched_items)
        )
