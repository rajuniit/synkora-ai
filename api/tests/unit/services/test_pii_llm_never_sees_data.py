"""
Proof: LLM never sees PII from tool results when PII redaction is enabled.

This test intercepts the actual messages sent to the LLM (the second call, after
tool execution) and asserts that they contain tokens ([PHONE_1], [EMAIL_1], etc.)
instead of real PII values.

Flow being tested:
  User prompt
    → LLM call #1 → returns tool call (e.g. internal_query_database)
    → Tool executes → returns rows with 100 phones + emails
    → PIIRedactor.redact(tool_result_json)   ← the critical step
    → LLM call #2 receives: tool message with [PHONE_1]..[PHONE_N]  ← we verify this
    → LLM responds referencing tokens
    → (optional) restore_streaming() swaps tokens back in response
"""

import json
import re
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.security.pii_redactor import PIIRedactionConfig, PIIRedactor

# ---------------------------------------------------------------------------
# Block the broken httplib2/googleapiclient import that fails in this env
# (pyparsing.DelimitedList missing).  adk_tools is not needed for these tests.
# ---------------------------------------------------------------------------
_fake_registry = MagicMock()
_fake_registry.list_tools.return_value = []
_fake_registry.get_tool.return_value = None

_fake_adk = ModuleType("src.services.agents.adk_tools")
_fake_adk.tool_registry = _fake_registry
sys.modules.setdefault("src.services.agents.adk_tools", _fake_adk)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_client(provider: str = "openai"):
    """Minimal mock LLM client whose provider attribute controls dispatch."""
    client = MagicMock()
    client.provider = provider
    client.config = MagicMock()
    client.config.max_tokens = 4096
    client.config.temperature = 0.7
    return client


def _tool_call_response(tool_name: str, arguments: dict):
    """
    Build a mock LLM response (first call) that requests a tool invocation.
    Mimics the OpenAI / LiteLLM response object shape used by
    _generate_openai_with_tools / _extract_function_calls.
    Uses SimpleNamespace to avoid Python class-body scoping issues.
    """
    from types import SimpleNamespace

    args_str = json.dumps(arguments)
    func = SimpleNamespace(name=tool_name, arguments=args_str)
    tool_call = SimpleNamespace(id="call_abc123", type="function", function=func)
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice], model="gpt-4o")


def _text_response(text: str):
    """Build a mock LLM response (second call) that returns plain text."""
    from types import SimpleNamespace

    message = SimpleNamespace(content=text, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="gpt-4o")


def _build_tool_result(num_rows: int = 100) -> dict:
    """Simulate internal_query_database returning num_rows rows, each with phone + email."""
    rows = [
        {
            "id": i,
            "name": f"User{i}",
            "phone": f"555-{i:03d}-{(i * 7) % 10000:04d}",
            "email": f"user{i}@example.com",
            "ssn": f"{i:03d}-{(i % 99) + 1:02d}-{i * 3:04d}",
        }
        for i in range(1, num_rows + 1)
    ]
    return {
        "success": True,
        "data": rows,
        "row_count": num_rows,
        "columns": ["id", "name", "phone", "email", "ssn"],
        "query_executed": "SELECT * FROM users",
        "connection_name": "test-db",
        "database_type": "postgresql",
    }


# ---------------------------------------------------------------------------
# Core fixture: capture every message list sent to the LLM
# ---------------------------------------------------------------------------


