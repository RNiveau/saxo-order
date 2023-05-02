import os
import yaml


class Configuration:
    def __init__(self):
        with open("secrets.yml", "r") as f:
            self.config = yaml.safe_load(f)
        if os.path.isfile("access_token"):
            with open("access_token", "r") as f:
                self.access_token = f.read().strip()

    @property
    def app_key(self) -> str:
        return self.config["app_key"]

    @property
    def app_secret(self) -> str:
        return self.config["app_secret"]
