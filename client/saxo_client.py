from utils.exception import SaxoException

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from typing import Dict, List

SAXO_URL = "https://gateway.saxobank.com/sim/openapi/"

class SaxoClient:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer "})
        self.session.headers.update({"Content-Type": "application/json"})
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)

    def get_stock(self, code:str, market:str) -> Dict:
        response = self.session.get(f"{SAXO_URL}ref/v1/instruments/?Keywords={code}:{market}&AssetTypes=Stock")
        response.raise_for_status()
        data = response.json()["Data"]
        if len(data) > 1:
            codes = map(lambda x: x["Symbol"], data)
            raise SaxoException(f"Stock {code}:{market} has more than one entry, check it: {codes}")
        return data[0]

    def get_total_amount(self) -> float:
        response = self.session.get(f"{SAXO_URL}port/v1/balances/me")
        response.raise_for_status()
        return response.json()["TotalValue"]

    def get_positions(self) -> List[Dict]:
        response = self.session.get(f"{SAXO_URL}/port/v1/positions/me/?top=50")
        response.raise_for_status()
        return response.json()