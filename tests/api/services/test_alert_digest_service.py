from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from api.services.alert_digest_service import AlertDigestService
from client.aws_client import DynamoDBClient


@pytest.fixture
def mock_dynamodb_client():
    return AsyncMock(spec=DynamoDBClient)


@pytest.fixture
def service(mock_dynamodb_client):
    return AlertDigestService(mock_dynamodb_client)


def _item(run_date: str, created_at: int) -> dict:
    return {
        "run_date": run_date,
        "created_at": Decimal(created_at),
        "summary": f"digest {run_date}",
        "counts": {
            "high": Decimal(1),
            "watch": Decimal(0),
            "noise": Decimal(0),
        },
        "triaged_assets": [
            {
                "asset_code": "SAN",
                "asset_description": "Sanofi",
                "exchange": "saxo",
                "country_code": "xpar",
                "conviction": "high",
                "rank": Decimal(1),
                "rationale": "double top + MA50 rejection",
                "patterns": ["double_top", "mm50_touch"],
                "ma50_slope": Decimal("-2.3"),
            }
        ],
        "fallback_used": False,
        "model": "claude-sonnet-5",
    }


class TestListRecent:
    async def test_list_recent_returns_newest_first_and_converts_decimals(
        self, service, mock_dynamodb_client
    ):
        mock_dynamodb_client.get_alert_digests.return_value = [
            _item("2026-07-16", 300),
            _item("2026-07-15", 200),
        ]
        mock_dynamodb_client.get_all_tradingview_links.return_value = {
            "SAN:xpar": "https://www.tradingview.com/chart/custom"
        }

        digests = await service.list_recent()

        assert [d.run_date for d in digests] == ["2026-07-16", "2026-07-15"]
        assert digests[0].counts == {"high": 1, "watch": 0, "noise": 0}
        assert digests[0].triaged_assets[0].ma50_slope == -2.3
        assert digests[0].triaged_assets[0].rank == 1
        assert (
            digests[0].triaged_assets[0].tradingview_url
            == "https://www.tradingview.com/chart/custom"
        )

    async def test_list_recent_uses_cache_on_second_call(
        self, service, mock_dynamodb_client
    ):
        mock_dynamodb_client.get_alert_digests.return_value = [
            _item("2026-07-16", 300)
        ]
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        await service.list_recent()
        await service.list_recent()

        mock_dynamodb_client.get_alert_digests.assert_called_once()


class TestGetByRunDate:
    async def test_get_by_run_date_returns_digest(
        self, service, mock_dynamodb_client
    ):
        mock_dynamodb_client.get_alert_digest.return_value = _item(
            "2026-07-16", 300
        )
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}

        digest = await service.get_by_run_date("2026-07-16")

        assert digest is not None
        assert digest.run_date == "2026-07-16"
        mock_dynamodb_client.get_alert_digest.assert_called_once_with(
            "2026-07-16"
        )

    async def test_get_by_run_date_returns_none_when_missing(
        self, service, mock_dynamodb_client
    ):
        mock_dynamodb_client.get_alert_digest.return_value = None

        digest = await service.get_by_run_date("2026-01-01")

        assert digest is None


class TestWorkflowTriggers:
    async def test_pre_feature_digest_without_the_key_reads_back_clean(
        self, service, mock_dynamodb_client
    ):
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}
        mock_dynamodb_client.get_alert_digests.return_value = [
            _item("2026-07-16", 300)
        ]

        digests = await service.list_recent()

        assert digests[0].triaged_assets[0].workflow_triggers is None

    async def test_triggers_are_hydrated_with_decimals_widened(
        self, service, mock_dynamodb_client
    ):
        item = _item("2026-07-16", 300)
        item["triaged_assets"][0]["workflow_triggers"] = [
            {
                "workflow_name": "SAN breakout H1",
                "direction": "BUY",
                "order_price": Decimal("158.4"),
                "trigger_close": Decimal("157.9"),
                "placed_at": Decimal(1768567800),
                "dry_run": False,
            }
        ]
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}
        mock_dynamodb_client.get_alert_digests.return_value = [item]

        digests = await service.list_recent()

        trigger = digests[0].triaged_assets[0].workflow_triggers[0]
        assert trigger.workflow_name == "SAN breakout H1"
        assert trigger.direction == "BUY"
        assert trigger.order_price == 158.4
        assert trigger.trigger_close == 157.9
        assert trigger.placed_at == 1768567800
        assert trigger.dry_run is False

    async def test_missing_trigger_close_stays_none(
        self, service, mock_dynamodb_client
    ):
        item = _item("2026-07-16", 300)
        item["triaged_assets"][0]["workflow_triggers"] = [
            {
                "workflow_name": "paper rule",
                "direction": "SELL",
                "order_price": Decimal("10"),
                "trigger_close": None,
                "placed_at": Decimal(1768567800),
                "dry_run": True,
            }
        ]
        mock_dynamodb_client.get_all_tradingview_links.return_value = {}
        mock_dynamodb_client.get_alert_digests.return_value = [item]

        digests = await service.list_recent()

        trigger = digests[0].triaged_assets[0].workflow_triggers[0]
        assert trigger.trigger_close is None
        assert trigger.dry_run is True
