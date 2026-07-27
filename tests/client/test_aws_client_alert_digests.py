from unittest.mock import AsyncMock

import pytest

from client.aws_client import DynamoDBClient
from model import AlertDigest, AlertType, Conviction, TriagedAsset


@pytest.fixture
def mock_dynamodb_resource():
    mock_resource = AsyncMock()
    mock_table = AsyncMock()
    mock_resource.Table.return_value = mock_table
    return mock_resource, mock_table


@pytest.fixture
def client(mock_dynamodb_resource):
    mock_resource, _ = mock_dynamodb_resource
    return DynamoDBClient(dynamodb_resource=mock_resource)


def _digest(run_date: str, created_at: int) -> AlertDigest:
    return AlertDigest(
        run_date=run_date,
        created_at=created_at,
        summary="1 high, 0 watch, 0 noise.",
        counts={"high": 1, "watch": 0, "noise": 0},
        triaged_assets=[
            TriagedAsset(
                asset_code="SAN",
                asset_description="Sanofi",
                exchange="saxo",
                conviction=Conviction.HIGH,
                rationale="double top + MA50 rejection, slope -2.3%",
                patterns=[AlertType.DOUBLE_TOP, AlertType.MM50_TOUCH],
                ma50_slope=-2.3,
                rank=1,
                country_code="xpar",
            )
        ],
        model="claude-sonnet-5",
        fallback_used=False,
    )


class TestStoreAlertDigest:
    async def test_store_alert_digest_converts_floats_and_enums(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        digest = _digest("2026-07-16", 1768579200)
        await client.store_alert_digest(digest)

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]["Item"]
        assert item["run_date"] == "2026-07-16"
        assert item["created_at"] == 1768579200
        assert item["fallback_used"] is False
        assert item["model"] == "claude-sonnet-5"

        asset = item["triaged_assets"][0]
        assert asset["asset_code"] == "SAN"
        assert asset["conviction"] == "high"
        assert asset["patterns"] == ["double_top", "mm50_touch"]
        assert str(asset["ma50_slope"]) == "-2.3"


class TestGetAlertDigests:
    async def test_get_alert_digests_returns_newest_first(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [
                {"run_date": "2026-07-14", "created_at": 100},
                {"run_date": "2026-07-16", "created_at": 300},
                {"run_date": "2026-07-15", "created_at": 200},
            ],
        }

        digests = await client.get_alert_digests()

        assert [d["created_at"] for d in digests] == [300, 200, 100]

    async def test_get_alert_digests_respects_limit(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.scan.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [
                {"run_date": "2026-07-14", "created_at": 100},
                {"run_date": "2026-07-16", "created_at": 300},
            ],
        }

        digests = await client.get_alert_digests(limit=1)

        assert len(digests) == 1
        assert digests[0]["created_at"] == 300


class TestGetAlertDigest:
    async def test_get_alert_digest_returns_latest_for_run_date(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.query.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [{"run_date": "2026-07-16", "created_at": 300}],
        }

        digest = await client.get_alert_digest("2026-07-16")

        assert digest is not None
        assert digest["created_at"] == 300
        query_kwargs = mock_table.query.call_args[1]
        assert query_kwargs["ScanIndexForward"] is False
        assert query_kwargs["Limit"] == 1

    async def test_get_alert_digest_returns_none_when_missing(
        self, mock_dynamodb_resource, client
    ):
        _, mock_table = mock_dynamodb_resource
        mock_table.query.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Items": [],
        }

        digest = await client.get_alert_digest("2026-07-01")

        assert digest is None
