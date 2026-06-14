from unittest.mock import AsyncMock

import pytest

from services.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_get_all_orders_deduplicates_by_workflow_id_keeping_latest():
    dynamodb_client = AsyncMock()
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

    service = WorkflowService(dynamodb_client=dynamodb_client)

    result = await service.get_all_orders(limit=100)

    assert len(result) == 2

    by_workflow = {item.workflow_id: item for item in result}
    assert by_workflow["wf-a"].id == "order-a-new"
    assert by_workflow["wf-a"].placed_at == 3_000
    assert by_workflow["wf-b"].id == "order-b"

    placed_at_values = [item.placed_at for item in result]
    assert placed_at_values == sorted(placed_at_values, reverse=True)

    dynamodb_client.get_all_workflow_orders.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_get_all_orders_applies_limit_after_dedup():
    dynamodb_client = AsyncMock()
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

    service = WorkflowService(dynamodb_client=dynamodb_client)

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


@pytest.mark.asyncio
async def test_get_workflow_by_id_uses_custom_tradingview_url_from_db():
    dynamodb_client = AsyncMock()
    dynamodb_client.get_workflow_by_id.return_value = _make_workflow_data(
        "wf-1", "NKE:xnys"
    )
    dynamodb_client.get_tradingview_link.return_value = (
        "https://www.tradingview.com/chart/custom"
    )

    service = WorkflowService(dynamodb_client=dynamodb_client)
    result = await service.get_workflow_by_id("wf-1")

    assert result is not None
    assert result.tradingview_url == "https://www.tradingview.com/chart/custom"
    dynamodb_client.get_tradingview_link.assert_awaited_once_with("NKE")


@pytest.mark.asyncio
async def test_get_workflow_by_id_builds_default_tradingview_url():
    dynamodb_client = AsyncMock()
    dynamodb_client.get_workflow_by_id.return_value = _make_workflow_data(
        "wf-2", "NKE:xnys"
    )
    dynamodb_client.get_tradingview_link.return_value = None

    service = WorkflowService(dynamodb_client=dynamodb_client)
    result = await service.get_workflow_by_id("wf-2")

    assert result is not None
    assert (
        result.tradingview_url
        == "https://www.tradingview.com/chart/?symbol=NYSE:NKE"
    )


@pytest.mark.asyncio
async def test_get_workflow_by_id_handles_dynamodb_failure():
    dynamodb_client = AsyncMock()
    dynamodb_client.get_workflow_by_id.return_value = _make_workflow_data(
        "wf-3", "MC:xpar"
    )
    dynamodb_client.get_tradingview_link.side_effect = RuntimeError("boom")

    service = WorkflowService(dynamodb_client=dynamodb_client)
    result = await service.get_workflow_by_id("wf-3")

    assert result is not None
    assert (
        result.tradingview_url
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:MC"
    )