class LLMCallCapture:
    """Records the conversation_history passed to each _generate_*_with_tools call."""

    def __init__(self):
        self.calls: list[list[dict]] = []

    def record(self, history: list[dict]) -> None:
        # Deep-copy so later mutations don't affect our snapshot
        self.calls.append(json.loads(json.dumps(history)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "redact_for_llm,redact_for_response",
    [
        (True, False),  # LLM redaction only — tokens restored in response
        (True, True),  # Both — LLM sees tokens, user sees tokens
        (False, True),  # Response-only — after fix, LLM also gets tokens (bug was here)
    ],
)
async def test_llm_never_sees_pii_in_tool_result(redact_for_llm, redact_for_response):
    """
    Prove that the conversation_history passed to LLM call #2 (after tool execution)
    contains PII tokens, NOT real phone/email/SSN values, for all redaction flag combos.
    """
    from src.services.agents.function_calling import FunctionCallingHandler

    pii_config = PIIRedactionConfig(
        redact_for_llm=redact_for_llm,
        redact_for_response=redact_for_response,
        patterns=["email", "phone", "ssn"],
    )
    pii_redactor = PIIRedactor(pii_config)

    llm_client = _make_llm_client(provider="openai")
    capture = LLMCallCapture()

    # First LLM call → tool request; second LLM call → final text answer.
    call_count = 0

    async def fake_generate_openai(history, temperature, max_tokens):
        nonlocal call_count
        capture.record(history)
        call_count += 1
        if call_count == 1:
            return _tool_call_response("internal_query_database", {"connection_id": "abc", "query": "SELECT *"})
        return _text_response("Here are the results with all user data.")

    handler = FunctionCallingHandler(
        llm_client=llm_client,
        tools=["internal_query_database"],
        pii_redactor=pii_redactor,
    )
    # Inject a fake tool definition so the handler enters the tool-calling loop
    handler.available_tools = [{"name": "internal_query_database", "description": "Query DB", "parameters": {}}]

    # Wire the mock LLM dispatcher
    handler._generate_openai_with_tools = fake_generate_openai

    # Make the tool executor return our fake DB rows
    tool_result = _build_tool_result(num_rows=100)

    with patch.object(
        handler,
        "_execute_functions",
        new_callable=AsyncMock,
        return_value=[MagicMock(result=tool_result, name="internal_query_database")],
    ):
        events = []
        async for event in handler.generate_with_functions_stream(
            prompt="Show me all users with their contact info.",
            temperature=0.7,
            max_tokens=4096,
            max_iterations=5,
        ):
            events.append(event)

    # We must have made exactly 2 LLM calls
    assert call_count == 2, f"Expected 2 LLM calls, got {call_count}"

    # ── Inspect call #2: this is what the LLM receives after tool execution ──
    second_call_history = capture.calls[1]

    # Find the tool result message
    tool_messages = [m for m in second_call_history if m.get("role") == "tool"]
    assert tool_messages, "No tool result message found in second LLM call"

    tool_content = tool_messages[0]["content"]

    # ── Assert: no real PII in the tool content sent to LLM ──
    real_phones = re.findall(r"\b555-\d{3}-\d{4}\b", tool_content)
    real_emails = re.findall(r"\buser\d+@example\.com\b", tool_content)
    real_ssns = re.findall(r"\b\d{3}-\d{2}-\d{4}\b", tool_content)

    assert not real_phones, (
        f"LLM received {len(real_phones)} real phone numbers! "
        f"First: {real_phones[0]}. redact_for_llm={redact_for_llm}, redact_for_response={redact_for_response}"
    )
    assert not real_emails, (
        f"LLM received {len(real_emails)} real email addresses! "
        f"First: {real_emails[0]}. redact_for_llm={redact_for_llm}, redact_for_response={redact_for_response}"
    )
    assert not real_ssns, (
        f"LLM received {len(real_ssns)} real SSNs! "
        f"First: {real_ssns[0]}. redact_for_llm={redact_for_llm}, redact_for_response={redact_for_response}"
    )

    # ── Assert: tokens ARE present ──
    phone_tokens = re.findall(r"\[PHONE_\d+\]", tool_content)
    email_tokens = re.findall(r"\[EMAIL_\d+\]", tool_content)

    assert phone_tokens, (
        f"No PHONE tokens found in tool content sent to LLM. "
        f"redact_for_llm={redact_for_llm}, redact_for_response={redact_for_response}"
    )
    assert email_tokens, (
        f"No EMAIL tokens found in tool content sent to LLM. "
        f"redact_for_llm={redact_for_llm}, redact_for_response={redact_for_response}"
    )

    # All 100 rows should have their phones and emails tokenised
    assert len(phone_tokens) == 100, f"Expected 100 PHONE tokens, got {len(phone_tokens)}"
    assert len(email_tokens) == 100, f"Expected 100 EMAIL tokens, got {len(email_tokens)}"


@pytest.mark.asyncio
async def test_no_redaction_when_disabled():
    """
    When PII redaction is disabled the LLM receives the raw tool result (no tokens).
    This proves the fix doesn't affect agents that have redaction off.
    """
    from src.services.agents.function_calling import FunctionCallingHandler

    # No redactor at all
    llm_client = _make_llm_client(provider="openai")
    capture = LLMCallCapture()
    call_count = 0

    async def fake_generate_openai(history, temperature, max_tokens):
        nonlocal call_count
        capture.record(history)
        call_count += 1
        if call_count == 1:
            return _tool_call_response("internal_query_database", {"connection_id": "abc", "query": "SELECT *"})
        return _text_response("Here are the results.")

    handler = FunctionCallingHandler(
        llm_client=llm_client,
        tools=["internal_query_database"],
        pii_redactor=None,  # disabled
    )
    handler.available_tools = [{"name": "internal_query_database", "description": "Query DB", "parameters": {}}]
    handler._generate_openai_with_tools = fake_generate_openai

    tool_result = _build_tool_result(num_rows=5)

    with patch.object(
        handler,
        "_execute_functions",
        new_callable=AsyncMock,
        return_value=[MagicMock(result=tool_result, name="internal_query_database")],
    ):
        async for _ in handler.generate_with_functions_stream(
            prompt="Show me users.", temperature=0.7, max_tokens=4096, max_iterations=5
        ):
            pass

    second_call_history = capture.calls[1]
    tool_messages = [m for m in second_call_history if m.get("role") == "tool"]
    tool_content = tool_messages[0]["content"]

    # Real phones MUST be present (no redaction)
    real_phones = re.findall(r"\b555-\d{3}-\d{4}\b", tool_content)
    assert len(real_phones) == 5, f"Expected 5 real phones when redaction is off, got {len(real_phones)}"

    # No tokens should exist
    tokens = re.findall(r"\[(?:PHONE|EMAIL|SSN)_\d+\]", tool_content)
    assert not tokens, f"Unexpected tokens found when redaction is disabled: {tokens}"


@pytest.mark.asyncio
async def test_all_100_rows_redacted_not_just_one():
    """
    Regression test for the original bug: only 1 phone was being redacted.
    Verifies all 100 are tokenised when redact_for_response=True (even without redact_for_llm).
    """
    from src.services.agents.function_calling import FunctionCallingHandler

    # This is the exact config the user reported as buggy
    pii_config = PIIRedactionConfig(redact_for_llm=False, redact_for_response=True)
    pii_redactor = PIIRedactor(pii_config)

    llm_client = _make_llm_client(provider="openai")
    capture = LLMCallCapture()
    call_count = 0

    async def fake_generate_openai(history, temperature, max_tokens):
        nonlocal call_count
        capture.record(history)
        call_count += 1
        if call_count == 1:
            return _tool_call_response("internal_query_database", {"query": "SELECT *"})
        return _text_response("Done.")

    handler = FunctionCallingHandler(
        llm_client=llm_client,
        tools=["internal_query_database"],
        pii_redactor=pii_redactor,
    )
    handler.available_tools = [{"name": "internal_query_database", "description": "Query DB", "parameters": {}}]
    handler._generate_openai_with_tools = fake_generate_openai

    with patch.object(
        handler,
        "_execute_functions",
        new_callable=AsyncMock,
        return_value=[MagicMock(result=_build_tool_result(num_rows=100), name="internal_query_database")],
    ):
        async for _ in handler.generate_with_functions_stream(
            prompt="List all users.", temperature=0.7, max_tokens=4096, max_iterations=5
        ):
            pass

    tool_content = next(m["content"] for m in capture.calls[1] if m.get("role") == "tool")

    phone_tokens = re.findall(r"\[PHONE_\d+\]", tool_content)
    real_phones = re.findall(r"\b555-\d{3}-\d{4}\b", tool_content)

    assert len(phone_tokens) == 100, (
        f"Bug regression: expected 100 PHONE tokens, got {len(phone_tokens)}. "
        f"Real phones still present: {len(real_phones)}"
    )
    assert len(real_phones) == 0, (
        f"Bug regression: LLM still sees {len(real_phones)} real phone numbers "
        f"when redact_for_response=True (should be 0)"
    )
