import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from model import Currency, Direction, ReportOrder, Taxes
from model.asset import Asset
from model.enum import AssetType, Exchange
from utils.exception import OuinexException
from utils.logger import Logger

SIGN_IN_MUTATION = """
mutation SignIn($apiKey: String!, $secretKey: String!) {
  signIn(apiKey: $apiKey, secretKey: $secretKey) {
    accessToken
    refreshToken
    expiresIn
  }
}
"""

INSTRUMENTS_QUERY = """
query Instruments {
  instruments {
    id
    symbol
    baseCurrency
    quoteCurrency
  }
}
"""

CLOSED_ORDERS_QUERY = """
query ClosedOrders($fromDate: String!) {
  closedOrders(fromDate: $fromDate) {
    symbol
    baseCurrency
    quoteCurrency
    side
    price
    quantity
    fee
    feeCurrency
    executedAt
  }
}
"""


class OuinexClient:
    """
    GraphQL + JWT client for the Ouinex crypto provider.

    Exposes the same public method surface the app already relies on for
    Binance (search / get_candles / get_report*), added incrementally by the
    user stories. This foundational layer provides the GraphQL transport and
    the JWT sign-in / refresh lifecycle every operation depends on.
    """

    TOKEN_REFRESH_MARGIN = 30

    def __init__(self, key: str, secret: str, graphql_url: str) -> None:
        self.logger = Logger.get_logger("ouinex_client", logging.INFO)
        self.key = key
        self.secret = secret
        self.graphql_url = graphql_url
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _sign_in(self) -> None:
        response = self.session.post(
            self.graphql_url,
            json={
                "query": SIGN_IN_MUTATION,
                "variables": {
                    "apiKey": self.key,
                    "secretKey": self.secret,
                },
            },
            timeout=10,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise OuinexException(f"Ouinex sign-in request failed: {e}")

        payload = response.json()
        if payload.get("errors"):
            raise OuinexException(f"Ouinex sign-in error: {payload['errors']}")

        data = (payload.get("data") or {}).get("signIn")
        if not data or not data.get("accessToken"):
            raise OuinexException("Ouinex sign-in returned no access token")

        self._access_token = data["accessToken"]
        self._token_expiry = time.time() + float(data.get("expiresIn", 0))

    def _ensure_token(self) -> None:
        if (
            self._access_token is None
            or time.time() >= self._token_expiry - self.TOKEN_REFRESH_MARGIN
        ):
            self._sign_in()

    def _execute(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query/mutation against the Ouinex endpoint with a
        valid JWT, refreshing the token once on an authentication failure.
        """
        self._ensure_token()

        def _post() -> requests.Response:
            return self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables or {}},
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=10,
            )

        response = _post()
        if response.status_code == 401:
            self._sign_in()
            response = _post()

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise OuinexException(f"Ouinex request failed: {e}")

        payload = response.json()
        if payload.get("errors"):
            raise OuinexException(f"Ouinex GraphQL error: {payload['errors']}")

        return payload.get("data") or {}

    def _map_instrument_to_asset(self, instrument: Dict[str, Any]) -> Asset:
        base = instrument.get("baseCurrency", "")
        quote = instrument.get("quoteCurrency", "")
        symbol = instrument.get("symbol") or f"{base}{quote}"
        identifier = instrument.get("id")
        return Asset(
            symbol=symbol,
            description=f"{base}/{quote}",
            asset_type=AssetType.CRYPTO,
            exchange=Exchange.OUINEX,
            identifier=int(identifier) if identifier is not None else None,
        )

    def search(self, keyword: str) -> List[Asset]:
        """
        Search Ouinex instruments by keyword.

        Fetches the instrument list via the `instruments` GraphQL query and
        filters client-side against the symbol and base/quote currencies,
        mirroring the Binance search behavior.

        Args:
            keyword: Search keyword to match against symbol or currencies

        Returns:
            List of Asset objects tagged Exchange.OUINEX / AssetType.CRYPTO
        """
        data = self._execute(INSTRUMENTS_QUERY)
        keyword_lower = keyword.lower()

        results = []
        for instrument in data.get("instruments", []):
            base = instrument.get("baseCurrency", "")
            quote = instrument.get("quoteCurrency", "")
            symbol = instrument.get("symbol") or f"{base}{quote}"

            if (
                keyword_lower in symbol.lower()
                or keyword_lower in base.lower()
                or keyword_lower in quote.lower()
            ):
                results.append(self._map_instrument_to_asset(instrument))

        return results

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _apply_commission(
        self, trade: Dict[str, Any], order: ReportOrder, usdeur_rate: float
    ) -> None:
        fee = float(trade.get("fee") or 0)
        if fee <= 0:
            order.taxes = Taxes(cost=0, taxes=0)
            return

        fee_currency = trade.get("feeCurrency", "")
        if fee_currency == order.name:
            # Fee charged in the base asset (e.g. 0.539 XRP on an XRP buy):
            # it reduces the quantity actually received and is valued in EUR
            # at the trade price.
            if order.direction == Direction.BUY:
                order.quantity -= fee
            order.taxes = Taxes(cost=fee * order.price * usdeur_rate, taxes=0)
        else:
            # Fee charged in the quote/cash currency: already a cash amount.
            order.taxes = Taxes(cost=fee * usdeur_rate, taxes=0)

    def _map_trade_to_order(
        self, trade: Dict[str, Any], usdeur_rate: float
    ) -> ReportOrder:
        base = trade.get("baseCurrency", "")
        side = (trade.get("side") or "").upper()
        direction = Direction.BUY if side == "BUY" else Direction.SELL
        order = ReportOrder(
            code=base,
            name=base,
            price=float(trade["price"]),
            quantity=float(trade["quantity"]),
            direction=direction,
            asset_type=AssetType.CRYPTO,
            date=self._parse_timestamp(trade["executedAt"]),
            currency=Currency.USD,
        )
        self._apply_commission(trade, order, usdeur_rate)
        return order

    def get_report_all(
        self, date: str, usdeur_rate: float
    ) -> List[ReportOrder]:
        """
        Get all closed Ouinex orders since `date`, mapped to ReportOrder.

        Args:
            date: Start date (as accepted by the Ouinex `closedOrders` query)
            usdeur_rate: USD→EUR rate used for commission conversion

        Returns:
            List of ReportOrder objects (asset_type=CRYPTO, currency=USD)
        """
        data = self._execute(CLOSED_ORDERS_QUERY, {"fromDate": date})
        return [
            self._map_trade_to_order(trade, usdeur_rate)
            for trade in data.get("closedOrders", [])
        ]

    def get_report(
        self, symbol: str, date: str, usdeur_rate: float
    ) -> List[ReportOrder]:
        """
        Get closed Ouinex orders for a single symbol since `date`.

        Args:
            symbol: Base currency code to filter on (e.g. "BTC")
            date: Start date (as accepted by the Ouinex `closedOrders` query)
            usdeur_rate: USD→EUR rate used for commission conversion

        Returns:
            List of ReportOrder objects for the given symbol
        """
        return [
            order
            for order in self.get_report_all(date, usdeur_rate)
            if order.code == symbol
        ]
