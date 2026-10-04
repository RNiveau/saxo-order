import base64

import httpx

from utils.configuration import Configuration


class SaxoAuthClient:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    async def login(self) -> str:
        async with self._http() as http:
            response = await http.get(
                f"{self.configuration.auth_url}authorize?"
                f"response_type=code&client_id={self.configuration.app_key}"
                "&state=y90dsygas98dygoidsahf8sa"
                "&redirect_uri=http%3A%2F%2Flocalhost",
                follow_redirects=False,
            )
        if not response.is_redirect:
            response.raise_for_status()
        return response.headers["Location"]

    async def access_token(self, code: str) -> tuple:
        async with self._http() as http:
            response = await http.post(
                f"{self.configuration.auth_url}token",
                content=f"grant_type=authorization_code&code={code}"
                "&redirect_uri=http%3A%2F%2Flocalhost",
                headers={"Authorization": f"Basic {self._auth_str()}"},
            )
        response.raise_for_status()
        return (
            response.json()["access_token"],
            response.json()["refresh_token"],
        )

    async def refresh_token(self) -> tuple:
        async with self._http() as http:
            response = await http.post(
                f"{self.configuration.auth_url}token",
                content=f"grant_type=refresh_token&"
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
