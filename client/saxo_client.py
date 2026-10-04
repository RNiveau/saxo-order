import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from cachetools import LRUCache, TTLCache

from client.client_helper import get_price_from_saxo_data
from client.saxo_auth_client import SaxoAuthClient
from model import (
    Account,
    AssetType,
    ConditionalOrder,
    Currency,
    Direction,
    Order,
    OrderType,
    ReportOrder,
    TriggerOrder,
    Underlying,
)
from model.asset import Asset
from model.enum import Exchange
from utils.configuration import Configuration
from utils.exception import EmptyResponseException, SaxoException
from utils.logger import Logger

logger = Logger.get_logger("saxo_client")

RATE_LIMITING_KEYS = [
    (
        "X-RateLimit-RefDataInstrumentsMinute-Remaining",
        "X-RateLimit-RefDataInstrumentsMinute-Reset",
    ),
    ("X-RateLimit-ChartMinute-Remaining", "X-RateLimit-ChartMinute-Reset"),
]
RETRY_STATUSES = {500, 502, 503, 504}
IDEMPOTENT_METHODS = frozenset(
    {"DELETE", "GET", "HEAD", "OPTIONS", "PUT", "TRACE"}
)
RETRY_ERRORS = (httpx.ReadError, httpx.ReadTimeout, httpx.RemoteProtocolError)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 30.0


