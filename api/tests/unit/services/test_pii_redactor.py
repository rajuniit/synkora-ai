"""Unit tests for PIIRedactor."""

import pytest

from src.services.security.pii_redactor import PIIRedactionConfig, PIIRedactor


# ---------------------------------------------------------------------------
# PIIRedactionConfig
# ---------------------------------------------------------------------------


class TestPIIRedactionConfig:
    def test_defaults_all_disabled(self):
        cfg = PIIRedactionConfig()
        assert cfg.redact_for_llm is False
        assert cfg.redact_for_response is False
        assert cfg.any_enabled is False

    def test_any_enabled_when_llm(self):
        cfg = PIIRedactionConfig(redact_for_llm=True)
        assert cfg.any_enabled is True

    def test_any_enabled_when_response(self):
        cfg = PIIRedactionConfig(redact_for_response=True)
        assert cfg.any_enabled is True

    def test_from_agent_metadata_none(self):
        cfg = PIIRedactionConfig.from_agent_metadata(None)
        assert cfg.any_enabled is False

    def test_from_agent_metadata_empty(self):
        cfg = PIIRedactionConfig.from_agent_metadata({})
        assert cfg.any_enabled is False

    def test_from_agent_metadata_no_pii_key(self):
        cfg = PIIRedactionConfig.from_agent_metadata({"agentic_config": {}})
        assert cfg.any_enabled is False

    def test_from_agent_metadata_full(self):
        metadata = {
            "pii_redaction": {
                "redact_for_llm": True,
                "redact_for_response": False,
                "patterns": ["email", "phone"],
            }
        }
        cfg = PIIRedactionConfig.from_agent_metadata(metadata)
        assert cfg.redact_for_llm is True
        assert cfg.redact_for_response is False
        assert cfg.patterns == ["email", "phone"]

    def test_from_agent_metadata_coerces_bool(self):
        metadata = {"pii_redaction": {"redact_for_llm": 1, "redact_for_response": 0}}
        cfg = PIIRedactionConfig.from_agent_metadata(metadata)
        assert cfg.redact_for_llm is True
        assert cfg.redact_for_response is False


# ---------------------------------------------------------------------------
# PIIRedactor.redact()
# ---------------------------------------------------------------------------


class TestRedact:
    def _redactor(self, **kwargs) -> PIIRedactor:
        cfg = PIIRedactionConfig(redact_for_llm=True, **kwargs)
        return PIIRedactor(cfg)

    def test_email_replaced(self):
        r = self._redactor()
        result = r.redact("Contact john@example.com today")
        assert "john@example.com" not in result
        assert "[EMAIL_1]" in result

    def test_phone_replaced(self):
        r = self._redactor()
        result = r.redact("Call 555-123-4567 now")
        assert "555-123-4567" not in result
        assert "[PHONE_1]" in result

    def test_ssn_replaced(self):
        r = self._redactor()
        result = r.redact("SSN: 123-45-6789")
        assert "123-45-6789" not in result
        assert "[SSN_1]" in result

    def test_credit_card_replaced(self):
        r = self._redactor()
        result = r.redact("Card: 4111 1111 1111 1111")
        assert "4111 1111 1111 1111" not in result
        assert "[CARD_1]" in result

    def test_ip_replaced(self):
        r = self._redactor()
        result = r.redact("Server at 192.168.1.1")
        assert "192.168.1.1" not in result
        assert "[IP_1]" in result

    def test_same_value_gets_same_token(self):
        r = self._redactor()
        t1 = r.redact("john@example.com")
        t2 = r.redact("john@example.com")
        assert t1 == t2  # idempotent

    def test_different_values_get_different_tokens(self):
        r = self._redactor()
        r.redact("a@example.com")
        r.redact("b@example.com")
        assert r._value_to_token.get("a@example.com") != r._value_to_token.get("b@example.com")

    def test_counters_increment(self):
        r = self._redactor()
        r.redact("a@example.com")
        r.redact("b@example.com")
        assert r._counters.get("EMAIL") == 2

    def test_noop_when_disabled(self):
        cfg = PIIRedactionConfig(redact_for_llm=False)
        r = PIIRedactor(cfg)
        text = "john@example.com"
        assert r.redact(text) == text

    def test_1000_unique_emails_all_distinct_tokens(self):
        r = self._redactor()
        emails = [f"user{i}@example.com" for i in range(1000)]
        text = " ".join(emails)
        redacted = r.redact(text)
        tokens = set(r._value_to_token.values())
        assert len(tokens) == 1000
        for email in emails:
            assert email not in redacted
        # All tokens should be in the redacted text
        for token in tokens:
            assert token in redacted

    def test_pattern_filter_respects_config(self):
        cfg = PIIRedactionConfig(redact_for_llm=True, patterns=["email"])
        r = PIIRedactor(cfg)
        result = r.redact("john@example.com and 555-123-4567")
        assert "[EMAIL_1]" in result
        assert "555-123-4567" in result  # phone not redacted


