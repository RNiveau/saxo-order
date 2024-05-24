import os

import boto3

from client.saxo_auth_client import SaxoAuthClient
from utils.configuration import Configuration
from utils.exception import SaxoException


def handler(event, _):
    match event.get("command"):
        case "refresh_token":
            s3 = boto3.client("s3")
            response = s3.get_object(Bucket="k-order", Key="access_token")
            # Read the content of the object
            content = response["Body"].read().decode("utf-8")
            content = content.strip()
            contents = content.split("\n")
            configuration = Configuration(os.getenv("SAXO_CONFIG"))
            configuration.access_token = contents[0]
            configuration.refresh_token = contents[1]
            auth_client = SaxoAuthClient(configuration)
            access_token, refresh_token = auth_client.refresh_token()
            s3.put_object(
                Bucket="k-order",
                Key="access_token",
                Body=f"{access_token}\n{refresh_token}",
            )
            return {"result": "ok", "message": "token has been refreshed"}
        case _:
            raise SaxoException(f"Command {event.get('command')} not found")

    # # Print the content to the CloudWatch logs (optional)
    # print(object_content)

    # s3.put_object(Bucket="k-order", Key="access_token", Body="plouf")
    return {"result": "ok"}
