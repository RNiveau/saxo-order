from typing import List

import pulumi_aws as aws

import pulumi


def bucket() -> aws.s3.Bucket:

    bucket = aws.s3.Bucket(
        "k-order",
        bucket="k-order",
        request_payer="BucketOwner",
        server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(  # noqa: E501
            rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(  # noqa: E501
                    sse_algorithm="AES256",
                ),
                bucket_key_enabled=True,
            ),
        ),
        versioning=aws.s3.BucketVersioningArgs(
            enabled=True,
        ),
        opts=pulumi.ResourceOptions(protect=True),
    )

    return bucket


def bucket_policy(bucket_id: str, role_arns: List[str]) -> None:
    s = ""
    for arn in role_arns:
        if s != "":
            s += ","
        s += '"' + arn + '"'
    aws.s3.BucketPolicy(
        "k-order-policy",
        bucket=bucket_id,
        policy=f"""{{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Principal": {{
                    "AWS": [{s}]
                }},
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::{bucket_id}",
                    "arn:aws:s3:::{bucket_id}/*"
                ]
            }}
        ]
    }}""",
    )
