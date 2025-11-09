import pulumi_aws as aws


def indicator_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "indicators",
        attributes=[aws.dynamodb.TableAttributeArgs(name="id", type="S")],
        hash_key="id",
        name="indicators",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
    )


def watchlist_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "watchlist",
        attributes=[aws.dynamodb.TableAttributeArgs(name="id", type="S")],
        hash_key="id",
        name="watchlist",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
    )


def asset_details_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "asset_details",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="asset_id", type="S")
        ],
        hash_key="asset_id",
        name="asset_details",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
    )
