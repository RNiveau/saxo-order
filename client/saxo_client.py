import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
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
from utils.configuration import Configuration
from utils.exception import SaxoException


class SaxoClient:
    def __init__(self, configuration: Configuration) -> None:
        self.session = requests.Session()
        self.configuration = configuration
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
            auth_client = SaxoAuthClient(self.configuration)
            access_token, refresh_token = auth_client.refresh_token()
            self.configuration.save_tokens(access_token, refresh_token)
            self.session.headers.update({"Authorization": f"Bearer {access_token}"})
            request.request.headers["Authorization"] = self.session.headers[
                "Authorization"
            ]
            return self.session.send(request.request)

    def get_asset(self, code: str, market: Optional[str] = None) -> Dict:
        symbol = f"{code}:{market}" if market is not None and market != "" else code
        data = self._find_asset(symbol)
        data = list(filter(lambda x: x["Symbol"].lower() == symbol.lower(), data))
        if len(data) > 1:
            codes = map(lambda x: x["Symbol"], data)
            raise SaxoException(
                f"Stock {code}:{market} has more than one entry, check it: {list(codes)}"
            )
        if len(data) == 0:
            raise SaxoException(f"Stock {code}:{market} doesn't exist")
        return data[0]

    def search(self, keyword: str) -> List:
        data = self._find_asset(keyword)
        if len(data) == 0:
            raise SaxoException(f"Nothing found for {keyword}")
        return data

    def _find_asset(self, keyword: str) -> List:
        response = self.session.get(
            f"{self.configuration.saxo_url}ref/v1/instruments/?Keywords={keyword}&AssetTypes={AssetType.all_saxo_values()}&IncludeNonTradable=true"
        )
        self._check_response(response)
        return response.json()["Data"]

    def get_total_amount(self) -> float:
        response = self.session.get(f"{self.configuration.saxo_url}port/v1/balances/me")
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
        response = self.session.get(f"{self.configuration.saxo_url}port/v1/accounts/me")
        self._check_response(response)
        return response.json()

    def get_account(self, account_key: str) -> Account:
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/accounts/{account_key}"
        )
        self._check_response(response)
        account = response.json()
        name = "NoName" if "DisplayName" not in account else account["DisplayName"]
        client_key = account["ClientKey"]

        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/balances/?AccountKey={account_key}&ClientKey={client_key}"
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
            f"{self.configuration.saxo_url}trade/v1/infoprices/?Uic={saxo_uic}&AssetType={asset_type}"
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
        self, account: Account, limit_order: Order, stop_order: Order, saxo_uic: str
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
            f"{self.configuration.saxo_url}ref/v1/instruments/details?Uics={saxo_uic}&AssetTypes={asset_type}"
        )
        self._check_response(asset_http)
        asset = asset_http.json()
        if len(asset["Data"]) != 1:
            raise SaxoException(f"Nothing found for {saxo_uic}")
        return asset["Data"][0]

    def get_report(self, account: Account, date_s: str) -> List[ReportOrder]:
        response = self.session.get(
            f"{self.configuration.saxo_url}cs/v1/audit/orderactivities/?ClientKey={account.client_key}&AccountKey={account.key}&status=FinalFill&FromDateTime={date_s}"
        )
        self._check_response(response)
        orders = []
        for data in response.json()["Data"]:
            date = datetime.fromisoformat(data["ActivityTime"])
            asset = self.get_asset_detail(data["Uic"], data["AssetType"])
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
                        else None
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
            f"{self.configuration.saxo_url}chart/v1/charts/?Uic={saxo_uic}&AssetType={asset_type}&Horizon=1&Mode=From&Count=2&Time={date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )
        if response.status_code == 403:
            print(f"Can't rertrieve information for {saxo_uic} {asset_type}")
            return 0.0
        self._check_response(response)
        data = response.json()["Data"]
        if len(data) == 0:
            return 0.0
        return get_price_from_saxo_data(data[0])

    def get_historical_data(
        self, saxo_uic: str, asset_type: str, horizon: int, count: int, date: datetime
    ) -> List:
        """
        Get historical data for a specific asset
        First date is the newest and the list is sorted in a decremental way
        """
        logging.debug(
            f"get_historical_data {saxo_uic}, horizon={horizon}, count={count}, {date}"
        )
        response = self.session.get(
            f"{self.configuration.saxo_url}chart/v1/charts/?&Uic={saxo_uic}&AssetType={asset_type}&Horizon={horizon}&Mode=UpTo&Count={count}&Time={date.strftime('%Y-%m-%dT%H:00:00Z')}"
        )
        self._check_response(response)
        data = response.json()["Data"]
        for d in data:
            d["Time"] = datetime.strptime(d["Time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        data = sorted(data, key=lambda x: x["Time"], reverse=True)
        return data

    @staticmethod
    def _check_response(response: Response) -> None:
        if response.status_code == 401:
            raise SaxoException("The access_token is expired")
        if (
            "X-RateLimit-RefDataInstrumentsMinute-Remaining" in response.headers
            and int(response.headers["X-RateLimit-RefDataInstrumentsMinute-Remaining"])
            <= 1
        ):
            print(
                f"Rate limiting: wait {response.headers['X-RateLimit-RefDataInstrumentsMinute-Reset']}"
            )
            time.sleep(
                int(response.headers["X-RateLimit-RefDataInstrumentsMinute-Reset"]) + 1
            )
        json = response.json()
        if "ErrorInfo" in json:
            raise SaxoException(json["ErrorInfo"]["Message"])
        if response.status_code == 400:
            raise SaxoException(json)
        response.raise_for_status()
