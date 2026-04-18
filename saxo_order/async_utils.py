import asyncio
import functools

import aioboto3


def run_async(func):
    """Decorator that wraps async functions with asyncio.run() for CLI use."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


async def create_dynamodb_client():
    """Create an async DynamoDBClient with managed resource for CLI use."""
    from client.aws_client import DynamoDBClient

    session = aioboto3.Session()
    resource = await session.resource(
        "dynamodb", region_name="eu-west-1"
    ).__aenter__()
    return DynamoDBClient(dynamodb_resource=resource), resource
