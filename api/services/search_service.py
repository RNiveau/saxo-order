from typing import List, Optional

from client.saxo_client import SaxoClient
from utils.logger import Logger

logger = Logger.get_logger("search_service")


class SearchService:
    def __init__(self, client: SaxoClient):
        self.client = client

    def search_instruments(
        self, keyword: str, asset_type: Optional[str] = None
    ) -> List[dict]:
        """
        Search for instruments using the Saxo API.

        Args:
            keyword: Search keyword
            asset_type: Optional asset type filter (e.g., "Stock", "ETF")

        Returns:
            List of instrument dictionaries with keys:
            - Symbol: Trading symbol
            - Description: Instrument name/description
            - Identifier: Unique identifier
            - AssetType: Type of asset
        """
        results = self.client.search(keyword=keyword, asset_type=asset_type)
        return results
