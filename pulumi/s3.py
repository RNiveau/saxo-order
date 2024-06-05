import pulumi_aws as aws

import pulumi


def bucket() -> aws.s3.Bucket:

    bucket = aws.s3.Bucket(
        "k-order",
        bucket="k-order",
        request_payer="BucketOwner",
        server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(
            rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
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


def bucket_policy(bucket_id: str, lambda_role_arn: str) -> None:
    aws.s3.BucketPolicy(
        "k-order-policy",
        bucket=bucket_id,
        policy=f"""{{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Principal": {{
                    "AWS": ["{lambda_role_arn}"]
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
