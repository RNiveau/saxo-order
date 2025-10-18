import os
from typing import Dict, Tuple

import yaml

from client.aws_client import S3Client
from utils.logger import Logger


class Configuration:
    def __init__(self, config_file: str):
        self.logger = Logger.get_logger("configuration")
        self.config = {}  # Initialize config as empty dict
        self.secrets = {}  # Initialize secrets as empty dict

        if os.path.isfile(config_file):
            self.logger.info(f"Open {config_file} configuration")
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.logger.warning(
                f"Config file {config_file} not found, using empty config"
            )

        if os.path.isfile("secrets.yml"):
            with open("secrets.yml", "r") as f:
                self.secrets = yaml.safe_load(f)
        else:
            self.logger.warning("secrets.yml not found, using empty secrets")
        self.access_token = ""
        self.refresh_token = ""
        self.aws_client = S3Client() if S3Client.is_aws_context() else None
        self.load_tokens()

    def load_tokens(self) -> None:
        content = ""
        if self.aws_client is not None:
            self.logger.info("Load tokens from aws")
            content = self.aws_client.get_access_token()
        else:
            if os.path.isfile("access_token"):
                self.logger.info("Load tokens from disk")
                with open("access_token", "r") as f:
                    content = f.read()
            else:
                self.logger.warning("No access_token file found")
                return

        if content:
            contents = content.strip().split("\n")
            if len(contents) == 2:
                self.access_token = contents[0]
                self.refresh_token = contents[1]
            else:
                self.logger.error("Can't decode access token")
        else:
            self.logger.warning("Empty access token content")

    def save_tokens(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        if self.aws_client is not None:
            self.logger.info("Save tokens to aws")
            self.aws_client.save_access_token(
                access_token=access_token, refresh_token=refresh_token
            )
        else:
            self.logger.info("Save tokens to disk")
            with open("access_token", "w") as f:
                f.write(f"{access_token}\n")
                f.write(f"{refresh_token}\n")

    def reload_tokens_from_s3(self) -> bool:
        """
        Reload tokens from S3 in API mode.
        Returns True if tokens were updated, False otherwise.
        """
        if self.aws_client is None:
            self.logger.warning(
                "Cannot reload tokens from S3: AWS client not available"
            )
            return False

        old_access_token = self.access_token
        old_refresh_token = self.refresh_token

        self.logger.info("Reloading tokens from S3")
        self.load_tokens()

        if (
            self.access_token == old_access_token
            and self.refresh_token == old_refresh_token
        ):
            self.logger.debug("Tokens unchanged in S3")
            return False

        self.logger.info("Tokens reloaded from S3")
        return True

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
        return (
            self.secrets["binance_api_key"],
            self.secrets["binance_secret_key"],
        )

    @property
    def slack_token(self) -> str:
        return self.secrets["slack_token"]

    @property
    def api_mode(self) -> bool:
        return os.getenv("API_MODE", "false").lower() == "true"
