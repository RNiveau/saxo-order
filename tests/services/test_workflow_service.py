from datetime import date
from unittest.mock import AsyncMock

import pytest

from services.workflow_service import WorkflowService


@pytest.fixture
def dynamodb_client():
    return AsyncMock()


@pytest.fixture
def service(dynamodb_client):
    return WorkflowService(dynamodb_client=dynamodb_client)


async def test_get_all_orders_deduplicates_by_workflow_id_keeping_latest(
    service, dynamodb_client
):
    dynamodb_client.get_all_workflow_orders.return_value = [
        {
            "id": "order-a-old",
            "workflow_id": "wf-a",
            "workflow_name": "Workflow A",
            "placed_at": 1_000,
            "order_code": "FRA40.I",
            "order_price": 7800.0,
            "order_quantity": 10.0,
            "order_direction": "BUY",
        },
        {
            "id": "order-a-new",
            "workflow_id": "wf-a",
            "workflow_name": "Workflow A",
            "placed_at": 3_000,
            "order_code": "FRA40.I",
            "order_price": 7850.0,
            "order_quantity": 10.0,
            "order_direction": "SELL",
        },
        {
            "id": "order-b",
            "workflow_id": "wf-b",
            "workflow_name": "Workflow B",
            "placed_at": 2_000,
            "order_code": "GER40.I",
            "order_price": 18000.0,
            "order_quantity": 5.0,
            "order_direction": "BUY",
        },
    ]

    result = await service.get_all_orders(limit=100)

    assert len(result) == 2

    by_workflow = {item.workflow_id: item for item in result}
    assert by_workflow["wf-a"].id == "order-a-new"
    assert by_workflow["wf-a"].placed_at == 3_000
    assert by_workflow["wf-b"].id == "order-b"

    placed_at_values = [item.placed_at for item in result]
    assert placed_at_values == sorted(placed_at_values, reverse=True)

    dynamodb_client.get_all_workflow_orders.assert_awaited_once_with()


async def test_get_all_orders_applies_limit_after_dedup(
    service, dynamodb_client
):
    dynamodb_client.get_all_workflow_orders.return_value = [
        {
            "id": f"order-{i}",
            "workflow_id": f"wf-{i}",
            "workflow_name": f"Workflow {i}",
            "placed_at": 1_000 + i,
            "order_code": "FRA40.I",
            "order_price": 100.0,
            "order_quantity": 1.0,
            "order_direction": "BUY",
        }
        for i in range(5)
    ]

    result = await service.get_all_orders(limit=2)

    assert len(result) == 2
    assert [item.workflow_id for item in result] == ["wf-4", "wf-3"]


