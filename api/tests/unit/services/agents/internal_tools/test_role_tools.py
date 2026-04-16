"""
Tests for role_tools.py - Role-Based Agent Tools

Tests the tools for agents with roles to access project context,
escalate to humans, and collaborate with other agents.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestInternalGetProjectInfo:
    """Tests for internal_get_project_info function."""

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_project(self):
        from src.services.agents.internal_tools.role_tools import internal_get_project_info

        mock_service = MagicMock()
        mock_service.get_project = AsyncMock(return_value=None)

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.project_service.ProjectService",
                return_value=mock_service,
            ),
        ):
            result = await internal_get_project_info(project_id=str(uuid4()))

            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_project_info(self):
        from src.services.agents.internal_tools.role_tools import internal_get_project_info

        project_id = uuid4()
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.name = "Test Project"
        mock_project.description = "A test project"
        mock_project.status = "active"
        mock_project.external_project_ref = {"jira": "TEST-123"}
        mock_project.knowledge_base_id = uuid4()
        mock_project.created_at = None

        mock_service = MagicMock()
        mock_service.get_project = AsyncMock(return_value=mock_project)

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.project_service.ProjectService",
                return_value=mock_service,
            ),
        ):
            result = await internal_get_project_info(project_id=str(project_id))

            assert result["success"] is True
            assert result["project"]["name"] == "Test Project"
            assert result["project"]["has_knowledge_base"] is True


class TestInternalGetProjectContext:
    """Tests for internal_get_project_context function."""

    @pytest.mark.asyncio
    async def test_returns_all_context(self):
        from src.services.agents.internal_tools.role_tools import internal_get_project_context

        project_id = uuid4()
        mock_service = MagicMock()
        mock_service.get_context = AsyncMock(return_value={"key1": "value1", "key2": "value2"})

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.project_service.ProjectService",
                return_value=mock_service,
            ),
        ):
            result = await internal_get_project_context(project_id=str(project_id))

            assert result["success"] is True
            assert "key1" in result["context"]

    @pytest.mark.asyncio
    async def test_returns_specific_key(self):
        from src.services.agents.internal_tools.role_tools import internal_get_project_context

        project_id = uuid4()
        mock_service = MagicMock()
        mock_service.get_context = AsyncMock(return_value={"status": "in_progress"})

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.project_service.ProjectService",
                return_value=mock_service,
            ),
        ):
            result = await internal_get_project_context(project_id=str(project_id), key="status")

            assert result["success"] is True
            assert result["key"] == "status"
            assert result["value"] == "in_progress"
            assert result["found"] is True


class TestInternalUpdateProjectContext:
    """Tests for internal_update_project_context function."""

    @pytest.mark.asyncio
    async def test_updates_context_successfully(self):
        from src.services.agents.internal_tools.role_tools import internal_update_project_context

        project_id = uuid4()
        mock_project = MagicMock()
        mock_project.tenant_id = uuid4()

        mock_service = MagicMock()
        mock_service.get_project = AsyncMock(return_value=mock_project)
        mock_service.set_context_value = AsyncMock(return_value=True)

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.project_service.ProjectService",
                return_value=mock_service,
            ),
        ):
            result = await internal_update_project_context(project_id=str(project_id), key="status", value="completed")

            assert result["success"] is True
            assert "updated successfully" in result["message"]


class TestInternalEscalateToHuman:
    """Tests for internal_escalate_to_human function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.role_tools import internal_escalate_to_human

        result = await internal_escalate_to_human(
            reason="uncertainty", subject="Need help", message="I'm stuck", runtime_context=None
        )

        assert "error" in result
        assert "Runtime context required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_agent_id_in_context(self):
        from src.services.agents.internal_tools.role_tools import internal_escalate_to_human

        result = await internal_escalate_to_human(
            reason="uncertainty",
            subject="Need help",
            message="I'm stuck",
            runtime_context={"conversation_id": "123"},  # Missing agent_id
        )

        assert "error" in result
        # The function checks for agent_id after checking for runtime_context
        assert "Agent ID" in result["error"] or "not found" in result["error"].lower()


