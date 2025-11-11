import logging
import time
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests
from cachetools import TTLCache
from requests import Response
from requests.adapters import HTTPAdapter, Retry

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
from utils.configuration import Configuration
from utils.exception import EmptyResponseException, SaxoException
from utils.logger import Logger

RATE_LIMITING_KEYS = [
    (
        "X-RateLimit-RefDataInstrumentsMinute-Remaining",
        "X-RateLimit-RefDataInstrumentsMinute-Reset",
    ),
    ("X-RateLimit-ChartMinute-Remaining", "X-RateLimit-ChartMinute-Reset"),
]


class SaxoClient:
    def __init__(self, configuration: Configuration) -> None:
        self.logger = Logger.get_logger("saxo_client", logging.INFO)
        self.session = requests.Session()
        self.configuration = configuration
        # Cache for historical data with 30 min TTL
        # (only for horizon=60 and horizon=1440)
        self.historical_data_cache: TTLCache = TTLCache(maxsize=256, ttl=1800)
        self.session.headers.update(
            {"Authorization": f"Bearer {configuration.access_token}"}
        )
        self.session.headers.update({"Content-Type": "application/json"})
        retries = Retry(
            total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.hooks["response"].append(self.refresh_token)

    def refresh_token(self, request, *args, **kwargs):
        if request.status_code == 401:
            # In API mode, first try to reload tokens from S3
            # (another container may have already refreshed them)
            if self.configuration.api_mode:
                self.logger.info(
                    "API mode: attempting to reload tokens from S3 first"
                )
                if self.configuration.reload_tokens_from_s3():
                    self.logger.info(
                        "Tokens reloaded from S3, retrying request"
                    )
                    auth_header = f"Bearer {self.configuration.access_token}"
                    self.session.headers.update({"Authorization": auth_header})
                    request.request.headers["Authorization"] = (
                        self.session.headers["Authorization"]
                    )
                    retry_response = self.session.send(request.request)

                    # If still 401, proceed to refresh token API call
                    if retry_response.status_code != 401:
                        return retry_response
                    self.logger.info(
                        "Still 401 after S3 reload, calling refresh token API"
                    )

            # Standard refresh flow: call refresh token API
            auth_client = SaxoAuthClient(self.configuration)
            access_token, refresh_token = auth_client.refresh_token()
            self.configuration.save_tokens(access_token, refresh_token)
            self.session.headers.update(
                {"Authorization": f"Bearer {access_token}"}
            )
            request.request.headers["Authorization"] = self.session.headers[
                "Authorization"
            ]
            return self.session.send(request.request)

    @lru_cache(maxsize=256)
    def get_asset(self, code: str, market: Optional[str] = None) -> Dict:
        symbol = (
            f"{code}:{market}" if market is not None and market != "" else code
        )
        self.logger.debug(f"get_asset {symbol}")
        data = self._find_asset(symbol)
        data = list(
            filter(lambda x: x["Symbol"].lower() == symbol.lower(), data)
        )
        if len(data) > 1:
            codes = map(lambda x: x["Symbol"], data)
            raise SaxoException(
                f"Stock {code}:{market} has more than one entry,"
                f" check it: {list(codes)}"
            )
        if len(data) == 0:
            raise SaxoException(f"Stock {code}:{market} doesn't exist")
        return data[0]

    def search(
        self, keyword: str, asset_type: Optional[str] = None
    ) -> List[Asset]:
        data = self._find_asset(keyword, asset_type)
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
                exchange="saxo",
                identifier=item.get("Identifier"),
            )
            results.append(asset)

        return results

    def _find_asset(
        self, keyword: str, asset_type: Optional[str] = None
    ) -> List:
        if asset_type is None:
            asset_type = AssetType.all_saxo_values()
        response = self.session.get(
            f"{self.configuration.saxo_url}ref/v1/instruments/?Keywords="
            f"{keyword}&AssetTypes={asset_type}&IncludeNonTradable=true"
        )
        self._check_response(response)
        return response.json()["Data"]

    def get_total_amount(self) -> float:
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/balances/me"
        )
        self._check_response(response)
        return response.json()["TotalValue"]

    def get_open_orders(self) -> List:
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/orders/me/?$top=50"
        )
        self._check_response(response)
        return response.json()["Data"]

    def get_positions(self) -> List[Dict]:
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/positions/me/?top=50"
        )
        self._check_response(response)
        return response.json()

    def get_accounts(self):
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/accounts/me"
        )
        self._check_response(response)
        return response.json()

    def get_account(self, account_key: str) -> Account:
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/accounts/{account_key}"
        )
        self._check_response(response)
        account = response.json()
        name = (
            "NoName"
            if "DisplayName" not in account
            else account["DisplayName"]
        )
        client_key = account["ClientKey"]

        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/balances/"
            f"?AccountKey={account_key}&ClientKey={client_key}"
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

    def get_price(self, saxo_uic: int, asset_type: str) -> float:
        response = self.session.get(
            f"{self.configuration.saxo_url}trade/v1/infoprices/"
            f"?Uic={saxo_uic}&AssetType={asset_type}"
        )
        self._check_response(response)
        price = response.json()
        if price["Quote"]["MarketState"] == "Closed":
            print("Market is closed, price is set to 1")
            return 1.0
        return price["Quote"]["Ask"]

    def set_order(
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

        response = self.session.post(
            f"{self.configuration.saxo_url}trade/v2/orders", json=data
        )
        self._check_response(response)
        return response.json()

    def set_oco_order(
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
        response = self.session.post(
            f"{self.configuration.saxo_url}trade/v2/orders", json=data
        )
        self._check_response(response)
        return response.json()

    def get_asset_detail(self, saxo_uic: int, asset_type: str) -> Dict:
        asset_http = self.session.get(
            f"{self.configuration.saxo_url}ref/v1/instruments/details?"
            f"Uics={saxo_uic}&AssetTypes={asset_type}"
        )
        self._check_response(asset_http)
        asset = asset_http.json()
        if len(asset["Data"]) != 1:
            raise SaxoException(f"Nothing found for {saxo_uic}")
        return asset["Data"][0]

    def get_report(self, account: Account, date_s: str) -> List[ReportOrder]:
        response = self.session.get(
            f"{self.configuration.saxo_url}cs/v1/audit/orderactivities/"
            f"?ClientKey={account.client_key}&AccountKey={account.key}"
            f"&status=FinalFill&FromDateTime={date_s}"
        )
        self._check_response(response)
        orders = []
        for data in response.json()["Data"]:
            date = datetime.fromisoformat(data["ActivityTime"])
            try:
                asset = self.get_asset_detail(data["Uic"], data["AssetType"])
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
                    underlying_close = self.get_historical_price(
                        asset["UnderlyingUic"],
                        asset_type=underlying_asset_type,
                        date=date,
                    )
                    underlying = Underlying(price=underlying_close)
                    report_order.underlying = underlying
            orders.append(report_order)
        return orders

    def get_historical_price(
        self, saxo_uic: int, date: datetime, asset_type: str
    ) -> float:
        response = self.session.get(
            f"{self.configuration.saxo_url}chart/v3/charts/?Uic={saxo_uic}"
            f"&AssetType={asset_type}&Horizon=1&Mode=From&"
            f"Count=2&Time={date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
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

    def get_historical_data(
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

        Caches data for horizon=60 (hourly) and horizon=1440 (daily)
        with 30min TTL
        """
        # Convert to string if int provided (for compatibility)
        saxo_uic = str(saxo_uic)

        # Store original date for cache key
        original_date = date

        # Check cache only for hourly (60) and daily (1440) horizons
        if horizon in [60, 1440]:
            cache_key = self._get_historical_data_cache_key(
                saxo_uic, asset_type, horizon, count, original_date
            )

            if cache_key in self.historical_data_cache:
                self.logger.debug(
                    f"Cache HIT for {saxo_uic} horizon={horizon} count={count}"
                )
                return self.historical_data_cache[cache_key]

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
            response = self.session.get(
                f"{self.configuration.saxo_url}chart/v3/charts/?&Uic="
                f"{saxo_uic}&AssetType={asset_type}&Horizon={horizon}"
                f"&Mode=UpTo&Count={real_count}&"
                f"Time={date.strftime('%Y-%m-%dT%H:%M:00Z')}"
            )
            if response.status_code == 403 or response.status_code == 404:
                self.logger.warning(
                    f"Can't rertrieve information for {saxo_uic} {asset_type}"
                )
                return []
            self._check_response(response)
            tmp_data = response.json()["Data"]
            for d in tmp_data:
                d["Time"] = datetime.strptime(
                    d["Time"], "%Y-%m-%dT%H:%M:%S.%fZ"
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
        if horizon in [60, 1440]:
            cache_key = self._get_historical_data_cache_key(
                saxo_uic, asset_type, horizon, count, original_date
            )
            self.historical_data_cache[cache_key] = data
            self.logger.debug(
                f"Cache STORED for {saxo_uic} horizon={horizon} count={count}"
            )

        return data

    def is_day_open(
        self, saxo_uic: str, asset_type: str, date: datetime
    ) -> bool:
        data = self.get_historical_data(saxo_uic, asset_type, 1, 1, date)
        if len(data) == 0:
            return False
        return data[0]["Time"].day == date.day

    @staticmethod
    def _check_response(response: Response) -> None:
        if response.status_code == 401:
            raise SaxoException("The access_token is expired")
        if response.status_code == 429:
            print(f"Rate limiting: ${response.headers}")
        for remaining_key, reset_key in RATE_LIMITING_KEYS:
            SaxoClient.handle_rate_limiting(response, remaining_key, reset_key)
        if response.text == "":
            raise EmptyResponseException()
        json = response.json()
        if "ErrorInfo" in json:
            raise SaxoException(json["ErrorInfo"]["Message"])
        if response.status_code == 400:
            raise SaxoException(json)
        response.raise_for_status()

    @staticmethod
    def handle_rate_limiting(response, remaining_key, reset_key):
        if (
            remaining_key in response.headers
            and int(response.headers[remaining_key]) <= 1
        ):
            wait_time = int(response.headers[reset_key]) + 1
            print(f"Rate limiting: wait {wait_time}")
            time.sleep(wait_time)
