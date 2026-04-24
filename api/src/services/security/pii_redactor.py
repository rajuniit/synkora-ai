"""
PII Redactor — per-conversation stateful redaction for tool results.

Supports two independent modes (both opt-in, both default off):
  - redact_for_llm:       Replace PII with tokens before sending tool results to the LLM.
                          Tokens are restored back to original values in the streamed response.
  - redact_for_response:  Strip PII from the final user-facing response (no restoration).
                          Works independently; when combined with redact_for_llm the LLM
                          never sees real PII AND the user never sees it either.

Performance design:
  Redaction:   patterns compiled once at module level; single re.sub pass per pattern.
  Restoration: single compiled _TOKEN_PATTERN regex, one sub pass (O(text_length)),
               O(1) dict lookup per token — scales to thousands of distinct values.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level compiled patterns (compiled once, reused for every call)
# ---------------------------------------------------------------------------

_PII_PATTERNS: dict[str, tuple[re.Pattern, str]] = {
    "email": (
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "EMAIL",
    ),
    "phone": (
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "PHONE",
    ),
    "ssn": (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "SSN",
    ),
    "credit_card": (
        re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        "CARD",
    ),
    "ip_address": (
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        "IP",
    ),
}

# Matches any token produced by redact() — used for single-pass restoration
_TOKEN_PATTERN = re.compile(r"\[(?:EMAIL|PHONE|SSN|CARD|IP)_\d+\]")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class PIIRedactionConfig:
    """Configuration for per-agent PII redaction.  All flags default to False."""

    redact_for_llm: bool = False
    """Replace PII in tool results with tokens before they reach the LLM.
    Tokens are restored to original values in the streamed response shown to users."""

    redact_for_response: bool = False
    """Mask PII in the final response shown to the user (no restoration).
    Works independently of redact_for_llm."""

    patterns: list[str] = field(default_factory=lambda: list(_PII_PATTERNS.keys()))
    """Which PII patterns to activate.  Defaults to all patterns."""

    @property
    def any_enabled(self) -> bool:
        return self.redact_for_llm or self.redact_for_response

    @classmethod
    def from_agent_metadata(cls, metadata: dict | None) -> "PIIRedactionConfig":
        """Build config from agent_metadata dict.  Returns disabled config when absent."""
        cfg = (metadata or {}).get("pii_redaction", {})
        if not cfg:
            return cls()
        return cls(
            redact_for_llm=bool(cfg.get("redact_for_llm", False)),
            redact_for_response=bool(cfg.get("redact_for_response", False)),
            patterns=cfg.get("patterns", list(_PII_PATTERNS.keys())),
        )


# ---------------------------------------------------------------------------
# Redactor
# ---------------------------------------------------------------------------


class PIIRedactor:
    """
    Per-conversation stateful PII redactor.

    Thread safety: instances are created per-request/per-conversation and are
    NOT shared across concurrent requests — no locking is required.
    """

    def __init__(self, config: PIIRedactionConfig) -> None:
        self.config = config
        # Bidirectional maps for token ↔ value
        self._value_to_token: dict[str, str] = {}
        self._token_to_value: dict[str, str] = {}
        # Per-label counters: "EMAIL" → 3  (means 3 distinct emails seen so far)
        self._counters: dict[str, int] = {}
        # Buffer for streaming restoration (holds partial tokens split at chunk boundaries)
        self._stream_buffer: str = ""

    # ------------------------------------------------------------------
    # Redaction (write path)
    # ------------------------------------------------------------------

    def redact(self, text: str) -> str:
        """Replace PII with tokens.  Same value always produces the same token (idempotent).

        Only active when config.redact_for_llm is True.
        """
        if not self.config.redact_for_llm:
            return text

        for pattern_name in self.config.patterns:
            entry = _PII_PATTERNS.get(pattern_name)
            if not entry:
                continue
            regex, label = entry

            def _replacer(m: re.Match, _label: str = label) -> str:
                val = m.group(0)
                existing = self._value_to_token.get(val)
                if existing:
                    return existing
                n = self._counters.get(_label, 0) + 1
                self._counters[_label] = n
                token = f"[{_label}_{n}]"
                self._value_to_token[val] = token
                self._token_to_value[token] = val
                return token

            text = regex.sub(_replacer, text)

        return text

    # ------------------------------------------------------------------
    # Restoration (read path)
    # ------------------------------------------------------------------

    def restore(self, text: str) -> str:
        """Single-pass restoration.  O(text_length) regardless of token count."""
        if not self._token_to_value:
            return text
        return _TOKEN_PATTERN.sub(
            lambda m: self._token_to_value.get(m.group(0), m.group(0)), text
        )

    def restore_streaming(self, chunk: str, *, flush: bool = False) -> str:
        """Buffer partial tokens split across SSE chunk boundaries, then restore.

        Call with flush=True at end-of-stream to drain the buffer.
        """
        self._stream_buffer += chunk

        if not self._token_to_value:
            # No tokens seen yet — pass everything through
            result, self._stream_buffer = self._stream_buffer, ""
            return result

        # Apply full-token restoration on whatever is in the buffer
        self._stream_buffer = _TOKEN_PATTERN.sub(
            lambda m: self._token_to_value.get(m.group(0), m.group(0)),
            self._stream_buffer,
        )

        if flush:
            safe, self._stream_buffer = self._stream_buffer, ""
            return safe

        # Hold back text after the last '[' in case it's an incomplete token.
        # Only withhold if the possible token start is near the end (< 20 chars from end).
        bracket_pos = self._stream_buffer.rfind("[")
        if bracket_pos != -1 and len(self._stream_buffer) - bracket_pos < 20:
            safe = self._stream_buffer[:bracket_pos]
            self._stream_buffer = self._stream_buffer[bracket_pos:]
        else:
            safe, self._stream_buffer = self._stream_buffer, ""

        return safe

    def flush_stream_buffer(self) -> str:
        """Drain any remaining buffered content at end-of-stream."""
        return self.restore_streaming("", flush=True)
