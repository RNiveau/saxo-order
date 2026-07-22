import logging
import time
from typing import Any, Dict, Optional

import requests

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
