import os

from slack_sdk import WebClient

from client.saxo_auth_client import SaxoAuthClient
from saxo_order.commands.alerting import run_alerting
from saxo_order.commands.workflow import execute_workflow
from utils.configuration import Configuration
from utils.exception import SaxoException


def handler(event, _):
    try:
        match event.get("command"):
            case "refresh_token":
                configuration = Configuration(os.getenv("SAXO_CONFIG"))
                auth_client = SaxoAuthClient(configuration)
                access_token, refresh_token = auth_client.refresh_token()
                configuration.save_tokens(access_token, refresh_token)
                return {"result": "ok", "message": "token has been refreshed"}
            case "alerting":
                run_alerting(os.getenv("SAXO_CONFIG"))
            case "workflows":
                execute_workflow(os.getenv("SAXO_CONFIG"))
            case _:
                raise SaxoException(
                    f"Command {event.get('command')} not found"
                )
    except Exception as e:
        slack_client = WebClient(token=configuration.slack_token)
        slack_client.chat_postMessage(
            channel="#errors",
            text=f"Command {event.get('command')} fails:\n```{e}```",
        )
        return {"result": "ko", "message": "can't refresh the token"}
    return {"result": "ok"}