class TestInternalGetMyHumanContact:
    """Tests for internal_get_my_human_contact function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.role_tools import internal_get_my_human_contact

        result = await internal_get_my_human_contact(runtime_context=None)

        assert "error" in result
        assert "Runtime context required" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_human_contact(self):
        from src.services.agents.internal_tools.role_tools import internal_get_my_human_contact

        agent_id = uuid4()
        mock_human = MagicMock()
        mock_human.id = uuid4()
        mock_human.name = "John Doe"
        mock_human.preferred_channel = "slack"
        mock_human.get_available_channels.return_value = ["slack", "email"]
        mock_human.is_active = True
        mock_human.timezone = "America/New_York"

        mock_service = MagicMock()
        mock_service.get_contact_for_agent = AsyncMock(return_value=mock_human)

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.human_contact_service.HumanContactService",
                return_value=mock_service,
            ),
        ):
            result = await internal_get_my_human_contact(runtime_context={"agent_id": str(agent_id)})

            assert result["success"] is True
            assert result["human"]["name"] == "John Doe"
            assert result["human"]["preferred_channel"] == "slack"


class TestInternalCheckEscalationStatus:
    """Tests for internal_check_escalation_status function."""

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_escalation(self):
        from src.services.agents.internal_tools.role_tools import internal_check_escalation_status

        mock_service = MagicMock()
        mock_service.get_escalation = AsyncMock(return_value=None)

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.human_escalation_service.HumanEscalationService",
                return_value=mock_service,
            ),
        ):
            result = await internal_check_escalation_status(escalation_id=str(uuid4()))

            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_escalation_status(self):
        from src.services.agents.internal_tools.role_tools import internal_check_escalation_status

        escalation_id = uuid4()
        mock_escalation = MagicMock()
        mock_escalation.id = escalation_id
        mock_escalation.status = "pending"
        mock_escalation.subject = "Need help"
        mock_escalation.reason = "uncertainty"
        mock_escalation.priority = "medium"
        mock_escalation.created_at = None
        mock_escalation.is_resolved = False
        mock_escalation.is_pending = True
        mock_escalation.human_response = None
        mock_escalation.notification_sent_at = None

        mock_service = MagicMock()
        mock_service.get_escalation = AsyncMock(return_value=mock_escalation)

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.human_escalation_service.HumanEscalationService",
                return_value=mock_service,
            ),
        ):
            result = await internal_check_escalation_status(escalation_id=str(escalation_id))

            assert result["success"] is True
            assert result["status"] == "pending"
            assert result["is_pending"] is True


class TestInternalGetProjectAgents:
    """Tests for internal_get_project_agents function."""

    @pytest.mark.asyncio
    async def test_returns_agents_list(self):
        from src.services.agents.internal_tools.role_tools import internal_get_project_agents

        project_id = uuid4()
        agent1_id = uuid4()

        mock_agent1 = MagicMock()
        mock_agent1.id = agent1_id
        mock_agent1.agent_name = "Agent 1"
        mock_agent1.agent_type = "assistant"
        mock_agent1.role = MagicMock(role_type="developer", role_name="Dev Lead")
        mock_agent1.human_contact_id = uuid4()

        mock_agent2 = MagicMock()
        mock_agent2.id = uuid4()
        mock_agent2.agent_name = "Agent 2"
        mock_agent2.agent_type = "assistant"
        mock_agent2.role = None
        mock_agent2.human_contact_id = None

        mock_service = MagicMock()
        mock_service.get_project_agents = AsyncMock(return_value=[mock_agent1, mock_agent2])

        mock_db = AsyncMock(spec=AsyncSession)

        async def mock_get_async_db():
            yield mock_db

        with (
            patch("src.core.database.get_async_db", mock_get_async_db),
            patch(
                "src.services.roles.project_service.ProjectService",
                return_value=mock_service,
            ),
        ):
            result = await internal_get_project_agents(
                project_id=str(project_id), runtime_context={"agent_id": str(agent1_id)}
            )

            assert result["success"] is True
            assert result["total_agents"] == 2
            assert result["agents"][0]["name"] == "Agent 1"
            assert result["agents"][0]["is_current"] is True
            assert result["agents"][1]["is_current"] is False


class TestInternalGetMyRole:
    """Tests for internal_get_my_role function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.role_tools import internal_get_my_role

        result = await internal_get_my_role(runtime_context=None)

        assert "error" in result
        assert "Runtime context required" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_role_info(self):
        from src.services.agents.internal_tools.role_tools import internal_get_my_role

        agent_id = uuid4()
        role_id = uuid4()

        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.role_type = "developer"
        mock_role.role_name = "Senior Developer"
        mock_role.description = "Handles complex development tasks"
        mock_role.suggested_tools = ["internal_github_clone_repo", "internal_jira_create_issue"]
        mock_role.default_capabilities = {"can_write_code": True}

        mock_agent = MagicMock()
        mock_agent.role = mock_role

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def mock_get_async_db():
            yield mock_db

        with patch("src.core.database.get_async_db", mock_get_async_db):
            result = await internal_get_my_role(runtime_context={"agent_id": str(agent_id)})

            assert result["success"] is True
            assert result["role"]["type"] == "developer"
            assert result["role"]["name"] == "Senior Developer"
            assert len(result["role"]["suggested_tools"]) == 2


class TestInternalGetPendingEscalations:
    """Tests for internal_get_pending_escalations function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.role_tools import internal_get_pending_escalations

        result = await internal_get_pending_escalations(runtime_context=None)

        assert "error" in result
        assert "Runtime context required" in result["error"]
