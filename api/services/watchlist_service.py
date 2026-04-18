from typing import List, Optional

from api.models.watchlist import WatchlistItem, WatchlistResponse, WatchlistTag
from api.services.indicator_service import IndicatorService
from client.aws_client import DynamoDBClient
from model import Currency, UnitTime
from model.enum import Exchange
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

    def enforce_tag_mutual_exclusivity(self, labels: List[str]) -> List[str]:
        has_slwin = WatchlistTag.SLWIN.value in labels
        has_short_term = WatchlistTag.SHORT_TERM.value in labels

        if has_slwin and has_short_term:
            labels = [
                label
                for label in labels
                if label != WatchlistTag.SHORT_TERM.value
            ]

        return labels

    async def _enrich_asset(
        self,
        asset_symbol: str,
        country_code: str,
        item_id: str,
        description: str = "",
        added_at: str = "",
        labels: Optional[List[str]] = None,
        asset_identifier: Optional[int] = None,
        asset_type: Optional[str] = None,
        exchange: str = "saxo",
    ) -> WatchlistItem:
        if labels is None:
            labels = []

        if ":" in asset_symbol:
            code = asset_symbol.split(":")[0]
        else:
            code = asset_symbol

        if exchange == "binance":
            indicators = await self.indicator_service.get_asset_indicators(
                code=code,
                exchange=Exchange.BINANCE,
                country_code="",
                unit_time=UnitTime.D,
            )
            current_price = indicators.current_price
            variation_pct = indicators.variation_pct
            currency = Currency.USD
            final_description = description
        else:
            asset_info = self.indicator_service.saxo_client.get_asset(
                code, country_code
            )
            currency = Currency.get_value(
                asset_info.get("CurrencyCode", "EUR")
            )

            current_price, variation_pct = (
                self.indicator_service.get_price_and_variation(
                    code=code,
                    country_code=country_code,
                    unit_time=UnitTime.D,
                    asset_identifier=asset_identifier,
                    asset_type=asset_type,
                )
            )
            final_description = description or asset_info.get(
                "Description", ""
            )

        tradingview_url = None
        try:
            tradingview_url = await self.dynamodb_client.get_tradingview_link(
                code
            )
        except Exception as e:
            logger.warning(f"Failed to get TradingView link for {code}: {e}")

        return WatchlistItem(
            id=item_id,
            asset_symbol=asset_symbol,
            description=final_description,
            country_code=country_code,
            current_price=round(current_price, 4),
            variation_pct=variation_pct,
            currency=currency,
            added_at=added_at,
            labels=labels,
            tradingview_url=tradingview_url,
            exchange=exchange,
        )

    async def _enrich_and_sort_watchlist(
        self, watchlist_items: List[dict]
    ) -> WatchlistResponse:
        enriched_items: List[WatchlistItem] = []
        for item in watchlist_items:
            try:
                enriched_item = await self._enrich_asset(
                    asset_symbol=item["asset_symbol"],
                    country_code=item.get("country_code", "xpar"),
                    item_id=item["id"],
                    description=item.get("description", ""),
                    added_at=item.get("added_at", ""),
                    labels=item.get("labels", []),
                    asset_identifier=item.get("asset_identifier"),
                    asset_type=item.get("asset_type"),
                    exchange=item.get("exchange", "saxo"),
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
                        exchange=item.get("exchange", "saxo"),
                    )
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing "
                    f"{item.get('asset_symbol', 'unknown')}: {e}"
                )

        def sort_key(item: WatchlistItem) -> tuple:
            has_short_term = WatchlistTag.SHORT_TERM.value in item.labels
            has_slwin = WatchlistTag.SLWIN.value in item.labels
            description = item.description.lower() if item.description else ""

            if has_short_term:
                priority = 0
            elif has_slwin:
                priority = 1
            else:
                priority = 2

            return (priority, description)

        sorted_items = sorted(enriched_items, key=sort_key)

        return WatchlistResponse(items=sorted_items, total=len(sorted_items))

    async def get_watchlist(self) -> WatchlistResponse:
        watchlist_items = await self.dynamodb_client.get_watchlist()

        filtered_items = []
        for item in watchlist_items:
            labels = item.get("labels", [])

            if WatchlistTag.LONG_TERM.value in labels:
                continue

            has_crypto = WatchlistTag.CRYPTO.value in labels
            has_short_term = WatchlistTag.SHORT_TERM.value in labels
            has_slwin = WatchlistTag.SLWIN.value in labels
            if has_crypto and not has_short_term and not has_slwin:
                continue

            filtered_items.append(item)

        return await self._enrich_and_sort_watchlist(filtered_items)

    async def get_all_watchlist(self) -> WatchlistResponse:
        watchlist_items = await self.dynamodb_client.get_watchlist()
        return await self._enrich_and_sort_watchlist(watchlist_items)

    async def get_long_term_positions(self) -> WatchlistResponse:
        watchlist_items = await self.dynamodb_client.get_watchlist()

        filtered_items = []
        for item in watchlist_items:
            labels = item.get("labels", [])
            if WatchlistTag.LONG_TERM.value in labels:
                filtered_items.append(item)

        return await self._enrich_and_sort_watchlist(filtered_items)

    async def get_indexes(self) -> WatchlistResponse:
        indexes = [
            {"symbol": "FRA40.I", "name": "CAC40"},
            {"symbol": "GER40.I", "name": "DAX"},
            {"symbol": "US500.I", "name": "S&P 500"},
            {"symbol": "GOLDDEC25", "name": "GOLD"},
        ]

        enriched_items: List[WatchlistItem] = []
        for index in indexes:
            try:
                enriched_item = await self._enrich_asset(
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
