from typing import List

import pulumi_aws as aws

import pulumi


def lambda_role() -> aws.iam.Role:
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    lambda_role = aws.iam.Role(
        "lambda-assume-role",
        assume_role_policy=pulumi.Output.json_dumps(assume_role_policy),
    )

    aws.iam.RolePolicyAttachment(
        "lambda-basic-execution",
        role=lambda_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/"
        "AWSLambdaBasicExecutionRole",
    )

    return lambda_role


def scheduler_role(account_id: str) -> aws.iam.Role:
    return aws.iam.Role(
        "scheduler-role",
        assume_role_policy=f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Action": "sts:AssumeRole",
                    "Principal": {{
                        "Service": "scheduler.amazonaws.com"
                    }},
                    "Effect": "Allow",
                    "Condition": {{
                    "StringEquals": {{
                        "aws:SourceAccount": "{account_id}"
                    }}
                }}
                }}
            ]
        }}""",
    )


def scheduler_role_policy(role_id: int, lambda_arns: List[str]) -> None:
    s = ""
    for arn in lambda_arns:
        if s != "":
            s += ","
        s += '"' + arn + '","' + arn + ':*"'
    aws.iam.RolePolicy(
        "scheduler-role-policy",
        role=role_id,
        policy=f"""{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                {s}
            ]
        }}
    ]    }}""",
    )


def dynamodb_policy(
    dynamodb_tables: List[aws.dynamodb.Table], lambda_role: aws.iam.Role
) -> None:
    import json

    lambda_policy = aws.iam.Policy(
        "lambdaPolicy",
        description="A policy to allow Lambda to access DynamoDB",
        policy=pulumi.Output.all(
            *[table.arn for table in dynamodb_tables]
        ).apply(
            lambda arns: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:BatchWriteItem",
                            ],
                            "Effect": "Allow",
                            "Resource": arns,
                        }
                    ],
                }
            )
        ),
    )

    aws.iam.RolePolicyAttachment(
        "lambdaPolicyAttachment",
        role=lambda_role.name,
        policy_arn=lambda_policy.arn,
    )


def k_order_user() -> tuple:
    user = aws.iam.User("k-order")
    access_key = aws.iam.AccessKey("k-order-accesskey", user=user.name)
    return user, access_key


def user_dynamodb_policy(
    dynamodb_tables: List[aws.dynamodb.Table], user: aws.iam.User
) -> None:
    import json

    user_policy = aws.iam.Policy(
        "userDynamoDBPolicy",
        description="A policy to allow k-order user to access DynamoDB",
        policy=pulumi.Output.all(
            *[table.arn for table in dynamodb_tables]
        ).apply(
            lambda arns: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:BatchWriteItem",
                            ],
                            "Effect": "Allow",
                            "Resource": arns,
                        }
                    ],
                }
            )
        ),
    )

    aws.iam.UserPolicyAttachment(
        "userDynamoDBPolicyAttachment",
        user=user.name,
        policy_arn=user_policy.arn,
    )
