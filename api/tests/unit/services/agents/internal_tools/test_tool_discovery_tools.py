"""
Tests for tool_discovery_tools.py - Tool Discovery

Tests the meta-tool for searching available tools and listing categories.
"""

from unittest.mock import MagicMock

import pytest


class TestNormalizeText:
    """Tests for _normalize_text helper function."""

    def test_lowercases(self):
        from src.services.agents.internal_tools.tool_discovery_tools import _normalize_text

        assert _normalize_text("Hello World") == "hello world"

    def test_removes_punctuation(self):
        from src.services.agents.internal_tools.tool_discovery_tools import _normalize_text

        result = _normalize_text("hello.world!")
        assert "." not in result
        assert "!" not in result


class TestCalculateRelevanceScore:
    """Tests for _calculate_relevance_score function."""

    def test_returns_higher_score_for_name_match(self):
        from src.services.agents.internal_tools.tool_discovery_tools import _calculate_relevance_score

        score = _calculate_relevance_score("slack", "internal_slack_send_message", "Send a message to Slack")
        assert score > 0.0

    def test_returns_zero_for_no_match(self):
        from src.services.agents.internal_tools.tool_discovery_tools import _calculate_relevance_score

        score = _calculate_relevance_score("xyz123", "internal_slack_send", "Send Slack message")
        assert score == 0.0

    def test_caps_at_one(self):
        from src.services.agents.internal_tools.tool_discovery_tools import _calculate_relevance_score

        score = _calculate_relevance_score(
            "slack send message channel", "internal_slack_send_message", "Send a slack message to a channel"
        )
        assert score <= 1.0


class TestInternalSearchAvailableTools:
    """Tests for internal_search_available_tools function."""

    @pytest.mark.asyncio
    async def test_requires_query(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        result = await internal_search_available_tools(query="")
        assert result["success"] is False
        assert "Query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_when_no_tools_available(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        result = await internal_search_available_tools(query="slack", runtime_context=None)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_finds_matching_tools(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        mock_runtime = MagicMock()
        mock_runtime.all_available_tools = [
            {"name": "internal_slack_send_message", "description": "Send a message to Slack channel"},
            {"name": "internal_gmail_send_email", "description": "Send an email via Gmail"},
        ]
        result = await internal_search_available_tools(query="slack message", runtime_context=mock_runtime)
        assert result["success"] is True
        assert result["count"] >= 1
        assert any("slack" in t["name"] for t in result["tools"])

    @pytest.mark.asyncio
    async def test_skips_discovery_tool_itself(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        mock_runtime = MagicMock()
        mock_runtime.all_available_tools = [
            {"name": "internal_search_available_tools", "description": "Search for tools"},
            {"name": "internal_slack_send_message", "description": "Send a slack message"},
        ]
        result = await internal_search_available_tools(query="search tools", runtime_context=mock_runtime)
        tool_names = [t["name"] for t in result.get("tools", [])]
        assert "internal_search_available_tools" not in tool_names

    @pytest.mark.asyncio
    async def test_uses_config_when_no_runtime_context(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        config = {
            "_all_available_tools": [
                {"name": "internal_slack_send_message", "description": "Send Slack message"},
            ]
        }
        result = await internal_search_available_tools(query="slack", config=config, runtime_context=None)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        mock_runtime = MagicMock()
        mock_runtime.all_available_tools = [
            {"name": "internal_slack_send_message", "description": "Send Slack message"},
        ]
        result = await internal_search_available_tools(query="xyznonexistent", runtime_context=mock_runtime)
        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_limits_results(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_search_available_tools

        mock_runtime = MagicMock()
        mock_runtime.all_available_tools = [
            {"name": f"internal_slack_tool_{i}", "description": "Slack tool"} for i in range(20)
        ]
        result = await internal_search_available_tools(query="slack", limit=5, runtime_context=mock_runtime)
        assert len(result["tools"]) <= 5


class TestInternalListToolCategories:
    """Tests for internal_list_tool_categories function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_no_tools(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_list_tool_categories

        result = await internal_list_tool_categories(runtime_context=None)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_groups_tools_by_category(self):
        from src.services.agents.internal_tools.tool_discovery_tools import internal_list_tool_categories

        mock_runtime = MagicMock()
        mock_runtime.all_available_tools = [
            {"name": "internal_slack_send_message", "description": ""},
            {"name": "internal_slack_list_channels", "description": ""},
            {"name": "internal_gmail_send_email", "description": ""},
        ]
        result = await internal_list_tool_categories(runtime_context=mock_runtime)
        assert result["success"] is True
        assert result["total_categories"] >= 2
        assert result["total_tools"] == 3
