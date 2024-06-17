import os

from slack_sdk import WebClient

from client.saxo_auth_client import SaxoAuthClient
from saxo_order.commands.alerting import run_alerting
from utils.configuration import Configuration
from utils.exception import SaxoException


def handler(event, _):
    match event.get("command"):
        case "refresh_token":
            configuration = Configuration(os.getenv("SAXO_CONFIG"))
            auth_client = SaxoAuthClient(configuration)
            try:
                access_token, refresh_token = auth_client.refresh_token()
            except Exception as e:
                slack_client = WebClient(token=configuration.slack_token)
                slack_client.chat_postMessage(
                    channel="#errors",
                    text=f"Refresh token fails:\n```{e}```",
                )
                return {"result": "ko", "message": "can't refresh the token"}
            configuration.save_tokens(access_token, refresh_token)
            return {"result": "ok", "message": "token has been refreshed"}
        case "alerting":
            run_alerting(os.getenv("SAXO_CONFIG"))
        case "test":
            from datetime import datetime

            print(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
        case _:
            raise SaxoException(f"Command {event.get('command')} not found")
    return {"result": "ok"}
