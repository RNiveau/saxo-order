import os

import boto3

from client.saxo_auth_client import SaxoAuthClient
from utils.configuration import Configuration
from utils.exception import SaxoException


def handler(event, _):
    match event.get("command"):
        case "refresh_token":
            configuration = Configuration(os.getenv("SAXO_CONFIG"))
            auth_client = SaxoAuthClient(configuration)
            access_token, refresh_token = auth_client.refresh_token()
            configuration.save_tokens(access_token, refresh_token)
            return {"result": "ok", "message": "token has been refreshed"}
        case _:
            raise SaxoException(f"Command {event.get('command')} not found")
    return {"result": "ok"}
