from utils.exception import SaxoException
from utils.configuration import Configuration

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from typing import Dict, List, Optional

SAXO_URL = "https://gateway.saxobank.com/sim/openapi/"


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

    def get_stock(self, code: str, market: str) -> Dict:
        response = self.session.get(
            f"{SAXO_URL}ref/v1/instruments/?Keywords={code}:{market}&AssetTypes=Stock"
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

    def get_total_amount(self) -> float:
        response = self.session.get(f"{SAXO_URL}port/v1/balances/me")
        self._check_response(response)
        return response.json()["TotalValue"]

    def get_positions(self) -> List[Dict]:
        response = self.session.get(f"{SAXO_URL}/port/v1/positions/me/?top=50")
        self._check_response(response)
        return response.json()

    def get_accounts(self):
        response = self.session.get(f"{SAXO_URL}/port/v1/accounts/me")
        self._check_response(response)
        return response.json()

    def set_order(
        self,
        account_key: str,
        stock_code: int,
        price: float,
        quantiy: int,
        order: str,
        direction: str,
        stop_price: Optional[float] = None,
    ) -> None:
        if order == "limit":
            order_type = "Limit"
        elif order == "stop":
            order_type = "Stop"
        else:
            order_type = "StopLimit"
        data = {
            "AccountKey": account_key,
            "Amount": quantiy,
            "AssetType": "Stock",
            "BuySell": direction.capitalize(),
            "OrderDuration": {"DurationType": "GoodTillCancel"},
            "ManualOrder": True,
            "OrderPrice": price,
            "OrderType": order_type,
            "Uic": stock_code,
        }
        if order_type == "StopLimit":
            data["OrderPrice"] = stop_price
            data["StopLimitPrice"] = price
        print(self.session.post(f"{SAXO_URL}trade/v2/orders", json=data).text)

    @staticmethod
    def _check_response(response: Response) -> None:
        if response.status_code == 401:
            raise SaxoException("The access_token is expired")
        response.raise_for_status()
