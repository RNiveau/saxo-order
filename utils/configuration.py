import logging
import os
from typing import Dict, Tuple

import yaml

from client.aws_client import AwsClient

logger = logging.getLogger(__name__)


class Configuration:
    def __init__(self, config_file: str):
        logger.setLevel(logging.INFO)
        if os.path.isfile(config_file):
            logger.info(f"Open {config_file} configuration")
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        if os.path.isfile("secrets.yml"):
            with open("secrets.yml", "r") as f:
                self.secrets = yaml.safe_load(f)
        self.access_token = ""
        self.refresh_token = ""
        self.aws_client = AwsClient() if AwsClient.is_aws_context() else None
        self.load_tokens()

    def load_tokens(self) -> None:
        if self.aws_client is not None:
            logger.info(f"Load tokens from aws")
            content = self.aws_client.get_access_token()
        else:
            if os.path.isfile("access_token"):
                logger.info(f"Load tokens from disk")
                with open("access_token", "r") as f:
                    content = f.read()
        contents = content.strip().split("\n")
        if len(contents) == 2:
            self.access_token = contents[0]
            self.refresh_token = contents[1]
        else:
            logger.error("Can't decode access token")

    def save_tokens(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        if self.aws_client is not None:
            logger.info(f"Save tokens to aws")
            self.aws_client.save_access_token(
                access_token=access_token, refresh_token=refresh_token
            )
        else:
            logger.info(f"Save tokens to disk")
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

    @property
    def slack_token(self) -> str:
        return self.secrets["slack_token"]
