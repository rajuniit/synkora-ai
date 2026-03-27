"""Unit tests for SlackStatusService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.slack.slack_status_service import SlackStatusService


def _make_client(ok: bool = True, error: str | None = None):
    client = MagicMock()
    response = {"ok": ok}
    if error:
        response["error"] = error
    client.api_call = AsyncMock(return_value=response)
    return client


@pytest.mark.unit
class TestSetStatus:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        svc = SlackStatusService(_make_client(ok=True))
        result = await svc.set_status("C123", "1234567890.000100", "is thinking...")
        assert result is True

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_method(self):
        client = _make_client()
        svc = SlackStatusService(client)
        await svc.set_status("C123", "ts.123", "working")
        client.api_call.assert_called_once_with(
            api_method="assistant.threads.setStatus",
            json={"status": "working", "channel_id": "C123", "thread_ts": "ts.123"},
        )

    @pytest.mark.asyncio
    async def test_default_status_is_thinking(self):
        client = _make_client()
        svc = SlackStatusService(client)
        await svc.set_status("C123", "ts.123")
        call_json = client.api_call.call_args[1]["json"]
        assert call_json["status"] == "is thinking..."

    @pytest.mark.asyncio
    async def test_returns_false_when_ok_is_false(self):
        svc = SlackStatusService(_make_client(ok=False, error="some_error"))
        result = await svc.set_status("C123", "ts.123")
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_scope_returns_false(self):
        client = MagicMock()
        client.api_call = AsyncMock(return_value={"ok": False, "error": "missing_scope", "needed": "assistant:write"})
        svc = SlackStatusService(client)
        result = await svc.set_status("C123", "ts.123")
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self):
        client = MagicMock()
        client.api_call = AsyncMock(side_effect=RuntimeError("network error"))
        svc = SlackStatusService(client)
        result = await svc.set_status("C123", "ts.123")
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate(self):
        client = MagicMock()
        client.api_call = AsyncMock(side_effect=Exception("boom"))
        svc = SlackStatusService(client)
        # Should not raise
        await svc.set_status("C123", "ts.123")


@pytest.mark.unit
class TestSetThinking:
    @pytest.mark.asyncio
    async def test_delegates_to_set_status(self):
        client = _make_client()
        svc = SlackStatusService(client)
        result = await svc.set_thinking("C456", "ts.456")
        assert result is True
        call_json = client.api_call.call_args[1]["json"]
        assert call_json["status"] == "is thinking..."
        assert call_json["channel_id"] == "C456"

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        svc = SlackStatusService(_make_client(ok=False, error="ratelimited"))
        result = await svc.set_thinking("C456", "ts.456")
        assert result is False


@pytest.mark.unit
class TestSetGenerating:
    @pytest.mark.asyncio
    async def test_sends_generating_status(self):
        client = _make_client()
        svc = SlackStatusService(client)
        await svc.set_generating("C789", "ts.789")
        call_json = client.api_call.call_args[1]["json"]
        assert "generating" in call_json["status"]

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        svc = SlackStatusService(_make_client(ok=True))
        result = await svc.set_generating("C789", "ts.789")
        assert result is True


@pytest.mark.unit
class TestSetCustomStatus:
    @pytest.mark.asyncio
    async def test_sends_custom_action(self):
        client = _make_client()
        svc = SlackStatusService(client)
        await svc.set_custom_status("C111", "ts.111", "is analyzing...")
        call_json = client.api_call.call_args[1]["json"]
        assert call_json["status"] == "is analyzing..."

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        svc = SlackStatusService(_make_client(ok=True))
        result = await svc.set_custom_status("C111", "ts.111", "searching")
        assert result is True


@pytest.mark.unit
class TestClearStatus:
    @pytest.mark.asyncio
    async def test_sends_empty_status(self):
        client = _make_client()
        svc = SlackStatusService(client)
        await svc.clear_status("C222", "ts.222")
        call_json = client.api_call.call_args[1]["json"]
        assert call_json["status"] == ""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        svc = SlackStatusService(_make_client(ok=True))
        result = await svc.clear_status("C222", "ts.222")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_api_fails(self):
        svc = SlackStatusService(_make_client(ok=False, error="channel_not_found"))
        result = await svc.clear_status("C222", "ts.222")
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_scope_still_returns_false(self):
        client = MagicMock()
        client.api_call = AsyncMock(return_value={"ok": False, "error": "missing_scope"})
        svc = SlackStatusService(client)
        result = await svc.clear_status("C222", "ts.222")
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self):
        client = MagicMock()
        client.api_call = AsyncMock(side_effect=ConnectionError("timeout"))
        svc = SlackStatusService(client)
        result = await svc.clear_status("C222", "ts.222")
        assert result is False
