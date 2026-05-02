"""Unit tests for ContextSummarizer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.agents.context_summarizer import ContextSummarizer


def _msgs(*pairs):
    """Build a list of {role, content} dicts from (role, content) tuples."""
    return [{"role": r, "content": c} for r, c in pairs]


@pytest.mark.unit
class TestFormatMessages:
    def setup_method(self):
        self.svc = ContextSummarizer()

    def test_formats_role_and_content(self):
        msgs = _msgs(("user", "hello"), ("assistant", "hi"))
        result = self.svc._format_messages(msgs)
        assert "[User]: hello" in result
        assert "[Assistant]: hi" in result

    def test_roles_are_capitalised(self):
        msgs = _msgs(("system", "context"))
        result = self.svc._format_messages(msgs)
        assert "[System]:" in result

    def test_long_content_truncated_at_1000(self):
        long = "x" * 2000
        msgs = _msgs(("user", long))
        result = self.svc._format_messages(msgs)
        assert "..." in result
        # The content part should be capped (1000 chars + "...")
        assert len(result) < 2000

    def test_empty_messages_returns_empty(self):
        assert self.svc._format_messages([]) == ""

    def test_messages_separated_by_double_newline(self):
        msgs = _msgs(("user", "a"), ("assistant", "b"))
        result = self.svc._format_messages(msgs)
        assert "\n\n" in result


@pytest.mark.unit
class TestSimpleSummarize:
    def setup_method(self):
        self.svc = ContextSummarizer()

    def test_returns_string(self):
        msgs = _msgs(("user", "Hello"), ("assistant", "Hi"))
        result = self.svc._simple_summarize(msgs, max_length=200)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_message_count(self):
        msgs = _msgs(("user", "A"), ("assistant", "B"), ("user", "C"))
        result = self.svc._simple_summarize(msgs, 200)
        assert "3" in result

    def test_includes_initial_request(self):
        msgs = _msgs(("user", "Please help me deploy"), ("assistant", "Sure"))
        result = self.svc._simple_summarize(msgs, 200)
        assert "deploy" in result

    def test_includes_latest_topic_when_multiple_user_messages(self):
        msgs = _msgs(("user", "First topic"), ("assistant", "reply"), ("user", "Second topic"))
        result = self.svc._simple_summarize(msgs, 200)
        assert "Second topic" in result

    def test_detects_action_keywords_in_assistant(self):
        msgs = _msgs(("user", "Do the task"), ("assistant", "I'll complete this task for you."))
        result = self.svc._simple_summarize(msgs, 200)
        assert "Actions taken" in result

    def test_truncates_to_max_length(self):
        msgs = _msgs(("user", "x" * 500))
        result = self.svc._simple_summarize(msgs, max_length=10)  # 10 words ≈ 40 chars
        assert len(result) <= 50  # 10 words * 4 chars + "..."

    def test_no_assistant_messages_handled(self):
        msgs = _msgs(("user", "a question"))
        result = self.svc._simple_summarize(msgs, 200)
        assert isinstance(result, str)


@pytest.mark.unit
class TestSummarizeMessagesNoLLM:
    """Tests for the fallback path (no LLM client)."""

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty_string(self):
        svc = ContextSummarizer(llm_client=None)
        result = await svc.summarize_messages([])
        assert result == ""

    @pytest.mark.asyncio
    async def test_falls_back_to_simple_when_no_client(self):
        svc = ContextSummarizer(llm_client=None)
        msgs = _msgs(("user", "test question"), ("assistant", "test answer"))
        result = await svc.summarize_messages(msgs)
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
class TestSummarizeMessagesWithLLM:
    @pytest.mark.asyncio
    async def test_calls_llm_generate_content(self):
        client = MagicMock()
        client.generate_content = AsyncMock(return_value="LLM summary")
        svc = ContextSummarizer(llm_client=client)

        msgs = _msgs(("user", "hi"), ("assistant", "hello"))
        result = await svc.summarize_messages(msgs)

        assert result == "LLM summary"
        client.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_simple(self):
        client = MagicMock()
        client.generate_content = AsyncMock(side_effect=RuntimeError("LLM down"))
        svc = ContextSummarizer(llm_client=client)

        msgs = _msgs(("user", "hi"), ("assistant", "hello"))
        result = await svc.summarize_messages(msgs)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_uses_incremental_prompt_when_previous_summary_in_prefix(self):
        client = MagicMock()
        client.generate_content = AsyncMock(return_value="updated summary")
        svc = ContextSummarizer(llm_client=client)

        msgs = _msgs(("user", "new info"))
        prefix = "Previous summary:\nOld summary text\n\nNew messages to incorporate:\n"
        await svc.summarize_messages(msgs, context_prefix=prefix)

        call_args = client.generate_content.call_args
        prompt = call_args[0][0]
        assert "Previous Summary" in prompt or "Previous summary" in prompt

    @pytest.mark.asyncio
    async def test_uses_technical_prompt_type(self):
        client = MagicMock()
        client.generate_content = AsyncMock(return_value="technical summary")
        svc = ContextSummarizer(llm_client=client)

        msgs = _msgs(("user", "debug this"))
        await svc.summarize_messages(msgs, prompt_type="technical")

        prompt = client.generate_content.call_args[0][0]
        assert "PROBLEM DESCRIPTION" in prompt or "technical" in prompt.lower()

    @pytest.mark.asyncio
    async def test_context_prefix_prepended_when_no_previous_summary(self):
        client = MagicMock()
        client.generate_content = AsyncMock(return_value="ok")
        svc = ContextSummarizer(llm_client=client)

        msgs = _msgs(("user", "test"))
        await svc.summarize_messages(msgs, context_prefix="Extra context: ")

        prompt = client.generate_content.call_args[0][0]
        assert "Extra context" in prompt


@pytest.mark.unit
class TestSummarizeWithContext:
    @pytest.mark.asyncio
    async def test_returns_dict_with_required_keys(self):
        svc = ContextSummarizer(llm_client=None)
        msgs = _msgs(("user", "topic"), ("assistant", "response"))
        result = await svc.summarize_with_context(msgs)

        assert "summary" in result
        assert "context_type" in result
        assert "original_message_count" in result
        assert "compression_ratio" in result
        assert "important_points" in result
        assert "timestamp" in result
        assert "had_existing_summary" in result

    @pytest.mark.asyncio
    async def test_message_count_correct(self):
        svc = ContextSummarizer(llm_client=None)
        msgs = _msgs(("user", "a"), ("assistant", "b"), ("user", "c"))
        result = await svc.summarize_with_context(msgs)
        assert result["original_message_count"] == 3

    @pytest.mark.asyncio
    async def test_had_existing_summary_false_by_default(self):
        svc = ContextSummarizer(llm_client=None)
        result = await svc.summarize_with_context(_msgs(("user", "hi")))
        assert result["had_existing_summary"] is False

    @pytest.mark.asyncio
    async def test_had_existing_summary_true_when_provided(self):
        svc = ContextSummarizer(llm_client=None)
        result = await svc.summarize_with_context(_msgs(("user", "hi")), existing_summary="Old summary")
        assert result["had_existing_summary"] is True

    @pytest.mark.asyncio
    async def test_compression_ratio_between_zero_and_one(self):
        svc = ContextSummarizer(llm_client=None)
        msgs = _msgs(("user", "x" * 500), ("assistant", "y" * 500))
        result = await svc.summarize_with_context(msgs)
        assert 0 <= result["compression_ratio"] <= 1.0

    @pytest.mark.asyncio
    async def test_important_points_passed_through(self):
        svc = ContextSummarizer(llm_client=None)
        points = ["point A", "point B"]
        result = await svc.summarize_with_context(_msgs(("user", "hi")), important_points=points)
        assert result["important_points"] == points


@pytest.mark.unit
class TestShouldSummarize:
    def setup_method(self):
        self.svc = ContextSummarizer()

    def test_returns_true_when_message_count_exceeds_threshold(self):
        msgs = _msgs(*[("user", "x") for _ in range(31)])
        assert self.svc.should_summarize(msgs, threshold_messages=30) is True

    def test_returns_false_when_below_threshold(self):
        msgs = _msgs(("user", "a"), ("assistant", "b"))
        assert self.svc.should_summarize(msgs, threshold_messages=30) is False

    def test_returns_true_when_estimated_tokens_exceed_threshold(self):
        # TokenCounter (tiktoken) is available so the fallback chars//4 is never
        # reached. Patch the class method to control the token count directly.
        msgs = _msgs(("user", "x"))
        with patch("src.services.agents.token_counter.TokenCounter.count_messages_tokens", return_value=60000):
            assert self.svc.should_summarize(msgs, threshold_messages=1000, threshold_tokens=50000) is True

    def test_empty_messages_returns_false(self):
        assert self.svc.should_summarize([], threshold_messages=30) is False


@pytest.mark.unit
class TestEstimateSummaryTokens:
    def setup_method(self):
        self.svc = ContextSummarizer()

    def test_returns_integer(self):
        msgs = _msgs(("user", "hello world"))
        result = self.svc.estimate_summary_tokens(msgs)
        assert isinstance(result, int)

    def test_compression_ratio_applied(self):
        # Patch TokenCounter so we get a deterministic base count (100 tokens)
        # regardless of tiktoken's BPE encoding of repeated characters.
        # Expected: int(100 * 0.1) = 10
        msgs = _msgs(("user", "x"))
        with patch("src.services.agents.token_counter.TokenCounter.count_messages_tokens", return_value=100):
            result = self.svc.estimate_summary_tokens(msgs, compression_ratio=0.1)
        assert result == 10

    def test_empty_messages_returns_zero(self):
        result = self.svc.estimate_summary_tokens([])
        assert result == 0
