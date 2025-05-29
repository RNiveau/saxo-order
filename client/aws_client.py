import os

import boto3


class S3Client:

    BUCKET_NAME = "k-order"
    ACCESS_TOKEN = "access_token"
    WORKFLOWS = "workflows.yml"

    def __init__(self) -> None:
        self.s3 = boto3.client("s3")

    def get_access_token(self) -> str:
        response = self.s3.get_object(
            Bucket=S3Client.BUCKET_NAME, Key=S3Client.ACCESS_TOKEN
        )
        return response["Body"].read().decode("utf-8")

    def save_access_token(self, access_token: str, refresh_token: str) -> None:
        self.s3.put_object(
            Bucket=S3Client.BUCKET_NAME,
            Key=S3Client.ACCESS_TOKEN,
            Body=f"{access_token}\n{refresh_token}\n",
        )

    def get_workflows(self) -> str:
        response = self.s3.get_object(
            Bucket=S3Client.BUCKET_NAME, Key=S3Client.WORKFLOWS
        )
        return response["Body"].read().decode("utf-8")

    def save_workflows(self, content: str) -> None:
        self.s3.put_object(
            Bucket=S3Client.BUCKET_NAME,
            Key=S3Client.WORKFLOWS,
            Body=f"{content}\n",
        )

    @staticmethod
    def is_aws_context() -> bool:
        return (
            "AWS_LAMBDA_FUNCTION_NAME" in os.environ
            or "AWS_PROFILE" in os.environ
        )
