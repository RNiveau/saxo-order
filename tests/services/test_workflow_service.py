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
