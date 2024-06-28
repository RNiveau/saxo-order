import base64

import requests

from utils.configuration import Configuration


class SaxoAuthClient:
    def __init__(self, configuration: Configuration) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        self.configuration = configuration

    def login(self) -> str:
        response = self.session.get(
            f"{self.configuration.auth_url}authorize?"
            f"response_type=code&client_id={self.configuration.app_key}&state"
            "=y90dsygas98dygoidsahf8sa&redirect_uri=http%3A%2F%2Flocalhost",
            allow_redirects=False,
        )
        response.raise_for_status()
        return response.headers["Location"]

    def access_token(self, code: str) -> tuple:
        response = self.session.post(
            f"{self.configuration.auth_url}token",
            data=f"grant_type=authorization_code&code={code}"
            "&redirect_uri=http%3A%2F%2Flocalhost",
            headers={"Authorization": f"Basic {self._auth_str()}"},
        )
        response.raise_for_status()
        return (
            response.json()["access_token"],
            response.json()["refresh_token"],
        )

    def refresh_token(self) -> tuple:
        response = self.session.post(
            f"{self.configuration.auth_url}token",
            data=f"grant_type=refresh_token&"
            f"refresh_token={self.configuration.refresh_token}",
            headers={"Authorization": f"Basic {self._auth_str()}"},
        )
        response.raise_for_status()
        return (
            response.json()["access_token"],
            response.json()["refresh_token"],
        )

    def _auth_str(self) -> str:
        auth_str = base64.b64encode(
            f"{self.configuration.app_key}:"
            f"{self.configuration.app_secret}".encode("utf-8")
        ).decode("utf-8")

        return auth_str
