import os
import yaml
from typing import List, Dict


class Configuration:
    def __init__(self, config_file: str):
        if os.path.isfile(config_file):
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        if os.path.isfile("secrets.yml"):
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

    @property
    def spreadsheet_id(self) -> str:
        return self.config["spreadsheet_id"]

    @property
    def gsheet_creds_path(self) -> str:
        return "gsheet-creds.json"

    @property
    def currencies_rate(self) -> Dict:
        return self.config["currencies_rate"]
