import os
from functools import lru_cache

from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.logger import Logger

logger = Logger.get_logger("api_dependencies")


@lru_cache()
def get_configuration() -> Configuration:
    """Get cached configuration instance."""
    config_file = os.getenv("CONFIG_FILE", "config.yml")
    logger.info(f"Loading configuration from: {config_file}")
    return Configuration(config_file)


def get_saxo_client() -> SaxoClient:
    """
    Create SaxoClient instance with configuration.
    This is a dependency that can be injected into FastAPI endpoints.
    """
    config = get_configuration()
    return SaxoClient(config)
