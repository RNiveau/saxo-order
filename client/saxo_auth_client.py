import base64

from utils.configuration import Configuration

import requests

from typing import Dict, List


class SaxoAuthClient:
    def __init__(self, configuration: Configuration) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        self.configuration = configuration

    def login(self) -> str:
        response = self.session.get(
            f"{self.configuration.auth_url}authorize?response_type=code&client_id={self.configuration.app_key}"
            "&state=y90dsygas98dygoidsahf8sa&redirect_uri=http%3A%2F%2Flocalhost",
            allow_redirects=False,
        )
        response.raise_for_status()
        return response.headers["Location"]

    def access_token(self, code: str) -> str:
        auth_str = base64.b64encode(
            f"{self.configuration.app_key}:{self.configuration.app_secret}".encode(
                "utf-8"
            )
        ).decode("utf-8")
        response = self.session.post(
            f"{self.configuration.auth_url}token",
            data=f"grant_type=authorization_code&code={code}&redirect_uri=http%3A%2F%2Flocalhost",
            headers={"Authorization": f"Basic {auth_str}"},
        )
        response.raise_for_status()
        return response.json()["access_token"]
