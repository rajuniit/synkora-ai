"""Unit tests for MCPServerHostService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.fixture
def agent():
    a = MagicMock()
    a.id = uuid4()
    a.agent_name = "test_agent"
    a.description = "A test agent"
    return a


@pytest.fixture
def service():
    from src.services.agents.mcp_server_host_service import MCPServerHostService
    return MCPServerHostService()


@pytest.mark.asyncio
async def test_initialize(service, agent):
    payload = {"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
    db = AsyncMock()
    result = await service.handle_request(agent, payload, db)
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == "1"
    assert "protocolVersion" in result["result"]
    assert result["result"]["protocolVersion"] == "2025-06-18"


@pytest.mark.asyncio
async def test_tools_list(service, agent):
    payload = {"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}}
    db = AsyncMock()
    result = await service.handle_request(agent, payload, db)
    assert result["result"]["tools"][0]["name"] == "chat"
    assert "inputSchema" in result["result"]["tools"][0]


@pytest.mark.asyncio
async def test_tools_call_success(service, agent):
    payload = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {"name": "chat", "arguments": {"message": "Hello"}},
    }
    db = AsyncMock()

    async def fake_stream(*args, **kwargs):
        yield 'data: {"type": "chunk", "content": "Hello back!"}\n\n'
        yield 'data: {"type": "done"}\n\n'

    with patch(
        "src.services.agents.mcp_server_host_service._collect_agent_response",
        new=AsyncMock(return_value="Hello back!"),
    ):
        result = await service.handle_request(agent, payload, db)

    assert result["result"]["content"][0]["text"] == "Hello back!"
    assert result["result"]["isError"] is False


@pytest.mark.asyncio
async def test_tools_call_unknown_tool(service, agent):
    payload = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "tools/call",
        "params": {"name": "unknown_tool", "arguments": {}},
    }
    db = AsyncMock()
    result = await service.handle_request(agent, payload, db)
    assert "error" in result
    assert result["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_tools_call_missing_message(service, agent):
    payload = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "tools/call",
        "params": {"name": "chat", "arguments": {}},
    }
    db = AsyncMock()
    result = await service.handle_request(agent, payload, db)
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_method(service, agent):
    payload = {"jsonrpc": "2.0", "id": "6", "method": "unknown/method", "params": {}}
    db = AsyncMock()
    result = await service.handle_request(agent, payload, db)
    assert result["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_ping(service, agent):
    payload = {"jsonrpc": "2.0", "id": "7", "method": "ping", "params": {}}
    db = AsyncMock()
    result = await service.handle_request(agent, payload, db)
    assert result["result"] == {}
