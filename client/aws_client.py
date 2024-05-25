import boto3

class AwsClient:

    BUCKET_NAME = "k-order"
    ACCESS_TOKEN = 'access_token'

    def __init__(self) -> None:
        self.s3 = boto3.client("s3")
        
    def get_access_token(self) -> str:
        response = self.s3.get_object(Bucket=AwsClient.BUCKET_NAME, Key=AwsClient.ACCESS_TOKEN)
        return response["Body"].read().decode("utf-8")

    def save_access_token(self, access_token:str, refresh_token:str) ->None:
            self.s3.put_object(
                Bucket=AwsClient.BUCKET_NAME,
                Key=AwsClient.ACCESS_TOKEN,
                Body=f"{access_token}\n{refresh_token}\n",
            )

        