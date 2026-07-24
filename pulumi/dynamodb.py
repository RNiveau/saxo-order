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


def alerts_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "alerts",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="asset_code", type="S"),
            aws.dynamodb.TableAttributeArgs(name="country_code", type="S"),
        ],
        hash_key="asset_code",
        range_key="country_code",
        name="alerts",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
        ttl=aws.dynamodb.TableTtlArgs(
            enabled=True,
            attribute_name="ttl",
        ),
    )


def workflows_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "workflows",
        attributes=[aws.dynamodb.TableAttributeArgs(name="id", type="S")],
        hash_key="id",
        name="workflows",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
    )


def workflow_orders_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "workflow_orders",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="workflow_id", type="S"),
            aws.dynamodb.TableAttributeArgs(name="placed_at", type="N"),
        ],
        hash_key="workflow_id",
        range_key="placed_at",
        name="workflow_orders",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
        ttl=aws.dynamodb.TableTtlArgs(
            enabled=True,
            attribute_name="ttl",
        ),
    )


def alert_digests_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "alert_digests",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="run_date", type="S"),
            aws.dynamodb.TableAttributeArgs(name="created_at", type="N"),
        ],
        hash_key="run_date",
        range_key="created_at",
        name="alert_digests",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
    )


def backtest_candle_cache_table() -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        "backtest_candle_cache",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="definition_code", type="S"),
            aws.dynamodb.TableAttributeArgs(name="trading_date", type="S"),
        ],
        hash_key="definition_code",
        range_key="trading_date",
        name="backtest_candle_cache",
        billing_mode="PAY_PER_REQUEST",
        stream_enabled=True,
        stream_view_type="NEW_AND_OLD_IMAGES",
        # No TTL (FR-040): a closed historical trading day's candles
        # never change once cached.
    )