class SaxoClient:
    def __init__(
        self,
        configuration: Configuration,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.logger = Logger.get_logger("saxo_client", logging.INFO)
        self.configuration = configuration
        # Cache for historical data with 30 min TTL
        # (only for horizon=30, horizon=60, horizon=1440, and horizon=10080)
        self.historical_data_cache: TTLCache = TTLCache(maxsize=256, ttl=1800)
        # Cache for 5min intraday data with 5 min TTL (only for horizon=5)
        self.intraday_data_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
        self.asset_cache: LRUCache = LRUCache(maxsize=256)
        self._refresh_lock = asyncio.Lock()
        self.http = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {configuration.access_token}",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport or httpx.AsyncHTTPTransport(retries=3),
        )

    async def __aenter__(self) -> "SaxoClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Send a request, retrying transient failures on idempotent
        methods only: replaying an order POST could place it twice."""
        retryable = method.upper() in IDEMPOTENT_METHODS
        for attempt in range(MAX_RETRIES + 1):
            last_attempt = not retryable or attempt == MAX_RETRIES
            try:
                response = await self._send(method, url, **kwargs)
            except RETRY_ERRORS:
                if last_attempt:
                    raise
            else:
                if response.status_code not in RETRY_STATUSES or last_attempt:
                    break
            await asyncio.sleep(RETRY_BACKOFF_SECONDS * 2**attempt)
        await self._wait_for_rate_limit(response)
        return response

    async def _send(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        response = await self.http.request(method, url, **kwargs)
        if response.status_code == 401:
            response = await self._retry_after_refresh(
                response, method, url, **kwargs
            )
        return response

    async def _retry_after_refresh(
        self, rejected: httpx.Response, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        rejected_auth = rejected.request.headers.get("Authorization")
        async with self._refresh_lock:
            if self.http.headers.get("Authorization") == rejected_auth:
                response = await self._reload_tokens_from_s3(
                    method, url, **kwargs
                )
                if response is not None and response.status_code != 401:
                    return response
                self.logger.info("Calling refresh token API")
                access_token, refresh_token = await SaxoAuthClient(
                    self.configuration
                ).refresh_token()
                await asyncio.to_thread(
                    self.configuration.save_tokens,
                    access_token,
                    refresh_token,
                )
                self.set_access_token(access_token)
        return await self.http.request(method, url, **kwargs)

    async def _reload_tokens_from_s3(
        self, method: str, url: str, **kwargs: Any
    ) -> Optional[httpx.Response]:
        """In API mode another container may have already refreshed the
        tokens, so try those before calling the refresh token API."""
        if not self.configuration.api_mode:
            return None
        self.logger.info("API mode: attempting to reload tokens from S3 first")
        if not await asyncio.to_thread(
            self.configuration.reload_tokens_from_s3
        ):
            return None
        self.logger.info("Tokens reloaded from S3, retrying request")
        self.set_access_token(self.configuration.access_token)
        return await self.http.request(method, url, **kwargs)

    def set_access_token(self, access_token: str) -> None:
        self.http.headers["Authorization"] = f"Bearer {access_token}"

    async def get_asset(self, code: str, market: Optional[str] = None) -> Dict:
        cache_key = (code, market)
        if cache_key in self.asset_cache:
            return self.asset_cache[cache_key]
        symbol = (
            f"{code}:{market}" if market is not None and market != "" else code
        )
        self.logger.debug(f"get_asset {symbol}")
        data = await self._find_asset(symbol)
        data = list(
            filter(lambda x: x["Symbol"].lower() == symbol.lower(), data)
        )
        if len(data) > 1:
            codes = map(lambda x: x["Symbol"], data)
            raise SaxoException(
                f"Stock {symbol} has more than one entry,"
                f" check it: {list(codes)}"
            )
        if len(data) == 0:
            raise SaxoException(f"Stock {symbol} doesn't exist")
        self.asset_cache[cache_key] = data[0]
        return data[0]

    async def search(
        self, keyword: str, asset_type: Optional[str] = None
    ) -> List[Asset]:
        data = await self._find_asset(keyword, asset_type)
        if len(data) == 0:
            raise SaxoException(f"Nothing found for {keyword}")

        results = []
        for item in data:
            asset_type_str = item.get("AssetType", "")
            try:
                asset_type_enum = AssetType(asset_type_str)
            except ValueError:
                self.logger.warning(f"Unknown asset type: {asset_type_str}")
                continue

            asset = Asset(
                symbol=item.get("Symbol", ""),
                description=item.get("Description", ""),
                asset_type=asset_type_enum,
                exchange=Exchange.SAXO,
                identifier=item.get("Identifier"),
            )
            results.append(asset)

        return results

    async def _find_asset(
        self, keyword: str, asset_type: Optional[str] = None
    ) -> List:
        if asset_type is None:
            asset_type = AssetType.all_saxo_values()
        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}ref/v1/instruments/?Keywords="
            f"{keyword}&AssetTypes={asset_type}&IncludeNonTradable=true",
        )
        self._check_response(response)
        return response.json()["Data"]

    async def list_instruments(
        self,
        asset_type: str = "Stock",
        exchange_id: Optional[str] = None,
        top: int = 100,
        skip: int = 0,
        include_non_tradable: bool = False,
    ) -> Dict:
        """
        List instruments of a specific asset type without keyword filter.

        Args:
            asset_type: Asset type to filter (default: "Stock")
            exchange_id: Optional exchange ID filter (e.g., "XPAR", "NYSE")
            top: Number of results to return (pagination)
            skip: Number of results to skip (pagination)
            include_non_tradable: Include non-tradable instruments

        Returns:
            Dict with 'Data' key containing list of instruments
        """
        params = {
            "AssetTypes": asset_type,
            "$top": top,
            "$skip": skip,
            "IncludeNonTradable": str(include_non_tradable).lower(),
        }

        if exchange_id:
            params["ExchangeId"] = exchange_id

        # Build query string
        query_string = "&".join(f"{k}={v}" for k, v in params.items())

        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}ref/v1/instruments/?{query_string}",
        )
        self._check_response(response)
        return response.json()

    async def get_total_amount(self) -> float:
        response = await self._request(
            "GET", f"{self.configuration.saxo_url}port/v1/balances/me"
        )
        self._check_response(response)
        return response.json()["TotalValue"]

    async def get_open_orders(self) -> List:
        response = await self._request(
            "GET", f"{self.configuration.saxo_url}port/v1/orders/me/?$top=50"
        )
        self._check_response(response)
        return response.json()["Data"]

    async def get_positions(self) -> List[Dict]:
        response = await self._request(
            "GET", f"{self.configuration.saxo_url}port/v1/positions/me/?top=50"
        )
        self._check_response(response)
        return response.json()

    async def get_accounts(self):
        response = await self._request(
            "GET", f"{self.configuration.saxo_url}port/v1/accounts/me"
        )
        self._check_response(response)
        return response.json()

    async def get_account(self, account_key: str) -> Account:
        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}port/v1/accounts/{account_key}",
        )
        self._check_response(response)
        account = response.json()
        name = (
            "NoName"
            if "DisplayName" not in account
            else account["DisplayName"]
        )
        client_key = account["ClientKey"]

        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}port/v1/balances/"
            f"?AccountKey={account_key}&ClientKey={client_key}",
        )
        self._check_response(response)
        account_balance = response.json()

        return Account(
            key=account_key,
            name=name,
            fund=account_balance["TotalValue"],
            available_fund=account_balance["CashAvailableForTrading"],
            client_key=client_key,
        )

    async def get_price(self, saxo_uic: int, asset_type: str) -> float:
        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}trade/v1/infoprices/"
            f"?Uic={saxo_uic}&AssetType={asset_type}",
        )
        self._check_response(response)
        price = response.json()
        if price["Quote"]["MarketState"] == "Closed":
            self.logger.warning("Market is closed, price is set to 1")
            return 1.0
        return price["Quote"]["Ask"]

    async def set_order(
        self,
        account: Account,
        order: Order,
        saxo_uic: int,
        conditional_order: Optional[ConditionalOrder] = None,
        stop_price: Optional[float] = None,
    ) -> Any:
        if order.type == OrderType.LIMIT:
            order_type = "Limit"
        elif order.type == OrderType.OPEN_STOP:
            order_type = "StopIfTraded"
        elif order.type == OrderType.STOP:
            order_type = "Stop"
        elif order.type == OrderType.MARKET:
            order_type = "Market"
        else:
            order_type = "StopLimit"
        data: Dict[str, Any] = {
            "AccountKey": account.key,
            "Amount": order.quantity,
            "AssetType": order.asset_type,
            "BuySell": order.direction,
            "OrderDuration": {"DurationType": "GoodTillCancel"},
            "ManualOrder": True,
            "OrderType": order_type,
            "Uic": saxo_uic,
        }
        if order.type != OrderType.MARKET:
            data["OrderPrice"] = order.price
        if order.type == OrderType.STOP_LIMIT:
            data["OrderPrice"] = stop_price
            data["StopLimitPrice"] = order.price
        if order.type == OrderType.MARKET:
            data["OrderDuration"]["DurationType"] = "DayOrder"

        if conditional_order is not None:
            data["Orders"] = [
                {
                    "AccountKey": account.key,
                    "OrderType": "TriggerLimit",
                    "AssetType": conditional_order.asset_type,
                    "Uic": conditional_order.saxo_uic,
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "TriggerOrderData": {
                        "LowerPrice": conditional_order.price,
                        "PriceType": "LastTraded",
                    },
                    "ManualOrder": True,
                    "BuySell": (
                        Direction.SELL
                        if conditional_order.trigger == TriggerOrder.ABOVE
                        else Direction.BUY
                    ),
                }
            ]

        response = await self._request(
            "POST", f"{self.configuration.saxo_url}trade/v2/orders", json=data
        )
        self._check_response(response)
        return response.json()

    async def set_oco_order(
        self,
        account: Account,
        limit_order: Order,
        stop_order: Order,
        saxo_uic: str,
    ) -> Any:
        saxo_limit_order = {
            "AccountKey": account.key,
            "Amount": limit_order.quantity,
            "AssetType": limit_order.asset_type,
            "BuySell": limit_order.direction,
            "OrderDuration": {"DurationType": "GoodTillCancel"},
            "ManualOrder": True,
            "OrderPrice": limit_order.price,
            "OrderType": "Limit",
            "Uic": saxo_uic,
        }
        saxo_stop_order = {
            "AccountKey": account.key,
            "Amount": stop_order.quantity,
            "AssetType": stop_order.asset_type,
            "BuySell": stop_order.direction,
            "OrderDuration": {"DurationType": "GoodTillCancel"},
            "ManualOrder": True,
            "OrderPrice": stop_order.price,
            "OrderType": "StopIfTraded",
            "Uic": saxo_uic,
        }
        data = {"Orders": [saxo_limit_order, saxo_stop_order]}
        response = await self._request(
            "POST", f"{self.configuration.saxo_url}trade/v2/orders", json=data
        )
        self._check_response(response)
        return response.json()

    async def get_asset_detail(
        self, saxo_uic: str | int, asset_type: str
    ) -> Dict:
        asset_http = await self._request(
            "GET",
            f"{self.configuration.saxo_url}ref/v1/instruments/details?"
            f"Uics={saxo_uic}&AssetTypes={asset_type}",
        )
        self._check_response(asset_http)
        asset = asset_http.json()
        if len(asset["Data"]) != 1:
            raise SaxoException(f"Nothing found for {saxo_uic}")
        return asset["Data"][0]

    async def get_report(
        self, account: Account, date_s: str
    ) -> List[ReportOrder]:
        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}cs/v1/audit/orderactivities/"
            f"?ClientKey={account.client_key}&AccountKey={account.key}"
            f"&status=FinalFill&FromDateTime={date_s}",
        )
        self._check_response(response)
        orders = []
        for data in response.json()["Data"]:
            date = datetime.fromisoformat(data["ActivityTime"])
            try:
                asset = await self.get_asset_detail(
                    data["Uic"], data["AssetType"]
                )
            except EmptyResponseException:
                self.logger.error(
                    f"No asset for {data['Uic']} {data['AssetType']} at {date}"
                )
                continue
            report_order = ReportOrder(
                code=asset["Symbol"].split(":")[0],
                price=data["AveragePrice"],
                name=asset["Description"],
                quantity=data["Amount"],
                direction=Direction.get_value(data["BuySell"]),
                asset_type=AssetType.get_value(asset["AssetType"]),
                currency=Currency.get_value(asset["CurrencyCode"]),
                date=date,
            )
            if report_order.asset_type not in [
                AssetType.STOCK,
                AssetType.CFDINDEX,
                AssetType.CFDFUTURE,
            ]:
                if "UnderlyingUic" in asset:
                    underlying_asset_type = (
                        asset["UnderlyingAssetType"]
                        if "UnderlyingAssetType" in asset
                        else ""
                    )
                    underlying_close = await self.get_historical_price(
                        asset["UnderlyingUic"],
                        asset_type=underlying_asset_type,
                        date=date,
                    )
                    underlying = Underlying(price=underlying_close)
                    report_order.underlying = underlying
            orders.append(report_order)
        return orders

    async def get_historical_price(
        self, saxo_uic: int, date: datetime, asset_type: str
    ) -> float:
        response = await self._request(
            "GET",
            f"{self.configuration.saxo_url}chart/v3/charts/?Uic={saxo_uic}"
            f"&AssetType={asset_type}&Horizon=1&Mode=From&"
            f"Count=2&Time={date.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        )
        if response.status_code == 403 or response.status_code == 404:
            self.logger.warning(
                f"Can't rertrieve information for {saxo_uic} {asset_type}"
            )
            return 0.0
        self._check_response(response)
        data = response.json()["Data"]
        if len(data) == 0:
            return 0.0
        return get_price_from_saxo_data(data[0])

    def _get_historical_data_cache(self, horizon: int) -> Optional[TTLCache]:
        """
        Select the cache store for a given horizon.

        Returns None when the horizon is not cached.
        """
        if horizon in [30, 60, 1440, 10080]:
            return self.historical_data_cache
        if horizon == 5:
            return self.intraday_data_cache
        return None

    def _get_historical_data_cache_key(
        self,
        saxo_uic: str,
        asset_type: str,
        horizon: int,
        count: int,
        date: Optional[datetime],
    ) -> tuple:
        """
        Generate cache key for historical data.

        Args:
            saxo_uic: Asset identifier
            asset_type: Type of asset
            horizon: Time horizon in minutes
            count: Number of data points
            date: Optional date (if None, uses current time rounded to minute)

        Returns:
            Cache key tuple
        """
        if date:
            date_key = date.isoformat()
        else:
            now = datetime.now()
            # Round to nearest minute for cache sharing
            rounded = now.replace(second=0, microsecond=0)
            date_key = rounded.isoformat()
        return (saxo_uic, asset_type, horizon, count, date_key)

    async def get_historical_data(
        self,
        saxo_uic: str | int,
        asset_type: str,
        horizon: int,
        count: int,
        date: Optional[datetime] = None,
    ) -> List:
        """
        Get historical data for a specific asset
        First date is the newest and the list is sorted in a decremental way

        Caches data for horizon=30 (30min), horizon=60 (hourly),
        horizon=1440 (daily), and horizon=10080 (weekly) with 30min TTL,
        and horizon=5 (5min) with 5min TTL
        """
        # Convert to string if int provided (for compatibility)
        saxo_uic = str(saxo_uic)

        # Store original date for cache key
        original_date = date

        cache = self._get_historical_data_cache(horizon)
        if cache is not None:
            cache_key = self._get_historical_data_cache_key(
                saxo_uic, asset_type, horizon, count, original_date
            )

            if cache_key in cache:
                self.logger.debug(
                    f"Cache HIT for {saxo_uic} horizon={horizon} count={count}"
                )
                return cache[cache_key]

        max_items = 1200
        if date is None:
            date = datetime.now()
        real_count = count if count <= max_items else max_items
        offset = 0
        data = []
        while offset + real_count <= count:
            self.logger.debug(
                f"get_historical_data {saxo_uic}, horizon={horizon},"
                f" count={count}, realcount={real_count}, offset={offset}"
                f", {date}"
            )
            response = await self._request(
                "GET",
                f"{self.configuration.saxo_url}chart/v3/charts/?&Uic="
                f"{saxo_uic}&AssetType={asset_type}&Horizon={horizon}"
                f"&Mode=UpTo&Count={real_count}&"
                f"Time={date.strftime('%Y-%m-%dT%H:%M:00Z')}",
            )
            if response.status_code == 403 or response.status_code == 404:
                self.logger.warning(
                    f"Can't rertrieve information for {saxo_uic} {asset_type}"
                )
                return []
            self._check_response(response)
            tmp_data = response.json()["Data"]
            for d in tmp_data:
                try:
                    d["Time"] = datetime.strptime(
                        d["Time"], "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                except ValueError:
                    d["Time"] = datetime.strptime(
                        d["Time"], "%Y-%m-%dT%H:%M:%SZ"
                    )
            data += sorted(tmp_data, key=lambda x: x["Time"], reverse=True)
            offset += real_count
            real_count = (
                count - offset if count - offset < max_items else max_items
            )
            date = (
                data[-1]["Time"]
                if data[-1]["Time"] is not None
                else datetime.now()
            )
            if real_count == 0:
                break

        # Store in cache if applicable
        if cache is not None:
            cache_key = self._get_historical_data_cache_key(
                saxo_uic, asset_type, horizon, count, original_date
            )
            cache[cache_key] = data
            self.logger.debug(
                f"Cache STORED for {saxo_uic} horizon={horizon} count={count}"
            )

        return data

    async def is_day_open(
        self, saxo_uic: str, asset_type: str, date: datetime
    ) -> bool:
        end_of_day = date.replace(hour=23, minute=59, second=0, microsecond=0)
        data = await self.get_historical_data(
            saxo_uic, asset_type, 1440, 1, end_of_day
        )
        if len(data) == 0:
            return False
        return data[0]["Time"].day == date.day

    @staticmethod
    def _check_response(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise SaxoException("The access_token is expired")
        if response.status_code == 429:
            logger.warning(f"Rate limiting: {response.headers}")
        if response.text == "":
            raise EmptyResponseException()
        try:
            json = response.json()
        except ValueError:
            response.raise_for_status()
            raise SaxoException(
                f"Saxo returned a non-JSON body ({response.status_code})"
            )
        if "ErrorInfo" in json:
            raise SaxoException(json["ErrorInfo"]["Message"])
        if response.status_code == 400:
            raise SaxoException(json)
        response.raise_for_status()

    @staticmethod
    async def _wait_for_rate_limit(response: httpx.Response) -> None:
        for remaining_key, reset_key in RATE_LIMITING_KEYS:
            if (
                remaining_key in response.headers
                and int(response.headers[remaining_key]) <= 1
            ):
                wait_time = int(response.headers[reset_key]) + 1
                logger.warning(f"Rate limiting: wait {wait_time}")
                await asyncio.sleep(wait_time)
