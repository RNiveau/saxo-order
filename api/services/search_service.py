import asyncio
from typing import List, Optional

from client.binance_client import BinanceClient
from client.ouinex_client import OuinexClient
from client.saxo_client import SaxoClient
from model.asset import Asset
from utils.logger import Logger

logger = Logger.get_logger("search_service")


class SearchService:
    def __init__(
        self,
        saxo_client: SaxoClient,
        binance_client: BinanceClient,
        ouinex_client: OuinexClient,
    ):
        self.saxo_client = saxo_client
        self.binance_client = binance_client
        self.ouinex_client = ouinex_client

    async def search_instruments(
        self, keyword: str, asset_type: Optional[str] = None
    ) -> List[Asset]:
        """
        Search for instruments using both Saxo and Binance APIs.

        Args:
            keyword: Search keyword
            asset_type: Optional asset type filter (only applies to Saxo)

        Returns:
            List of Asset objects from both Saxo and Binance
        """
        results: List[Asset] = []

        try:
            saxo_results = await self.saxo_client.search(
                keyword=keyword, asset_type=asset_type
            )
            results.extend(saxo_results)
        except Exception as e:
            logger.error(f"Saxo search error: {e}")

        try:
            binance_results = await asyncio.to_thread(
                self.binance_client.search, keyword=keyword
            )
            results.extend(binance_results)
        except Exception as e:
            logger.error(f"Binance search error: {e}")

        try:
            ouinex_results = await asyncio.to_thread(
                self.ouinex_client.search, keyword=keyword
            )
            results.extend(ouinex_results)
        except Exception as e:
            logger.error(f"Ouinex search error: {e}")

        return results
