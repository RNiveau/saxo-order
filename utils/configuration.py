import os
import yaml


class Configuration:
    def __init__(self, config_file: str):
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
        with open("secrets.yml", "r") as f:
            self.secrets = yaml.safe_load(f)
        if os.path.isfile("access_token"):
            with open("access_token", "r") as f:
                self.access_token = f.read().strip()

    @property
    def app_key(self) -> str:
        return self.secrets["app_key"]

    @property
    def app_secret(self) -> str:
        return self.secrets["app_secret"]

    @property
    def auth_url(self) -> str:
        return self.config["auth_url"]

    @property
    def saxo_url(self) -> str:
        return self.config["saxo_url"]
