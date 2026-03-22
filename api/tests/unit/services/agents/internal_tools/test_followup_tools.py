"""
Tests for followup_tools.py - Followup Item Management

Tests the followup tracking system for managing followup items
via Slack and email.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEnsureUserIdFormat:
    """Tests for _ensure_user_id_format helper function."""

    def test_adds_at_to_user_ids(self):
        from src.services.agents.internal_tools.followup_tools import _ensure_user_id_format

        result = _ensure_user_id_format("user U07V0LB1CDD")
        assert "@U07V0LB1CDD" in result

    def test_handles_none(self):
        from src.services.agents.internal_tools.followup_tools import _ensure_user_id_format

        assert _ensure_user_id_format(None) is None

    def test_does_not_double_at(self):
        from src.services.agents.internal_tools.followup_tools import _ensure_user_id_format

        result = _ensure_user_id_format("@U07V0LB1CDD")
        assert "@@" not in result


class TestInternalCreateFollowupItem:
    """Tests for internal_create_followup_item function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id_and_tenant_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_create_followup_item

        result = await internal_create_followup_item(
            title="Test",
            initial_message="Hello",
            source_type="slack_message",
            source_id="123",
            runtime_context=None,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_requires_both_ids_in_context(self):
        from src.services.agents.internal_tools.followup_tools import internal_create_followup_item

        result = await internal_create_followup_item(
            title="Test",
            initial_message="Hello",
            source_type="slack_message",
            source_id="123",
            runtime_context={"agent_id": None, "tenant_id": None},
        )
        assert result["success"] is False


class TestInternalListPendingFollowups:
    """Tests for internal_list_pending_followups function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_list_pending_followups

        result = await internal_list_pending_followups(runtime_context=None)
        assert result["success"] is False
        assert "agent_id" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_agent_id_in_context(self):
        from src.services.agents.internal_tools.followup_tools import internal_list_pending_followups

        result = await internal_list_pending_followups(runtime_context={})
        assert result["success"] is False


class TestInternalSendFollowupMessage:
    """Tests for internal_send_followup_message function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_send_followup_message

        result = await internal_send_followup_message(
            followup_item_id="123",
            message="Hello",
            runtime_context=None,
        )
        assert result["success"] is False
        assert "agent_id" in result["error"]


class TestInternalMarkFollowupComplete:
    """Tests for internal_mark_followup_complete function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_mark_followup_complete

        result = await internal_mark_followup_complete(
            followup_item_id="123",
            runtime_context=None,
        )
        assert result["success"] is False
        assert "agent_id" in result["error"]


class TestInternalGetFollowupHistory:
    """Tests for internal_get_followup_history function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_get_followup_history

        result = await internal_get_followup_history(
            followup_item_id="123",
            runtime_context=None,
        )
        assert result["success"] is False
        assert "agent_id" in result["error"]


class TestInternalUpdateFollowupPriority:
    """Tests for internal_update_followup_priority function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_update_followup_priority

        result = await internal_update_followup_priority(
            followup_item_id="123",
            priority="high",
            runtime_context=None,
        )
        assert result["success"] is False
        assert "agent_id" in result["error"]


class TestInternalEscalateFollowup:
    """Tests for internal_escalate_followup function."""

    @pytest.mark.asyncio
    async def test_requires_agent_id(self):
        from src.services.agents.internal_tools.followup_tools import internal_escalate_followup

        result = await internal_escalate_followup(
            followup_item_id="123",
            escalation_targets=["user1"],
            runtime_context=None,
        )
        assert result["success"] is False
        assert "agent_id" in result["error"]


class TestInternalSearchSlackMentions:
    """Tests for internal_search_slack_mentions function."""

    @pytest.mark.asyncio
    async def test_delegates_to_slack_search(self):
        from src.services.agents.internal_tools.followup_tools import internal_search_slack_mentions

        with patch(
            "src.services.agents.internal_tools.followup_tools.internal_slack_search_messages",
            new_callable=AsyncMock,
            return_value={"success": True, "messages": []},
        ):
            result = await internal_search_slack_mentions(
                keywords=["deadline"],
                runtime_context=MagicMock(),
            )
            assert result["success"] is True
