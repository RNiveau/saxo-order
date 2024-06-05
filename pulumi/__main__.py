import ecr
import iam
import lambda_
import pulumi_aws as aws
import s3
import scheduler

import pulumi

caller_identity = aws.get_caller_identity()
user, access_key = iam.k_order_user()
bucket = s3.bucket()
lambda_role = iam.lambda_role()
scheduler_role = iam.scheduler_role(caller_identity.account_id)
ecr_repository = ecr.ecr_repository()
refresh_token_lambda = ecr_repository.repository_url.apply(
    lambda repository_url: lambda_.resfreh_token_lambda(repository_url, lambda_role.arn)
)
alerting_lambda = ecr_repository.repository_url.apply(
    lambda repository_url: lambda_.alerting_lambda(repository_url, lambda_role.arn)
)
pulumi.Output.all(refresh_token_lambda.arn, alerting_lambda.arn).apply(
    lambda args: iam.scheduler_role_policy(scheduler_role.id, [args[0], args[1]])
)
pulumi.Output.all(lambda_arn=alerting_lambda.arn, role_arn=scheduler_role.arn).apply(
    lambda args: scheduler.alerting_schedule(args["lambda_arn"], args["role_arn"])
)
pulumi.Output.all(
    lambda_arn=refresh_token_lambda.arn, role_arn=scheduler_role.arn
).apply(
    lambda args: scheduler.refresh_token_schedule(args["lambda_arn"], args["role_arn"])
)

pulumi.Output.all(
    bucket_id=bucket.id, lambda_arn=lambda_role.arn, user_arn=user.arn
).apply(
    lambda args: s3.bucket_policy(
        args["bucket_id"], [args["lambda_arn"], args["user_arn"]]
    )
)

pulumi.export("refresh_token_lambda_arn", refresh_token_lambda.arn)
pulumi.export("alerting_lambda_arn", alerting_lambda.arn)
pulumi.export("lambda_role_arn", lambda_role.arn)
pulumi.export("scheduler_role_arn", scheduler_role.arn)
pulumi.export("bucket_name", bucket.id)
pulumi.export(
    "bucket_url", pulumi.Output.concat("http://", bucket.bucket_regional_domain_name)
)
pulumi.export("repository_url", ecr_repository.repository_url)
pulumi.export("account_id", caller_identity.account_id)
pulumi.export("user_arn", user.arn)
pulumi.export("access_key_id", access_key.id)
pulumi.export("secret_access_key", access_key.secret)
