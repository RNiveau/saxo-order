from utils.exception import SaxoException
from utils.configuration import Configuration
from model import Account, Order, OrderType, Direction

import requests
from requests import Response
from requests.adapters import HTTPAdapter, Retry

from typing import Dict, List, Optional, Any


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

    def get_asset(self, code: str, market: str) -> Dict:
        response = self.session.get(
            f"{self.configuration.saxo_url}ref/v1/instruments/?Keywords={code}:{market}&AssetTypes=Stock,MiniFuture"
        )
        self._check_response(response)
        data = response.json()["Data"]
        if len(data) > 1:
            codes = map(lambda x: x["Symbol"], data)
            raise SaxoException(
                f"Stock {code}:{market} has more than one entry, check it: {codes}"
            )
        if len(data) == 0:
            raise SaxoException(f"Stock {code}:{market} doesn't exist")
        return data[0]

    def search(self, keyword: str) -> Dict:
        response = self.session.get(
            f"{self.configuration.saxo_url}ref/v1/instruments/?Keywords={keyword}&AssetTypes=Stock,MiniFuture"
        )
        self._check_response(response)
        data = response.json()["Data"]
        if len(data) == 0:
            raise SaxoException(f"Nothing found for {keyword}")
        return data

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

    def get_account(self, account_key: str, client_key: str) -> Account:
        response = self.session.get(
            f"{self.configuration.saxo_url}port/v1/balances/?AccountKey={account_key}&ClientKey={client_key}"
        )
        self._check_response(response)
        account = response.json()
        return Account(
            account_key, account["TotalValue"], account["CashAvailableForTrading"]
        )

    def set_order(
        self,
        account: Account,
        order: Order,
        saxo_uic: int,
        stop_price: Optional[float] = None,
    ) -> Any:
        if order.type == OrderType.LIMIT:
            order_type = "Limit"
        elif order.type == OrderType.STOP and order.direction == Direction.BUY:
            order_type = "StopIfTraded"
        elif order.type == OrderType.STOP:
            order_type = "Stop"
        else:
            order_type = "StopLimit"
        data = {
            "AccountKey": account.key,
            "Amount": order.quantity,
            "AssetType": order.asset_type,
            "BuySell": order.direction,
            "OrderDuration": {"DurationType": "GoodTillCancel"},
            "ManualOrder": True,
            "OrderPrice": order.price,
            "OrderType": order_type,
            "Uic": saxo_uic,
        }
        if order.type == OrderType.STOP_LIMIT:
            data["OrderPrice"] = stop_price
            data["StopLimitPrice"] = order.price

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
            "AssetType": limit_order.type,
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
            "AssetType": stop_order.type,
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

    @staticmethod
    def _check_response(response: Response) -> None:
        if response.status_code == 401:
            raise SaxoException("The access_token is expired")
        json = response.json()
        if "ErrorInfo" in json:
            raise SaxoException(json["ErrorInfo"]["Message"])
        if response.status_code == 400:
            raise SaxoException(json)
        response.raise_for_status()
