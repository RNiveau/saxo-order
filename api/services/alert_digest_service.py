import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from api.models.alert_digest import (
    AlertDigestResponse,
    TriagedAssetResponse,
)
from client.aws_client import DynamoDBClient
from utils.logger import Logger

logger = Logger.get_logger("alert_digest_api_service")


class AlertDigestService:
    """Service for reading persisted alert-triage digests via API."""

    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb_client = dynamodb_client
        self._cache: TTLCache = TTLCache(maxsize=8, ttl=300)
        self._cache_lock = asyncio.Lock()

    async def list_recent(
        self, limit: Optional[int] = None
    ) -> List[AlertDigestResponse]:
        cache_key = f"digests_{limit}"
        async with self._cache_lock:
            if cache_key in self._cache:
                logger.debug("Using cached alert digests")
                return self._cache[cache_key]

            logger.info("Cache miss - fetching alert digests from DynamoDB")
            items = await self.dynamodb_client.get_alert_digests(limit=limit)
            tradingview_links = (
                await self.dynamodb_client.get_all_tradingview_links()
            )
            digests = [
                self._to_response(item, tradingview_links) for item in items
            ]
            self._cache[cache_key] = digests
            return digests

    async def get_by_run_date(
        self, run_date: str
    ) -> Optional[AlertDigestResponse]:
        item = await self.dynamodb_client.get_alert_digest(run_date)
        if item is None:
            return None
        tradingview_links = await self.dynamodb_client.get_all_tradingview_links()
        return self._to_response(item, tradingview_links)

    def _to_response(
        self, item: Dict[str, Any], tradingview_links: Dict[str, str]
    ) -> AlertDigestResponse:
        return AlertDigestResponse(
            run_date=item["run_date"],
            created_at=int(item["created_at"]),
            summary=item["summary"],
            counts={k: int(v) for k, v in item["counts"].items()},
            triaged_assets=[
                self._to_triaged_asset(asset, tradingview_links)
                for asset in item.get("triaged_assets", [])
            ],
            fallback_used=bool(item["fallback_used"]),
            model=item["model"],
        )

    def _to_triaged_asset(
        self, asset: Dict[str, Any], tradingview_links: Dict[str, str]
    ) -> TriagedAssetResponse:
        country_code = asset.get("country_code")
        asset_id = (
            f"{asset['asset_code']}:{country_code}"
            if country_code
            else asset["asset_code"]
        )
        return TriagedAssetResponse(
            asset_code=asset["asset_code"],
            asset_description=asset["asset_description"],
            exchange=asset["exchange"],
            country_code=country_code,
            conviction=asset["conviction"],
            rank=(
                int(asset["rank"]) if asset.get("rank") is not None else None
            ),
            rationale=asset["rationale"],
            patterns=asset["patterns"],
            ma50_slope=(
                float(asset["ma50_slope"])
                if isinstance(asset.get("ma50_slope"), Decimal)
                else asset.get("ma50_slope")
            ),
            tradingview_url=tradingview_links.get(asset_id),
        )
