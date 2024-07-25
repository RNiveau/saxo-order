import pulumi_aws as aws

import pulumi


def resfreh_token_lambda(
    repository_url: str, lambda_role_arn: str
) -> aws.lambda_.Function:
    refresh_token_lambda = aws.lambda_.Function(
        "refresh_token",
        role=lambda_role_arn,
        image_uri=f"{_get_image_uri(repository_url)}",
        memory_size=256,
        timeout=20,
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={"SAXO_CONFIG": "prod_config.yml"}
        ),
        package_type="Image",
    )

    aws.lambda_.FunctionEventInvokeConfig(
        "refresh_token_retry_policy",
        function_name=refresh_token_lambda.name,
        maximum_event_age_in_seconds=60,
        maximum_retry_attempts=0,
    )

    return refresh_token_lambda


def alerting_lambda(
    repository_url: str, lambda_role_arn: str
) -> aws.lambda_.Function:
    alerting_lambda = aws.lambda_.Function(
        "alerting",
        role=lambda_role_arn,
        image_uri=f"{_get_image_uri(repository_url)}",
        timeout=600,
        memory_size=512,
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={"SAXO_CONFIG": "prod_config.yml"}
        ),
        package_type="Image",
    )

    aws.lambda_.FunctionEventInvokeConfig(
        "alerting_retry_policy",
        function_name=alerting_lambda.name,
        maximum_event_age_in_seconds=60,
        maximum_retry_attempts=0,
    )
    return alerting_lambda


def workflows_lambda(
    repository_url: str, lambda_role_arn: str
) -> aws.lambda_.Function:
    alerting_lambda = aws.lambda_.Function(
        "workflows",
        role=lambda_role_arn,
        image_uri=f"{_get_image_uri(repository_url)}",
        memory_size=512,
        timeout=600,
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={"SAXO_CONFIG": "prod_config.yml", "LOG_LEVEL": "DEBUG"},
        ),
        package_type="Image",
    )

    aws.lambda_.FunctionEventInvokeConfig(
        "workflows_retry_policy",
        function_name=alerting_lambda.name,
        maximum_event_age_in_seconds=60,
        maximum_retry_attempts=0,
    )
    return alerting_lambda


def _get_image_uri(repository_url: str) -> str:
    config = pulumi.Config()
    return f"{repository_url}:{config.get('image-tag')}"
