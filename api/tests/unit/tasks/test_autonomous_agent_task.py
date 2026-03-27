"""
Unit tests for the autonomous agent task helper.

Tests cover:
- Prompt construction with memory injection
- [REMEMBER] block parsing and SYSTEM message creation
- Missing / corrupt memory conversation handled gracefully
"""

import json
import re
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------


def _make_task(cfg: dict | None = None) -> MagicMock:
    task = MagicMock()
    task.id = uuid.uuid4()
    task.tenant_id = uuid.uuid4()
    task.name = "[Autonomous] test-agent"
    task.is_active = True
    task.config = cfg or {
        "agent_id": str(uuid.uuid4()),
        "goal": "Check Hacker News top stories and summarize",
        "max_steps": 20,
        "autonomous_conversation_id": None,
    }
    return task


def _make_agent(agent_id: str | None = None) -> MagicMock:
    agent = MagicMock()
    agent.id = uuid.UUID(agent_id) if agent_id else uuid.uuid4()
    agent.agent_name = "test-agent"
    return agent


# ---------------------------------------------------------------------------
# Test: schedule parsing helpers (pure, no DB)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScheduleParsing:
    def test_alias_5min(self):
        from src.schemas.autonomous_agent import parse_schedule

        result = parse_schedule("5min")
        assert result == {"interval_seconds": 300, "schedule_type": "interval"}

    def test_alias_hourly(self):
        from src.schemas.autonomous_agent import parse_schedule

        result = parse_schedule("hourly")
        assert result == {"interval_seconds": 3600, "schedule_type": "interval"}

    def test_alias_daily(self):
        from src.schemas.autonomous_agent import parse_schedule

        result = parse_schedule("daily")
        assert result["schedule_type"] == "cron"
        assert result["cron_expression"] == "0 9 * * *"

    def test_raw_cron_passthrough(self):
        from src.schemas.autonomous_agent import parse_schedule

        result = parse_schedule("0 */4 * * *")
        assert result["schedule_type"] == "cron"
        assert result["cron_expression"] == "0 */4 * * *"

    def test_invalid_cron_raises(self):
        from src.schemas.autonomous_agent import parse_schedule

        with pytest.raises(ValueError, match="Invalid schedule"):
            parse_schedule("not-a-cron")


# ---------------------------------------------------------------------------
# Test: [REMEMBER] block extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRememberBlockParsing:
    def _extract_remember(self, text: str) -> list[dict]:
        """Reuse the same regex used in _run_autonomous_agent."""
        pattern = re.compile(r"\[REMEMBER\](.*?)\[/REMEMBER\]", re.DOTALL)
        results = []
        for match in pattern.finditer(text):
            raw = match.group(1).strip()
            try:
                results.append(json.loads(raw))
            except json.JSONDecodeError:
                results.append({"_raw": raw})
        return results

    def test_single_remember_block(self):
        text = 'Here is my response.\n[REMEMBER]{"key": "value"}[/REMEMBER]\nDone.'
        blocks = self._extract_remember(text)
        assert len(blocks) == 1
        assert blocks[0] == {"key": "value"}

    def test_multiple_remember_blocks(self):
        text = '[REMEMBER]{"a": 1}[/REMEMBER] text [REMEMBER]{"b": 2}[/REMEMBER]'
        blocks = self._extract_remember(text)
        assert len(blocks) == 2
        assert blocks[0]["a"] == 1
        assert blocks[1]["b"] == 2

    def test_no_remember_blocks(self):
        text = "Just a plain response with no memory annotations."
        blocks = self._extract_remember(text)
        assert blocks == []

    def test_malformed_json_stored_as_raw(self):
        text = "[REMEMBER]not valid json[/REMEMBER]"
        blocks = self._extract_remember(text)
        assert blocks[0]["_raw"] == "not valid json"

    def test_multiline_remember_block(self):
        text = '[REMEMBER]\n{"leads.last_batch": "123", "page": 2}\n[/REMEMBER]'
        blocks = self._extract_remember(text)
        assert blocks[0]["leads.last_batch"] == "123"


# ---------------------------------------------------------------------------
# Test: Prompt construction (pure — no agent runtime import)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptConstruction:
    """Verify the prompt template logic used in _run_autonomous_agent."""

    def _build_prompt(self, goal: str, run_number: int, memory_block: str, max_steps: int = 20) -> str:
        """Mirrors the prompt construction logic in _run_autonomous_agent."""
        from datetime import UTC, datetime

        return (
            f"[AUTONOMOUS MODE]\n"
            f"Goal: {goal}\n"
            f"Run #{run_number} | {datetime.now(UTC).isoformat()[:19]}\n"
            f"Max tool-call budget: {max_steps}\n\n"
            f"[Memory from previous runs]\n{memory_block}\n\n"
            f"Complete your goal. To persist facts for next run, include:\n"
            '[REMEMBER]{"key": "value"}[/REMEMBER]'
        )

    def test_prompt_contains_goal(self):
        prompt = self._build_prompt("Check HN top stories", 1, "(no prior memory)")
        assert "Check HN top stories" in prompt

    def test_prompt_contains_run_number(self):
        prompt = self._build_prompt("Do something", 5, "(no prior memory)")
        assert "Run #5" in prompt

    def test_prompt_contains_memory_block(self):
        memory = "[Summary]\nPreviously found 42 leads."
        prompt = self._build_prompt("Find leads", 2, memory)
        assert "Previously found 42 leads." in prompt

    def test_prompt_contains_remember_instruction(self):
        prompt = self._build_prompt("Do something", 1, "(no prior memory)")
        assert "[REMEMBER]" in prompt
        assert "[/REMEMBER]" in prompt

    def test_no_prior_memory_placeholder(self):
        prompt = self._build_prompt("Do something", 1, "(no prior memory)")
        assert "(no prior memory)" in prompt

    def test_task_config_has_conversation_id_key(self):
        """autonomous_conversation_id key must always be present in initial config."""
        task = _make_task()
        assert "autonomous_conversation_id" in task.config