def _make_workflow_data(workflow_id: str, index: str) -> dict:
    return {
        "id": workflow_id,
        "name": "Test Workflow",
        "index": index,
        "cfd": index,
        "enable": True,
        "dry_run": False,
        "is_us": False,
        "end_date": None,
        "conditions": [
            {
                "indicator": {
                    "name": "ma7",
                    "ut": "daily",
                    "value": None,
                    "zone_value": None,
                },
                "close": {
                    "direction": "above",
                    "ut": "daily",
                    "spread": 0.5,
                },
                "element": None,
            }
        ],
        "trigger": {
            "ut": "daily",
            "signal": "breakout",
            "location": "higher",
            "order_direction": "buy",
            "quantity": 1.0,
        },
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


async def test_get_workflow_by_id_uses_custom_tradingview_url_from_db(
    service, dynamodb_client
):
    dynamodb_client.get_workflow_by_id.return_value = _make_workflow_data(
        "wf-1", "NKE:xnys"
    )
    dynamodb_client.get_tradingview_link.return_value = (
        "https://www.tradingview.com/chart/custom"
    )

    result = await service.get_workflow_by_id("wf-1")

    assert result is not None
    assert result.tradingview_url == "https://www.tradingview.com/chart/custom"
    dynamodb_client.get_tradingview_link.assert_awaited_once_with("NKE")


async def test_get_workflow_by_id_builds_default_tradingview_url(
    service, dynamodb_client
):
    dynamodb_client.get_workflow_by_id.return_value = _make_workflow_data(
        "wf-2", "NKE:xnys"
    )
    dynamodb_client.get_tradingview_link.return_value = None

    result = await service.get_workflow_by_id("wf-2")

    assert result is not None
    assert (
        result.tradingview_url
        == "https://www.tradingview.com/chart/?symbol=NYSE:NKE"
    )


async def test_get_workflow_by_id_handles_dynamodb_failure(
    service, dynamodb_client
):
    dynamodb_client.get_workflow_by_id.return_value = _make_workflow_data(
        "wf-3", "MC:xpar"
    )
    dynamodb_client.get_tradingview_link.side_effect = RuntimeError("boom")

    result = await service.get_workflow_by_id("wf-3")

    assert result is not None
    assert (
        result.tradingview_url
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:MC"
    )


def _stored_workflow(**overrides):
    workflow = {
        "id": "wf-dax",
        "name": "dax breakout",
        "index": "DAX.I",
        "cfd": "GER40.I",
        "enable": True,
        "dry_run": False,
        "is_us": False,
        "end_date": None,
        "conditions": [
            {
                "indicator": {"name": "ma50", "ut": "daily"},
                "close": {"direction": "above", "ut": "h1", "spread": 10},
            }
        ],
        "trigger": {
            "ut": "h1",
            "signal": "breakout",
            "location": "higher",
            "order_direction": "buy",
            "quantity": 0.1,
        },
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    workflow.update(overrides)
    return workflow


TODAY = date(2026, 10, 4)


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({}, True),
        ({"enable": False}, False),
        ({"end_date": "2026-10-03"}, False),
        ({"end_date": "2026-10-04"}, True),
        ({"end_date": "2026/10/05"}, True),
        ({"end_date": "2026/10/03"}, False),
    ],
)
async def test_get_active_workflows_by_asset_keeps_what_the_engine_runs(
    service, dynamodb_client, overrides, expected
):
    dynamodb_client.get_all_workflows.return_value = [
        _stored_workflow(**overrides)
    ]

    result = await service.get_active_workflows_by_asset("DAX.I", TODAY)

    assert bool(result.workflows) is expected
    assert result.unreadable == []


@pytest.mark.parametrize("code", ["DAX.I", "dax.i", "GER40.I", "ger40.i"])
async def test_get_active_workflows_by_asset_matches_index_or_cfd(
    service, dynamodb_client, code
):
    dynamodb_client.get_all_workflows.return_value = [
        _stored_workflow(),
        _stored_workflow(id="wf-cac", index="CAC40.I", cfd="FRA40.I"),
    ]

    result = await service.get_active_workflows_by_asset(code, TODAY)

    assert [w.id for w in result.workflows] == ["wf-dax"]
    assert result.workflows[0].trigger.order_direction == "buy"
    assert result.workflows[0].conditions[0].indicator.name == "ma50"


async def test_get_active_workflows_by_asset_unrelated_asset_is_empty(
    service, dynamodb_client
):
    dynamodb_client.get_all_workflows.return_value = [_stored_workflow()]

    result = await service.get_active_workflows_by_asset("ITP:xpar", TODAY)

    assert result.workflows == []
    assert result.unreadable == []


@pytest.mark.parametrize(
    "overrides, missing_key",
    [
        ({"end_date": "not a date"}, None),
        ({"trigger": {"signal": "breakout"}}, None),
        ({}, "created_at"),
    ],
)
async def test_get_active_workflows_by_asset_reports_unreadable_rows(
    service, dynamodb_client, overrides, missing_key
):
    broken = _stored_workflow(id="wf-broken", name="broken", **overrides)
    if missing_key:
        del broken[missing_key]
    dynamodb_client.get_all_workflows.return_value = [
        broken,
        _stored_workflow(),
    ]

    result = await service.get_active_workflows_by_asset("DAX.I", TODAY)

    assert [w.id for w in result.workflows] == ["wf-dax"]
    assert result.unreadable == ["broken"]


async def test_get_active_workflows_by_asset_normalises_and_orders(
    service, dynamodb_client
):
    dynamodb_client.get_all_workflows.return_value = [
        _stored_workflow(id="wf-z", name="z", end_date="2026/12/01"),
        _stored_workflow(id="wf-a", name="a"),
        _stored_workflow(id="wf-null", index=None, cfd=None),
    ]

    result = await service.get_active_workflows_by_asset("DAX.I", TODAY)

    assert [w.id for w in result.workflows] == ["wf-a", "wf-z"]
    assert result.workflows[1].end_date == "2026-12-01"
