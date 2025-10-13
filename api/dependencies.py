import os
from functools import lru_cache
from typing import Union

from client.mock_saxo_client import MockSaxoClient
from client.saxo_client import SaxoClient
from services.candles_service import CandlesService
from utils.configuration import Configuration
from utils.logger import Logger

logger = Logger.get_logger("api_dependencies")


@lru_cache()
def get_configuration() -> Configuration:
    """Get cached configuration instance."""
    config_file = os.getenv("CONFIG_FILE", "config.yml")
    logger.info(f"Loading configuration from: {config_file}")
    return Configuration(config_file)


@lru_cache()
def get_saxo_client() -> Union[SaxoClient, MockSaxoClient]:
    """
    Get cached SaxoClient instance with configuration.
    This is a dependency that can be injected into FastAPI endpoints.

    Returns MockSaxoClient if no access token is available.
    SaxoClient handles its own token refresh strategy.

    The client is cached as a singleton to ensure token refresh state
    is shared across all requests.
    """
    config = get_configuration()

    if not config.access_token:
        logger.warning(
            "No access token found, using MockSaxoClient for local development"
        )
        return MockSaxoClient(config)

    logger.debug("Using SaxoClient with token refresh capability")
    try:
        return SaxoClient(config)
    except Exception as e:
        logger.error(f"Failed to initialize SaxoClient: {e}")
        logger.warning("Falling back to MockSaxoClient")
        return MockSaxoClient(config)


@lru_cache()
def get_candles_service() -> CandlesService:
    """
    Get cached CandlesService instance.
    This is a dependency that can be injected into FastAPI endpoints.

    Uses the same cached saxo_client to ensure consistent token state.
    """
    saxo_client = get_saxo_client()
    return CandlesService(saxo_client)
