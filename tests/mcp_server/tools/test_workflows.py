from unittest.mock import AsyncMock

import pytest
from mcp.client import Client
from mcp.server.mcpserver.exceptions import ToolError

from client.aws_client import DynamoDBOperationError
from mcp_server import server
from mcp_server.tools import workflows


def _stored_workflow(**overrides):
    workflow = {
        "id": "wf-dax",
        "name": "dax breakout",
        "index": "DAX.I",
        "cfd": "GER40.I",
        "enable": True,
        "dry_run": True,
        "end_date": None,
        "conditions": [
            {
                "indicator": {"name": "ma50", "ut": "daily"},
                "close": {"direction": "above", "ut": "h1", "spread": 10},
                "element": "close",
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


@pytest.fixture
def store():
    client = AsyncMock()
    client.get_all_workflows.return_value = [
        _stored_workflow(),
        _stored_workflow(id="wf-off", enable=False),
    ]
    return client


async def test_returns_only_active_workflows_with_their_rules(store):
    result = await workflows.get_workflows("GER40.I", store)

    assert result.none_reason is None
    assert [w.id for w in result.workflows] == ["wf-dax"]
    workflow = result.workflows[0]
    assert workflow.index == "DAX.I"
    assert workflow.cfd == "GER40.I"
    assert workflow.dry_run is True
    assert workflow.conditions[0].close.direction == "above"
    assert workflow.trigger.location == "higher"


async def test_no_active_workflow_is_explicit_not_an_error(store):
    result = await workflows.get_workflows("ITP:xpar", store)

    assert result.workflows == []
    assert result.none_reason is not None
    assert "ITP:xpar" in result.none_reason


async def test_unreachable_store_names_the_cause():
    with pytest.raises(ToolError, match="workflow store is unreachable"):
        await workflows.get_workflows("DAX.I", None)


class _ConnectedStore:
    def __init__(self, client):
        self.client = client

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, *exc):
        return False


async def test_the_registered_tool_reads_the_lifespan_store(
    monkeypatch, store
):
    monkeypatch.setenv("AWS_PROFILE", "test")
    monkeypatch.setattr(
        "mcp_server.server.DynamoDBClient", lambda: _ConnectedStore(store)
    )

    async with Client(server.mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        result = await client.call_tool("get_workflows", {"code": "dax.i"})

    assert list(tools["get_workflows"].input_schema["properties"]) == ["code"]
    assert result.is_error is not True
    assert [w["id"] for w in result.structured_content["workflows"]] == [
        "wf-dax"
    ]


async def test_the_registered_tool_reports_a_missing_store(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)

    async with Client(server.mcp) as client:
        result = await client.call_tool("get_workflows", {"code": "DAX.I"})

    assert result.is_error is True
    assert "workflow store is unreachable" in result.content[0].text


async def test_an_unreadable_workflow_is_surfaced(store):
    store.get_all_workflows.return_value = [
        _stored_workflow(name="broken", trigger={"signal": "breakout"})
    ]

    result = await workflows.get_workflows("DAX.I", store)

    assert result.workflows == []
    assert result.unreadable_workflows == ["broken"]
    assert "unreadable_workflows" in result.none_reason


async def test_a_failed_store_read_reaches_the_model_readably(
    monkeypatch, store
):
    monkeypatch.setenv("AWS_PROFILE", "test")
    monkeypatch.setattr(
        "mcp_server.server.DynamoDBClient", lambda: _ConnectedStore(store)
    )
    store.get_all_workflows.side_effect = DynamoDBOperationError(
        "get_all_workflows", "workflows table throttled"
    )

    async with Client(server.mcp) as client:
        result = await client.call_tool("get_workflows", {"code": "DAX.I"})

    assert result.is_error is True
    assert "workflows table throttled" in result.content[0].text


async def test_a_blank_code_is_rejected(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)

    async with Client(server.mcp) as client:
        result = await client.call_tool("get_workflows", {"code": ""})

    assert result.is_error is True
    assert "unreachable" not in result.content[0].text
