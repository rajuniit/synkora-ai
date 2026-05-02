"""Unit tests for A2AService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def agent():
    a = MagicMock()
    a.id = uuid4()
    a.agent_name = "data_agent"
    a.description = "A data analysis agent"
    a.tenant_id = uuid4()
    a.agent_metadata = {
        "integrations_config": {
            "a2a_enabled": True,
            "a2a_public": False,
            "a2a_skills": [{"id": "analyze", "name": "Analyze Data", "description": "Run data analysis"}],
        }
    }
    return a


@pytest.fixture
def service():
    from src.services.agents.a2a_service import A2AService

    return A2AService()


def test_get_agent_card(service, agent):
    card = service.get_agent_card(agent, "http://localhost:5001")
    assert card["url"] == f"http://localhost:5001/api/a2a/agents/{agent.id}"
    assert card["capabilities"]["streaming"] is True
    assert card["authentication"]["schemes"] == ["Bearer"]
    assert len(card["skills"]) == 1
    assert card["skills"][0]["id"] == "analyze"


def test_get_agent_card_default_skills(service, agent):
    agent.agent_metadata = {"integrations_config": {"a2a_enabled": True, "a2a_skills": []}}
    card = service.get_agent_card(agent, "http://localhost:5001")
    # Should get a default 'chat' skill
    assert len(card["skills"]) == 1
    assert card["skills"][0]["id"] == "chat"


@pytest.mark.asyncio
async def test_send_message_success(service, agent):
    db = AsyncMock()
    input_msg = {"message": {"role": "user", "parts": [{"type": "text", "text": "Hello!"}]}}

    with patch(
        "src.services.agents.a2a_service._collect_agent_response",
        new=AsyncMock(return_value="Hi there!"),
    ):
        result = await service.send_message(agent, input_msg, db)

    assert result["status"]["state"] == "completed"
    assert result["artifacts"][0]["parts"][0]["text"] == "Hi there!"


@pytest.mark.asyncio
async def test_send_message_error(service, agent):
    db = AsyncMock()
    input_msg = {"message": {"role": "user", "parts": [{"type": "text", "text": "Hello!"}]}}

    with patch(
        "src.services.agents.a2a_service._collect_agent_response",
        new=AsyncMock(side_effect=RuntimeError("LLM failure")),
    ):
        result = await service.send_message(agent, input_msg, db)

    assert result["status"]["state"] == "failed"
    assert "error" in result["status"]


@pytest.mark.asyncio
async def test_create_task(service, agent):
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    input_msg = {
        "message": {"role": "user", "parts": [{"type": "text", "text": "Run analysis"}]},
    }

    with patch("src.tasks.a2a_tasks.execute_a2a_task") as mock_task:
        mock_task.delay = MagicMock()
        await service.create_task(agent, input_msg, {"ip": "127.0.0.1"}, db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    mock_task.delay.assert_called_once()


def test_extract_message_text():
    from src.services.agents.a2a_service import _extract_message_text

    msg = {"parts": [{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}]}
    assert _extract_message_text(msg) == "Hello World"

    empty = {"parts": []}
    assert _extract_message_text(empty) == ""

    no_parts = {}
    assert _extract_message_text(no_parts) == ""


def test_task_to_dict_completed():
    from datetime import UTC, datetime

    from src.models.agent_a2a_task import A2ATaskStatus, AgentA2ATask
    from src.services.agents.a2a_service import _task_to_dict

    task = MagicMock(spec=AgentA2ATask)
    task.task_id = "task-123"
    task.context_id = "ctx-456"
    task.status = A2ATaskStatus.COMPLETED
    task.output_text = "Analysis complete"
    task.updated_at = datetime.now(UTC)

    result = _task_to_dict(task)
    assert result["id"] == "task-123"
    assert result["status"]["state"] == A2ATaskStatus.COMPLETED
    assert result["artifacts"][0]["parts"][0]["text"] == "Analysis complete"


def test_task_to_dict_failed():
    from datetime import UTC, datetime

    from src.models.agent_a2a_task import A2ATaskStatus, AgentA2ATask
    from src.services.agents.a2a_service import _task_to_dict

    task = MagicMock(spec=AgentA2ATask)
    task.task_id = "task-789"
    task.context_id = "ctx-000"
    task.status = A2ATaskStatus.FAILED
    task.output_text = None
    task.error_code = "INTERNAL_ERROR"
    task.error_message = "Something broke"
    task.updated_at = datetime.now(UTC)

    result = _task_to_dict(task)
    assert result["status"]["state"] == A2ATaskStatus.FAILED
    assert result["status"]["error"]["code"] == "INTERNAL_ERROR"
