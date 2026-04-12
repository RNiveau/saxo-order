import os
from functools import lru_cache
from typing import Optional, Union

from fastapi import Depends, HTTPException, Request

from api.services.asset_details_service import AssetDetailsService
from client.aws_client import AwsClient, DynamoDBClient
from client.binance_client import BinanceClient
from client.gsheet_client import GSheetClient
from client.mock_saxo_client import MockSaxoClient
from client.saxo_client import SaxoClient
from services.candles_service import CandlesService
from services.workflow_service import WorkflowService
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
    saxo_client = get_saxo_client()
    return CandlesService(saxo_client)


def get_dynamodb_client(request: Request) -> DynamoDBClient:
    if not AwsClient.is_aws_context():
        raise HTTPException(
            status_code=403,
            detail="AWS context not available. "
            "Set AWS_PROFILE environment variable.",
        )
    dynamodb = getattr(request.app.state, "dynamodb", None)
    return DynamoDBClient(dynamodb_resource=dynamodb)


def get_dynamodb_client_optional(request: Request) -> Optional[DynamoDBClient]:
    if AwsClient.is_aws_context():
        dynamodb = getattr(request.app.state, "dynamodb", None)
        return DynamoDBClient(dynamodb_resource=dynamodb)
    return None


@lru_cache()
def get_binance_client() -> BinanceClient:
    config = get_configuration()
    logger.debug("Using authenticated BinanceClient")
    return BinanceClient(
        key=config.binance_keys[0], secret=config.binance_keys[1]
    )


@lru_cache()
def get_gsheet_client() -> GSheetClient:
    config = get_configuration()
    logger.debug("Using GSheetClient for order logging")
    return GSheetClient(
        key_path=config.gsheet_creds_path,
        spreadsheet_id=config.spreadsheet_id,
    )


def get_asset_details_service(
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
) -> AssetDetailsService:
    return AssetDetailsService(dynamodb_client)


def get_workflow_service(
    dynamodb_client: DynamoDBClient = Depends(get_dynamodb_client),
) -> WorkflowService:
    return WorkflowService(dynamodb_client)
