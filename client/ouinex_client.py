import logging
import time
from typing import Any, Dict, List, Optional

import requests

from model.asset import Asset
from model.enum import AssetType, Exchange
from utils.exception import OuinexException
from utils.logger import Logger

# UNVERIFIED: the Ouinex schema exposes no `signIn` mutation (introspection is
# disabled, and no candidate name validates). Authenticated operations —
# candles and reporting — stay blocked until the auth entry point is known.
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
    instrument_id
    name
    base_currency {
      currency_id
    }
    quote_currency {
      currency_id
    }
  }
}
"""

CONVERSION_SUFFIX = "_CONV"


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
            raise OuinexException(
                f"Ouinex sign-in request failed: {e} - {response.text}"
            )

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
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query/mutation against the Ouinex endpoint.

        Authenticated operations sign in first and refresh the token once on an
        authentication failure. Public operations (`authenticated=False`, e.g.
        `instruments`) are sent without a bearer token and never sign in, but a
        401 still triggers one signed retry.
        """
        if authenticated:
            self._ensure_token()

        def _post() -> requests.Response:
            headers = (
                {"Authorization": f"Bearer {self._access_token}"}
                if self._access_token
                else {}
            )
            return self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables or {}},
                headers=headers,
                timeout=10,
            )

        response = _post()
        if response.status_code == 401:
            self._sign_in()
            response = _post()

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise OuinexException(
                f"Ouinex request failed: {e} - {response.text}"
            )

        payload = response.json()
        if payload.get("errors"):
            raise OuinexException(f"Ouinex GraphQL error: {payload['errors']}")

        return payload.get("data") or {}

    @staticmethod
    def _currencies(instrument: Dict[str, Any]) -> tuple:
        base = (instrument.get("base_currency") or {}).get("currency_id", "")
        quote = (instrument.get("quote_currency") or {}).get("currency_id", "")
        return base, quote

    def _map_instrument_to_asset(self, instrument: Dict[str, Any]) -> Asset:
        base, quote = self._currencies(instrument)
        symbol = instrument.get("instrument_id") or f"{base}{quote}"
        return Asset(
            symbol=symbol,
            description=instrument.get("name") or f"{base}/{quote}",
            asset_type=AssetType.CRYPTO,
            exchange=Exchange.OUINEX,
            identifier=None,
        )

    def search(self, keyword: str) -> List[Asset]:
        """
        Search Ouinex instruments by keyword.

        Fetches the instrument list via the public `instruments` GraphQL query
        and filters client-side against the symbol and base/quote currencies,
        mirroring the Binance search behavior. Conversion pairs (`*_CONV`) are
        excluded — they are not tradable instruments.

        Args:
            keyword: Search keyword to match against symbol or currencies

        Returns:
            List of Asset objects tagged Exchange.OUINEX / AssetType.CRYPTO
        """
        data = self._execute(INSTRUMENTS_QUERY, authenticated=False)
        keyword_lower = keyword.lower()

        results = []
        for instrument in data.get("instruments", []):
            base, quote = self._currencies(instrument)
            symbol = instrument.get("instrument_id") or f"{base}{quote}"

            if symbol.endswith(CONVERSION_SUFFIX):
                continue

            if (
                keyword_lower in symbol.lower()
                or keyword_lower in base.lower()
                or keyword_lower in quote.lower()
            ):
                results.append(self._map_instrument_to_asset(instrument))

        return results
