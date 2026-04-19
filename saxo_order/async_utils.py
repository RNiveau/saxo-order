import asyncio
import functools
from contextlib import asynccontextmanager

import aioboto3


def run_async(func):
    """Decorator that wraps async functions with asyncio.run() for CLI use."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@asynccontextmanager
async def create_dynamodb_client():
    """Create an async DynamoDBClient with managed resource for CLI use."""
    from client.aws_client import DynamoDBClient

    session = aioboto3.Session()
    resource = await session.resource(
        "dynamodb", region_name="eu-west-1"
    ).__aenter__()
    try:
        yield DynamoDBClient(dynamodb_resource=resource)
    finally:
        try:
            await asyncio.wait_for(
                resource.__aexit__(None, None, None), timeout=5.0
            )
        except asyncio.TimeoutError:
            pass
