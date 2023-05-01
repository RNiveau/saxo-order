import yaml

class Configuration:
    def __init__(self):
        with open("secrets.yml", "r") as f:
            self.config = yaml.safe_load(f)

    @property
    def app_key(self) -> str:
        return self.config["app_key"]
    
    @property
    def app_secret(self) -> str:
        return self.config["app_secret"]