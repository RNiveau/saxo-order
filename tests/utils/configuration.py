from utils.configuration import Configuration


class MockConfiguration(Configuration):
    def __init__(self):
        pass

    @property
    def app_key(self) -> str:
        return "app_key"

    @property
    def app_secret(self) -> str:
        return "app_secret"

    @property
    def auth_url(self) -> str:
        return "auth_url"

    @property
    def saxo_url(self) -> str:
        return "saxo_url"

    @property
    def access_token(self) -> str:
        return "access_token"
