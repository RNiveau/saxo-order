import pulumi_aws as aws


def alerting_schedule(
    lambda_arn: str, scheduler_role_arn: str
) -> aws.scheduler.Schedule:
    return aws.scheduler.Schedule(
        "daily-alerting",
        schedule_expression="cron(15 18 * * ? *)",
        schedule_expression_timezone="Europe/Paris",
        flexible_time_window={"mode": "FLEXIBLE", "maximum_window_in_minutes": 5},
        target=aws.scheduler.ScheduleTargetArgs(
            arn=lambda_arn,
            role_arn=scheduler_role_arn,
            input='{"command": "alerting"}',
            retry_policy=aws.scheduler.ScheduleTargetRetryPolicyArgs(
                maximum_event_age_in_seconds=60,
                maximum_retry_attempts=0,
            ),
        ),
    )


def refresh_token_schedule(
    lambda_arn: str, scheduler_role_arn: str
) -> aws.scheduler.Schedule:
    return aws.scheduler.Schedule(
        "refresh_token",
        schedule_expression="rate(45 minutes)",
        flexible_time_window={"mode": "FLEXIBLE", "maximum_window_in_minutes": 5},
        target=aws.scheduler.ScheduleTargetArgs(
            arn=lambda_arn,
            role_arn=scheduler_role_arn,
            input='{"command": "refresh_token"}',
            retry_policy=aws.scheduler.ScheduleTargetRetryPolicyArgs(
                maximum_event_age_in_seconds=60,
                maximum_retry_attempts=0,
            ),
        ),
    )


def workflows_schedule(
    lambda_arn: str, scheduler_role_arn: str
) -> aws.scheduler.Schedule:
    return aws.scheduler.Schedule(
        "workflows",
        schedule_expression="cron(1 * ? * 1-5 *)",
        flexible_time_window={"mode": "OFF"},
        target=aws.scheduler.ScheduleTargetArgs(
            arn=lambda_arn,
            role_arn=scheduler_role_arn,
            input='{"command": "workflows"}',
            retry_policy=aws.scheduler.ScheduleTargetRetryPolicyArgs(
                maximum_event_age_in_seconds=60,
                maximum_retry_attempts=0,
            ),
        ),
    )
