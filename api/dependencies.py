import os
from functools import lru_cache
from typing import Optional, Union

from fastapi import HTTPException

from client.aws_client import AwsClient, DynamoDBClient
from client.binance_client import BinanceClient
from client.gsheet_client import GSheetClient
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


def get_dynamodb_client() -> DynamoDBClient:
    """
    Create DynamoDBClient instance.
    Validates AWS context before allowing access.

    This is a dependency that can be injected into FastAPI endpoints.
    """
    if not AwsClient.is_aws_context():
        raise HTTPException(
            status_code=403,
            detail="AWS context not available. "
            "Set AWS_PROFILE environment variable.",
        )
    return DynamoDBClient()


def get_dynamodb_client_optional() -> Optional[DynamoDBClient]:
    """
    Get DynamoDB client if AWS context is available, otherwise None.

    This is a dependency that can be injected into FastAPI endpoints
    where DynamoDB access is optional.
    """
    if AwsClient.is_aws_context():
        return DynamoDBClient()
    return None


@lru_cache()
def get_binance_client() -> BinanceClient:
    """
    Get cached BinanceClient instance.
    This is a dependency that can be injected into FastAPI endpoints.

    For search functionality, authentication is not required as the
    exchangeInfo endpoint is public. We use empty strings for key/secret
    since the search method doesn't use authenticated endpoints.
    """
    logger.debug("Using BinanceClient for search")
    return BinanceClient(key="", secret="")


@lru_cache()
def get_gsheet_client() -> GSheetClient:
    """
    Get cached GSheetClient instance.
    This is a dependency that can be injected into FastAPI endpoints.

    The client is cached as a singleton to reuse the Google Sheets
    connection across requests.
    """
    config = get_configuration()
    logger.debug("Using GSheetClient for order logging")
    return GSheetClient(
        key_path=config.gsheet_creds_path,
        spreadsheet_id=config.spreadsheet_id,
    )
