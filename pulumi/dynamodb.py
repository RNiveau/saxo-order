import pulumi_aws as aws


def dynamodb_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "indicators",
        attributes=[aws.dynamodb.TableAttributeArgs(name="id", type="S")],
        hash_key="id",
        name="indicators",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
    )
