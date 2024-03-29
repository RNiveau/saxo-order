import os
from typing import Dict, Tuple

import yaml


class Configuration:
    def __init__(self, config_file: str):
        if os.path.isfile(config_file):
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        if os.path.isfile("secrets.yml"):
            with open("secrets.yml", "r") as f:
                self.secrets = yaml.safe_load(f)
        self.access_token = ""
        self.refresh_token = ""
        self.load_tokens()

    def load_tokens(self) -> None:
        if os.path.isfile("access_token"):
            with open("access_token", "r") as f:
                content = f.read().strip()
                contents = content.split("\n")
                if len(contents) == 2:
                    self.access_token = contents[0]
                    self.refresh_token = contents[1]

    def save_tokens(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        with open("access_token", "w") as f:
            f.write(f"{access_token}\n")
            f.write(f"{refresh_token}\n")

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

    @property
    def spreadsheet_id(self) -> str:
        return self.config["spreadsheet_id"]

    @property
    def gsheet_creds_path(self) -> str:
        return "gsheet-creds.json"

    @property
    def currencies_rate(self) -> Dict:
        return self.config["currencies_rate"]

    @property
    def binance_keys(self) -> Tuple:
        return (self.secrets["binance_api_key"], self.secrets["binance_secret_key"])