# ---------------------------------------------------------------------------
# PIIRedactor.restore()
# ---------------------------------------------------------------------------


class TestRestore:
    def _redactor(self) -> PIIRedactor:
        cfg = PIIRedactionConfig(redact_for_llm=True)
        return PIIRedactor(cfg)

    def test_restore_single(self):
        r = self._redactor()
        redacted = r.redact("john@example.com")
        assert r.restore(redacted) == "john@example.com"

    def test_restore_multiple(self):
        r = self._redactor()
        redacted = r.redact("a@x.com and b@y.com")
        restored = r.restore(redacted)
        assert "a@x.com" in restored
        assert "b@y.com" in restored

    def test_restore_noop_no_tokens(self):
        r = self._redactor()
        assert r.restore("no pii here") == "no pii here"

    def test_restore_1000_tokens_single_pass(self):
        r = self._redactor()
        emails = [f"user{i}@example.com" for i in range(1000)]
        text = " ".join(emails)
        redacted = r.redact(text)
        restored = r.restore(redacted)
        for email in emails:
            assert email in restored


# ---------------------------------------------------------------------------
# PIIRedactor.restore_streaming()
# ---------------------------------------------------------------------------


class TestRestoreStreaming:
    def _redactor(self) -> PIIRedactor:
        cfg = PIIRedactionConfig(redact_for_llm=True)
        return PIIRedactor(cfg)

    def test_complete_token_in_one_chunk(self):
        r = self._redactor()
        r.redact("john@example.com")  # populate token map
        # Manually inject token as if it came from LLM
        r._token_to_value["[EMAIL_1]"] = "john@example.com"
        out = r.restore_streaming("[EMAIL_1] said hello", flush=True)
        assert "john@example.com" in out

    def test_token_split_across_chunks(self):
        r = self._redactor()
        r.redact("john@example.com")
        # "[EMAIL_1]" split: "[EMAIL_" in first chunk, "1]" in second
        out1 = r.restore_streaming("[EMAIL_")
        out2 = r.restore_streaming("1] done", flush=True)
        combined = out1 + out2
        assert "john@example.com" in combined
        assert "[EMAIL_" not in combined

    def test_flush_drains_buffer(self):
        """flush_stream_buffer drains whatever is held back in the buffer.

        Scenario: two chunks where the token is split exactly at the boundary,
        then flush is used instead of a second restore_streaming call.
        """
        r = self._redactor()
        r.redact("john@example.com")
        # First chunk holds back "[EMAIL_" because it looks like an incomplete token
        out1 = r.restore_streaming("[EMAIL_")
        assert out1 == ""
        # Second chunk completes the token; we flush to drain
        r._stream_buffer += "1]"  # simulate receiving the rest
        trailing = r.flush_stream_buffer()
        assert "john@example.com" in trailing
        assert r._stream_buffer == ""

    def test_passthrough_when_no_tokens(self):
        r = self._redactor()
        out = r.restore_streaming("hello world", flush=True)
        assert out == "hello world"

    def test_multiple_chunks_no_token_split(self):
        r = self._redactor()
        r.redact("a@x.com")
        chunks = ["Hello ", "[EMAIL_1]", " world"]
        result = ""
        for i, chunk in enumerate(chunks):
            result += r.restore_streaming(chunk, flush=(i == len(chunks) - 1))
        assert "a@x.com" in result
        assert "[EMAIL_1]" not in result


# ---------------------------------------------------------------------------
# redact_for_response semantics (tokens never injected)
# ---------------------------------------------------------------------------


class TestRedactForResponseOnly:
    def test_redact_noop_when_only_response_flag(self):
        """When only redact_for_response is True, redact() is a no-op (tokens never injected)."""
        cfg = PIIRedactionConfig(redact_for_llm=False, redact_for_response=True)
        r = PIIRedactor(cfg)
        text = "john@example.com"
        assert r.redact(text) == text

    def test_no_tokens_in_map_when_only_response_flag(self):
        cfg = PIIRedactionConfig(redact_for_llm=False, redact_for_response=True)
        r = PIIRedactor(cfg)
        r.redact("john@example.com")
        assert len(r._token_to_value) == 0
