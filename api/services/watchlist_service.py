from typing import List, Optional

from api.models.watchlist import WatchlistItem, WatchlistResponse
from api.services.indicator_service import IndicatorService
from client.aws_client import DynamoDBClient
from model import Currency, UnitTime
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

    def _enrich_asset(
        self,
        asset_symbol: str,
        country_code: str,
        item_id: str,
        description: str = "",
        added_at: str = "",
        labels: Optional[List[str]] = None,
        asset_identifier: Optional[int] = None,
        asset_type: Optional[str] = None,
    ) -> WatchlistItem:
        """
        Enrich an asset with current price, variation, and currency.

        Args:
            asset_symbol: Asset symbol (e.g., 'itp:xpar')
            country_code: Country code (e.g., 'xpar', or empty string)
            item_id: Unique identifier for the item
            description: Asset description/name
            added_at: ISO timestamp when added
            labels: Labels for the asset
            asset_identifier: Optional cached Saxo UIC
            asset_type: Optional cached asset type

        Returns:
            WatchlistItem with enriched data
        """
        if labels is None:
            labels = []

        # Extract code from symbol (e.g., "itp:xpar" -> "itp")
        if ":" in asset_symbol:
            code = asset_symbol.split(":")[0]
        else:
            code = asset_symbol

        # Get asset info to retrieve currency
        asset_info = self.indicator_service.saxo_client.get_asset(
            code, country_code
        )
        currency = Currency.get_value(asset_info.get("CurrencyCode", "EUR"))

        # Get current price and variation using IndicatorService
        current_price, variation_pct = (
            self.indicator_service.get_price_and_variation(
                code=code,
                country_code=country_code,
                unit_time=UnitTime.D,
                asset_identifier=asset_identifier,
                asset_type=asset_type,
            )
        )

        # Get TradingView URL if available
        tradingview_url = None
        try:
            tradingview_url = self.dynamodb_client.get_tradingview_link(code)
        except Exception as e:
            logger.warning(f"Failed to get TradingView link for {code}: {e}")

        return WatchlistItem(
            id=item_id,
            asset_symbol=asset_symbol,
            description=description or asset_info.get("Description", ""),
            country_code=country_code,
            current_price=round(current_price, 4),
            variation_pct=variation_pct,
            currency=currency,
            added_at=added_at,
            labels=labels,
            tradingview_url=tradingview_url,
        )

    def get_watchlist(self) -> WatchlistResponse:
        """
        Get all watchlist items with current prices and variations.
        Items are sorted with short-term labeled items first (alphabetically),
        then other items (alphabetically).

        Returns:
            WatchlistResponse with enriched and sorted watchlist data
        """
        # Get watchlist from DynamoDB
        watchlist_items = self.dynamodb_client.get_watchlist()

        # Enrich with current prices and variations
        enriched_items: List[WatchlistItem] = []
        for item in watchlist_items:
            try:
                enriched_item = self._enrich_asset(
                    asset_symbol=item["asset_symbol"],
                    country_code=item.get("country_code", "xpar"),
                    item_id=item["id"],
                    description=item.get("description", ""),
                    added_at=item.get("added_at", ""),
                    labels=item.get("labels", []),
                    asset_identifier=item.get("asset_identifier"),
                    asset_type=item.get("asset_type"),
                )
                enriched_items.append(enriched_item)
            except SaxoException as e:
                logger.warning(
                    f"Failed to get price for {item['asset_symbol']}: {e}"
                )
                enriched_items.append(
                    WatchlistItem(
                        id=item["id"],
                        asset_symbol=item.get("asset_symbol", ""),
                        description=item.get("description", ""),
                        country_code=item.get("country_code", "xpar"),
                        current_price=0.0,
                        variation_pct=0.0,
                        currency=Currency.EURO,
                        added_at=item.get("added_at", ""),
                        labels=item.get("labels", []),
                    )
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing "
                    f"{item.get('asset_symbol', 'unknown')}: {e}"
                )

        # Sort items: short-term positions first (alphabetically),
        # then other items (alphabetically)
        def sort_key(item: WatchlistItem) -> tuple:
            has_short_term = "short-term" in item.labels
            description = item.description.lower() if item.description else ""
            # Items with short-term label get priority (0), others get (1)
            # Then sort alphabetically by description
            return (0 if has_short_term else 1, description)

        sorted_items = sorted(enriched_items, key=sort_key)

        return WatchlistResponse(items=sorted_items, total=len(sorted_items))

    def get_indexes(self) -> WatchlistResponse:
        """
        Get main market indexes with current prices and variations.

        Returns:
            WatchlistResponse with index data
        """
        # Define the indexes to track (order matters)
        indexes = [
            {"symbol": "FRA40.I", "name": "CAC40"},
            {"symbol": "GER40.I", "name": "DAX"},
            {"symbol": "US500.I", "name": "S&P 500"},
            {"symbol": "GOLDDEC25", "name": "GOLD"},
        ]

        enriched_items: List[WatchlistItem] = []
        for index in indexes:
            try:
                enriched_item = self._enrich_asset(
                    asset_symbol=index["symbol"],
                    country_code="",
                    item_id=index["symbol"],
                    description=index["name"],
                    added_at="",
                    labels=[],
                    asset_identifier=None,
                    asset_type=None,
                )
                enriched_items.append(enriched_item)
            except SaxoException as e:
                logger.warning(
                    f"Failed to get data for index {index['symbol']}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing index {index['symbol']}: {e}"
                )

        return WatchlistResponse(
            items=enriched_items, total=len(enriched_items)
        )
